"""Services for project operational domain entities (phases 15-25)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.audit.services import write_audit
from apps.project_management.models import (
    ChangeOrder, MaterialRequest, MaterialRequestLine, ProjectEquipment, ProjectExpense, ProjectInventoryAllocation,
    ProjectInvoice, ProjectIssue, ProjectRisk, QualityInspection, SafetyIncident, SiteReport,
)
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class ProjectOperationError(ValueError):
    pass


class ProjectOperationService:
    model = None
    project_field = "project"

    @classmethod
    def _scope(cls, qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if cls.project_field:
            qs = qs.filter(project__is_archived=False)
            if branch_id:
                qs = qs.filter(project__branch_id=branch_id)
        return qs

    @classmethod
    def list(cls, *, project_id=None, user=None, request=None, branch_id=None, **_):
        qs = cls.model.active_objects()
        if cls.project_field:
            qs = qs.select_related("project")
            if project_id:
                qs = qs.filter(project_id=project_id)
        return cls._scope(qs, user=user, request=request, branch_id=branch_id).order_by("-created_at")

    @classmethod
    def get(cls, *, pk, user=None, request=None):
        return cls._scope(cls.model.active_objects(), user=user, request=request).get(pk=pk)

    @classmethod
    def _clean_payload(cls, payload):
        result = {}
        field_map = {field.name: field for field in cls.model._meta.fields}
        for name, field in field_map.items():
            key = field.attname if field.is_relation else name
            if key not in payload and name not in payload:
                continue
            value = payload.get(key, payload.get(name))
            if field.is_relation:
                result[key] = value or None
            elif field.get_internal_type() == "DateField":
                result[name] = parse_date(str(value)[:10]) if value else None
            elif field.get_internal_type() == "DateTimeField":
                result[name] = parse_datetime(str(value)) if value else None
            elif field.get_internal_type() == "DecimalField":
                result[name] = Decimal(str(value or 0))
            elif isinstance(value, str):
                result[name] = value.strip()
            else:
                result[name] = value
        return result

    @classmethod
    def _validate_related(cls, row):
        project = getattr(row, "project", None)
        if not project:
            return
        for field_name in ("wbs_node", "unit", "site", "task"):
            related = getattr(row, field_name, None)
            if related and getattr(related, "project_id", project.id) != project.id:
                raise ProjectOperationError(f"{field_name.replace('_', ' ').title()} is not part of this project.")

    @classmethod
    @transaction.atomic
    def create(cls, *, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        if cls.project_field:
            project_id = payload.get("project_id")
            if not project_id:
                raise ProjectOperationError("project_id is required.")
            project = ProjectService.get_project(pk=project_id, user=user, request=request)
            payload["tenant_id"] = project.tenant_id
        if cls.model is MaterialRequestLine:
            request_row = MaterialRequest.active_objects().filter(pk=payload.get("request_id")).first()
            if not request_row:
                raise ProjectOperationError("Material request not found.")
            payload["tenant_id"] = request_row.tenant_id
        values = cls._clean_payload(payload)
        values["tenant_id"] = payload.get("tenant_id")
        if cls.project_field:
            values["project_id"] = project.id
        if hasattr(cls.model, "code") and not values.get("code"):
            values["code"] = f"{cls.model.__name__.upper()[:8]}-{cls.model.objects.filter(project_id=project.id).count() + 1:04d}"
        if hasattr(cls.model, "requested_by") and not values.get("requested_by_id"):
            values["requested_by"] = user
        if hasattr(cls.model, "reported_by") and not values.get("reported_by_id"):
            values["reported_by"] = user
        values["created_by"] = user
        row = cls.model(**values)
        cls._validate_related(row)
        if hasattr(row, "status") and row.status not in dict(row.STATUS_CHOICES):
            raise ProjectOperationError(f"Invalid status: {row.status}")
        row.save()
        write_audit(action="create", module="project_management", entity=row, user=user, request=request)
        return row

    @classmethod
    @transaction.atomic
    def update(cls, *, row, data, user=None, request=None):
        values = cls._clean_payload(dict(data or {}))
        values.pop("project_id", None)
        values.pop("tenant_id", None)
        for field, value in values.items():
            setattr(row, field, value)
        cls._validate_related(row)
        row.updated_by = user
        row.save()
        write_audit(action="update", module="project_management", entity=row, user=user, request=request)
        return row

    @classmethod
    @transaction.atomic
    def transition_status(cls, *, row, status, user=None, request=None):
        if not hasattr(row, "STATUS_CHOICES") or status not in dict(row.STATUS_CHOICES):
            raise ProjectOperationError(f"Invalid status: {status}")
        row.status = status
        if isinstance(row, ChangeOrder) and status == "approved":
            row.approved_at = timezone.now()
        row.updated_by = user
        row.save()
        write_audit(action="status", module="project_management", entity=row, user=user, request=request, new_values={"status": status})
        return row

    @classmethod
    def soft_delete(cls, *, row, user=None, request=None):
        row.soft_delete(user=user)
        write_audit(action="delete", module="project_management", entity=row, user=user, request=request)
        return row


def _service(name, model):
    return type(name, (ProjectOperationService,), {"model": model, "project_field": None if model is MaterialRequestLine else "project"})


MaterialRequestService = _service("MaterialRequestService", MaterialRequest)
MaterialRequestLineService = _service("MaterialRequestLineService", MaterialRequestLine)
ProjectEquipmentService = _service("ProjectEquipmentService", ProjectEquipment)
ProjectInventoryAllocationService = _service("ProjectInventoryAllocationService", ProjectInventoryAllocation)


class ProjectInventoryService:
    """Creates project allocations for project-dimensioned purchase receipts."""

    @staticmethod
    def allocate_from_grn(*, purchase_order, lines, user=None, notes=""):
        if not purchase_order.project_id:
            return []
        allocations = []
        for line in lines:
            quantity = Decimal(str(line.quantity_received))
            if quantity <= 0:
                continue
            item = purchase_order.items.select_related("product").get(product_id=line.product_id)
            unit_cost = Decimal(str(line.unit_cost)) if line.unit_cost is not None else Decimal(str(item.unit_cost))
            allocations.append(
                ProjectInventoryAllocation.objects.create(
                    tenant_id=purchase_order.tenant_id,
                    project_id=purchase_order.project_id,
                    wbs_node_id=purchase_order.wbs_node_id,
                    product_id=line.product_id,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    source_type="grn",
                    source_id=purchase_order.id,
                    notes=notes or f"Goods receipt for {purchase_order.order_number}",
                    created_by=user,
                )
            )
        return allocations
ProjectExpenseService = _service("ProjectExpenseService", ProjectExpense)
ChangeOrderService = _service("ChangeOrderService", ChangeOrder)
SiteReportService = _service("SiteReportService", SiteReport)
QualityInspectionService = _service("QualityInspectionService", QualityInspection)
SafetyIncidentService = _service("SafetyIncidentService", SafetyIncident)
ProjectRiskService = _service("ProjectRiskService", ProjectRisk)
ProjectIssueService = _service("ProjectIssueService", ProjectIssue)


class ProjectInvoiceService(ProjectOperationService):
    model = ProjectInvoice
    project_field = "project"

    @classmethod
    @transaction.atomic
    def transition_status(cls, *, row, status, user=None, request=None):
        row = super().transition_status(row=row, status=status, user=user, request=request)
        if status == "issued" and not row.journal_entry_id:
            try:
                row = ProjectAccountingService.post_invoice(
                    invoice=row, user=user, request=request
                )
            except ProjectOperationError:
                # Invoice stays issued; retry via post-accounting endpoint.
                pass
        return row


class ProjectAccountingService:
    """Project billing ↔ central accounting engine (preview + real journal posting)."""

    @staticmethod
    def _resolve_accounts(*, tenant_id, user=None):
        from apps.finance.services.chart_service import ChartService
        from apps.finance.services.mapping_service import MappingService

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)
        return {
            "ar": MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user),
            "revenue": MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant_id, user=user),
            "tax": MappingService.resolve(key="DEFAULT_TAX_PAYABLE", tenant_id=tenant_id, user=user),
        }

    @staticmethod
    def suggest_posting(project_invoice, *, user=None):
        tenant_id = project_invoice.tenant_id or project_invoice.project.tenant_id
        accounts = ProjectAccountingService._resolve_accounts(tenant_id=tenant_id, user=user)
        amount = float(project_invoice.amount or 0)
        tax = float(project_invoice.tax_amount or 0)
        total = float(project_invoice.total_amount or 0)
        lines = [
            {
                "account_id": str(accounts["ar"].id),
                "account_code": accounts["ar"].code,
                "account_name": accounts["ar"].name,
                "debit": total,
                "credit": 0.0,
                "description": f"Accounts receivable for {project_invoice.invoice_number}",
            },
            {
                "account_id": str(accounts["revenue"].id),
                "account_code": accounts["revenue"].code,
                "account_name": accounts["revenue"].name,
                "debit": 0.0,
                "credit": amount,
                "description": f"Project revenue for {project_invoice.invoice_number}",
            },
        ]
        if tax > 0:
            lines.append(
                {
                    "account_id": str(accounts["tax"].id),
                    "account_code": accounts["tax"].code,
                    "account_name": accounts["tax"].name,
                    "debit": 0.0,
                    "credit": tax,
                    "description": f"Tax for {project_invoice.invoice_number}",
                }
            )
        return {
            "source": "project_invoice",
            "invoice_id": str(project_invoice.id),
            "currency": getattr(project_invoice.project, "currency", "USD"),
            "already_posted": bool(project_invoice.journal_entry_id),
            "journal_entry_id": str(project_invoice.journal_entry_id)
            if project_invoice.journal_entry_id
            else None,
            "lines": lines,
            "note": "Preview of central ledger posting (Dr AR / Cr Revenue).",
        }

    @staticmethod
    @transaction.atomic
    def post_invoice(*, invoice, user=None, request=None):
        from apps.finance.services.posting_service import AccountingPostingService, PostingError

        if invoice.journal_entry_id:
            return invoice
        if invoice.status == "draft":
            invoice.status = "issued"
            invoice.save(update_fields=["status", "updated_at"])
        try:
            entry = AccountingPostingService.post_project_invoice(invoice=invoice, user=user)
        except PostingError as exc:
            raise ProjectOperationError(str(exc)) from exc
        if entry is None:
            raise ProjectOperationError("Accounting engine did not create a journal entry.")
        invoice.journal_entry = entry
        invoice.posted_at = timezone.now()
        invoice.updated_by = user
        invoice.save(
            update_fields=["journal_entry", "posted_at", "status", "updated_by", "updated_at"]
        )
        write_audit(
            action="post_accounting",
            module="project_management",
            entity=invoice,
            user=user,
            request=request,
            new_values={"journal_entry_id": str(entry.id), "entry_number": entry.entry_number},
        )
        return invoice
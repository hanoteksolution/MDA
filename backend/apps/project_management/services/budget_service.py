"""Project budget services."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import write_audit
from apps.project_management.models import Project, ProjectBudget, ProjectBudgetLine
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class BudgetError(ValueError):
    pass


class ProjectBudgetService:
    STATUS_TRANSITIONS = {
        ProjectBudget.STATUS_DRAFT: {ProjectBudget.STATUS_SUBMITTED},
        ProjectBudget.STATUS_SUBMITTED: {
            ProjectBudget.STATUS_APPROVED,
            ProjectBudget.STATUS_DRAFT,
        },
        ProjectBudget.STATUS_APPROVED: {ProjectBudget.STATUS_LOCKED},
        ProjectBudget.STATUS_LOCKED: set(),
    }

    @staticmethod
    def _scope_budgets(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(project__branch_id=branch_id)
        qs = qs.filter(project__is_archived=False)
        return qs

    @staticmethod
    def list_budgets(*, project_id=None, user=None, request=None, branch_id=None):
        qs = ProjectBudget.active_objects().select_related("project", "project__branch")
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = ProjectBudgetService._scope_budgets(
            qs, user=user, request=request, branch_id=branch_id
        )
        return qs.order_by("-version")

    @staticmethod
    def get_budget(*, pk, user=None, request=None):
        qs = ProjectBudget.active_objects().select_related("project", "project__branch")
        qs = ProjectBudgetService._scope_budgets(qs, user=user, request=request)
        return qs.prefetch_related("lines").get(pk=pk)

    @staticmethod
    def _next_version(*, project_id) -> int:
        latest = (
            ProjectBudget.objects.filter(project_id=project_id)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        return (latest or 0) + 1

    @staticmethod
    @transaction.atomic
    def create_budget(*, data, user=None, request=None) -> ProjectBudget:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        project_id = payload.get("project_id")
        if not project_id:
            raise BudgetError("project_id is required.")
        project = ProjectService.get_project(pk=project_id, user=user, request=request)
        name = (payload.get("name") or "").strip()
        if not name:
            raise BudgetError("Budget name is required.")

        row = ProjectBudget(
            tenant_id=project.tenant_id,
            project=project,
            version=ProjectBudgetService._next_version(project_id=project.id),
            name=name,
            currency=(payload.get("currency") or project.currency or "USD").strip() or "USD",
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        row.save()
        for idx, line in enumerate(payload.get("lines") or []):
            ProjectBudgetService._upsert_line(
                budget=row,
                data=line,
                sort_order=idx,
                user=user,
            )
        row.recalc_totals()
        row.save(update_fields=["total_planned", "updated_at"])
        write_audit(
            action="create",
            module="project_management",
            entity=row,
            user=user,
            request=request,
            new_values={"project_id": str(project.id), "version": row.version},
        )
        return row

    @staticmethod
    def _upsert_line(*, budget, data, sort_order=0, user=None, line_id=None):
        description = (data.get("description") or "").strip()
        if not description:
            raise BudgetError("Budget line description is required.")
        planned = Decimal(str(data.get("planned_amount") or 0))
        if line_id:
            line = budget.lines.filter(pk=line_id).first()
            if not line:
                raise BudgetError("Budget line not found.")
        else:
            line = ProjectBudgetLine(
                tenant_id=budget.tenant_id,
                budget=budget,
                created_by=user,
            )
        line.category = data.get("category") or ProjectBudgetLine.CAT_OTHER
        line.description = description
        line.planned_amount = planned
        line.committed_amount = Decimal(str(data.get("committed_amount") or line.committed_amount or 0))
        line.actual_amount = Decimal(str(data.get("actual_amount") or line.actual_amount or 0))
        line.sort_order = int(data.get("sort_order") if data.get("sort_order") is not None else sort_order)
        line.notes = (data.get("notes") or "").strip()
        line.updated_by = user
        line.save()
        return line

    @staticmethod
    @transaction.atomic
    def update_budget(*, budget: ProjectBudget, data, user=None, request=None) -> ProjectBudget:
        if budget.status != ProjectBudget.STATUS_DRAFT:
            raise BudgetError("Only draft budgets can be edited.")
        payload = dict(data or {})
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise BudgetError("Budget name is required.")
            budget.name = name
        if "notes" in payload:
            budget.notes = (payload.get("notes") or "").strip()
        if "currency" in payload and payload.get("currency"):
            budget.currency = payload["currency"]
        budget.updated_by = user
        budget.save()
        if "lines" in payload:
            budget.lines.all().delete()
            for idx, line in enumerate(payload.get("lines") or []):
                ProjectBudgetService._upsert_line(
                    budget=budget, data=line, sort_order=idx, user=user
                )
        budget.recalc_totals()
        budget.save(update_fields=["total_planned", "updated_at"])
        write_audit(
            action="update",
            module="project_management",
            entity=budget,
            user=user,
            request=request,
        )
        return budget

    @staticmethod
    @transaction.atomic
    def update_status(*, budget: ProjectBudget, status: str, user=None, request=None) -> ProjectBudget:
        if status not in dict(ProjectBudget.STATUS_CHOICES):
            raise BudgetError(f"Invalid status: {status}")
        allowed = ProjectBudgetService.STATUS_TRANSITIONS.get(budget.status, set())
        if status not in allowed:
            raise BudgetError(f"Invalid transition from '{budget.status}' to '{status}'.")
        budget.status = status
        if status == ProjectBudget.STATUS_APPROVED:
            budget.approved_at = timezone.now()
            budget.is_active = True
            ProjectBudget.objects.filter(project_id=budget.project_id).exclude(pk=budget.pk).update(
                is_active=False
            )
        budget.updated_by = user
        budget.save()
        write_audit(
            action="status",
            module="project_management",
            entity=budget,
            user=user,
            request=request,
            new_values={"status": status},
        )
        return budget

    @staticmethod
    def soft_delete_budget(*, budget: ProjectBudget, user=None, request=None) -> ProjectBudget:
        if budget.status != ProjectBudget.STATUS_DRAFT:
            raise BudgetError("Only draft budgets can be deleted.")
        budget.soft_delete(user=user)
        write_audit(
            action="delete",
            module="project_management",
            entity=budget,
            user=user,
            request=request,
        )
        return budget

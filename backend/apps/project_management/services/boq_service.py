from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import write_audit
from apps.project_management.models import Boq, BoqLine, Project
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope


class BoqError(ValueError):
    pass


class BoqService:
    TRANSITIONS = {"draft": {"submitted"}, "submitted": {"draft", "approved"}, "approved": {"locked"}, "locked": set()}

    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request).filter(project__is_archived=False)
        return qs.filter(project__branch_id=branch_id) if branch_id else qs

    @classmethod
    def list(cls, *, project_id=None, user=None, request=None, branch_id=None):
        qs = cls._scope(Boq.active_objects().select_related("project").prefetch_related("lines"), user=user, request=request, branch_id=branch_id)
        return qs.filter(project_id=project_id) if project_id else qs

    @classmethod
    def get(cls, *, pk, user=None, request=None):
        return cls._scope(Boq.active_objects().select_related("project").prefetch_related("lines"), user=user, request=request).get(pk=pk)

    @staticmethod
    def _line(boq, data, user):
        quantity, unit_rate = Decimal(str(data.get("quantity") or 0)), Decimal(str(data.get("unit_rate") or 0))
        return BoqLine.objects.create(
            tenant_id=boq.tenant_id, boq=boq, created_by=user, item_code=data.get("item_code") or "",
            description=data.get("description") or "", unit_of_measure=data.get("unit_of_measure") or "unit",
            quantity=quantity, unit_rate=unit_rate, amount=quantity * unit_rate,
            category=data.get("category") or "other", sort_order=data.get("sort_order") or 0, notes=data.get("notes") or "",
            wbs_node_id=data.get("wbs_node_id") or None, unit_id=data.get("unit_id") or None,
        )

    @classmethod
    @transaction.atomic
    def create(cls, *, data, user=None, request=None):
        payload = dict(data or {})
        project = ProjectService.get_project(pk=payload.get("project_id"), user=user, request=request)
        version = payload.get("version") or (Boq.objects.filter(project=project).order_by("-version").values_list("version", flat=True).first() or 0) + 1
        boq = Boq.objects.create(tenant_id=project.tenant_id, project=project, version=version, name=payload.get("name") or f"BOQ v{version}", currency=payload.get("currency") or project.currency or "USD", notes=payload.get("notes") or "", created_by=user)
        for index, line in enumerate(payload.get("lines") or []):
            line.setdefault("sort_order", index)
            cls._line(boq, line, user)
        boq.recalc_total(); boq.save(update_fields=["total_amount", "updated_at"])
        write_audit(action="create", module="project_management", entity=boq, user=user, request=request)
        return boq

    @classmethod
    @transaction.atomic
    def update(cls, *, boq, data, user=None, request=None):
        if boq.status != "draft": raise BoqError("Only draft BOQs can be edited.")
        payload = dict(data or {})
        for field in ("name", "currency", "notes"):
            if field in payload: setattr(boq, field, payload[field])
        if "lines" in payload:
            boq.lines.all().delete()
            for index, line in enumerate(payload["lines"]):
                line.setdefault("sort_order", index); cls._line(boq, line, user)
        boq.updated_by = user; boq.recalc_total(); boq.save()
        write_audit(action="update", module="project_management", entity=boq, user=user, request=request)
        return boq

    @classmethod
    def update_status(cls, *, boq, status, user=None, request=None):
        if status not in cls.TRANSITIONS.get(boq.status, set()): raise BoqError(f"Invalid transition from '{boq.status}' to '{status}'.")
        boq.status = status
        if status == "approved":
            boq.approved_at = timezone.now()
            Boq.objects.filter(project=boq.project).exclude(pk=boq.pk).update(is_active=False)
        boq.updated_by = user; boq.save()
        write_audit(action="status", module="project_management", entity=boq, user=user, request=request, new_values={"status": status})
        return boq

    @staticmethod
    def soft_delete(*, boq, user=None, request=None):
        if boq.status != "draft": raise BoqError("Only draft BOQs can be deleted.")
        boq.soft_delete(user=user); write_audit(action="delete", module="project_management", entity=boq, user=user, request=request)

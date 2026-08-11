"""Project milestone services."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.audit.services import write_audit
from apps.project_management.models import ProjectMilestone, WbsNode
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


def _as_date(value):
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value
    return parse_date(str(value)[:10])


class ProjectMilestoneError(ValueError):
    pass


class ProjectMilestoneService:
    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(project__branch_id=branch_id)
        return qs.filter(project__is_archived=False)

    @staticmethod
    def list_milestones(*, project_id=None, search=None, user=None, request=None, branch_id=None):
        qs = ProjectMilestone.active_objects().select_related("project", "wbs_node")
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = ProjectMilestoneService._scope(qs, user=user, request=request, branch_id=branch_id)
        if search:
            term = search.strip()
            qs = qs.filter(
                Q(code__icontains=term) | Q(name__icontains=term) | Q(description__icontains=term)
            )
        return qs.order_by("sort_order", "due_date", "code")

    @staticmethod
    def get_milestone(*, pk, user=None, request=None):
        qs = ProjectMilestone.active_objects().select_related("project", "wbs_node")
        return ProjectMilestoneService._scope(qs, user=user, request=request).get(pk=pk)

    @staticmethod
    def _next_code(*, project_id):
        return f"MS-{ProjectMilestone.objects.filter(project_id=project_id).count() + 1:04d}"

    @staticmethod
    def _wbs_node(*, project, wbs_node_id):
        if not wbs_node_id:
            return None
        row = WbsNode.active_objects().filter(pk=wbs_node_id, project=project).first()
        if not row:
            raise ProjectMilestoneError("WBS node not found for this project.")
        return row

    @staticmethod
    @transaction.atomic
    def create_milestone(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        project_id = payload.get("project_id")
        if not project_id:
            raise ProjectMilestoneError("project_id is required.")
        project = ProjectService.get_project(pk=project_id, user=user, request=request)
        name = (payload.get("name") or "").strip()
        if not name:
            raise ProjectMilestoneError("Milestone name is required.")
        status = payload.get("status") or ProjectMilestone.STATUS_PENDING
        if status not in dict(ProjectMilestone.STATUS_CHOICES):
            raise ProjectMilestoneError(f"Invalid status: {status}")
        row = ProjectMilestone(
            tenant_id=project.tenant_id,
            project=project,
            wbs_node=ProjectMilestoneService._wbs_node(
                project=project, wbs_node_id=payload.get("wbs_node_id")
            ),
            code=(payload.get("code") or "").strip()
            or ProjectMilestoneService._next_code(project_id=project.id),
            name=name,
            description=(payload.get("description") or "").strip(),
            due_date=_as_date(payload.get("due_date")),
            status=status,
            is_critical=bool(payload.get("is_critical", False)),
            sort_order=int(payload.get("sort_order") or 0),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        if not row.code:
            raise ProjectMilestoneError("Milestone code is required.")
        if status == ProjectMilestone.STATUS_ACHIEVED:
            row.completed_at = timezone.now()
        row.save()
        write_audit(
            action="create", module="project_management", entity=row, user=user, request=request,
            new_values={"project_id": str(project.id), "code": row.code},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_milestone(*, milestone, data, user=None, request=None):
        payload = dict(data or {})
        if "name" in payload:
            milestone.name = (payload.get("name") or "").strip()
            if not milestone.name:
                raise ProjectMilestoneError("Milestone name is required.")
        for field in ("code", "description", "notes"):
            if field in payload:
                setattr(milestone, field, (payload.get(field) or "").strip())
        if "code" in payload and not milestone.code:
            raise ProjectMilestoneError("Milestone code is required.")
        if "wbs_node_id" in payload:
            milestone.wbs_node = ProjectMilestoneService._wbs_node(
                project=milestone.project, wbs_node_id=payload.get("wbs_node_id")
            )
        if "due_date" in payload:
            milestone.due_date = _as_date(payload.get("due_date"))
        if "is_critical" in payload:
            milestone.is_critical = bool(payload["is_critical"])
        if "sort_order" in payload:
            milestone.sort_order = int(payload.get("sort_order") or 0)
        milestone.updated_by = user
        milestone.save()
        write_audit(action="update", module="project_management", entity=milestone, user=user, request=request)
        return milestone

    @staticmethod
    @transaction.atomic
    def update_status(*, milestone, status, user=None, request=None):
        if status not in dict(ProjectMilestone.STATUS_CHOICES):
            raise ProjectMilestoneError(f"Invalid status: {status}")
        milestone.status = status
        milestone.completed_at = timezone.now() if status == ProjectMilestone.STATUS_ACHIEVED else None
        milestone.updated_by = user
        milestone.save()
        write_audit(
            action="status", module="project_management", entity=milestone, user=user, request=request,
            new_values={"status": status},
        )
        return milestone

    @staticmethod
    def soft_delete_milestone(*, milestone, user=None, request=None):
        milestone.soft_delete(user=user)
        write_audit(
            action="delete", module="project_management", entity=milestone, user=user, request=request
        )
        return milestone

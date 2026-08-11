"""Project task services."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date

from apps.audit.services import write_audit
from apps.project_management.models import ProjectTask, WbsNode
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


def _as_date(value):
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value
    return parse_date(str(value)[:10])


class ProjectTaskError(ValueError):
    pass


class ProjectTaskService:
    STATUS_TRANSITIONS = {
        ProjectTask.STATUS_TODO: {
            ProjectTask.STATUS_IN_PROGRESS,
            ProjectTask.STATUS_BLOCKED,
            ProjectTask.STATUS_CANCELLED,
        },
        ProjectTask.STATUS_IN_PROGRESS: {
            ProjectTask.STATUS_BLOCKED,
            ProjectTask.STATUS_REVIEW,
            ProjectTask.STATUS_DONE,
            ProjectTask.STATUS_CANCELLED,
        },
        ProjectTask.STATUS_BLOCKED: {
            ProjectTask.STATUS_TODO,
            ProjectTask.STATUS_IN_PROGRESS,
            ProjectTask.STATUS_CANCELLED,
        },
        ProjectTask.STATUS_REVIEW: {
            ProjectTask.STATUS_IN_PROGRESS,
            ProjectTask.STATUS_BLOCKED,
            ProjectTask.STATUS_DONE,
            ProjectTask.STATUS_CANCELLED,
        },
        ProjectTask.STATUS_DONE: {ProjectTask.STATUS_IN_PROGRESS},
        ProjectTask.STATUS_CANCELLED: {ProjectTask.STATUS_TODO},
    }

    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(project__branch_id=branch_id)
        return qs.filter(project__is_archived=False)

    @staticmethod
    def list_tasks(*, project_id=None, search=None, user=None, request=None, branch_id=None):
        qs = ProjectTask.active_objects().select_related("project", "wbs_node", "assignee")
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = ProjectTaskService._scope(qs, user=user, request=request, branch_id=branch_id)
        if search:
            term = search.strip()
            qs = qs.filter(
                Q(task_code__icontains=term)
                | Q(title__icontains=term)
                | Q(description__icontains=term)
            )
        return qs.order_by("sort_order", "task_code")

    @staticmethod
    def get_task(*, pk, user=None, request=None):
        qs = ProjectTask.active_objects().select_related("project", "wbs_node", "assignee")
        return ProjectTaskService._scope(qs, user=user, request=request).get(pk=pk)

    @staticmethod
    def _next_code(*, project_id):
        return f"TASK-{ProjectTask.objects.filter(project_id=project_id).count() + 1:04d}"

    @staticmethod
    def _related_rows(*, project, payload):
        wbs_node = None
        if payload.get("wbs_node_id"):
            wbs_node = WbsNode.active_objects().filter(
                pk=payload["wbs_node_id"], project=project
            ).first()
            if not wbs_node:
                raise ProjectTaskError("WBS node not found for this project.")

        assignee = None
        if payload.get("assignee_id"):
            assignee = get_user_model().objects.filter(pk=payload["assignee_id"]).first()
            if not assignee or getattr(assignee, "tenant_id", project.tenant_id) != project.tenant_id:
                raise ProjectTaskError("Assignee not found for this tenant.")
        return wbs_node, assignee

    @staticmethod
    @transaction.atomic
    def create_task(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        project_id = payload.get("project_id")
        if not project_id:
            raise ProjectTaskError("project_id is required.")
        project = ProjectService.get_project(pk=project_id, user=user, request=request)
        title = (payload.get("title") or "").strip()
        if not title:
            raise ProjectTaskError("Task title is required.")
        wbs_node, assignee = ProjectTaskService._related_rows(project=project, payload=payload)
        row = ProjectTask(
            tenant_id=project.tenant_id,
            project=project,
            wbs_node=wbs_node,
            assignee=assignee,
            task_code=(payload.get("task_code") or "").strip()
            or ProjectTaskService._next_code(project_id=project.id),
            title=title,
            description=(payload.get("description") or "").strip(),
            priority=payload.get("priority") or ProjectTask.PRIORITY_MEDIUM,
            status=payload.get("status") or ProjectTask.STATUS_TODO,
            planned_start=_as_date(payload.get("planned_start")),
            planned_end=_as_date(payload.get("planned_end")),
            actual_start=_as_date(payload.get("actual_start")),
            actual_end=_as_date(payload.get("actual_end")),
            progress_percent=Decimal(str(payload.get("progress_percent") or 0)),
            estimated_hours=Decimal(str(payload.get("estimated_hours") or 0)),
            actual_hours=Decimal(str(payload.get("actual_hours") or 0)),
            sort_order=int(payload.get("sort_order") or 0),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        if row.status not in dict(ProjectTask.STATUS_CHOICES):
            raise ProjectTaskError(f"Invalid status: {row.status}")
        if row.priority not in dict(ProjectTask.PRIORITY_CHOICES):
            raise ProjectTaskError(f"Invalid priority: {row.priority}")
        row.save()
        write_audit(
            action="create", module="project_management", entity=row, user=user, request=request,
            new_values={"project_id": str(project.id), "task_code": row.task_code},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_task(*, task, data, user=None, request=None):
        payload = dict(data or {})
        if "title" in payload:
            task.title = (payload.get("title") or "").strip()
            if not task.title:
                raise ProjectTaskError("Task title is required.")
        for field in ("task_code", "description", "notes"):
            if field in payload:
                setattr(task, field, (payload.get(field) or "").strip())
        if "task_code" in payload and not task.task_code:
            raise ProjectTaskError("Task code is required.")
        if "wbs_node_id" in payload or "assignee_id" in payload:
            related_payload = {
                "wbs_node_id": payload.get("wbs_node_id") if "wbs_node_id" in payload else task.wbs_node_id,
                "assignee_id": payload.get("assignee_id") if "assignee_id" in payload else task.assignee_id,
            }
            task.wbs_node, task.assignee = ProjectTaskService._related_rows(
                project=task.project, payload=related_payload
            )
        for field in ("priority",):
            if field in payload and payload[field]:
                if payload[field] not in dict(ProjectTask.PRIORITY_CHOICES):
                    raise ProjectTaskError(f"Invalid priority: {payload[field]}")
                setattr(task, field, payload[field])
        for field in ("planned_start", "planned_end", "actual_start", "actual_end"):
            if field in payload:
                setattr(task, field, _as_date(payload.get(field)))
        for field in ("progress_percent", "estimated_hours", "actual_hours"):
            if field in payload:
                setattr(task, field, Decimal(str(payload.get(field) or 0)))
        if "sort_order" in payload:
            task.sort_order = int(payload.get("sort_order") or 0)
        task.updated_by = user
        task.save()
        write_audit(action="update", module="project_management", entity=task, user=user, request=request)
        return task

    @staticmethod
    @transaction.atomic
    def update_status(*, task, status, user=None, request=None):
        if status not in dict(ProjectTask.STATUS_CHOICES):
            raise ProjectTaskError(f"Invalid status: {status}")
        if status not in ProjectTaskService.STATUS_TRANSITIONS.get(task.status, set()):
            raise ProjectTaskError(f"Invalid transition from '{task.status}' to '{status}'.")
        task.status = status
        task.updated_by = user
        task.save()
        write_audit(
            action="status", module="project_management", entity=task, user=user, request=request,
            new_values={"status": status},
        )
        return task

    @staticmethod
    def soft_delete_task(*, task, user=None, request=None):
        task.soft_delete(user=user)
        write_audit(action="delete", module="project_management", entity=task, user=user, request=request)
        return task

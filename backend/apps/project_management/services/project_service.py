"""Project Management services."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.audit.services import write_audit
from apps.project_management.models import Project
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() not in {"0", "false", "no", ""}


def _as_date(value):
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value
    return parse_date(str(value)[:10])


class ProjectError(ValueError):
    pass


class ProjectService:
    STATUS_TRANSITIONS = {
        Project.STATUS_DRAFT: {Project.STATUS_PLANNING, Project.STATUS_CANCELLED},
        Project.STATUS_PLANNING: {Project.STATUS_APPROVED, Project.STATUS_CANCELLED},
        Project.STATUS_APPROVED: {Project.STATUS_ACTIVE, Project.STATUS_CANCELLED},
        Project.STATUS_ACTIVE: {
            Project.STATUS_ON_HOLD,
            Project.STATUS_AT_RISK,
            Project.STATUS_DELAYED,
            Project.STATUS_COMPLETED,
            Project.STATUS_CANCELLED,
        },
        Project.STATUS_ON_HOLD: {Project.STATUS_ACTIVE, Project.STATUS_CANCELLED},
        Project.STATUS_AT_RISK: {
            Project.STATUS_ACTIVE,
            Project.STATUS_DELAYED,
            Project.STATUS_CANCELLED,
        },
        Project.STATUS_DELAYED: {
            Project.STATUS_ACTIVE,
            Project.STATUS_COMPLETED,
            Project.STATUS_CANCELLED,
        },
        Project.STATUS_COMPLETED: {Project.STATUS_CLOSED},
        Project.STATUS_CANCELLED: set(),
        Project.STATUS_CLOSED: set(),
    }

    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None, include_archived=False):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise ProjectError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            branch = Branch.active_objects().filter(pk=branch_id).first()
        if not branch:
            raise ProjectError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _next_project_code(*, tenant_id, branch_id) -> str:
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"PRJ-{today}-"
        count = (
            Project.objects.filter(
                tenant_id=tenant_id,
                branch_id=branch_id,
                project_code__startswith=prefix,
            ).count()
            + 1
        )
        return f"{prefix}{count:04d}"

    @staticmethod
    def summary(*, branch_id=None, user=None, request=None) -> dict:
        # Imported here to keep ProjectService usable while model modules initialize.
        from apps.project_management.models import ProjectIssue, ProjectRisk, ProjectTask, ProjectWorker

        qs = ProjectService.list_projects(
            branch_id=branch_id, user=user, request=request, include_archived=False
        )
        active_statuses = {
            Project.STATUS_ACTIVE,
            Project.STATUS_AT_RISK,
            Project.STATUS_DELAYED,
        }
        agg = qs.aggregate(
            total_budget=Sum("budget"),
            total_contract=Sum("contract_value"),
            total_revenue=Sum("expected_revenue"),
            total_cost=Sum("cost_estimate"),
        )
        return {
            "total_projects": qs.count(),
            "active_projects": qs.filter(status__in=active_statuses).count(),
            "completed_projects": qs.filter(status=Project.STATUS_COMPLETED).count(),
            "delayed_projects": qs.filter(status=Project.STATUS_DELAYED).count(),
            "at_risk_projects": qs.filter(
                Q(status=Project.STATUS_AT_RISK) | Q(health=Project.HEALTH_AT_RISK)
            ).count(),
            "total_budget": float(agg["total_budget"] or 0),
            "total_contract_value": float(agg["total_contract"] or 0),
            "total_expected_revenue": float(agg["total_revenue"] or 0),
            "total_cost_estimate": float(agg["total_cost"] or 0),
            "tasks_count": ProjectTask.active_objects().filter(project__in=qs).count(),
            "workers_count": ProjectWorker.active_objects().filter(project__in=qs).count(),
            "open_risks_count": ProjectRisk.active_objects().filter(project__in=qs, status__in=["open", "mitigating"]).count(),
            "open_issues_count": ProjectIssue.active_objects().filter(project__in=qs, status__in=["open", "in_progress"]).count(),
        }

    @staticmethod
    def list_projects(
        *,
        branch_id=None,
        status=None,
        project_type=None,
        search=None,
        include_archived=False,
        user=None,
        request=None,
    ):
        qs = Project.active_objects().select_related(
            "branch", "client", "project_manager", "cost_center"
        )
        qs = ProjectService._scope(
            qs,
            user=user,
            request=request,
            branch_id=branch_id,
            include_archived=include_archived,
        )
        if status:
            qs = qs.filter(status=status)
        if project_type:
            qs = qs.filter(project_type=project_type)
        if search:
            term = search.strip()
            qs = qs.filter(
                Q(name__icontains=term)
                | Q(project_code__icontains=term)
                | Q(owner_name__icontains=term)
                | Q(location__icontains=term)
            )
        return qs.order_by("-created_at")

    @staticmethod
    def get_project(*, pk, user=None, request=None, include_archived=False):
        qs = Project.objects.select_related(
            "branch", "client", "project_manager", "cost_center"
        )
        if include_archived:
            qs = apply_tenant_scope(qs, user=user, request=request)
        else:
            qs = Project.active_objects().select_related(
                "branch", "client", "project_manager", "cost_center"
            )
            qs = ProjectService._scope(
                qs, user=user, request=request, include_archived=False
            )
        return qs.get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_project(*, data, user=None, request=None) -> Project:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = ProjectService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        tenant_id = payload.get("tenant_id") or branch.tenant_id
        name = (payload.get("name") or "").strip()
        if not name:
            raise ProjectError("Project name is required.")
        code = (payload.get("project_code") or "").strip()
        if not code:
            code = ProjectService._next_project_code(tenant_id=tenant_id, branch_id=branch.id)

        row = Project(
            tenant_id=tenant_id,
            branch=branch,
            project_code=code,
            name=name,
            project_type=payload.get("project_type") or Project.TYPE_GENERAL,
            owner_name=(payload.get("owner_name") or "").strip(),
            location=(payload.get("location") or "").strip(),
            description=(payload.get("description") or "").strip(),
            start_date=_as_date(payload.get("start_date")),
            planned_end_date=_as_date(payload.get("planned_end_date")),
            status=Project.STATUS_DRAFT,
            priority=payload.get("priority") or Project.PRIORITY_MEDIUM,
            health=payload.get("health") or Project.HEALTH_UNKNOWN,
            progress_percent=Decimal(str(payload.get("progress_percent") or 0)),
            budget=Decimal(str(payload.get("budget") or 0)),
            contract_value=Decimal(str(payload.get("contract_value") or 0)),
            expected_revenue=Decimal(str(payload.get("expected_revenue") or 0)),
            cost_estimate=Decimal(str(payload.get("cost_estimate") or 0)),
            currency=(payload.get("currency") or "USD").strip() or "USD",
            tax_rate=Decimal(str(payload.get("tax_rate") or 0)),
            payment_terms=(payload.get("payment_terms") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            client_id=payload.get("client_id") or None,
            project_manager_id=payload.get("project_manager_id") or None,
            cost_center_id=payload.get("cost_center_id") or None,
            created_by=user,
        )
        row.recalc_profit_estimate()
        row.save()
        write_audit(
            action="create",
            module="project_management",
            entity=row,
            user=user,
            request=request,
            new_values={"project_code": row.project_code, "name": row.name},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_project(*, project: Project, data, user=None, request=None) -> Project:
        payload = dict(data or {})
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ProjectError("Project name is required.")
            project.name = name
        if "project_code" in payload:
            code = (payload.get("project_code") or "").strip()
            if not code:
                raise ProjectError("Project code is required.")
            project.project_code = code
        if "project_type" in payload and payload.get("project_type"):
            project.project_type = payload["project_type"]
        if "owner_name" in payload:
            project.owner_name = (payload.get("owner_name") or "").strip()
        if "location" in payload:
            project.location = (payload.get("location") or "").strip()
        if "description" in payload:
            project.description = (payload.get("description") or "").strip()
        if "start_date" in payload:
            project.start_date = _as_date(payload.get("start_date"))
        if "planned_end_date" in payload:
            project.planned_end_date = _as_date(payload.get("planned_end_date"))
        if "actual_end_date" in payload:
            project.actual_end_date = _as_date(payload.get("actual_end_date"))
        if "priority" in payload and payload.get("priority"):
            project.priority = payload["priority"]
        if "health" in payload and payload.get("health"):
            project.health = payload["health"]
        if "progress_percent" in payload:
            project.progress_percent = Decimal(str(payload.get("progress_percent") or 0))
        for field in ("budget", "contract_value", "expected_revenue", "cost_estimate"):
            if field in payload:
                setattr(project, field, Decimal(str(payload.get(field) or 0)))
        if "currency" in payload:
            project.currency = (payload.get("currency") or "USD").strip() or "USD"
        if "tax_rate" in payload:
            project.tax_rate = Decimal(str(payload.get("tax_rate") or 0))
        if "payment_terms" in payload:
            project.payment_terms = (payload.get("payment_terms") or "").strip()
        if "notes" in payload:
            project.notes = (payload.get("notes") or "").strip()
        if "client_id" in payload:
            project.client_id = payload.get("client_id") or None
        if "project_manager_id" in payload:
            project.project_manager_id = payload.get("project_manager_id") or None
        if "cost_center_id" in payload:
            project.cost_center_id = payload.get("cost_center_id") or None
        project.recalc_profit_estimate()
        project.updated_by = user
        project.save()
        write_audit(
            action="update",
            module="project_management",
            entity=project,
            user=user,
            request=request,
        )
        return project

    @staticmethod
    @transaction.atomic
    def update_status(*, project: Project, status: str, user=None, request=None) -> Project:
        if status not in dict(Project.STATUS_CHOICES):
            raise ProjectError(f"Invalid status: {status}")
        current = project.status
        allowed = ProjectService.STATUS_TRANSITIONS.get(current, set())
        if status not in allowed:
            raise ProjectError(f"Invalid transition from '{current}' to '{status}'.")
        project.status = status
        if status in (Project.STATUS_COMPLETED, Project.STATUS_CLOSED, Project.STATUS_CANCELLED):
            if not project.actual_end_date:
                project.actual_end_date = timezone.localdate()
        if status == Project.STATUS_AT_RISK:
            project.health = Project.HEALTH_AT_RISK
        project.updated_by = user
        project.save()
        write_audit(
            action="status",
            module="project_management",
            entity=project,
            user=user,
            request=request,
            new_values={"from": current, "to": status},
        )
        return project

    @staticmethod
    def soft_delete_project(*, project: Project, user=None, request=None) -> Project:
        project.is_archived = True
        project.updated_by = user
        project.save(update_fields=["is_archived", "updated_by", "updated_at"])
        project.soft_delete(user=user)
        write_audit(
            action="archive",
            module="project_management",
            entity=project,
            user=user,
            request=request,
        )
        return project

    @staticmethod
    def restore_project(*, project: Project, user=None, request=None) -> Project:
        project.restore()
        project.is_archived = False
        project.updated_by = user
        project.save(update_fields=["is_archived", "updated_by", "updated_at"])
        write_audit(
            action="restore",
            module="project_management",
            entity=project,
            user=user,
            request=request,
        )
        return project

    @staticmethod
    @transaction.atomic
    def duplicate_project(*, project: Project, user=None, request=None) -> Project:
        suffix = timezone.localdate().strftime("%m%d")
        base_code = project.project_code[:30]
        new_code = f"{base_code}-CPY-{suffix}"
        n = 1
        while Project.active_objects().filter(
            tenant_id=project.tenant_id,
            branch_id=project.branch_id,
            project_code=new_code,
        ).exists():
            new_code = f"{base_code}-CPY-{suffix}-{n}"[:40]
            n += 1
        row = Project.objects.create(
            tenant_id=project.tenant_id,
            branch=project.branch,
            project_code=new_code,
            name=f"{project.name} (Copy)",
            project_type=project.project_type,
            owner_name=project.owner_name,
            location=project.location,
            description=project.description,
            start_date=project.start_date,
            planned_end_date=project.planned_end_date,
            status=Project.STATUS_DRAFT,
            priority=project.priority,
            health=Project.HEALTH_UNKNOWN,
            progress_percent=0,
            budget=project.budget,
            contract_value=project.contract_value,
            expected_revenue=project.expected_revenue,
            cost_estimate=project.cost_estimate,
            profit_estimate=project.profit_estimate,
            currency=project.currency,
            tax_rate=project.tax_rate,
            payment_terms=project.payment_terms,
            notes=project.notes,
            client_id=project.client_id,
            project_manager_id=project.project_manager_id,
            cost_center_id=project.cost_center_id,
            created_by=user,
        )
        write_audit(
            action="duplicate",
            module="project_management",
            entity=row,
            user=user,
            request=request,
            new_values={"source_id": str(project.id)},
        )
        return row

from django.db import transaction

from apps.audit.services import write_audit
from apps.project_management.models import Project, ProjectBuilding, ProjectFloor, ProjectSite, ProjectUnit
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope


class ConstructionError(ValueError):
    pass


class ConstructionService:
    MODELS = {"site": ProjectSite, "building": ProjectBuilding, "floor": ProjectFloor, "unit": ProjectUnit}

    @staticmethod
    def _scope(qs, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request).filter(project__is_archived=False)
        return qs.filter(project__branch_id=branch_id) if branch_id else qs

    @classmethod
    def list(cls, kind, *, project_id=None, user=None, request=None, branch_id=None):
        qs = cls._scope(cls.MODELS[kind].active_objects().select_related("project"), user, request, branch_id)
        return qs.filter(project_id=project_id) if project_id else qs

    @classmethod
    def get(cls, kind, *, pk, user=None, request=None):
        return cls._scope(cls.MODELS[kind].active_objects().select_related("project"), user, request).get(pk=pk)

    @classmethod
    @transaction.atomic
    def create(cls, kind, *, data, user=None, request=None):
        payload = dict(data or {})
        project = ProjectService.get_project(pk=payload.pop("project_id", None), user=user, request=request)
        if not (payload.get("code") or "").strip() or not (payload.get("name") or "").strip():
            raise ConstructionError("code and name are required.")
        for field in ("site", "building", "floor"):
            raw = payload.pop(f"{field}_id", None)
            if raw:
                obj = cls.get(field, pk=raw, user=user, request=request)
                if obj.project_id != project.id:
                    raise ConstructionError(f"{field} must belong to the project.")
                payload[field] = obj
        row = cls.MODELS[kind](project=project, tenant_id=project.tenant_id, created_by=user, **payload)
        row.save()
        write_audit(action="create", module="project_management", entity=row, user=user, request=request)
        return row

    @classmethod
    def update(cls, kind, *, row, data, user=None, request=None):
        for key, value in dict(data or {}).items():
            if key in {"project_id", "tenant_id", "id"} or not hasattr(row, key):
                continue
            setattr(row, key, value)
        row.updated_by = user
        row.save()
        write_audit(action="update", module="project_management", entity=row, user=user, request=request)
        return row

    @staticmethod
    def soft_delete(*, row, user=None, request=None):
        row.soft_delete(user=user)
        write_audit(action="delete", module="project_management", entity=row, user=user, request=request)
        return row

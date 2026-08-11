from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils.dateparse import parse_date

from apps.audit.services import write_audit
from apps.project_management.models import DailyWageEntry, ProjectWorker, WorkerAttendance, WorkerRateHistory
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope


class WorkforceError(ValueError):
    pass


class WorkforceService:
    MODELS = {"worker": ProjectWorker, "attendance": WorkerAttendance, "wage": DailyWageEntry}

    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request).filter(project__is_archived=False)
        return qs.filter(project__branch_id=branch_id) if branch_id else qs

    @classmethod
    def list(cls, kind, *, project_id=None, user=None, request=None, branch_id=None):
        related = ("project",) if kind == "worker" else ("project", "worker")
        qs = cls._scope(cls.MODELS[kind].active_objects().select_related(*related), user=user, request=request, branch_id=branch_id)
        return qs.filter(project_id=project_id) if project_id else qs

    @classmethod
    def get(cls, kind, *, pk, user=None, request=None):
        related = ("project",) if kind == "worker" else ("project", "worker")
        return cls._scope(cls.MODELS[kind].active_objects().select_related(*related), user=user, request=request).get(pk=pk)

    @classmethod
    @transaction.atomic
    def create_worker(cls, *, data, user=None, request=None):
        payload = dict(data or {}); project = ProjectService.get_project(pk=payload.pop("project_id", None), user=user, request=request)
        effective_from = payload.pop("effective_from", None)
        if not payload.get("code") or not payload.get("full_name"): raise WorkforceError("code and full_name are required.")
        worker = ProjectWorker.objects.create(tenant_id=project.tenant_id, project=project, created_by=user, **payload)
        if worker.daily_rate:
            WorkerRateHistory.objects.create(tenant_id=project.tenant_id, worker=worker, rate=worker.daily_rate, effective_from=effective_from or date.today(), created_by=user)
        write_audit(action="create", module="project_management", entity=worker, user=user, request=request)
        return worker

    @classmethod
    def update_worker(cls, *, worker, data, user=None, request=None):
        payload = dict(data or {}); old_rate = worker.daily_rate
        for key, value in payload.items():
            if key not in {"project_id", "daily_rate", "effective_from"} and hasattr(worker, key): setattr(worker, key, value)
        if "daily_rate" in payload:
            worker.daily_rate = Decimal(str(payload["daily_rate"]))
            if worker.daily_rate != old_rate:
                WorkerRateHistory.objects.filter(worker=worker, effective_to__isnull=True).update(effective_to=payload.get("effective_from") or date.today())
                WorkerRateHistory.objects.create(tenant_id=worker.tenant_id, worker=worker, rate=worker.daily_rate, effective_from=payload.get("effective_from") or date.today(), created_by=user)
        worker.updated_by = user; worker.save()
        write_audit(action="update", module="project_management", entity=worker, user=user, request=request)
        return worker

    @classmethod
    @transaction.atomic
    def create_attendance(cls, *, data, user=None, request=None):
        payload = dict(data or {}); project = ProjectService.get_project(pk=payload.pop("project_id", None), user=user, request=request)
        worker = cls.get("worker", pk=payload.pop("worker_id", None), user=user, request=request)
        if worker.project_id != project.id: raise WorkforceError("worker must belong to the project.")
        if isinstance(payload.get("work_date"), str):
            payload["work_date"] = parse_date(payload["work_date"])
        if not payload.get("work_date"):
            raise WorkforceError("work_date is required.")
        row = WorkerAttendance.objects.create(tenant_id=project.tenant_id, project=project, worker=worker, rate_applied=worker.daily_rate, created_by=user, **payload)
        write_audit(action="create", module="project_management", entity=row, user=user, request=request)
        return row

    @classmethod
    @transaction.atomic
    def create_wage(cls, *, data, user=None, request=None):
        payload = dict(data or {}); attendance_id = payload.pop("attendance_id", None)
        attendance = cls.get("attendance", pk=attendance_id, user=user, request=request) if attendance_id else None
        project = attendance.project if attendance else ProjectService.get_project(pk=payload.pop("project_id", None), user=user, request=request)
        worker = attendance.worker if attendance else cls.get("worker", pk=payload.pop("worker_id", None), user=user, request=request)
        hours = Decimal(str(payload.get("hours") if payload.get("hours") is not None else (attendance.hours_worked if attendance else 0)))
        rate = attendance.rate_applied if attendance else Decimal(str(payload.get("rate") if payload.get("rate") is not None else worker.daily_rate))
        work_date = payload.get("work_date") or (attendance.work_date if attendance else None)
        if isinstance(work_date, str):
            work_date = parse_date(work_date)
        if not work_date:
            raise WorkforceError("work_date is required.")
        row = DailyWageEntry.objects.create(tenant_id=project.tenant_id, project=project, worker=worker, attendance=attendance, work_date=work_date, hours=hours, rate=rate, amount=hours * rate, notes=payload.get("notes") or "", created_by=user)
        write_audit(action="create", module="project_management", entity=row, user=user, request=request)
        return row

    @classmethod
    def update(cls, kind, *, row, data, user=None, request=None):
        for key, value in dict(data or {}).items():
            if key not in {"project_id", "worker_id", "rate_applied", "rate", "amount"} and hasattr(row, key): setattr(row, key, value)
        row.updated_by = user; row.save()
        write_audit(action="update", module="project_management", entity=row, user=user, request=request)
        return row

    @classmethod
    def update_wage_status(cls, *, wage, status, user=None, request=None):
        allowed = {"draft": {"approved"}, "approved": {"paid"}, "paid": set()}
        if status not in allowed.get(wage.status, set()): raise WorkforceError(f"Invalid transition from '{wage.status}' to '{status}'.")
        wage.status = status; wage.updated_by = user; wage.save()
        write_audit(action="status", module="project_management", entity=wage, user=user, request=request, new_values={"status": status})
        return wage

    @staticmethod
    def soft_delete(*, row, user=None, request=None):
        row.soft_delete(user=user); write_audit(action="delete", module="project_management", entity=row, user=user, request=request)

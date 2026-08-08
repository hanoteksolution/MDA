"""Gym trainers, assignments, and PT sessions (STEP 17)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.gym.models import (
    Member,
    MemberTrainerAssignment,
    PersonalTrainingSession,
    Trainer,
    TrainerSchedule,
    TrainerSpecialty,
)
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


class TrainerError(ValueError):
    pass


class TrainerService:
    @staticmethod
    def list_specialties(*, user=None, request=None):
        qs = TrainerSpecialty.active_objects().filter(is_active=True)
        return apply_tenant_scope(qs, user=user, request=request).order_by("name")

    @staticmethod
    def ensure_specialty(*, code, name=None, user=None, request=None) -> TrainerSpecialty:
        code = (code or "").strip().lower().replace(" ", "_")
        if not code:
            raise TrainerError("Specialty code is required.")
        qs = apply_tenant_scope(
            TrainerSpecialty.active_objects(), user=user, request=request
        )
        existing = qs.filter(code=code).first()
        if existing:
            return existing
        payload = stamp_tenant_id(
            {"code": code, "name": (name or code).strip().title(), "is_active": True},
            user=user,
            request=request,
        )
        if "tenant" in payload or "tenant_id" in payload:
            return TrainerSpecialty.objects.create(**payload, created_by=user)
        tenant = resolve_acting_tenant(user=user, request=request)
        return TrainerSpecialty.objects.create(
            code=code,
            name=(name or code).strip().title(),
            tenant=tenant,
            created_by=user,
        )

    @staticmethod
    def list(*, search=None, status=None, user=None, request=None):
        qs = Trainer.active_objects().prefetch_related("specialties", "schedules")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(code__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        return qs.order_by("full_name")

    @staticmethod
    def get(*, pk, user=None, request=None):
        return TrainerService.list(user=user, request=request).get(pk=pk)

    @staticmethod
    def serialize(trainer: Trainer) -> dict:
        return {
            "id": str(trainer.id),
            "code": trainer.code,
            "full_name": trainer.full_name,
            "email": trainer.email or "",
            "phone": trainer.phone or "",
            "bio": trainer.bio or "",
            "status": trainer.status,
            "hourly_rate": float(trainer.hourly_rate or 0),
            "notes": trainer.notes or "",
            "branch_id": str(trainer.branch_id) if trainer.branch_id else None,
            "branch_name": trainer.branch.name if trainer.branch_id else None,
            "user_id": str(trainer.user_id) if trainer.user_id else None,
            "specialties": [
                {"id": str(s.id), "code": s.code, "name": s.name}
                for s in trainer.specialties.all()
                if s.deleted_at is None
            ],
            "schedules": [
                {
                    "id": str(s.id),
                    "day_of_week": s.day_of_week,
                    "start_time": s.start_time.strftime("%H:%M") if s.start_time else None,
                    "end_time": s.end_time.strftime("%H:%M") if s.end_time else None,
                    "is_active": s.is_active,
                }
                for s in trainer.schedules.all()
                if s.deleted_at is None
            ],
        }

    @staticmethod
    def _next_code(*, tenant_id) -> str:
        n = Trainer.objects.filter(tenant_id=tenant_id).count() + 1
        candidate = f"TR-{n:04d}"
        while Trainer.active_objects().filter(tenant_id=tenant_id, code=candidate).exists():
            n += 1
            candidate = f"TR-{n:04d}"
        return candidate

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> Trainer:
        prepared = {
            "full_name": (data.get("full_name") or "").strip(),
            "email": data.get("email") or "",
            "phone": data.get("phone") or "",
            "bio": data.get("bio") or "",
            "status": data.get("status") or Trainer.STATUS_ACTIVE,
            "notes": data.get("notes") or "",
            "hourly_rate": Decimal(str(data.get("hourly_rate") or 0)),
        }
        if not prepared["full_name"]:
            raise TrainerError("Trainer full name is required.")
        if data.get("tenant"):
            prepared["tenant"] = data["tenant"]
        if data.get("tenant_id"):
            prepared["tenant_id"] = data["tenant_id"]
        prepared = stamp_tenant_id(prepared, user=user, request=request)

        tenant_id = prepared.get("tenant_id") or getattr(prepared.get("tenant"), "pk", None)
        code = (data.get("code") or "").strip()
        if not code:
            if not tenant_id:
                raise TrainerError("Tenant is required.")
            code = TrainerService._next_code(tenant_id=tenant_id)
        prepared["code"] = code

        if data.get("branch_id"):
            branch = apply_tenant_scope(
                Branch.active_objects(), user=user, request=request
            ).filter(pk=data["branch_id"]).first()
            if branch is None and tenant_id:
                branch = Branch.active_objects().filter(
                    pk=data["branch_id"], tenant_id=tenant_id
                ).first()
            if branch is None:
                raise TrainerError("Branch not found.")
            prepared["branch"] = branch

        if tenant_id and Trainer.active_objects().filter(
            tenant_id=tenant_id, code=code
        ).exists():
            raise TrainerError(f"Trainer code '{code}' already exists.")

        trainer = Trainer.objects.create(**prepared, created_by=user)

        specialty_codes = data.get("specialty_codes") or data.get("specialties") or []
        for item in specialty_codes:
            if isinstance(item, dict):
                code = (item.get("code") or item.get("name") or "").strip().lower().replace(" ", "_")
                name = item.get("name") or code
            else:
                code = str(item).strip().lower().replace(" ", "_")
                name = str(item).replace("_", " ").title()
            if not code:
                continue
            spec = TrainerSpecialty.active_objects().filter(
                tenant_id=trainer.tenant_id, code=code
            ).first()
            if not spec:
                spec = TrainerSpecialty.objects.create(
                    code=code,
                    name=name,
                    tenant_id=trainer.tenant_id,
                    created_by=user,
                )
            trainer.specialties.add(spec)

        for slot in data.get("schedules") or []:
            TrainerService._add_schedule(trainer, slot, user=user)

        return trainer

    @staticmethod
    def _add_schedule(trainer: Trainer, slot: dict, *, user=None):
        from datetime import datetime

        start = slot.get("start_time")
        end = slot.get("end_time")
        if isinstance(start, str):
            start = datetime.strptime(start[:5], "%H:%M").time()
        if isinstance(end, str):
            end = datetime.strptime(end[:5], "%H:%M").time()
        if start is None or end is None:
            raise TrainerError("Schedule requires start_time and end_time.")
        if end <= start:
            raise TrainerError("Schedule end_time must be after start_time.")
        return TrainerSchedule.objects.create(
            trainer=trainer,
            day_of_week=int(slot.get("day_of_week", 0)),
            start_time=start,
            end_time=end,
            is_active=bool(slot.get("is_active", True)),
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def update(*, trainer: Trainer, data, user=None, request=None) -> Trainer:
        for key in ("full_name", "email", "phone", "bio", "status", "notes"):
            if key in data:
                setattr(trainer, key, data[key] if data[key] is not None else "")
        if "hourly_rate" in data:
            trainer.hourly_rate = Decimal(str(data.get("hourly_rate") or 0))
        if "code" in data and data["code"]:
            code = str(data["code"]).strip()
            clash = (
                Trainer.active_objects()
                .filter(tenant_id=trainer.tenant_id, code=code)
                .exclude(pk=trainer.pk)
                .exists()
            )
            if clash:
                raise TrainerError(f"Trainer code '{code}' already exists.")
            trainer.code = code
        if "branch_id" in data:
            branch_id = data.get("branch_id") or None
            trainer.branch_id = branch_id
        trainer.updated_by = user
        trainer.save()

        if "specialty_codes" in data or "specialties" in data:
            trainer.specialties.clear()
            for item in data.get("specialty_codes") or data.get("specialties") or []:
                code = item.get("code") if isinstance(item, dict) else str(item)
                name = item.get("name") if isinstance(item, dict) else None
                spec = TrainerSpecialty.active_objects().filter(
                    tenant_id=trainer.tenant_id, code=str(code).lower().replace(" ", "_")
                ).first()
                if not spec:
                    spec = TrainerSpecialty.objects.create(
                        code=str(code).lower().replace(" ", "_"),
                        name=(name or str(code)).title(),
                        tenant_id=trainer.tenant_id,
                        created_by=user,
                    )
                trainer.specialties.add(spec)

        if "schedules" in data:
            for old in trainer.schedules.filter(deleted_at__isnull=True):
                old.soft_delete(user=user)
            for slot in data.get("schedules") or []:
                TrainerService._add_schedule(trainer, slot, user=user)

        return trainer

    @staticmethod
    def soft_delete(*, trainer: Trainer, user=None):
        trainer.soft_delete(user=user)
        return trainer

    @staticmethod
    def summary(*, user=None, request=None):
        qs = apply_tenant_scope(Trainer.active_objects(), user=user, request=request)
        return {
            "total": qs.count(),
            "active": qs.filter(status=Trainer.STATUS_ACTIVE).count(),
            "assignments_active": apply_tenant_scope(
                MemberTrainerAssignment.active_objects().filter(
                    status=MemberTrainerAssignment.STATUS_ACTIVE
                ),
                user=user,
                request=request,
            ).count(),
            "sessions_upcoming": apply_tenant_scope(
                PersonalTrainingSession.active_objects().filter(
                    status=PersonalTrainingSession.STATUS_SCHEDULED,
                    scheduled_at__gte=timezone.now(),
                ),
                user=user,
                request=request,
            ).count(),
        }


class AssignmentService:
    @staticmethod
    def list(*, member_id=None, trainer_id=None, status=None, user=None, request=None):
        qs = MemberTrainerAssignment.active_objects().select_related("member", "trainer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if trainer_id:
            qs = qs.filter(trainer_id=trainer_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-start_date")

    @staticmethod
    def serialize(row: MemberTrainerAssignment) -> dict:
        return {
            "id": str(row.id),
            "member_id": str(row.member_id),
            "member_name": row.member.full_name if row.member_id else "",
            "membership_number": row.member.membership_number if row.member_id else "",
            "trainer_id": str(row.trainer_id),
            "trainer_name": row.trainer.full_name if row.trainer_id else "",
            "status": row.status,
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "notes": row.notes or "",
        }

    @staticmethod
    @transaction.atomic
    def assign(
        *,
        member_id,
        trainer_id,
        start_date=None,
        end_date=None,
        notes="",
        user=None,
        request=None,
    ) -> MemberTrainerAssignment:
        member = apply_tenant_scope(Member.active_objects(), user=user, request=request).get(
            pk=member_id
        )
        trainer = apply_tenant_scope(Trainer.active_objects(), user=user, request=request).get(
            pk=trainer_id
        )
        if trainer.status != Trainer.STATUS_ACTIVE:
            raise TrainerError("Trainer is not active.")
        if member.tenant_id and trainer.tenant_id and member.tenant_id != trainer.tenant_id:
            raise TrainerError("Member and trainer must belong to the same tenant.")

        start = start_date or timezone.localdate()
        if isinstance(start, str):
            start = parse_date(start) or timezone.localdate()
        end = end_date
        if isinstance(end, str) and end:
            end = parse_date(end)
        elif end in ("", None):
            end = None

        existing = MemberTrainerAssignment.active_objects().filter(
            member=member,
            trainer=trainer,
            status=MemberTrainerAssignment.STATUS_ACTIVE,
        ).first()
        if existing:
            raise TrainerError("Member is already assigned to this trainer.")

        return MemberTrainerAssignment.objects.create(
            member=member,
            trainer=trainer,
            start_date=start,
            end_date=end,
            notes=notes or "",
            status=MemberTrainerAssignment.STATUS_ACTIVE,
            tenant_id=member.tenant_id or trainer.tenant_id,
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def end(*, assignment: MemberTrainerAssignment, end_date=None, user=None):
        assignment.status = MemberTrainerAssignment.STATUS_ENDED
        assignment.end_date = end_date or timezone.localdate()
        if isinstance(assignment.end_date, str):
            assignment.end_date = parse_date(assignment.end_date) or timezone.localdate()
        assignment.updated_by = user
        assignment.save()
        return assignment


class PTSessionService:
    @staticmethod
    def list(*, member_id=None, trainer_id=None, status=None, user=None, request=None):
        qs = PersonalTrainingSession.active_objects().select_related("member", "trainer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if trainer_id:
            qs = qs.filter(trainer_id=trainer_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-scheduled_at")

    @staticmethod
    def serialize(row: PersonalTrainingSession) -> dict:
        return {
            "id": str(row.id),
            "member_id": str(row.member_id),
            "member_name": row.member.full_name if row.member_id else "",
            "trainer_id": str(row.trainer_id),
            "trainer_name": row.trainer.full_name if row.trainer_id else "",
            "trainer_hourly_rate": float(row.trainer.hourly_rate or 0)
            if row.trainer_id
            else 0.0,
            "assignment_id": str(row.assignment_id) if row.assignment_id else None,
            "scheduled_at": row.scheduled_at.isoformat() if row.scheduled_at else None,
            "duration_minutes": row.duration_minutes,
            "status": row.status,
            "amount_charged": float(row.amount_charged or 0),
            "suggested_amount": float(
                (Decimal(str(row.duration_minutes or 60)) / Decimal("60"))
                * Decimal(str(getattr(row.trainer, "hourly_rate", 0) or 0))
            )
            if row.trainer_id
            else 0.0,
            "invoice_id": str(row.invoice_id) if row.invoice_id else None,
            "payment_reference": row.payment_reference or "",
            "notes": row.notes or "",
        }

    @staticmethod
    @transaction.atomic
    def schedule(
        *,
        member_id,
        trainer_id,
        scheduled_at,
        duration_minutes=60,
        assignment_id=None,
        notes="",
        user=None,
        request=None,
    ) -> PersonalTrainingSession:
        member = apply_tenant_scope(Member.active_objects(), user=user, request=request).get(
            pk=member_id
        )
        trainer = apply_tenant_scope(Trainer.active_objects(), user=user, request=request).get(
            pk=trainer_id
        )
        when = scheduled_at
        if isinstance(when, str):
            when = parse_datetime(when)
        if when is None:
            raise TrainerError("scheduled_at is required.")

        assignment = None
        if assignment_id:
            assignment = apply_tenant_scope(
                MemberTrainerAssignment.active_objects(), user=user, request=request
            ).filter(pk=assignment_id).first()
        else:
            assignment = MemberTrainerAssignment.active_objects().filter(
                member=member,
                trainer=trainer,
                status=MemberTrainerAssignment.STATUS_ACTIVE,
            ).first()

        return PersonalTrainingSession.objects.create(
            member=member,
            trainer=trainer,
            assignment=assignment,
            scheduled_at=when,
            duration_minutes=int(duration_minutes or 60),
            notes=notes or "",
            status=PersonalTrainingSession.STATUS_SCHEDULED,
            tenant_id=member.tenant_id or trainer.tenant_id,
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def set_status(*, session: PersonalTrainingSession, status: str, user=None):
        valid = {c[0] for c in PersonalTrainingSession.STATUS_CHOICES}
        if status not in valid:
            raise TrainerError(f"Invalid session status: {status}")
        session.status = status
        session.updated_by = user
        session.save(update_fields=["status", "updated_by", "updated_at"])
        return session

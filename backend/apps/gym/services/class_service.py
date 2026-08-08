"""Gym classes + capacity-safe booking with waitlist (STEP 18)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.gym.models import (
    ClassBooking,
    ClassSchedule,
    GymClass,
    Member,
    Trainer,
)
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class ClassError(ValueError):
    pass


class ClassService:
    @staticmethod
    def list_classes(*, search=None, is_active=None, user=None, request=None):
        qs = GymClass.active_objects().select_related("default_trainer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs.order_by("name")

    @staticmethod
    def serialize_class(obj: GymClass) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "description": obj.description or "",
            "default_capacity": obj.default_capacity,
            "duration_minutes": obj.duration_minutes,
            "drop_in_price": float(obj.drop_in_price or 0),
            "default_trainer_id": str(obj.default_trainer_id) if obj.default_trainer_id else None,
            "default_trainer_name": obj.default_trainer.full_name if obj.default_trainer_id else None,
            "is_active": obj.is_active,
        }

    @staticmethod
    @transaction.atomic
    def create_class(*, data, user=None, request=None) -> GymClass:
        code = (data.get("code") or "").strip().lower().replace(" ", "_")
        name = (data.get("name") or "").strip()
        if not code or not name:
            raise ClassError("code and name are required.")
        payload = {
            "code": code,
            "name": name,
            "description": data.get("description") or "",
            "default_capacity": int(data.get("default_capacity") or 20),
            "duration_minutes": int(data.get("duration_minutes") or 60),
            "drop_in_price": Decimal(str(data.get("drop_in_price") or 0)),
            "is_active": bool(data.get("is_active", True)),
        }
        if data.get("tenant"):
            payload["tenant"] = data["tenant"]
        if data.get("tenant_id"):
            payload["tenant_id"] = data["tenant_id"]
        payload = stamp_tenant_id(payload, user=user, request=request)
        tenant_id = payload.get("tenant_id") or getattr(payload.get("tenant"), "pk", None)
        if tenant_id and GymClass.active_objects().filter(
            tenant_id=tenant_id, code=code
        ).exists():
            raise ClassError(f"Class code '{code}' already exists.")
        if data.get("default_trainer_id"):
            trainer = apply_tenant_scope(
                Trainer.active_objects(), user=user, request=request
            ).filter(pk=data["default_trainer_id"]).first()
            if trainer is None and tenant_id:
                trainer = Trainer.active_objects().filter(
                    pk=data["default_trainer_id"], tenant_id=tenant_id
                ).first()
            if trainer is None:
                raise ClassError("Trainer not found.")
            payload["default_trainer"] = trainer
        if payload["default_capacity"] < 1:
            raise ClassError("default_capacity must be at least 1.")
        return GymClass.objects.create(**payload, created_by=user)

    @staticmethod
    def serialize_schedule(sched: ClassSchedule) -> dict:
        confirmed = sched.bookings.filter(
            deleted_at__isnull=True, status=ClassBooking.STATUS_CONFIRMED
        ).count()
        waitlisted = sched.bookings.filter(
            deleted_at__isnull=True, status=ClassBooking.STATUS_WAITLISTED
        ).count()
        return {
            "id": str(sched.id),
            "gym_class_id": str(sched.gym_class_id),
            "class_name": sched.gym_class.name if sched.gym_class_id else "",
            "class_code": sched.gym_class.code if sched.gym_class_id else "",
            "drop_in_price": float(
                getattr(sched.gym_class, "drop_in_price", 0) or 0
            )
            if sched.gym_class_id
            else 0.0,
            "trainer_id": str(sched.trainer_id) if sched.trainer_id else None,
            "trainer_name": sched.trainer.full_name if sched.trainer_id else None,
            "branch_id": str(sched.branch_id) if sched.branch_id else None,
            "starts_at": sched.starts_at.isoformat() if sched.starts_at else None,
            "ends_at": sched.ends_at.isoformat() if sched.ends_at else None,
            "capacity": sched.capacity,
            "confirmed_count": confirmed,
            "waitlisted_count": waitlisted,
            "spots_remaining": max(0, sched.capacity - confirmed),
            "status": sched.status,
            "notes": sched.notes or "",
        }

    @staticmethod
    def list_schedules(
        *,
        gym_class_id=None,
        upcoming_only=True,
        status=None,
        user=None,
        request=None,
    ):
        qs = ClassSchedule.active_objects().select_related(
            "gym_class", "trainer", "branch"
        ).prefetch_related("bookings")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if gym_class_id:
            qs = qs.filter(gym_class_id=gym_class_id)
        if status:
            qs = qs.filter(status=status)
        elif upcoming_only:
            qs = qs.filter(
                status=ClassSchedule.STATUS_SCHEDULED,
                starts_at__gte=timezone.now() - timedelta(hours=1),
            )
        return qs.order_by("starts_at")

    @staticmethod
    @transaction.atomic
    def create_schedule(*, data, user=None, request=None) -> ClassSchedule:
        gym_class_id = data.get("gym_class_id") or data.get("class_id")
        if not gym_class_id:
            raise ClassError("gym_class_id is required.")
        gym_class = apply_tenant_scope(
            GymClass.active_objects(), user=user, request=request
        ).get(pk=gym_class_id)

        starts_at = data.get("starts_at")
        if isinstance(starts_at, str):
            starts_at = parse_datetime(starts_at)
        if starts_at is None:
            raise ClassError("starts_at is required.")

        ends_at = data.get("ends_at")
        if isinstance(ends_at, str):
            ends_at = parse_datetime(ends_at)
        if ends_at is None:
            ends_at = starts_at + timedelta(minutes=int(gym_class.duration_minutes))

        if ends_at <= starts_at:
            raise ClassError("ends_at must be after starts_at.")

        capacity = int(data.get("capacity") or gym_class.default_capacity)
        if capacity < 1:
            raise ClassError("capacity must be at least 1.")

        trainer = None
        trainer_id = data.get("trainer_id") or gym_class.default_trainer_id
        if trainer_id:
            trainer = apply_tenant_scope(
                Trainer.active_objects(), user=user, request=request
            ).filter(pk=trainer_id).first()
            if trainer is None and gym_class.tenant_id:
                trainer = Trainer.active_objects().filter(
                    pk=trainer_id, tenant_id=gym_class.tenant_id
                ).first()

        branch = None
        if data.get("branch_id"):
            branch = apply_tenant_scope(
                Branch.active_objects(), user=user, request=request
            ).filter(pk=data["branch_id"]).first()

        return ClassSchedule.objects.create(
            gym_class=gym_class,
            trainer=trainer,
            branch=branch,
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=capacity,
            status=ClassSchedule.STATUS_SCHEDULED,
            notes=data.get("notes") or "",
            tenant_id=gym_class.tenant_id,
            created_by=user,
        )


class BookingService:
    @staticmethod
    def serialize(booking: ClassBooking) -> dict:
        drop_in = Decimal("0")
        if booking.schedule_id and booking.schedule.gym_class_id:
            drop_in = Decimal(str(booking.schedule.gym_class.drop_in_price or 0))
        return {
            "id": str(booking.id),
            "schedule_id": str(booking.schedule_id),
            "class_name": booking.schedule.gym_class.name if booking.schedule_id else "",
            "starts_at": (
                booking.schedule.starts_at.isoformat()
                if booking.schedule_id and booking.schedule.starts_at
                else None
            ),
            "member_id": str(booking.member_id),
            "member_name": booking.member.full_name if booking.member_id else "",
            "membership_number": booking.member.membership_number if booking.member_id else "",
            "status": booking.status,
            "booked_at": booking.booked_at.isoformat() if booking.booked_at else None,
            "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
            "drop_in_price": float(drop_in),
            "amount_charged": float(booking.amount_charged or 0),
            "invoice_id": str(booking.invoice_id) if booking.invoice_id else None,
            "payment_reference": booking.payment_reference or "",
            "notes": booking.notes or "",
        }

    @staticmethod
    def list(*, schedule_id=None, member_id=None, status=None, user=None, request=None):
        qs = ClassBooking.active_objects().select_related(
            "member", "schedule", "schedule__gym_class"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if schedule_id:
            qs = qs.filter(schedule_id=schedule_id)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("booked_at")

    @staticmethod
    @transaction.atomic
    def book(
        *,
        schedule_id,
        member_id,
        allow_waitlist=True,
        notes="",
        user=None,
        request=None,
    ) -> ClassBooking:
        """Capacity-safe booking. Uses row lock on schedule to prevent overbook."""
        schedule = (
            apply_tenant_scope(ClassSchedule.active_objects(), user=user, request=request)
            .select_for_update()
            .get(pk=schedule_id)
        )
        if schedule.status != ClassSchedule.STATUS_SCHEDULED:
            raise ClassError("This class session is not open for booking.")

        member = apply_tenant_scope(Member.active_objects(), user=user, request=request).get(
            pk=member_id
        )
        if (
            schedule.tenant_id
            and member.tenant_id
            and schedule.tenant_id != member.tenant_id
        ):
            raise ClassError("Member and schedule tenant mismatch.")

        existing = (
            ClassBooking.active_objects()
            .filter(
                schedule=schedule,
                member=member,
                status__in=[
                    ClassBooking.STATUS_CONFIRMED,
                    ClassBooking.STATUS_WAITLISTED,
                ],
            )
            .first()
        )
        if existing:
            raise ClassError("Member already booked for this session.")

        confirmed = (
            ClassBooking.active_objects()
            .filter(schedule=schedule, status=ClassBooking.STATUS_CONFIRMED)
            .count()
        )
        if confirmed < schedule.capacity:
            status = ClassBooking.STATUS_CONFIRMED
        elif allow_waitlist:
            status = ClassBooking.STATUS_WAITLISTED
        else:
            raise ClassError("Class is full.")

        try:
            return ClassBooking.objects.create(
                schedule=schedule,
                member=member,
                status=status,
                notes=notes or "",
                tenant_id=schedule.tenant_id or member.tenant_id,
                created_by=user,
            )
        except IntegrityError as exc:
            raise ClassError("Member already booked for this session.") from exc

    @staticmethod
    @transaction.atomic
    def cancel(*, booking_id=None, booking=None, user=None, request=None) -> ClassBooking:
        if booking is None:
            booking = (
                apply_tenant_scope(
                    ClassBooking.active_objects(), user=user, request=request
                )
                .select_related("schedule")
                .get(pk=booking_id)
            )
        if booking.status == ClassBooking.STATUS_CANCELLED:
            return booking

        was_confirmed = booking.status == ClassBooking.STATUS_CONFIRMED
        schedule = (
            ClassSchedule.active_objects()
            .select_for_update()
            .get(pk=booking.schedule_id)
        )

        booking.status = ClassBooking.STATUS_CANCELLED
        booking.cancelled_at = timezone.now()
        booking.updated_by = user
        booking.save(update_fields=["status", "cancelled_at", "updated_by", "updated_at"])

        if was_confirmed and schedule.status == ClassSchedule.STATUS_SCHEDULED:
            # Promote earliest waitlisted member into a confirmed spot.
            wait = (
                ClassBooking.active_objects()
                .select_for_update()
                .filter(schedule=schedule, status=ClassBooking.STATUS_WAITLISTED)
                .order_by("booked_at")
                .first()
            )
            if wait:
                wait.status = ClassBooking.STATUS_CONFIRMED
                wait.updated_by = user
                wait.save(update_fields=["status", "updated_by", "updated_at"])

        return booking

    @staticmethod
    def summary(*, user=None, request=None):
        sched = apply_tenant_scope(
            ClassSchedule.active_objects().filter(
                status=ClassSchedule.STATUS_SCHEDULED,
                starts_at__gte=timezone.now(),
            ),
            user=user,
            request=request,
        )
        books = apply_tenant_scope(
            ClassBooking.active_objects().filter(
                status__in=[
                    ClassBooking.STATUS_CONFIRMED,
                    ClassBooking.STATUS_WAITLISTED,
                ]
            ),
            user=user,
            request=request,
        )
        return {
            "upcoming_sessions": sched.count(),
            "active_bookings": books.filter(status=ClassBooking.STATUS_CONFIRMED).count(),
            "waitlisted": books.filter(status=ClassBooking.STATUS_WAITLISTED).count(),
            "class_templates": apply_tenant_scope(
                GymClass.active_objects().filter(is_active=True),
                user=user,
                request=request,
            ).count(),
        }

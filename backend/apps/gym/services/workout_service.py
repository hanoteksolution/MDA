"""Gym workouts, assignments, progress logs, and body measurements (STEP 19)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.gym.models import (
    BodyMeasurement,
    Exercise,
    Member,
    MemberWorkoutAssignment,
    Trainer,
    WorkoutDay,
    WorkoutExercise,
    WorkoutPlan,
    WorkoutProgress,
    WorkoutProgressSet,
)
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class WorkoutError(ValueError):
    pass


def _dec(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _resolve_member(*, member_id, user=None, request=None, tenant_id=None) -> Member:
    qs = apply_tenant_scope(Member.active_objects(), user=user, request=request)
    member = qs.filter(pk=member_id).first()
    if member is None and tenant_id:
        member = Member.active_objects().filter(pk=member_id, tenant_id=tenant_id).first()
    if member is None:
        raise WorkoutError("Member not found.")
    return member


def _resolve_plan(*, plan_id, user=None, request=None, tenant_id=None) -> WorkoutPlan:
    qs = apply_tenant_scope(WorkoutPlan.active_objects(), user=user, request=request)
    plan = qs.filter(pk=plan_id).first()
    if plan is None and tenant_id:
        plan = WorkoutPlan.active_objects().filter(pk=plan_id, tenant_id=tenant_id).first()
    if plan is None:
        raise WorkoutError("Workout plan not found.")
    return plan


class ExerciseService:
    @staticmethod
    def list(*, search=None, muscle_group=None, is_active=None, user=None, request=None):
        qs = Exercise.active_objects()
        qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if muscle_group:
            qs = qs.filter(muscle_group__iexact=muscle_group)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs.order_by("name")

    @staticmethod
    def serialize(obj: Exercise) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "description": obj.description or "",
            "muscle_group": obj.muscle_group or "",
            "equipment": obj.equipment or "",
            "is_active": obj.is_active,
        }

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> Exercise:
        code = (data.get("code") or "").strip().lower().replace(" ", "_")
        name = (data.get("name") or "").strip()
        if not code or not name:
            raise WorkoutError("code and name are required.")
        payload = {
            "code": code,
            "name": name,
            "description": data.get("description") or "",
            "muscle_group": (data.get("muscle_group") or "").strip().lower(),
            "equipment": (data.get("equipment") or "").strip(),
            "is_active": bool(data.get("is_active", True)),
        }
        if data.get("tenant"):
            payload["tenant"] = data["tenant"]
        if data.get("tenant_id"):
            payload["tenant_id"] = data["tenant_id"]
        payload = stamp_tenant_id(payload, user=user, request=request)
        tenant_id = payload.get("tenant_id") or getattr(payload.get("tenant"), "pk", None)
        if tenant_id and Exercise.active_objects().filter(tenant_id=tenant_id, code=code).exists():
            raise WorkoutError(f"Exercise code '{code}' already exists.")
        return Exercise.objects.create(**payload, created_by=user)


class WorkoutPlanService:
    @staticmethod
    def list(*, search=None, is_active=None, user=None, request=None):
        qs = WorkoutPlan.active_objects().select_related("trainer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs.order_by("name")

    @staticmethod
    def get(*, pk, user=None, request=None) -> WorkoutPlan:
        qs = WorkoutPlan.active_objects().select_related("trainer").prefetch_related(
            "days__exercises__exercise"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        plan = qs.filter(pk=pk).first()
        if plan is None:
            raise WorkoutError("Workout plan not found.")
        return plan

    @staticmethod
    def serialize_day(day: WorkoutDay) -> dict:
        exercises = [
            WorkoutPlanService.serialize_workout_exercise(we)
            for we in day.exercises.filter(deleted_at__isnull=True).select_related("exercise")
        ]
        return {
            "id": str(day.id),
            "day_number": day.day_number,
            "name": day.name,
            "notes": day.notes or "",
            "exercises": exercises,
        }

    @staticmethod
    def serialize_workout_exercise(we: WorkoutExercise) -> dict:
        return {
            "id": str(we.id),
            "exercise_id": str(we.exercise_id),
            "exercise_name": we.exercise.name if we.exercise_id else "",
            "exercise_code": we.exercise.code if we.exercise_id else "",
            "sort_order": we.sort_order,
            "sets": we.sets,
            "reps": we.reps,
            "duration_seconds": we.duration_seconds,
            "rest_seconds": we.rest_seconds,
            "notes": we.notes or "",
        }

    @staticmethod
    def serialize(plan: WorkoutPlan, *, include_days=False) -> dict:
        data = {
            "id": str(plan.id),
            "code": plan.code,
            "name": plan.name,
            "description": plan.description or "",
            "goal": plan.goal,
            "duration_weeks": plan.duration_weeks,
            "is_active": plan.is_active,
            "trainer_id": str(plan.trainer_id) if plan.trainer_id else None,
            "trainer_name": plan.trainer.full_name if plan.trainer_id else None,
            "day_count": plan.days.filter(deleted_at__isnull=True).count(),
        }
        if include_days:
            days = plan.days.filter(deleted_at__isnull=True).order_by("day_number")
            data["days"] = [WorkoutPlanService.serialize_day(d) for d in days]
        return data

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> WorkoutPlan:
        code = (data.get("code") or "").strip().lower().replace(" ", "_")
        name = (data.get("name") or "").strip()
        if not code or not name:
            raise WorkoutError("code and name are required.")
        payload = {
            "code": code,
            "name": name,
            "description": data.get("description") or "",
            "goal": data.get("goal") or WorkoutPlan.GOAL_GENERAL,
            "duration_weeks": int(data.get("duration_weeks") or 4),
            "is_active": bool(data.get("is_active", True)),
        }
        if data.get("tenant"):
            payload["tenant"] = data["tenant"]
        if data.get("tenant_id"):
            payload["tenant_id"] = data["tenant_id"]
        payload = stamp_tenant_id(payload, user=user, request=request)
        tenant_id = payload.get("tenant_id") or getattr(payload.get("tenant"), "pk", None)
        if tenant_id and WorkoutPlan.active_objects().filter(
            tenant_id=tenant_id, code=code
        ).exists():
            raise WorkoutError(f"Plan code '{code}' already exists.")
        if data.get("trainer_id"):
            trainer = apply_tenant_scope(
                Trainer.active_objects(), user=user, request=request
            ).filter(pk=data["trainer_id"]).first()
            if trainer is None and tenant_id:
                trainer = Trainer.active_objects().filter(
                    pk=data["trainer_id"], tenant_id=tenant_id
                ).first()
            if trainer is None:
                raise WorkoutError("Trainer not found.")
            payload["trainer"] = trainer
        plan = WorkoutPlan.objects.create(**payload, created_by=user)
        for day_data in data.get("days") or []:
            WorkoutPlanService._add_day(
                plan=plan,
                day_data=day_data,
                user=user,
                request=request,
                tenant_id=tenant_id,
            )
        return plan

    @staticmethod
    def _add_day(*, plan, day_data, user=None, request=None, tenant_id=None):
        day_number = int(day_data.get("day_number") or 1)
        name = (day_data.get("name") or f"Day {day_number}").strip()
        day = WorkoutDay.objects.create(
            workout_plan=plan,
            day_number=day_number,
            name=name,
            notes=day_data.get("notes") or "",
            created_by=user,
        )
        for idx, ex_data in enumerate(day_data.get("exercises") or [], start=1):
            exercise_id = ex_data.get("exercise_id")
            if not exercise_id:
                continue
            exercise = apply_tenant_scope(
                Exercise.active_objects(), user=user, request=request
            ).filter(pk=exercise_id).first()
            if exercise is None and tenant_id:
                exercise = Exercise.active_objects().filter(
                    pk=exercise_id, tenant_id=tenant_id
                ).first()
            if exercise is None:
                raise WorkoutError(f"Exercise {exercise_id} not found.")
            WorkoutExercise.objects.create(
                workout_day=day,
                exercise=exercise,
                sort_order=int(ex_data.get("sort_order") or idx),
                sets=int(ex_data.get("sets") or 3),
                reps=str(ex_data.get("reps") or "10"),
                duration_seconds=ex_data.get("duration_seconds"),
                rest_seconds=int(ex_data.get("rest_seconds") or 60),
                notes=ex_data.get("notes") or "",
                created_by=user,
            )
        return day


class AssignmentService:
    @staticmethod
    def list(*, member_id=None, status=None, user=None, request=None):
        qs = MemberWorkoutAssignment.active_objects().select_related(
            "member", "workout_plan", "trainer"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-start_date")

    @staticmethod
    def serialize(obj: MemberWorkoutAssignment) -> dict:
        return {
            "id": str(obj.id),
            "member_id": str(obj.member_id),
            "member_name": obj.member.full_name if obj.member_id else "",
            "workout_plan_id": str(obj.workout_plan_id),
            "plan_name": obj.workout_plan.name if obj.workout_plan_id else "",
            "plan_code": obj.workout_plan.code if obj.workout_plan_id else "",
            "trainer_id": str(obj.trainer_id) if obj.trainer_id else None,
            "trainer_name": obj.trainer.full_name if obj.trainer_id else None,
            "start_date": obj.start_date.isoformat() if obj.start_date else None,
            "end_date": obj.end_date.isoformat() if obj.end_date else None,
            "status": obj.status,
            "notes": obj.notes or "",
        }

    @staticmethod
    @transaction.atomic
    def assign(*, data, user=None, request=None) -> MemberWorkoutAssignment:
        member_id = data.get("member_id")
        plan_id = data.get("workout_plan_id") or data.get("plan_id")
        if not member_id or not plan_id:
            raise WorkoutError("member_id and workout_plan_id are required.")
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if data.get("tenant"):
            tenant_id = data["tenant"].pk
        member = _resolve_member(
            member_id=member_id, user=user, request=request, tenant_id=tenant_id
        )
        plan = _resolve_plan(
            plan_id=plan_id, user=user, request=request, tenant_id=tenant_id or member.tenant_id
        )
        if member.tenant_id and plan.tenant_id and member.tenant_id != plan.tenant_id:
            raise WorkoutError("Member and plan must belong to the same tenant.")
        start = parse_date(data.get("start_date") or "") or timezone.localdate()
        payload = {
            "member": member,
            "workout_plan": plan,
            "start_date": start,
            "status": MemberWorkoutAssignment.STATUS_ACTIVE,
            "notes": data.get("notes") or "",
        }
        if data.get("tenant"):
            payload["tenant"] = data["tenant"]
        elif member.tenant_id:
            payload["tenant_id"] = member.tenant_id
        payload = stamp_tenant_id(payload, user=user, request=request)
        if data.get("trainer_id"):
            trainer = apply_tenant_scope(
                Trainer.active_objects(), user=user, request=request
            ).filter(pk=data["trainer_id"]).first()
            if trainer:
                payload["trainer"] = trainer
        if data.get("end_date"):
            end = parse_date(data["end_date"])
            if end:
                payload["end_date"] = end
        return MemberWorkoutAssignment.objects.create(**payload, created_by=user)


class ProgressService:
    @staticmethod
    def list(*, member_id=None, user=None, request=None):
        qs = WorkoutProgress.active_objects().select_related(
            "member", "assignment", "workout_day"
        ).prefetch_related("sets__exercise")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        return qs.order_by("-completed_at")

    @staticmethod
    def serialize(obj: WorkoutProgress) -> dict:
        return {
            "id": str(obj.id),
            "member_id": str(obj.member_id),
            "member_name": obj.member.full_name if obj.member_id else "",
            "assignment_id": str(obj.assignment_id) if obj.assignment_id else None,
            "workout_day_id": str(obj.workout_day_id) if obj.workout_day_id else None,
            "day_name": obj.workout_day.name if obj.workout_day_id else None,
            "completed_at": obj.completed_at.isoformat() if obj.completed_at else None,
            "duration_minutes": obj.duration_minutes,
            "notes": obj.notes or "",
            "sets": [
                {
                    "id": str(s.id),
                    "exercise_id": str(s.exercise_id),
                    "exercise_name": s.exercise.name if s.exercise_id else "",
                    "set_number": s.set_number,
                    "reps": s.reps,
                    "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None,
                    "notes": s.notes or "",
                }
                for s in obj.sets.filter(deleted_at__isnull=True).select_related("exercise")
            ],
        }

    @staticmethod
    @transaction.atomic
    def log(*, data, user=None, request=None) -> WorkoutProgress:
        member_id = data.get("member_id")
        if not member_id:
            raise WorkoutError("member_id is required.")
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if data.get("tenant"):
            tenant_id = data["tenant"].pk
        member = _resolve_member(
            member_id=member_id, user=user, request=request, tenant_id=tenant_id
        )
        completed_at = parse_datetime(data.get("completed_at") or "")
        if completed_at is None:
            completed_at = timezone.now()
        row_payload = {
            "member": member,
            "completed_at": completed_at,
            "duration_minutes": data.get("duration_minutes"),
            "notes": data.get("notes") or "",
        }
        if data.get("tenant"):
            row_payload["tenant"] = data["tenant"]
        elif member.tenant_id:
            row_payload["tenant_id"] = member.tenant_id
        row_payload = stamp_tenant_id(row_payload, user=user, request=request)
        if data.get("assignment_id"):
            assignment = apply_tenant_scope(
                MemberWorkoutAssignment.active_objects(), user=user, request=request
            ).filter(pk=data["assignment_id"], member_id=member.id).first()
            if assignment:
                row_payload["assignment"] = assignment
        if data.get("workout_day_id"):
            day = WorkoutDay.active_objects().select_related("workout_plan").filter(
                pk=data["workout_day_id"]
            ).first()
            if day and day.workout_plan.tenant_id == member.tenant_id:
                row_payload["workout_day"] = day
        progress = WorkoutProgress.objects.create(**row_payload, created_by=user)
        for set_data in data.get("sets") or []:
            exercise_id = set_data.get("exercise_id")
            if not exercise_id:
                continue
            exercise = apply_tenant_scope(
                Exercise.active_objects(), user=user, request=request
            ).filter(pk=exercise_id).first()
            if exercise is None and member.tenant_id:
                exercise = Exercise.active_objects().filter(
                    pk=exercise_id, tenant_id=member.tenant_id
                ).first()
            if exercise is None:
                continue
            WorkoutProgressSet.objects.create(
                progress=progress,
                exercise=exercise,
                set_number=int(set_data.get("set_number") or 1),
                reps=set_data.get("reps"),
                weight_kg=_dec(set_data.get("weight_kg")),
                notes=set_data.get("notes") or "",
                created_by=user,
            )
        return progress


class BodyMeasurementService:
    @staticmethod
    def list(*, member_id=None, user=None, request=None):
        qs = BodyMeasurement.active_objects().select_related("member")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        return qs.order_by("-measured_at")

    @staticmethod
    def serialize(obj: BodyMeasurement) -> dict:
        return {
            "id": str(obj.id),
            "member_id": str(obj.member_id),
            "member_name": obj.member.full_name if obj.member_id else "",
            "measured_at": obj.measured_at.isoformat() if obj.measured_at else None,
            "weight_kg": float(obj.weight_kg) if obj.weight_kg is not None else None,
            "body_fat_pct": float(obj.body_fat_pct) if obj.body_fat_pct is not None else None,
            "chest_cm": float(obj.chest_cm) if obj.chest_cm is not None else None,
            "waist_cm": float(obj.waist_cm) if obj.waist_cm is not None else None,
            "hips_cm": float(obj.hips_cm) if obj.hips_cm is not None else None,
            "arms_cm": float(obj.arms_cm) if obj.arms_cm is not None else None,
            "thighs_cm": float(obj.thighs_cm) if obj.thighs_cm is not None else None,
            "notes": obj.notes or "",
        }

    @staticmethod
    @transaction.atomic
    def record(*, data, user=None, request=None) -> BodyMeasurement:
        member_id = data.get("member_id")
        if not member_id:
            raise WorkoutError("member_id is required.")
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if data.get("tenant"):
            tenant_id = data["tenant"].pk
        member = _resolve_member(
            member_id=member_id, user=user, request=request, tenant_id=tenant_id
        )
        measured_at = parse_datetime(data.get("measured_at") or "")
        if measured_at is None:
            measured_at = timezone.now()
        row_payload = {
            "member": member,
            "measured_at": measured_at,
            "weight_kg": _dec(data.get("weight_kg")),
            "body_fat_pct": _dec(data.get("body_fat_pct")),
            "chest_cm": _dec(data.get("chest_cm")),
            "waist_cm": _dec(data.get("waist_cm")),
            "hips_cm": _dec(data.get("hips_cm")),
            "arms_cm": _dec(data.get("arms_cm")),
            "thighs_cm": _dec(data.get("thighs_cm")),
            "notes": data.get("notes") or "",
        }
        if data.get("tenant"):
            row_payload["tenant"] = data["tenant"]
        elif member.tenant_id:
            row_payload["tenant_id"] = member.tenant_id
        row_payload = stamp_tenant_id(row_payload, user=user, request=request)
        return BodyMeasurement.objects.create(**row_payload, created_by=user)

    @staticmethod
    def chart_series(*, member_id, metric="weight_kg", user=None, request=None):
        """Return time-series points for a member metric (newest last)."""
        allowed = {
            "weight_kg",
            "body_fat_pct",
            "chest_cm",
            "waist_cm",
            "hips_cm",
            "arms_cm",
            "thighs_cm",
        }
        if metric not in allowed:
            raise WorkoutError(f"Unknown metric '{metric}'.")
        rows = BodyMeasurementService.list(member_id=member_id, user=user, request=request)[
            :50
        ]
        points = []
        for row in reversed(list(rows)):
            val = getattr(row, metric)
            if val is not None:
                points.append(
                    {
                        "date": row.measured_at.date().isoformat(),
                        "value": float(val),
                    }
                )
        return points


class WorkoutSummaryService:
    @staticmethod
    def summary(*, user=None, request=None):
        exercises = apply_tenant_scope(
            Exercise.active_objects().filter(is_active=True), user=user, request=request
        ).count()
        plans = apply_tenant_scope(
            WorkoutPlan.active_objects().filter(is_active=True), user=user, request=request
        ).count()
        assignments = apply_tenant_scope(
            MemberWorkoutAssignment.active_objects().filter(
                status=MemberWorkoutAssignment.STATUS_ACTIVE
            ),
            user=user,
            request=request,
        ).count()
        progress = apply_tenant_scope(
            WorkoutProgress.active_objects(), user=user, request=request
        ).count()
        measurements = apply_tenant_scope(
            BodyMeasurement.active_objects(), user=user, request=request
        ).count()
        return {
            "exercises": exercises,
            "plans": plans,
            "active_assignments": assignments,
            "progress_logs": progress,
            "measurements": measurements,
        }

"""STEP 19 — gym workouts, progress logs, body measurements + tenant privacy."""

import pytest

from apps.gym.services.member_service import MemberService
from apps.gym.services.workout_service import (
    AssignmentService,
    BodyMeasurementService,
    ExerciseService,
    ProgressService,
    WorkoutError,
    WorkoutPlanService,
)
from apps.platform.models import Tenant
from core.tenancy import tenant_context


@pytest.fixture
def wo_env(db):
    tenant = Tenant.objects.create(
        name="Workout Co", slug="workout-co", status=Tenant.STATUS_ACTIVE
    )
    member = MemberService.create(data={"full_name": "Lifter One", "tenant": tenant})
    squat = ExerciseService.create(
        data={
            "code": "squat",
            "name": "Back Squat",
            "muscle_group": "legs",
            "tenant": tenant,
        }
    )
    bench = ExerciseService.create(
        data={
            "code": "bench",
            "name": "Bench Press",
            "muscle_group": "chest",
            "tenant": tenant,
        }
    )
    plan = WorkoutPlanService.create(
        data={
            "code": "push_pull",
            "name": "Push Pull",
            "goal": "strength",
            "tenant": tenant,
            "days": [
                {
                    "day_number": 1,
                    "name": "Push",
                    "exercises": [
                        {"exercise_id": bench.id, "sets": 4, "reps": "8"},
                    ],
                },
                {
                    "day_number": 2,
                    "name": "Legs",
                    "exercises": [
                        {"exercise_id": squat.id, "sets": 5, "reps": "5"},
                    ],
                },
            ],
        }
    )
    return {
        "tenant": tenant,
        "member": member,
        "squat": squat,
        "bench": bench,
        "plan": plan,
    }


@pytest.mark.django_db
def test_create_plan_with_days_and_exercises(wo_env):
    plan = WorkoutPlanService.get(pk=wo_env["plan"].id)
    data = WorkoutPlanService.serialize(plan, include_days=True)
    assert data["day_count"] == 2
    assert len(data["days"]) == 2
    assert data["days"][0]["exercises"][0]["exercise_code"] == "bench"


@pytest.mark.django_db
def test_assign_plan_and_log_progress(wo_env):
    assignment = AssignmentService.assign(
        data={
            "member_id": wo_env["member"].id,
            "workout_plan_id": wo_env["plan"].id,
            "tenant": wo_env["tenant"],
        }
    )
    assert assignment.status == "active"
    day_id = wo_env["plan"].days.first().id
    progress = ProgressService.log(
        data={
            "member_id": wo_env["member"].id,
            "assignment_id": assignment.id,
            "workout_day_id": day_id,
            "duration_minutes": 45,
            "sets": [
                {
                    "exercise_id": wo_env["bench"].id,
                    "set_number": 1,
                    "reps": 8,
                    "weight_kg": "60",
                }
            ],
            "tenant": wo_env["tenant"],
        }
    )
    serialized = ProgressService.serialize(progress)
    assert serialized["duration_minutes"] == 45
    assert len(serialized["sets"]) == 1
    assert serialized["sets"][0]["weight_kg"] == 60.0


@pytest.mark.django_db
def test_body_measurement_chart_series(wo_env):
    BodyMeasurementService.record(
        data={
            "member_id": wo_env["member"].id,
            "weight_kg": "80",
            "measured_at": "2026-01-01T10:00:00Z",
            "tenant": wo_env["tenant"],
        }
    )
    BodyMeasurementService.record(
        data={
            "member_id": wo_env["member"].id,
            "weight_kg": "78.5",
            "measured_at": "2026-02-01T10:00:00Z",
            "tenant": wo_env["tenant"],
        }
    )
    points = BodyMeasurementService.chart_series(
        member_id=wo_env["member"].id, metric="weight_kg"
    )
    assert len(points) == 2
    assert points[0]["value"] == 80.0
    assert points[1]["value"] == 78.5


@pytest.mark.django_db
def test_body_measurements_tenant_isolated(wo_env):
    other = Tenant.objects.create(
        name="Other Gym", slug="other-gym", status=Tenant.STATUS_ACTIVE
    )
    other_member = MemberService.create(
        data={"full_name": "Other Person", "tenant": other}
    )
    BodyMeasurementService.record(
        data={
            "member_id": wo_env["member"].id,
            "weight_kg": "90",
            "tenant": wo_env["tenant"],
        }
    )
    BodyMeasurementService.record(
        data={
            "member_id": other_member.id,
            "weight_kg": "70",
            "tenant": other,
        }
    )
    with tenant_context(wo_env["tenant"], enforce=True):
        visible = list(BodyMeasurementService.list())
    assert len(visible) == 1
    assert visible[0].member_id == wo_env["member"].id


@pytest.mark.django_db
def test_duplicate_exercise_code_blocked(wo_env):
    with pytest.raises(WorkoutError, match="already exists"):
        ExerciseService.create(
            data={"code": "squat", "name": "Squat Again", "tenant": wo_env["tenant"]}
        )

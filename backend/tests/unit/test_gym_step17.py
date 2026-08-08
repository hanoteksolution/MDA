"""STEP 17 — gym trainers + assignments + PT sessions."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.gym.models import MemberTrainerAssignment, PersonalTrainingSession
from apps.gym.services.member_service import MemberService
from apps.gym.services.trainer_service import (
    AssignmentService,
    PTSessionService,
    TrainerError,
    TrainerService,
)
from apps.platform.models import Tenant


@pytest.fixture
def tr_env(db):
    tenant = Tenant.objects.create(
        name="Train Co", slug="train-co", status=Tenant.STATUS_ACTIVE
    )
    member = MemberService.create(
        data={"full_name": "Client One", "tenant": tenant}
    )
    trainer = TrainerService.create(
        data={
            "full_name": "Coach Alex",
            "phone": "111",
            "specialty_codes": ["strength", "cardio"],
            "schedules": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "12:00"},
                {"day_of_week": 2, "start_time": "14:00", "end_time": "18:00"},
            ],
            "tenant": tenant,
        }
    )
    return {"tenant": tenant, "member": member, "trainer": trainer}


@pytest.mark.django_db
def test_create_trainer_with_specialties_and_schedule(tr_env):
    t = tr_env["trainer"]
    assert t.code.startswith("TR-")
    assert t.specialties.count() == 2
    assert t.schedules.filter(deleted_at__isnull=True).count() == 2
    data = TrainerService.serialize(t)
    assert len(data["specialties"]) == 2
    assert data["schedules"][0]["start_time"] == "09:00"


@pytest.mark.django_db
def test_assign_and_end(tr_env):
    row = AssignmentService.assign(
        member_id=tr_env["member"].id,
        trainer_id=tr_env["trainer"].id,
    )
    assert row.status == MemberTrainerAssignment.STATUS_ACTIVE
    with pytest.raises(TrainerError, match="already assigned"):
        AssignmentService.assign(
            member_id=tr_env["member"].id,
            trainer_id=tr_env["trainer"].id,
        )
    ended = AssignmentService.end(assignment=row)
    assert ended.status == MemberTrainerAssignment.STATUS_ENDED
    assert ended.end_date is not None


@pytest.mark.django_db
def test_schedule_pt_session(tr_env):
    AssignmentService.assign(
        member_id=tr_env["member"].id,
        trainer_id=tr_env["trainer"].id,
    )
    when = timezone.now() + timedelta(days=1)
    session = PTSessionService.schedule(
        member_id=tr_env["member"].id,
        trainer_id=tr_env["trainer"].id,
        scheduled_at=when,
        duration_minutes=45,
    )
    assert session.status == PersonalTrainingSession.STATUS_SCHEDULED
    assert session.assignment_id is not None
    assert session.duration_minutes == 45
    session = PTSessionService.set_status(
        session=session, status=PersonalTrainingSession.STATUS_COMPLETED
    )
    assert session.status == "completed"


@pytest.mark.django_db
def test_trainer_code_unique(tr_env):
    with pytest.raises(TrainerError, match="already exists"):
        TrainerService.create(
            data={
                "full_name": "Other",
                "code": tr_env["trainer"].code,
                "tenant": tr_env["tenant"],
            }
        )

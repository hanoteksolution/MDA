"""STEP 16 — gym attendance check-in/out."""

from datetime import date, timedelta

import pytest

from apps.gym.models import Attendance
from apps.gym.services.attendance_service import AttendanceError, AttendanceService
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService, SubscriptionService
from apps.platform.models import Tenant


@pytest.fixture
def att_env(db):
    tenant = Tenant.objects.create(
        name="Attend Co", slug="attend-co", status=Tenant.STATUS_ACTIVE
    )
    member = MemberService.create(
        data={
            "full_name": "Check In Guy",
            "membership_number": "MEM-ATT-1",
            "phone": "999",
            "tenant": tenant,
        }
    )
    plan = PlanService.create(
        data={
            "code": "day",
            "name": "Day Pass",
            "duration_days": 30,
            "price": "10",
            "visit_limit": 5,
            "tenant": tenant,
        }
    )
    sub = SubscriptionService.subscribe(
        member_id=member.id, plan_id=plan.id, activate=True
    )
    return {"tenant": tenant, "member": member, "plan": plan, "sub": sub}


@pytest.mark.django_db
def test_check_in_success_increments_visits(att_env):
    row = AttendanceService.check_in(membership_number="MEM-ATT-1")
    assert row.member_id == att_env["member"].id
    assert row.check_out_at is None
    assert row.source == Attendance.SOURCE_MEMBERSHIP_NUMBER
    att_env["sub"].refresh_from_db()
    assert att_env["sub"].visits_used == 1


@pytest.mark.django_db
def test_expired_membership_rejected(att_env):
    sub = att_env["sub"]
    sub.end_date = date.today() - timedelta(days=1)
    sub.save(update_fields=["end_date", "updated_at"])
    with pytest.raises(AttendanceError, match="No active membership"):
        AttendanceService.check_in(member_id=att_env["member"].id)


@pytest.mark.django_db
def test_duplicate_check_in_blocked(att_env):
    AttendanceService.check_in(member_id=att_env["member"].id)
    with pytest.raises(AttendanceError, match="already checked in"):
        AttendanceService.check_in(member_id=att_env["member"].id)


@pytest.mark.django_db
def test_check_out_then_check_in_again(att_env):
    AttendanceService.check_in(member_id=att_env["member"].id)
    AttendanceService.check_out(member_id=att_env["member"].id)
    row = AttendanceService.check_in(member_id=att_env["member"].id)
    assert row.check_out_at is None
    att_env["sub"].refresh_from_db()
    assert att_env["sub"].visits_used == 2


@pytest.mark.django_db
def test_check_out_closes_visit(att_env):
    row = AttendanceService.check_in(member_id=att_env["member"].id)
    out = AttendanceService.check_out(attendance_id=row.id)
    assert out.check_out_at is not None
    assert out.is_open is False if hasattr(out, "is_open") else out.check_out_at


@pytest.mark.django_db
def test_qr_payload_resolves_member(att_env):
    row = AttendanceService.check_in(qr_payload="mem:MEM-ATT-1")
    assert row.source == Attendance.SOURCE_QR
    assert row.member_id == att_env["member"].id


@pytest.mark.django_db
def test_visit_limit_blocks_check_in(att_env):
    sub = att_env["sub"]
    sub.visits_used = 5
    sub.visits_allowed = 5
    sub.save(update_fields=["visits_used", "visits_allowed", "updated_at"])
    with pytest.raises(AttendanceError, match="No active membership"):
        AttendanceService.check_in(member_id=att_env["member"].id)

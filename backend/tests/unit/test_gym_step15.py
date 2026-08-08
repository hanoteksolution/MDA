"""STEP 15 — gym plans + subscription lifecycle."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.gym.models import MembershipPlan, MembershipSubscription
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import (
    PlanService,
    SubscriptionError,
    SubscriptionService,
)
from apps.platform.models import Tenant


@pytest.fixture
def gym_env(db):
    tenant = Tenant.objects.create(
        name="Fit Co", slug="fit-co", status=Tenant.STATUS_ACTIVE
    )
    member = MemberService.create(
        data={"full_name": "Jane Athlete", "phone": "100", "tenant": tenant}
    )
    plan = PlanService.create(
        data={
            "code": "monthly",
            "name": "Monthly",
            "duration_days": 30,
            "price": "50.00",
            "visit_limit": 20,
            "max_freeze_days": 7,
            "tenant": tenant,
        }
    )
    return {"tenant": tenant, "member": member, "plan": plan}


@pytest.mark.django_db
def test_subscribe_pending_then_activate_creates_active(gym_env):
    sub = SubscriptionService.subscribe(
        member_id=gym_env["member"].id,
        plan_id=gym_env["plan"].id,
        activate=False,
    )
    assert sub.status == MembershipSubscription.STATUS_PENDING
    assert sub.start_date is None

    sub = SubscriptionService.activate(
        subscription=sub,
        payment_reference="PAY-1",
        price_paid="50.00",
    )
    assert sub.status == MembershipSubscription.STATUS_ACTIVE
    assert sub.payment_reference == "PAY-1"
    assert sub.price_paid == Decimal("50.00")
    assert sub.start_date == date.today()
    assert sub.end_date == date.today() + timedelta(days=30)
    assert sub.activated_at is not None
    assert SubscriptionService.is_access_allowed(sub) is True


@pytest.mark.django_db
def test_subscribe_mark_paid_immediate_active(gym_env):
    sub = SubscriptionService.subscribe(
        member_id=gym_env["member"].id,
        plan_id=gym_env["plan"].id,
        activate=True,
        payment_reference="CASH",
    )
    assert sub.status == MembershipSubscription.STATUS_ACTIVE
    assert sub.end_date == date.today() + timedelta(days=30)


@pytest.mark.django_db
def test_server_side_expiry(gym_env):
    sub = SubscriptionService.subscribe(
        member_id=gym_env["member"].id,
        plan_id=gym_env["plan"].id,
        activate=True,
    )
    sub.end_date = date.today() - timedelta(days=1)
    sub.save(update_fields=["end_date", "updated_at"])

    assert SubscriptionService.is_access_allowed(sub) is False
    sub.refresh_from_db()
    assert sub.status == MembershipSubscription.STATUS_EXPIRED


@pytest.mark.django_db
def test_freeze_and_unfreeze_extends_end(gym_env):
    sub = SubscriptionService.subscribe(
        member_id=gym_env["member"].id,
        plan_id=gym_env["plan"].id,
        activate=True,
    )
    original_end = sub.end_date
    sub = SubscriptionService.freeze(subscription=sub)
    assert sub.status == MembershipSubscription.STATUS_FROZEN
    assert sub.frozen_at == date.today()

    # Simulate frozen yesterday so unfreeze adds 1 day
    sub.frozen_at = date.today() - timedelta(days=1)
    sub.save(update_fields=["frozen_at", "updated_at"])
    sub = SubscriptionService.unfreeze(subscription=sub)
    assert sub.status == MembershipSubscription.STATUS_ACTIVE
    assert sub.freeze_days_used == 1
    assert sub.end_date == original_end + timedelta(days=1)


@pytest.mark.django_db
def test_cancel_subscription(gym_env):
    sub = SubscriptionService.subscribe(
        member_id=gym_env["member"].id,
        plan_id=gym_env["plan"].id,
        activate=True,
    )
    sub = SubscriptionService.cancel(subscription=sub, notes="left town")
    assert sub.status == MembershipSubscription.STATUS_CANCELLED
    assert SubscriptionService.is_access_allowed(sub) is False


@pytest.mark.django_db
def test_plan_code_unique_per_tenant(gym_env):
    with pytest.raises(SubscriptionError, match="already exists"):
        PlanService.create(
            data={
                "code": "monthly",
                "name": "Dup",
                "duration_days": 30,
                "tenant": gym_env["tenant"],
            }
        )

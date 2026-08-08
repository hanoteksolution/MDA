"""STEP 20 — gym membership checkout via central Invoice + Payment."""

from decimal import Decimal

import pytest

from apps.gym.models import MembershipSubscription
from apps.gym.services.gym_payment_service import GymPaymentError, GymPaymentService
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService, SubscriptionService
from apps.platform.models import Tenant
from apps.sales.models import Invoice, Payment
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pay_env(db):
    tenant = Tenant.objects.create(
        name="Pay Gym", slug="pay-gym", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Pay Gym Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Front Desk", code="FD", is_default=True
    )
    member = MemberService.create(
        data={"full_name": "Pay Member", "phone": "555", "tenant": tenant, "branch_id": branch.id}
    )
    plan = PlanService.create(
        data={
            "code": "gold",
            "name": "Gold Monthly",
            "duration_days": 30,
            "price": "75.00",
            "tenant": tenant,
        }
    )
    return {"tenant": tenant, "branch": branch, "member": member, "plan": plan}


@pytest.mark.django_db
def test_checkout_cash_creates_invoice_payment_and_active_sub(pay_env):
    result = GymPaymentService.checkout_membership(
        data={
            "member_id": pay_env["member"].id,
            "plan_id": pay_env["plan"].id,
            "payment_method": "cash",
            "payment_reference": "RCPT-100",
            "tenant": pay_env["tenant"],
        }
    )
    sub_data = result["subscription"]
    assert sub_data["status"] == MembershipSubscription.STATUS_ACTIVE
    assert sub_data["payment_reference"] == "RCPT-100"
    assert sub_data["invoice_id"] is not None

    invoice = Invoice.active_objects().get(pk=result["invoice"]["id"])
    assert invoice.status == Invoice.STATUS_PAID
    assert invoice.total_amount == Decimal("75.0000")
    assert invoice.gym_subscriptions.count() == 1

    payments = Payment.objects.filter(invoice=invoice)
    assert payments.count() == 1
    assert payments.first().method == Payment.METHOD_CASH
    assert payments.first().amount == Decimal("75.0000")

    sub = MembershipSubscription.active_objects().get(pk=sub_data["id"])
    assert SubscriptionService.is_access_allowed(sub) is True
    pay_env["member"].refresh_from_db()
    assert pay_env["member"].customer_id is not None


@pytest.mark.django_db
def test_checkout_on_account_leaves_pending_sub(pay_env):
    result = GymPaymentService.checkout_membership(
        data={
            "member_id": pay_env["member"].id,
            "plan_id": pay_env["plan"].id,
            "payment_method": "on_account",
            "activate_on_pay": False,
            "tenant": pay_env["tenant"],
        }
    )
    assert result["subscription"]["status"] == MembershipSubscription.STATUS_PENDING
    invoice = Invoice.active_objects().get(pk=result["invoice"]["id"])
    assert invoice.status == Invoice.STATUS_SENT
    assert Payment.objects.filter(invoice=invoice).count() == 1
    assert Payment.objects.filter(invoice=invoice).first().amount == Decimal("0")


@pytest.mark.django_db
def test_pay_pending_subscription_activates(pay_env):
    sub = SubscriptionService.subscribe(
        member_id=pay_env["member"].id,
        plan_id=pay_env["plan"].id,
        activate=False,
    )
    assert sub.status == MembershipSubscription.STATUS_PENDING

    result = GymPaymentService.pay_pending_subscription(
        subscription_id=sub.id,
        data={
            "payment_method": "mobile",
            "payment_reference": "MOMO-9",
            "tenant": pay_env["tenant"],
        },
    )
    assert result["subscription"]["status"] == MembershipSubscription.STATUS_ACTIVE
    assert result["payments"][0]["method"] == Payment.METHOD_MOBILE


@pytest.mark.django_db
def test_checkout_idempotency_replays(pay_env):
    key = "gym-checkout-key-1"
    r1 = GymPaymentService.checkout_membership(
        data={
            "member_id": pay_env["member"].id,
            "plan_id": pay_env["plan"].id,
            "payment_method": "cash",
            "idempotency_key": key,
            "tenant": pay_env["tenant"],
        }
    )
    r2 = GymPaymentService.checkout_membership(
        data={
            "member_id": pay_env["member"].id,
            "plan_id": pay_env["plan"].id,
            "payment_method": "cash",
            "idempotency_key": key,
            "tenant": pay_env["tenant"],
        }
    )
    assert r2["idempotent_replay"] is True
    assert r1["subscription"]["id"] == r2["subscription"]["id"]
    assert Invoice.objects.filter(idempotency_key=key).count() == 1
    assert MembershipSubscription.active_objects().filter(invoice__idempotency_key=key).count() == 1


@pytest.mark.django_db
def test_split_payment_tenders(pay_env):
    result = GymPaymentService.checkout_membership(
        data={
            "member_id": pay_env["member"].id,
            "plan_id": pay_env["plan"].id,
            "payments": [
                {"method": "cash", "amount": "40"},
                {"method": "mobile", "amount": "35", "reference": "MM-1"},
            ],
            "tenant": pay_env["tenant"],
        }
    )
    invoice = Invoice.active_objects().get(pk=result["invoice"]["id"])
    assert Payment.objects.filter(invoice=invoice).count() == 2
    assert result["subscription"]["status"] == MembershipSubscription.STATUS_ACTIVE


@pytest.mark.django_db
def test_pay_non_pending_raises(pay_env):
    sub = SubscriptionService.subscribe(
        member_id=pay_env["member"].id,
        plan_id=pay_env["plan"].id,
        activate=True,
    )
    with pytest.raises(GymPaymentError, match="Only pending"):
        GymPaymentService.pay_pending_subscription(
            subscription_id=sub.id,
            data={"payment_method": "cash", "tenant": pay_env["tenant"]},
        )

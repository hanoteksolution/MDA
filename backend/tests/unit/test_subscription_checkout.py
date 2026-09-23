"""ERP subscription checkout: only a verified provider settlement activates/renews, exactly once."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.finance.models import JournalEntry
from apps.integrations.models import PaymentIntent, ReconciliationRecord
from apps.integrations.providers.payment_mock import MockPaymentProvider
from apps.platform.models import SubscriptionPayment, SubscriptionPlan, TenantSubscription
from apps.platform.services.platform_service import PlatformService
from apps.sales.models import Invoice, Payment
from tests.helpers.branch_factory import add_owner, build_branch_tenant
from tests.helpers.payment_factory import build_payment_ctx, deliver, make_provider
from tests.helpers.platform_admin import superadmin_client
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db
B = "/api/v1/billing/subscription"


@pytest.fixture(autouse=True)
def setup(settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    MockPaymentProvider.remote.clear()


def make_sub(ctx, *, status="trial", expires_in=3, plan="starter", ref="SUBT"):
    PlatformService.ensure_default_plans()
    return TenantSubscription.objects.create(
        reference_code=f"{ref}-{ctx.tenant.slug}"[:20], tenant=ctx.tenant, plan=SubscriptionPlan.objects.get(code=plan),
        status=status, expires_at=timezone.localdate() + timedelta(days=expires_in),
    )


@pytest.fixture
def world():
    house = build_payment_ctx("safari-billing", branches=("HQ",))
    provider = make_provider(house, name="safari-subs")
    shop = build_branch_tenant(slug="sub-shop", branch_codes=("MAIN",))
    other = build_branch_tenant(slug="sub-other", branch_codes=("MAIN",))
    sub, other_sub = make_sub(shop), make_sub(other, ref="SUBO")
    admin = superadmin_client("subs_root")
    r = admin.put("/api/v1/platform/subscriptions/payment-config/", {"payment_provider_id": str(provider.pk), "currency": "USD"}, format="json")
    assert r.status_code == 200, r.content
    return {
        "house": house, "provider": provider, "shop": shop, "sub": sub, "other_sub": other_sub, "admin": admin,
        "owner": auth_client_as(APIClient(), add_owner(shop, username="sub_owner")),
        "other_owner": auth_client_as(APIClient(), add_owner(other, username="sub_other_owner")),
    }


def checkout(world, plan_code=None, key="k1", client=None):
    plan = SubscriptionPlan.objects.get(code=plan_code) if plan_code else world["sub"].plan
    r = (client or world["owner"]).post(f"{B}/checkout/", {"plan_id": str(plan.pk), "idempotency_key": key}, format="json")
    assert r.status_code in (200, 201), r.content
    return SubscriptionPayment.objects.get(pk=r.json()["data"]["id"])


def pay(world, payment, *, event_id="evt-1", amount=None, kind="payment.succeeded", secret=None):
    kw = {"secret": secret} if secret else {}
    return deliver(world["provider"], event_id=event_id, reference=payment.intent.provider_reference,
                   amount=str(amount if amount is not None else payment.amount), kind=kind, **kw)


def fresh(obj):
    obj.refresh_from_db()
    return obj


def journals(world, prefix):
    return JournalEntry.objects.filter(tenant=world["house"].tenant, idempotency_key__startswith=prefix)


def test_checkout_creates_invoice_and_intent_but_activates_nothing(world):
    sub, before = world["sub"], world["sub"].expires_at
    payment = checkout(world)
    assert payment.status == "pending" and payment.intent.status == PaymentIntent.STATUS_PENDING
    assert payment.invoice.tenant_id == world["house"].tenant.pk and payment.invoice.status == Invoice.STATUS_SENT
    assert payment.amount == Decimal(sub.effective_monthly_fee) and payment.currency == "USD"
    assert fresh(sub).status == "trial" and sub.expires_at == before
    assert checkout(world).pk == payment.pk  # same idempotency key → same checkout
    assert not journals(world, "").exists()  # nothing posted before verified payment


def test_verified_payment_activates_once_with_accounting_and_audit(world):
    sub = world["sub"]
    trial_end = sub.expires_at
    payment = checkout(world)
    event = pay(world, payment)
    assert "Subscription activated." in event.reason
    sub = fresh(sub)
    assert sub.status == "active" and sub.expires_at == trial_end + timedelta(days=30)  # existing policy: extend from running expiry
    assert fresh(payment).status == "confirmed" and payment.auto_renewed
    assert fresh(payment.invoice).status == Invoice.STATUS_PAID
    # Duplicate and replayed confirmations change nothing.
    pay(world, payment, event_id="evt-1")
    assert pay(world, payment, event_id="evt-2").reason == "Already settled."
    assert fresh(sub).expires_at == trial_end + timedelta(days=30)
    assert Payment.objects.filter(invoice=payment.invoice).count() == 1
    assert journals(world, "CUSTOMER_PAYMENT_RECEIVED").count() == 1
    assert journals(world, "SALE_COMPLETED").count() == 1  # revenue: Dr AR / Cr Revenue, once
    assert AuditLog.objects.filter(new_values__event="subscription_activated_by_verified_payment").count() == 1


def test_expired_subscription_renews_from_today_and_can_change_plan(world):
    sub = world["sub"]
    TenantSubscription.objects.filter(pk=sub.pk).update(status="expired", expires_at=timezone.localdate() - timedelta(days=20))
    payment = checkout(world, plan_code="business")
    pay(world, payment)
    sub = fresh(sub)
    assert sub.status == "active" and sub.expires_at == timezone.localdate() + timedelta(days=30)
    assert sub.plan_id == payment.plan_id


def test_active_renewal_extends_from_current_expiry_and_never_shortens(world):
    sub = world["sub"]
    TenantSubscription.objects.filter(pk=sub.pk).update(status="active", expires_at=timezone.localdate() + timedelta(days=12))
    pay(world, checkout(world))
    assert fresh(sub).expires_at == timezone.localdate() + timedelta(days=42)


def test_plan_change_during_active_period_is_refused(world):
    TenantSubscription.objects.filter(pk=world["sub"].pk).update(status="active", expires_at=timezone.localdate() + timedelta(days=12))
    other = SubscriptionPlan.objects.exclude(pk=world["sub"].plan_id).filter(is_active=True, monthly_price__gt=0).first()
    if other is None:
        pytest.skip("only one paid plan seeded")
    r = world["owner"].post(f"{B}/checkout/", {"plan_id": str(other.pk), "idempotency_key": "chg"}, format="json")
    assert r.status_code == 400 and "proration" in r.json()["message"]


@pytest.mark.parametrize("case", ["forged", "wrong_amount", "failed", "wrong_currency", "unknown"])
def test_unverified_or_mismatched_payments_never_activate(world, case):
    sub = world["sub"]
    before = (sub.status, sub.expires_at)
    payment = checkout(world)
    if case == "forged":
        assert pay(world, payment, secret="not-the-secret").status == "rejected"
    elif case == "wrong_amount":
        pay(world, payment, amount=payment.amount - 1)
        assert ReconciliationRecord.objects.get(intent=payment.intent).kind == ReconciliationRecord.KIND_AMOUNT
    elif case == "failed":
        pay(world, payment, kind="payment.failed")
        assert fresh(payment.intent).status == PaymentIntent.STATUS_FAILED
    elif case == "wrong_currency":
        SubscriptionPayment.objects.filter(pk=payment.pk).update(currency="EUR")
        event = pay(world, payment)
        assert "currency" in event.reason and fresh(payment).status == "review"
        assert ReconciliationRecord.objects.filter(intent=payment.intent, kind=ReconciliationRecord.KIND_UNAPPLIED).exists()
    elif case == "unknown":
        assert deliver(world["provider"], event_id="u", reference="mockpay-nope", amount="1").status == "ignored"
    sub = fresh(sub)
    assert (sub.status, sub.expires_at) == before


def test_superseded_or_expired_checkout_late_payment_does_not_activate(world):
    sub, before = world["sub"], world["sub"].expires_at
    first = checkout(world, key="a")
    second = checkout(world, key="b")
    assert fresh(first).status == "expired" and fresh(first.invoice).status == Invoice.STATUS_CANCELLED
    pay(world, first, event_id="late")
    assert fresh(sub).expires_at == before and fresh(first).status == "expired"
    assert ReconciliationRecord.objects.filter(intent=first.intent).exists()
    pay(world, second, event_id="ok")
    assert fresh(sub).expires_at == before + timedelta(days=30)


def test_tenant_cannot_mark_paid_or_see_other_tenants(world):
    payment = checkout(world)
    owner, other = world["owner"], world["other_owner"]
    assert owner.post(f"/api/v1/platform/payments/{payment.pk}/confirm/", {"reason": "paid"}, format="json").status_code == 403
    assert owner.patch(f"{B}/payments/{payment.pk}/", {"status": "confirmed"}, format="json").status_code == 405
    assert owner.post(f"{B}/payments/{payment.pk}/", {"status": "confirmed"}, format="json").status_code == 405
    assert APIClient().post("/api/v1/platform/payments/waafi-callback/", {"reference": payment.payment_reference}, format="json").status_code == 410
    assert other.get(f"{B}/payments/{payment.pk}/").status_code == 404
    assert other.get(f"{B}/").json()["data"]["payments"] == []
    body = owner.get(f"{B}/").content.decode()
    assert str(world["provider"].pk) not in body and "credential" not in body
    assert fresh(world["sub"]).status == "trial" and fresh(payment).status == "pending"


def test_manual_confirmation_is_audited_recovery_not_checkout(world):
    admin, payment = world["admin"], checkout(world)
    assert admin.post(f"/api/v1/platform/payments/{payment.pk}/confirm/", {"reason": "customer says paid"}, format="json").status_code == 400
    legacy = PlatformService.ensure_pending_payment(subscription=world["sub"])
    assert admin.post(f"/api/v1/platform/payments/{legacy.pk}/confirm/", {}, format="json").status_code == 400  # reason required
    r = admin.post(f"/api/v1/platform/payments/{legacy.pk}/confirm/", {"reason": "Bank transfer verified by finance"}, format="json")
    assert r.status_code == 200
    assert AuditLog.objects.filter(new_values__event="subscription_payment_manual_confirm").count() == 1


def test_expired_tenant_can_still_check_out(world):
    TenantSubscription.objects.filter(pk=world["sub"].pk).update(status="expired", expires_at=timezone.localdate() - timedelta(days=60))
    r = world["owner"].post(f"{B}/checkout/", {"plan_id": str(world["sub"].plan_id), "idempotency_key": "late"}, format="json")
    assert r.status_code == 201, r.content


def test_only_superadmin_changes_the_billing_provider(world):
    owner = world["owner"]
    assert owner.put("/api/v1/platform/subscriptions/payment-config/", {"payment_provider_id": ""}, format="json").status_code == 403
    assert world["admin"].put("/api/v1/platform/subscriptions/payment-config/", {"payment_provider_id": "not-a-provider"}, format="json").status_code == 400

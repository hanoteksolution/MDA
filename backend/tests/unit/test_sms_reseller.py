"""SMS reseller packages & credits: purchase only via verified payment, exactly-once crediting,
reserve/charge/release consumption, expiry, never-negative balance, tenant isolation."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.integrations.models import (
    SmsCreditEntry,
    SmsCreditLot,
    SmsLog,
    SmsPackagePurchase,
    SmsProvider,
)
from apps.integrations.providers.mock import MockProvider
from apps.integrations.services import SmsService
from apps.integrations.services.sms_credit_service import SmsCreditError, SmsCreditService, sms_segments
from tests.helpers.branch_factory import add_owner, add_user, build_branch_tenant
from tests.helpers.payment_factory import WEBHOOK_SECRET, deliver, make_provider
from tests.helpers.platform_admin import PLATFORM_INTEGRATIONS as P, superadmin_client
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db
T = "/api/v1/integrations/sms-billing"


@pytest.fixture(autouse=True)
def setup(settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    settings.SMS_CREDITS_ENFORCED = True
    MockProvider.outbox.clear()


@pytest.fixture
def world():
    safari = build_branch_tenant(slug="safari-house", branch_codes=("HQ",))
    shop = build_branch_tenant(slug="reseller-shop", branch_codes=("HODAN",))
    other = build_branch_tenant(slug="reseller-other", branch_codes=("MAIN",))
    billing = make_provider(safari, name="safari-pay")  # Safari's own merchant account
    admin = superadmin_client("reseller_root")
    assert admin.put(f"{P}/sms-billing/settings/", {"payment_provider_id": str(billing.pk)}, format="json").status_code == 200
    pkg = admin.post(f"{P}/sms-billing/packages/", {
        "name": "Starter", "code": "S100", "sms_quantity": 100, "price": "5.00", "currency": "usd", "validity_days": 30,
    }, format="json").json()["data"]
    SmsProvider.objects.create(tenant=shop.tenant, name="gw", provider_type="MOCK", is_default=True)
    return {
        "safari": safari, "shop": shop, "other": other, "billing": billing, "admin": admin, "pkg": pkg,
        "owner": auth_client_as(APIClient(), add_owner(shop, username="shop_owner")),
        "other_owner": auth_client_as(APIClient(), add_owner(other, username="other_owner")),
    }


def buy(world, key="k1"):
    r = world["owner"].post(f"{T}/purchases/", {"package_id": world["pkg"]["id"], "idempotency_key": key}, format="json")
    assert r.status_code in (200, 201), r.content
    return r.json()["data"]


def pay(world, purchase, *, event_id="evt-1", amount="5.00", kind="payment.succeeded", secret=WEBHOOK_SECRET):
    return deliver(world["billing"], event_id=event_id, reference=purchase["payment_reference"], amount=amount, kind=kind, secret=secret)


def balance(ctx):
    return SmsCreditService.balance(ctx.tenant.pk)


# ── packages ────────────────────────────────────────────────────────────────────

def test_platform_manages_packages_and_tenants_see_only_active_ones(world):
    admin, owner = world["admin"], world["owner"]
    assert world["pkg"]["currency"] == "USD" and world["pkg"]["validity_days"] == 30
    assert admin.post(f"{P}/sms-billing/packages/", {"name": "Dup", "code": "S100", "sms_quantity": 1, "price": "1"}, format="json").status_code == 400
    assert admin.post(f"{P}/sms-billing/packages/", {"name": "Bad", "code": "B", "sms_quantity": 0, "price": "1"}, format="json").status_code == 400
    assert admin.post(f"{P}/sms-billing/packages/", {"name": "Bad", "code": "B", "sms_quantity": 5, "price": "-1"}, format="json").status_code == 400
    listed = owner.get(f"{T}/packages/").json()["data"]
    assert [p["code"] for p in listed] == ["S100"]
    assert admin.patch(f"{P}/sms-billing/packages/{world['pkg']['id']}/", {"is_active": False}, format="json").status_code == 200
    assert owner.get(f"{T}/packages/").json()["data"] == []
    assert owner.post(f"{T}/purchases/", {"package_id": world["pkg"]["id"], "idempotency_key": "x"}, format="json").status_code == 400


def test_tenants_cannot_reach_platform_billing_endpoints(world):
    owner, q = world["owner"], f"?tenant_id={world['shop'].tenant.pk}"
    for method, path, body in [
        ("get", "sms-billing/packages/", None), ("post", "sms-billing/packages/", {"name": "x", "code": "x", "sms_quantity": 1, "price": "1"}),
        ("patch", f"sms-billing/packages/{world['pkg']['id']}/", {"price": "0"}), ("get", "sms-billing/settings/", None),
        ("put", "sms-billing/settings/", {"payment_provider_id": None}), ("get", "sms-billing/balances/", None),
        ("get", f"sms-billing/ledger/{q}", None), ("post", f"sms-billing/adjustments/{q}", {"units": 1000, "reason": "free"}),
    ]:
        r = getattr(owner, method)(f"{P}/{path}", body, format="json") if body is not None else getattr(owner, method)(f"{P}/{path}")
        assert r.status_code == 403, (method, path, r.status_code)
    assert balance(world["shop"]) == 0


def test_tenant_billing_needs_billing_permissions(world):
    cashier = auth_client_as(APIClient(), add_user(world["shop"], username="sms_cashier", role_slug="cashier", branches=("HODAN",)))
    for path in ("packages/", "summary/", "ledger/", "purchases/"):
        assert cashier.get(f"{T}/{path}").status_code == 403, path
    assert cashier.post(f"{T}/purchases/", {"package_id": world["pkg"]["id"], "idempotency_key": "c"}, format="json").status_code == 403


# ── purchasing, verification, idempotency ───────────────────────────────────────

def test_purchase_credits_only_after_a_verified_payment(world):
    purchase = buy(world)
    assert purchase["status"] == "pending" and purchase["payment_reference"]
    assert "provider" not in json.dumps(purchase).replace("payment_reference", "")
    assert balance(world["shop"]) == 0
    # No client path can credit: the detail endpoint is read-only.
    assert world["owner"].post(f"{T}/purchases/{purchase['id']}/", {"status": "credited"}, format="json").status_code == 405
    assert world["owner"].patch(f"{T}/purchases/{purchase['id']}/", {"status": "credited"}, format="json").status_code == 405
    # Forged signature → rejected, nothing credited.
    assert pay(world, purchase, secret="wrong").status == "rejected"
    assert balance(world["shop"]) == 0
    event = pay(world, purchase)
    assert event.status == "processed" and event.reason == "SMS purchase credited."
    assert balance(world["shop"]) == 100
    lot = SmsCreditLot.objects.get(purchase_id=purchase["id"])
    assert timedelta(days=29) < lot.expires_at - timezone.now() <= timedelta(days=30)
    assert world["owner"].get(f"{T}/purchases/{purchase['id']}/").json()["data"]["status"] == "credited"


def test_duplicate_and_replayed_confirmations_credit_once(world):
    purchase = buy(world)
    assert buy(world)["id"] == purchase["id"]  # same idempotency key → same purchase
    pay(world, purchase, event_id="e1")
    pay(world, purchase, event_id="e1")  # redelivery of the same event
    second = pay(world, purchase, event_id="e2")  # a new event for the same payment
    assert second.reason == "SMS purchase already credited."
    assert balance(world["shop"]) == 100
    assert SmsCreditEntry.objects.filter(kind="purchase", purchase_id=purchase["id"]).count() == 1
    assert world["owner"].post(f"{T}/purchases/", {"package_id": world["pkg"]["id"], "idempotency_key": "k1"}, format="json").status_code == 200


def test_amount_mismatch_and_failed_payments_never_credit(world):
    wrong = buy(world, "k-wrong")
    assert pay(world, wrong, amount="1.00").reason == "SMS purchase amount mismatch; not credited."
    assert SmsPackagePurchase.objects.get(pk=wrong["id"]).status == "review"
    failed = buy(world, "k-fail")
    pay(world, failed, kind="payment.failed", event_id="e-fail")
    assert SmsPackagePurchase.objects.get(pk=failed["id"]).status == "failed"
    pay(world, failed, event_id="e-late")  # late success after failure → review, not credit
    assert SmsPackagePurchase.objects.get(pk=failed["id"]).status == "review"
    assert balance(world["shop"]) == 0


def test_purchase_needs_a_configured_billing_provider(world):
    world["admin"].put(f"{P}/sms-billing/settings/", {"payment_provider_id": None}, format="json")
    r = world["owner"].post(f"{T}/purchases/", {"package_id": world["pkg"]["id"], "idempotency_key": "np"}, format="json")
    assert r.status_code == 400 and not SmsPackagePurchase.objects.exists()


# ── consumption ─────────────────────────────────────────────────────────────────

def test_no_credit_no_send_and_balance_never_negative(world):
    shop = world["shop"]
    log = SmsService.send(tenant=shop.tenant, to="+252611234567", body="hello")
    assert log.status == SmsLog.STATUS_FAILED and log.error == "Insufficient SMS credits."
    assert MockProvider.outbox == [] and not SmsCreditEntry.objects.filter(tenant=shop.tenant).exists()
    SmsCreditService.adjust(tenant=shop.tenant, units=1, reason="trial", user=None)
    long_log = SmsService.send(tenant=shop.tenant, to="+252611234567", body="x" * 200)  # 2 segments
    assert long_log.status == SmsLog.STATUS_FAILED and balance(shop) == 1
    with pytest.raises(SmsCreditError):
        SmsCreditService.adjust(tenant=shop.tenant, units=-2, reason="too much", user=None)
    assert balance(shop) == 1


def test_sent_messages_are_charged_and_failed_ones_released(world, settings):
    shop = world["shop"]
    SmsCreditService.adjust(tenant=shop.tenant, units=5, reason="grant", user=None)
    sent = SmsService.send(tenant=shop.tenant, to="+252611234567", body="hi")
    assert sent.status == "SENT" and sent.credit_state == "charged" and sent.credit_units == 1
    assert balance(shop) == 4
    SmsProvider.objects.filter(tenant=shop.tenant).update(config={"mode": "rejected"})
    rejected = SmsService.send(tenant=shop.tenant, to="+252611234567", body="hi")
    assert rejected.status == "FAILED" and SmsLog.objects.get(pk=rejected.pk).credit_state == "released"
    assert balance(shop) == 4
    SmsProvider.objects.filter(tenant=shop.tenant).update(config={"mode": "timeout"})
    retrying = SmsService.send(tenant=shop.tenant, to="+252611234567", body="hi")
    assert retrying.status == "RETRYING" and retrying.credit_state == "reserved" and balance(shop) == 3
    for _ in range(3):
        SmsLog.objects.filter(pk=retrying.pk).update(next_retry_at=timezone.now())
        SmsService.dispatch(retrying.pk)
    retrying.refresh_from_db()
    assert retrying.status == "FAILED" and retrying.credit_state == "released" and balance(shop) == 4
    kinds = list(SmsCreditEntry.objects.filter(tenant=shop.tenant).order_by("created_at").values_list("kind", flat=True))
    assert kinds == ["adjust_credit", "reserve", "reserve", "release", "reserve", "release"]


def test_expiry_and_soonest_expiring_credits_are_used_first(world):
    shop, now = world["shop"], timezone.now()
    SmsCreditService.adjust(tenant=shop.tenant, units=3, reason="long", user=None, expires_at=now + timedelta(days=60))
    soon = SmsCreditService.adjust(tenant=shop.tenant, units=2, reason="soon", user=None, expires_at=now + timedelta(days=1))
    SmsService.send(tenant=shop.tenant, to="+252611234567", body="hi")
    assert SmsCreditLot.objects.get(pk=soon.lot_id).units_remaining == 1
    SmsCreditLot.objects.filter(pk=soon.lot_id).update(expires_at=now - timedelta(minutes=1))
    assert balance(shop) == 3  # expired units never count, even before the sweep
    assert SmsCreditService.expire_due() == 1
    assert SmsCreditEntry.objects.filter(tenant=shop.tenant, kind="expire").get().units == -1
    assert balance(shop) == 3


def test_ledger_is_immutable_and_adjustments_are_audited(world):
    shop, admin, q = world["shop"], world["admin"], f"?tenant_id={world['shop'].tenant.pk}"
    assert admin.post(f"{P}/sms-billing/adjustments/{q}", {"units": 10}, format="json").status_code == 400  # reason required
    r = admin.post(f"{P}/sms-billing/adjustments/{q}", {"units": 10, "reason": "Goodwill"}, format="json")
    assert r.status_code == 201 and r.json()["data"]["balance_after"] == 10
    assert admin.post(f"{P}/sms-billing/adjustments/{q}", {"units": -11, "reason": "x"}, format="json").status_code == 400
    assert admin.post(f"{P}/sms-billing/adjustments/{q}", {"units": -4, "reason": "Correction"}, format="json").status_code == 201
    assert balance(shop) == 6
    assert AuditLog.objects.filter(module="integrations", new_values__event="sms_credit_adjustment").count() == 2
    entry = SmsCreditEntry.objects.filter(tenant=shop.tenant).first()
    entry.units = 999
    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        entry.delete()
    ledger = admin.get(f"{P}/sms-billing/ledger/{q}").json()["data"]
    assert ledger["summary"]["balance"] == 6 and len(ledger["entries"]) == 2
    balances = {row["tenant_name"]: row["balance"] for row in admin.get(f"{P}/sms-billing/balances/").json()["data"]}
    assert balances[shop.tenant.name] == 6


def test_tenants_are_isolated(world):
    purchase = buy(world)
    pay(world, purchase)
    other = world["other_owner"]
    assert other.get(f"{T}/purchases/{purchase['id']}/").status_code == 404
    assert other.get(f"{T}/purchases/").json()["data"] == []
    assert other.get(f"{T}/ledger/").json()["data"] == []
    assert other.get(f"{T}/summary/").json()["data"]["balance"] == 0
    assert world["owner"].get(f"{T}/summary/").json()["data"]["balance"] == 100
    # Tenant responses never carry provider configuration or secrets.
    text = json.dumps([world["owner"].get(f"{T}/{p}").json() for p in ("packages/", "summary/", "purchases/", "ledger/")])
    assert WEBHOOK_SECRET not in text and str(world["billing"].pk) not in text


def test_segment_counting():
    assert sms_segments("a" * 160) == 1 and sms_segments("a" * 161) == 2
    assert sms_segments("ß" * 10) == 1  # GSM-7
    assert sms_segments("مرحبا" * 14) == 1 and sms_segments("مرحبا" * 15) == 2  # 70 / 75 UCS-2 chars

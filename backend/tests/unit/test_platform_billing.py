"""Platform Admin → Billing: elevated-only read models over real billing rows, and Super Admin recovery."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.authentication.models import Permission, Role, User, UserPermission
from apps.integrations.models import PaymentIntent, ReconciliationRecord
from apps.platform.models import SubscriptionPayment, TenantSubscription
from apps.sales.models import Invoice, Payment
from tests.helpers.shop_factory import auth_client_as
from tests.unit.test_subscription_checkout import checkout, fresh, pay, setup, world  # noqa: F401 - fixtures

pytestmark = pytest.mark.django_db
B = "/api/v1/platform/billing"


def platform_admin_client(username="plat_admin"):
    """Platform Admin role: elevated (may view billing) but not Super Admin (may not recover)."""
    user = User.objects.create_user(username=username, password="pass12345", role=Role.objects.get(slug="platform_admin"))
    user.apply_elevated_flags()
    user.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])
    return auth_client_as(APIClient(), user)


def grant(client_user_name, *codes):
    user = User.objects.get(username=client_user_name)
    for code in codes:
        perm, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": "platform"})
        UserPermission.objects.create(user=user, permission=perm)


@pytest.fixture
def paid(world):
    """One verified checkout (ledger-backed) + one open reconciliation discrepancy."""
    payment = checkout(world)
    pay(world, payment)
    other = checkout(world, key="k2")
    pay(world, other, event_id="evt-2", amount=Decimal(other.amount) + 1)  # amount mismatch → reconciliation
    return fresh(payment), fresh(other)


ENDPOINTS = ["overview/", "subscriptions/", "payments/", "invoices/", "reconciliation/", "plans/"]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_tenant_users_are_refused_even_with_platform_permissions(world, path):
    grant("sub_owner", "platform.view", "subscriptions.manage")  # tenant admin with platform-ish perms
    assert world["owner"].get(f"{B}/{path}").status_code == 403
    assert world["owner"].get(f"{B}/tenants/{world['shop'].tenant.pk}/").status_code == 403
    assert world["other_owner"].get(f"{B}/tenants/{world['shop'].tenant.pk}/").status_code == 403
    assert APIClient().get(f"{B}/{path}").status_code == 401


def test_overview_counts_and_ledger_backed_revenue(world, paid):
    payment, mismatched = paid
    TenantSubscription.objects.filter(pk=world["other_sub"].pk).update(status="suspended")
    data = world["admin"].get(f"{B}/overview/").json()["data"]
    assert data["subscriptions"]["active"] == 1 and data["subscriptions"]["suspended"] == 1
    assert data["tenants"]["total"] >= 3  # house + two shops
    assert data["payments"]["confirmed"] == 1 and data["payments"]["pending"] == 1  # mismatch leaves it pending
    assert data["reconciliation_open"] == 1
    assert data["revenue"]["verified"] == [{"currency": "USD", "amount": str(Decimal(payment.amount).quantize(Decimal("0.01")))}]
    assert data["revenue"]["manual_unposted"] == []
    assert data["can_recover"] is True
    assert not any(w in str(data).lower() for w in ("secret", "credential", "api_key"))


def test_subscriptions_table_search_filter_and_pagination(world, paid):
    admin = world["admin"]
    page = admin.get(f"{B}/subscriptions/", {"page_size": 1}).json()["data"]
    assert page["count"] == 2 and len(page["results"]) == 1 and page["page"] == 1
    rows = admin.get(f"{B}/subscriptions/", {"search": "sub-shop"}).json()["data"]["results"]
    assert [r["tenant_slug"] for r in rows] == ["sub-shop"]
    row = rows[0]
    assert row["status"] == "active" and row["billing_status"] == "pending"  # a newer checkout is pending
    assert row["last_payment_amount"] == str(Decimal(paid[0].amount).quantize(Decimal("0.01")))
    assert row["next_billing_at"] == row["expires_at"]
    assert admin.get(f"{B}/subscriptions/", {"status": "trial"}).json()["data"]["count"] == 1
    assert admin.get(f"{B}/subscriptions/", {"billing_status": "pending"}).json()["data"]["count"] == 1
    assert admin.get(f"{B}/subscriptions/", {"plan": "no-such-plan"}).json()["data"]["count"] == 0


def test_payments_invoices_reconciliation_tables(world, paid):
    admin = world["admin"]
    payments = admin.get(f"{B}/payments/").json()["data"]
    assert payments["count"] == 2 and {r["kind"] for r in payments["results"]} == {"checkout"}
    assert admin.get(f"{B}/payments/", {"status": "confirmed"}).json()["data"]["count"] == 1
    assert admin.get(f"{B}/payments/", {"kind": "manual"}).json()["data"]["count"] == 0
    invoices = admin.get(f"{B}/invoices/").json()["data"]["results"]
    assert {i["status"] for i in invoices} == {Invoice.STATUS_PAID, Invoice.STATUS_SENT}
    recon = admin.get(f"{B}/reconciliation/", {"status": "open"}).json()["data"]["results"]
    assert len(recon) == 1 and recon[0]["kind"] == "amount_mismatch" and recon[0]["tenant_name"] == world["shop"].tenant.name
    plans = admin.get(f"{B}/plans/").json()["data"]
    assert any(p["code"] == "starter" and p["subscriptions"] == 2 for p in plans)


def test_tenant_billing_detail(world, paid):
    data = world["admin"].get(f"{B}/tenants/{world['shop'].tenant.pk}/").json()["data"]
    assert data["subscription"]["reference_code"] == world["sub"].reference_code
    assert len(data["payments"]) == 2 and len(data["invoices"]) == 2 and len(data["reconciliation"]) == 1
    assert any(e["event"] == "subscription_activated_by_verified_payment" for e in data["renewal_history"])
    assert any(e["event"] == "renewed" for e in data["timeline"])
    assert world["admin"].get(f"{B}/tenants/00000000-0000-0000-0000-000000000000/").status_code == 404


def test_platform_admin_views_billing_but_cannot_recover(world):
    client = platform_admin_client()
    assert client.get(f"{B}/overview/").json()["data"]["can_recover"] is False
    r = client.post(f"{B}/subscriptions/{world['sub'].pk}/recover/", {"reason": "Provider outage recovery", "confirm": True}, format="json")
    assert r.status_code == 403
    r = world["owner"].post(f"{B}/subscriptions/{world['sub'].pk}/recover/", {"reason": "Provider outage recovery", "confirm": True}, format="json")
    assert r.status_code == 403


def test_super_admin_recovery_requires_reason_and_confirmation_and_creates_no_payment(world):
    sub, admin = world["sub"], world["admin"]
    TenantSubscription.objects.filter(pk=sub.pk).update(status="expired", expires_at=timezone.localdate() - timedelta(days=3))
    url = f"{B}/subscriptions/{sub.pk}/recover/"
    counts = lambda: (SubscriptionPayment.objects.count(), Invoice.objects.count(), PaymentIntent.objects.count(), Payment.objects.count())  # noqa: E731
    before = counts()
    assert admin.post(url, {"reason": "short", "confirm": True}, format="json").status_code == 400
    assert admin.post(url, {"reason": "Provider outage recovery", "confirm": False}, format="json").status_code == 400
    assert admin.post(url, {"reason": "Provider outage recovery", "confirm": "true"}, format="json").status_code == 400
    assert fresh(sub).status == "expired"
    r = admin.post(url, {"reason": "Provider outage recovery", "confirm": True}, format="json")
    assert r.status_code == 200, r.content
    sub = fresh(sub)
    assert sub.status == "active" and sub.expires_at == timezone.localdate() + timedelta(days=30)
    assert sub.last_paid_at is None  # no money was received
    assert counts() == before  # no payment, invoice, intent or receipt fabricated
    log = AuditLog.objects.get(new_values__event="subscription_manual_recovery")
    assert log.new_values["reason"] == "Provider outage recovery" and log.new_values["payment_created"] is False
    assert log.old_values["status"] == "expired"
    assert not ReconciliationRecord.objects.exists()

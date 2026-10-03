"""Platform Billing manual recovery under real PostgreSQL concurrency.

``PlatformBillingService.recover`` locks the subscription with
``select_for_update(of=("self",))`` while joining the nullable plan/tenant. SQLite ignores the
lock, so both the SQL itself and the no-lost-update claim are proven only here. A skip is a gate failure.

    DJANGO_SETTINGS_MODULE=config.settings.branch_verification \\
        python3 -m pytest tests/unit/test_platform_billing_postgresql.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import connection, connections
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.authentication.models import User
from apps.integrations.models import PaymentIntent
from apps.platform.models import SubscriptionPayment, TenantSubscription
from apps.platform.services.platform_billing_service import PlatformBillingService
from apps.sales.models import Invoice, Payment
from tests.unit.test_subscription_checkout import setup, world  # noqa: F401 - fixtures

pytestmark = pytest.mark.django_db(transaction=True)
REASON = "Provider outage recovery"


def race(n, work):
    barrier, results, errors = Barrier(n), [], []

    def run(i):
        try:
            barrier.wait(timeout=20)
            results.append(work(i))
        except Exception as exc:  # noqa: BLE001 - collected and asserted by the caller
            errors.append(exc)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=n) as pool:
        [f.result() for f in [pool.submit(run, i) for i in range(n)]]
    return results, errors


@pytest.fixture
def expired(world):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locking.")
    sub = world["sub"]
    TenantSubscription.objects.filter(pk=sub.pk).update(
        status="expired", expires_at=timezone.localdate() - timedelta(days=3), last_paid_at=None
    )
    sub.refresh_from_db()
    return sub


def counts():
    return (SubscriptionPayment.objects.count(), Invoice.objects.count(), PaymentIntent.objects.count(), Payment.objects.count())


def test_concurrent_recoveries_serialise_without_lost_updates(expired):
    admin = User.objects.get(username="subs_root")
    before, n = counts(), 4

    results, errors = race(n, lambda i: PlatformBillingService.recover(
        subscription=expired, reason=REASON, confirmed=True, user=admin
    ).expires_at)

    assert errors == []
    expired.refresh_from_db()
    period = expired.billing_period_days or 30
    # Each recovery extends from the previous one's committed expiry: no extension is lost.
    assert expired.expires_at == timezone.localdate() + timedelta(days=period * n)
    assert sorted(results) == [timezone.localdate() + timedelta(days=period * k) for k in range(1, n + 1)]
    assert expired.status == "active" and expired.last_paid_at is None
    assert AuditLog.objects.filter(new_values__event="subscription_manual_recovery").count() == n
    assert counts() == before  # no payment, invoice, intent or receipt fabricated


def test_recovery_endpoint_runs_the_locking_query_on_postgresql(world, expired):
    r = world["admin"].post(
        f"/api/v1/platform/billing/subscriptions/{expired.pk}/recover/",
        {"reason": REASON, "confirm": True},
        format="json",
    )
    assert r.status_code == 200, r.content
    expired.refresh_from_db()
    assert expired.status == "active" and expired.last_paid_at is None

"""Subscription settlement and SMS credit locking under real PostgreSQL concurrency.

SQLite ignores ``select_for_update``; these claims are proven only here. A skip is a gate failure.

    DJANGO_SETTINGS_MODULE=config.settings.branch_verification python3 -m pytest tests/unit/test_billing_postgresql.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import connection, connections
from django.utils import timezone

pytestmark = pytest.mark.django_db(transaction=True)


def require_postgres():
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locking.")


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
def billing(settings):
    from cryptography.fernet import Fernet

    from apps.platform.models import SubscriptionPlan, TenantSubscription
    from apps.platform.services.platform_service import PlatformService
    from tests.helpers.branch_factory import build_branch_tenant
    from tests.helpers.payment_factory import build_payment_ctx, make_provider

    require_postgres()
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    house = build_payment_ctx("pg-safari", branches=("HQ",))
    provider = make_provider(house, name="pg-subs")
    PlatformService.save_subscription_payment_config(data={"payment_provider_id": str(provider.pk), "currency": "USD"})
    shop = build_branch_tenant(slug="pg-sub-shop", branch_codes=("MAIN",))
    PlatformService.ensure_default_plans()
    sub = TenantSubscription.objects.create(
        reference_code="PGSUB-1", tenant=shop.tenant, plan=SubscriptionPlan.objects.get(code="starter"),
        status="active", expires_at=timezone.localdate() + timedelta(days=10),
    )
    return {"house": house, "provider": provider, "shop": shop, "sub": sub}


def _checkout(billing, key="pg-1"):
    from apps.platform.services.subscription_billing_service import SubscriptionBillingService

    payment, _ = SubscriptionBillingService.checkout(tenant=billing["shop"].tenant, plan_id=billing["sub"].plan_id, idempotency_key=key)
    return payment


def _assert_activated_once(billing, payment, expected_expiry):
    from apps.finance.models import JournalEntry
    from apps.platform.models import SubscriptionPayment, TenantSubscription
    from apps.sales.models import Payment

    sub = TenantSubscription.objects.get(pk=billing["sub"].pk)
    assert sub.status == "active" and sub.expires_at == expected_expiry
    assert SubscriptionPayment.objects.get(pk=payment.pk).status == "confirmed"
    assert Payment.objects.filter(invoice_id=payment.invoice_id).count() == 1
    journals = JournalEntry.objects.filter(tenant=billing["house"].tenant)
    assert journals.filter(idempotency_key__startswith="CUSTOMER_PAYMENT_RECEIVED").count() == 1
    assert journals.filter(idempotency_key__startswith="SALE_COMPLETED").count() == 1


@pytest.mark.parametrize("same_event", [True, False])
def test_concurrent_verified_webhooks_activate_the_subscription_once(billing, same_event):
    from apps.integrations.services import PaymentService
    from tests.helpers.payment_factory import signed

    payment = _checkout(billing)
    expected = billing["sub"].expires_at + timedelta(days=30)
    ref, amount = payment.intent.provider_reference, str(payment.amount)
    deliveries = [signed(event_id="pg-evt" if same_event else f"pg-evt-{i}", reference=ref, amount=amount) for i in range(8)]

    def deliver(i):
        body, sig, ts = deliveries[i]
        return PaymentService.receive_webhook(provider=billing["provider"], raw_body=body, signature=sig, timestamp=ts).status

    statuses, errors = race(8, deliver)
    assert not errors and set(statuses) == {"processed"}
    _assert_activated_once(billing, payment, expected)


def test_concurrent_checkouts_with_one_key_create_one_invoice_and_intent(billing):
    from apps.platform.models import SubscriptionPayment

    ids, errors = race(6, lambda i: str(_checkout(billing, key="same-key").pk))
    assert not errors and len(set(ids)) == 1
    payment = SubscriptionPayment.objects.get()
    assert payment.intent_id and payment.invoice_id


def test_sms_credit_reservations_never_oversell_or_go_negative(settings):
    from apps.integrations.models import SmsCreditEntry, SmsLog, SmsProvider
    from apps.integrations.services import SmsService
    from apps.integrations.services.sms_credit_service import SmsCreditService
    from tests.helpers.branch_factory import build_branch_tenant

    require_postgres()
    settings.SMS_CREDITS_ENFORCED = True
    ctx = build_branch_tenant(slug="pg-sms", branch_codes=("HODAN",))
    SmsProvider.objects.create(tenant=ctx.tenant, name="gw", provider_type="MOCK", is_default=True)
    SmsCreditService.adjust(tenant=ctx.tenant, units=3, reason="pg race", user=None)

    statuses, errors = race(10, lambda i: SmsService.send(tenant=ctx.tenant, to="+252611234567", body=f"hi {i}").status)
    assert not errors
    assert sorted(statuses) == ["FAILED"] * 7 + ["SENT"] * 3
    assert SmsCreditService.balance(ctx.tenant.pk) == 0
    assert SmsLog.objects.filter(tenant=ctx.tenant, credit_state="charged").count() == 3
    assert SmsLog.objects.filter(tenant=ctx.tenant, error="Insufficient SMS credits.").count() == 7
    assert SmsCreditEntry.objects.filter(tenant=ctx.tenant, kind="reserve").count() == 3
    assert min(SmsCreditEntry.objects.filter(tenant=ctx.tenant).values_list("balance_after", flat=True)) >= 0


def test_sms_debit_adjustments_racing_sends_never_go_negative(settings):
    from apps.integrations.models import SmsProvider
    from apps.integrations.services import SmsService
    from apps.integrations.services.sms_credit_service import SmsCreditError, SmsCreditService
    from tests.helpers.branch_factory import build_branch_tenant

    require_postgres()
    settings.SMS_CREDITS_ENFORCED = True
    ctx = build_branch_tenant(slug="pg-sms-adj", branch_codes=("HODAN",))
    SmsProvider.objects.create(tenant=ctx.tenant, name="gw", provider_type="MOCK", is_default=True)
    SmsCreditService.adjust(tenant=ctx.tenant, units=4, reason="pg", user=None)

    def work(i):
        if i % 2:
            try:
                SmsCreditService.adjust(tenant=ctx.tenant, units=-2, reason="race debit", user=None)
                return "debited"
            except SmsCreditError:
                return "refused"
        return SmsService.send(tenant=ctx.tenant, to="+252611234567", body="x").status

    results, errors = race(8, work)
    assert not errors
    spent = results.count("SENT") + 2 * results.count("debited")
    assert spent <= 4 and SmsCreditService.balance(ctx.tenant.pk) == 4 - spent >= 0


def test_sms_purchase_confirmations_racing_credit_once(settings):
    from apps.integrations.models import SmsBillingSettings, SmsCreditLot, SmsPackage
    from apps.integrations.services import PaymentService
    from apps.integrations.services.sms_credit_service import SmsCreditService, SmsPurchaseService
    from cryptography.fernet import Fernet
    from tests.helpers.branch_factory import build_branch_tenant
    from tests.helpers.payment_factory import build_payment_ctx, make_provider, signed

    require_postgres()
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    house = build_payment_ctx("pg-sms-house", branches=("HQ",))
    provider = make_provider(house, name="pg-sms-pay")
    settings_row = SmsBillingSettings.load()
    settings_row.payment_provider = provider
    settings_row.save()
    shop = build_branch_tenant(slug="pg-sms-buyer", branch_codes=("MAIN",))
    package = SmsPackage.objects.create(name="P", code="P100", sms_quantity=100, price="5.00", currency="USD")
    purchase, _ = SmsPurchaseService.create(tenant=shop.tenant, package_id=package.pk, idempotency_key="pg")
    deliveries = [signed(event_id=f"sms-{i}", reference=purchase.provider_reference, amount="5.00") for i in range(8)]

    def deliver(i):
        body, sig, ts = deliveries[i]
        return PaymentService.receive_webhook(provider=provider, raw_body=body, signature=sig, timestamp=ts).status

    statuses, errors = race(8, deliver)
    assert not errors and set(statuses) == {"processed"}
    assert SmsCreditLot.objects.filter(purchase=purchase).count() == 1
    assert SmsCreditService.balance(shop.tenant.pk) == 100

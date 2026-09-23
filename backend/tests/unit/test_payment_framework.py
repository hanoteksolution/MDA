"""B8-1..B8-3, B8-5..B8-8: payment intents, verified settlement, webhooks, reconciliation."""

from __future__ import annotations

import time
from decimal import Decimal
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient

from apps.finance.models import JournalEntry
from apps.integrations.models import (
    PaymentIntent,
    PaymentWebhookEvent,
    ReconciliationRecord,
)
from apps.integrations.providers.payment_mock import MockPaymentProvider
from apps.integrations.services import PaymentError, PaymentService, ReconciliationService
from apps.sales.models import Invoice, Payment
from tests.helpers.branch_factory import add_owner, add_user
from tests.helpers.payment_factory import (
    WEBHOOK_SECRET,
    build_payment_ctx,
    deliver,
    make_invoice,
    make_provider,
    signed,
    start_payment,
)
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db

BASE = "/api/v1/integrations"
S = PaymentIntent


@pytest.fixture(autouse=True)
def key(settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    MockPaymentProvider.remote.clear()


@pytest.fixture
def ctx():
    return build_payment_ctx("pay-tenant")


@pytest.fixture
def provider(ctx):
    return make_provider(ctx)


@pytest.fixture
def invoice(ctx):
    return make_invoice(ctx, "HODAN", total="100")


def payment_journals(ctx):
    return JournalEntry.objects.filter(tenant=ctx.tenant, idempotency_key__startswith="CUSTOMER_PAYMENT_RECEIVED")


def pending_intent(ctx, invoice, provider, key="k1", amount=None):
    intent, created = start_payment(ctx, invoice, key=key, amount=amount, provider=provider)
    assert intent.status == S.STATUS_PENDING and intent.provider_reference
    return intent


def fresh(obj):
    return type(obj).objects.get(pk=obj.pk)


# --------------------------------------------------------------------------- #
# B8-1: PAID only through a verified server-side confirmation
# --------------------------------------------------------------------------- #


def test_creating_an_intent_does_not_pay_the_invoice(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    invoice.refresh_from_db()
    assert invoice.status == Invoice.STATUS_SENT and invoice.amount_paid == 0
    assert not Payment.objects.filter(invoice=invoice).exists() and not payment_journals(ctx).exists()
    assert intent.payment_id is None


def test_a_signed_confirmation_settles_the_invoice_with_payment_and_journal(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    event = deliver(provider, event_id="evt-1", reference=intent.provider_reference, amount="100")
    assert event.status == PaymentWebhookEvent.STATUS_PROCESSED
    invoice.refresh_from_db()
    intent.refresh_from_db()
    assert invoice.status == Invoice.STATUS_PAID and invoice.amount_paid == Decimal("100")
    assert intent.status == S.STATUS_SUCCEEDED and intent.payment.amount == Decimal("100")
    assert payment_journals(ctx).count() == 1


def test_no_api_route_lets_a_client_declare_success(ctx, provider, invoice):
    """There is no 'confirm' endpoint: the intent detail is GET-only and the create response is pending."""
    owner = add_owner(ctx, username="pay_owner")
    client = auth_client_as(APIClient(), owner)
    created = client.post(
        f"{BASE}/payments/intents/",
        {"invoice_id": str(invoice.pk), "idempotency_key": "api-1", "status": "succeeded", "amount": "100"},
        format="json",
    )
    assert created.status_code == 201 and created.json()["data"]["status"] == "pending"
    intent_id = created.json()["data"]["id"]
    for verb in (client.post, client.patch, client.put, client.delete):
        assert verb(f"{BASE}/payments/intents/{intent_id}/", {"status": "succeeded"}, format="json").status_code == 405
    invoice.refresh_from_db()
    assert invoice.status == Invoice.STATUS_SENT and invoice.amount_paid == 0


def test_the_webhook_endpoint_is_public_but_only_a_valid_signature_settles(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    url = f"{BASE}/payments/webhooks/{provider.pk}/"
    anon = APIClient()
    body, sig, ts = signed(event_id="e", reference=intent.provider_reference, amount="100")
    assert anon.post(url, body, content_type="application/json").status_code == 401  # unsigned
    ok = anon.post(url, body, content_type="application/json",
                   HTTP_X_PAYMENT_SIGNATURE=sig, HTTP_X_PAYMENT_TIMESTAMP=ts)
    assert ok.status_code == 200
    assert fresh(invoice).status == Invoice.STATUS_PAID
    assert anon.post(f"{BASE}/payments/webhooks/00000000-0000-0000-0000-000000000000/", body,
                     content_type="application/json").status_code == 404
    big = b"x" * (64 * 1024 + 1)
    assert anon.post(url, big, content_type="application/json").status_code == 413


# --------------------------------------------------------------------------- #
# B8-2: lifecycle
# --------------------------------------------------------------------------- #


def test_lifecycle_created_pending_succeeded(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    deliver(provider, event_id="e1", reference=intent.provider_reference, amount="100")
    assert fresh(intent).status == S.STATUS_SUCCEEDED


def test_lifecycle_pending_failed_leaves_the_invoice_unpaid(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    deliver(provider, event_id="e1", reference=intent.provider_reference, amount="100", kind="payment.failed")
    assert fresh(intent).status == S.STATUS_FAILED
    assert fresh(invoice).status == Invoice.STATUS_SENT and not Payment.objects.exists()


def test_lifecycle_pending_expired(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    assert PaymentService.expire_due() == 0  # not due yet
    S.objects.filter(pk=intent.pk).update(expires_at=intent.created_at)
    assert PaymentService.expire_due() == 1
    assert fresh(intent).status == S.STATUS_EXPIRED


@pytest.mark.parametrize("terminal", [S.STATUS_SUCCEEDED, S.STATUS_FAILED, S.STATUS_EXPIRED])
@pytest.mark.parametrize("target", [S.STATUS_CREATED, S.STATUS_PENDING, S.STATUS_SUCCEEDED, S.STATUS_FAILED, S.STATUS_EXPIRED])
def test_terminal_states_never_move(ctx, provider, invoice, terminal, target):
    intent = pending_intent(ctx, invoice, provider)
    S.objects.filter(pk=intent.pk).update(status=terminal)
    with pytest.raises(PaymentError):
        PaymentService._transition(fresh(intent), target)


def test_pending_cannot_go_back_to_created(ctx, provider, invoice):
    with pytest.raises(PaymentError):
        PaymentService._transition(pending_intent(ctx, invoice, provider), S.STATUS_CREATED)


@pytest.mark.parametrize("mode", ["timeout", "server_error", "rejected"])
def test_provider_trouble_at_creation_yields_a_failed_intent_not_an_exception(ctx, invoice, mode):
    bad = make_provider(ctx, name=f"bad-{mode}", mode=mode)
    intent, _ = start_payment(ctx, invoice, key=f"k-{mode}", provider=bad)
    assert intent.status == S.STATUS_FAILED and intent.failure_reason and not intent.provider_reference
    assert fresh(invoice).status == Invoice.STATUS_SENT


def test_late_success_after_expiry_is_flagged_not_settled(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    S.objects.filter(pk=intent.pk).update(expires_at=intent.created_at)
    PaymentService.expire_due()
    event = deliver(provider, event_id="late", reference=intent.provider_reference, amount="100")
    assert event.status == PaymentWebhookEvent.STATUS_PROCESSED
    assert fresh(intent).status == S.STATUS_EXPIRED and fresh(invoice).status == Invoice.STATUS_SENT
    assert ReconciliationRecord.objects.get(intent=intent).kind == ReconciliationRecord.KIND_LATE_SUCCESS


def test_amount_mismatch_is_not_settled(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    deliver(provider, event_id="short", reference=intent.provider_reference, amount="99")
    assert fresh(intent).status == S.STATUS_PENDING and fresh(invoice).status == Invoice.STATUS_SENT
    assert ReconciliationRecord.objects.get(intent=intent).kind == ReconciliationRecord.KIND_AMOUNT


def test_invoice_paid_meanwhile_leaves_money_taken_flagged_not_double_applied(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    Invoice.objects.filter(pk=invoice.pk).update(status=Invoice.STATUS_PAID, amount_paid=Decimal("100"))
    deliver(provider, event_id="dup-pay", reference=intent.provider_reference, amount="100")
    intent.refresh_from_db()
    assert intent.status == S.STATUS_SUCCEEDED and intent.payment_id is None
    assert fresh(invoice).amount_paid == Decimal("100") and not Payment.objects.exists()
    assert ReconciliationRecord.objects.get(intent=intent).kind == ReconciliationRecord.KIND_UNAPPLIED


def test_partial_payment_keeps_the_invoice_open(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider, amount="40")
    deliver(provider, event_id="part", reference=intent.provider_reference, amount="40")
    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("40") and invoice.status == Invoice.STATUS_SENT


def test_cannot_collect_more_than_the_balance_or_on_an_unpayable_invoice(ctx, provider, invoice):
    with pytest.raises(PaymentError):
        start_payment(ctx, invoice, key="big", amount="100.01", provider=provider)
    for status in ("draft", "cancelled", "on_hold"):
        with pytest.raises(PaymentError):
            start_payment(ctx, make_invoice(ctx, status=status), key=f"s-{status}", provider=provider)


def test_settlement_failure_rolls_back_marks_the_event_errored_and_a_retry_succeeds(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    with mock.patch(
        "apps.finance.services.posting_service.AccountingPostingService.post_customer_payment",
        side_effect=RuntimeError("ledger down"),
    ):
        event = deliver(provider, event_id="flaky", reference=intent.provider_reference, amount="100")
    assert event.status == PaymentWebhookEvent.STATUS_ERROR
    assert fresh(invoice).status == Invoice.STATUS_SENT and not Payment.objects.exists()
    assert fresh(intent).status == S.STATUS_PENDING
    # The provider redelivers the same event; the errored one is retried, not skipped as a duplicate.
    again = deliver(provider, event_id="flaky", reference=intent.provider_reference, amount="100")
    assert again.pk == event.pk and again.status == PaymentWebhookEvent.STATUS_PROCESSED
    assert fresh(invoice).status == Invoice.STATUS_PAID and payment_journals(ctx).count() == 1


# --------------------------------------------------------------------------- #
# B8-3: idempotency
# --------------------------------------------------------------------------- #


def test_replaying_an_intent_key_returns_the_same_intent(ctx, provider, invoice):
    first, created = start_payment(ctx, invoice, key="same", provider=provider)
    second, created_again = start_payment(ctx, invoice, key="same", provider=provider)
    assert created and not created_again and first.pk == second.pk
    assert S.objects.filter(tenant=ctx.tenant).count() == 1 and len(MockPaymentProvider.remote) == 1


def test_a_key_reused_for_a_different_request_is_refused(ctx, provider, invoice):
    start_payment(ctx, invoice, key="same", amount="50", provider=provider)
    with pytest.raises(PaymentError):
        start_payment(ctx, invoice, key="same", amount="60", provider=provider)
    with pytest.raises(PaymentError):
        start_payment(ctx, make_invoice(ctx), key="same", amount="50", provider=provider)


def test_replayed_webhooks_create_exactly_one_payment_and_one_journal(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    ref = intent.provider_reference
    first = deliver(provider, event_id="evt-A", reference=ref, amount="100")
    replay = deliver(provider, event_id="evt-A", reference=ref, amount="100")  # identical redelivery
    other = deliver(provider, event_id="evt-B", reference=ref, amount="100")  # provider re-sent under a new id
    assert first.pk == replay.pk and other.pk != first.pk
    assert other.reason == "Already settled."
    assert Payment.objects.filter(invoice=invoice).count() == 1
    assert payment_journals(ctx).count() == 1
    assert fresh(invoice).amount_paid == Decimal("100")


# --------------------------------------------------------------------------- #
# B8-5 / B8-6: signature verification, replay protection, raw persistence
# --------------------------------------------------------------------------- #


def receive(provider, body, signature, timestamp):
    return PaymentService.receive_webhook(provider=provider, raw_body=body, signature=signature, timestamp=timestamp)


def test_unsigned_wrongly_signed_stale_and_tampered_webhooks_are_rejected(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    ref, now = intent.provider_reference, int(time.time())
    body, sig, ts = signed(event_id="e", reference=ref, amount="100")
    forged_body, _, _ = signed(event_id="e", reference=ref, amount="1")
    cases = {
        "unsigned": (body, "", ""),
        "no signature": (body, "", ts),
        "no timestamp": (body, sig, ""),
        "garbage signature": (body, "deadbeef", ts),
        "wrong secret": signed(event_id="e", reference=ref, amount="100", secret="another-secret"),
        "stale timestamp": signed(event_id="e", reference=ref, amount="100", ts=now - 3600),
        "future timestamp": signed(event_id="e", reference=ref, amount="100", ts=now + 3600),
        "non-numeric timestamp": (body, sig, "yesterday"),
        "tampered body": (forged_body, sig, ts),
    }
    for name, (b, s, t) in cases.items():
        event = receive(provider, b, s, t)
        assert event.status == PaymentWebhookEvent.STATUS_REJECTED, name
        assert not event.signature_valid and event.event_id == "", name
    assert fresh(intent).status == S.STATUS_PENDING and fresh(invoice).status == Invoice.STATUS_SENT
    assert not Payment.objects.exists() and not payment_journals(ctx).exists()


def test_a_captured_valid_webhook_cannot_be_replayed_after_the_window(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    body, sig, ts = signed(event_id="e", reference=intent.provider_reference, amount="100")
    replay = PaymentService.receive_webhook(
        provider=provider, raw_body=body, signature=sig, timestamp=ts, now=time.time() + 3600
    )
    assert replay.status == PaymentWebhookEvent.STATUS_REJECTED and "replay" in replay.reason
    assert fresh(invoice).status == Invoice.STATUS_SENT


def test_provider_without_a_webhook_secret_rejects_everything(ctx, invoice):
    bare = make_provider(ctx, name="bare")
    bare.webhook_credential = None
    bare.save()
    intent = pending_intent(ctx, invoice, bare)
    assert deliver(bare, event_id="e", reference=intent.provider_reference, amount="100").status == "rejected"


def test_unverified_webhooks_are_persisted_raw_and_change_nothing(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    body, _, ts = signed(event_id="e", reference=intent.provider_reference, amount="100")
    event = receive(provider, body, "bad", ts)
    stored = PaymentWebhookEvent.objects.get(pk=event.pk)
    assert stored.raw_body == body.decode() and stored.tenant_id == ctx.tenant.pk and stored.intent_id is None
    assert not Payment.objects.exists() and fresh(invoice).amount_paid == 0 and fresh(intent).status == S.STATUS_PENDING


def test_a_forged_event_cannot_burn_a_real_event_id(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    body, _, ts = signed(event_id="evt-real", reference=intent.provider_reference, amount="100")
    assert receive(provider, body, "forged", ts).status == "rejected"
    real = deliver(provider, event_id="evt-real", reference=intent.provider_reference, amount="100")
    assert real.status == PaymentWebhookEvent.STATUS_PROCESSED and fresh(invoice).status == Invoice.STATUS_PAID


def test_signed_but_unusable_and_unknown_events_are_stored_and_inert(ctx, provider, invoice):
    pending_intent(ctx, invoice, provider)
    junk = b"not json at all"
    ts = str(int(time.time()))
    from apps.integrations.providers.payment_base import sign

    invalid = receive(provider, junk, sign(WEBHOOK_SECRET, ts, junk), ts)
    assert invalid.status == PaymentWebhookEvent.STATUS_INVALID and invalid.raw_body == "not json at all"
    unknown = deliver(provider, event_id="ghost", reference="mockpay-doesnotexist", amount="100")
    assert unknown.status == PaymentWebhookEvent.STATUS_IGNORED and unknown.intent_id is None
    other = deliver(provider, event_id="misc", reference="x", amount="1", kind="payment.refunded")
    assert other.status == PaymentWebhookEvent.STATUS_IGNORED
    assert not Payment.objects.exists()


# --------------------------------------------------------------------------- #
# B8-7: reconciliation reports, never corrects
# --------------------------------------------------------------------------- #


def snapshot(invoice, intent):
    return (
        Invoice.objects.values_list("status", "amount_paid").get(pk=invoice.pk),
        S.objects.values_list("status", "payment_id").get(pk=intent.pk),
        Payment.objects.count(), JournalEntry.objects.count(),
    )


def test_lost_webhook_is_reported_and_nothing_is_changed(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    MockPaymentProvider.remote[intent.provider_reference]["status"] = "succeeded"  # provider took the money
    before = snapshot(invoice, intent)
    summary = ReconciliationService.run(tenant=ctx.tenant)
    assert summary["checked"] == 1 and summary["mismatches"] == 1
    rec = ReconciliationRecord.objects.get(intent=intent)
    assert rec.kind == ReconciliationRecord.KIND_STATUS and rec.provider_status == "succeeded"
    assert rec.ledger_status == "pending" and rec.branch_id == invoice.branch_id
    assert snapshot(invoice, intent) == before  # reported, not auto-corrected
    again = ReconciliationService.run(tenant=ctx.tenant)
    assert again["mismatches"] == 0 and ReconciliationRecord.objects.count() == 1  # no duplicates


def test_settled_payment_missing_its_journal_and_provider_amount_drift_are_reported(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    deliver(provider, event_id="e", reference=intent.provider_reference, amount="100")
    MockPaymentProvider.remote[intent.provider_reference].update(status="succeeded", amount=Decimal("90"))
    payment_journals(ctx).delete()
    before = snapshot(invoice, intent)
    ReconciliationService.run(tenant=ctx.tenant)
    kinds = set(ReconciliationRecord.objects.filter(intent=intent).values_list("kind", flat=True))
    assert kinds == {ReconciliationRecord.KIND_MISSING_JOURNAL, ReconciliationRecord.KIND_AMOUNT}
    assert snapshot(invoice, intent) == before and not payment_journals(ctx).exists()


def test_a_clean_ledger_reconciles_with_no_records(ctx, provider, invoice):
    intent = pending_intent(ctx, invoice, provider)
    MockPaymentProvider.remote[intent.provider_reference]["status"] = "succeeded"
    deliver(provider, event_id="e", reference=intent.provider_reference, amount="100")
    assert ReconciliationService.run(tenant=ctx.tenant)["mismatches"] == 0


def test_unreachable_provider_is_counted_not_flagged(ctx, invoice):
    flaky = make_provider(ctx, name="flaky", status_mode="timeout")
    pending_intent(ctx, invoice, flaky)
    summary = ReconciliationService.run(tenant=ctx.tenant)
    assert summary["unreachable"] == 1 and summary["mismatches"] == 0


def test_resolving_a_record_needs_a_note_and_changes_no_money(ctx, provider, invoice):
    owner = add_owner(ctx, username="rec_owner")
    intent = pending_intent(ctx, invoice, provider)
    MockPaymentProvider.remote[intent.provider_reference]["status"] = "succeeded"
    ReconciliationService.run(tenant=ctx.tenant)
    rec = ReconciliationRecord.objects.get(intent=intent)
    with pytest.raises(PaymentError):
        ReconciliationService.resolve(record=rec, user=owner, note=" ")
    ReconciliationService.resolve(record=rec, user=owner, note="Settled manually via voucher.")
    rec.refresh_from_db()
    assert rec.status == "resolved" and rec.resolved_by_id == owner.pk
    assert fresh(invoice).status == Invoice.STATUS_SENT
    with pytest.raises(PaymentError):
        ReconciliationService.resolve(record=rec, user=owner, note="again")


def test_reconciliation_api_is_platform_only(ctx, provider):
    """Reconciliation is platform infrastructure: tenant users (even with the reconcile permission)
    get 403; a Super Admin sees and runs it for an explicitly selected tenant."""
    from tests.helpers.platform_admin import PLATFORM_INTEGRATIONS, superadmin_client

    hodan, bakaaro = make_invoice(ctx, "HODAN"), make_invoice(ctx, "BAKAARO")
    for n, inv in enumerate((hodan, bakaaro)):
        intent = pending_intent(ctx, inv, provider, key=f"k{n}")
        MockPaymentProvider.remote[intent.provider_reference]["status"] = "succeeded"
    ReconciliationService.run(tenant=ctx.tenant)
    record = ReconciliationRecord.objects.get(branch=bakaaro.branch)
    tenant_user = auth_client_as(APIClient(), add_user(ctx, username="hodan_rec", branches=("HODAN",)))
    base, q = f"{PLATFORM_INTEGRATIONS}/payments", f"?tenant_id={ctx.tenant.pk}"
    assert tenant_user.get(f"{base}/reconciliation/{q}").status_code == 403
    assert tenant_user.post(f"{base}/reconcile/{q}", {}, format="json").status_code == 403
    assert tenant_user.post(f"{base}/reconciliation/{record.pk}/resolve/{q}", {"note": "x"}, format="json").status_code == 403
    assert tenant_user.get(f"{BASE}/payments/reconciliation/").status_code == 404

    admin = superadmin_client("rec_root")
    assert admin.get(f"{base}/reconciliation/").status_code == 400  # tenant must be named
    rows = admin.get(f"{base}/reconciliation/{q}").json()["data"]
    assert {r["branch_id"] for r in rows} == {str(hodan.branch_id), str(bakaaro.branch_id)}
    assert admin.post(f"{base}/reconcile/{q}", {}, format="json").json()["data"]["checked"] == 2
    resolved = admin.post(f"{base}/reconciliation/{record.pk}/resolve/{q}", {"note": "Checked with provider."}, format="json")
    assert resolved.status_code == 200 and resolved.json()["data"]["status"] == "resolved"


# --------------------------------------------------------------------------- #
# B8-8: branch stamping
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("code", ["HODAN", "BAKAARO"])
def test_payment_intent_and_payment_carry_the_invoice_branch(ctx, provider, code):
    invoice = make_invoice(ctx, code)
    intent = pending_intent(ctx, invoice, provider, key=f"b-{code}")
    deliver(provider, event_id=f"e-{code}", reference=intent.provider_reference, amount="100")
    intent.refresh_from_db()
    assert intent.branch_id == invoice.branch_id == intent.payment.branch_id
    entry = payment_journals(ctx).get()
    assert set(entry.lines.values_list("branch_id", flat=True)) == {invoice.branch_id}


def test_a_branch_provider_cannot_collect_for_another_branch(ctx, invoice):
    bakaaro_gw = make_provider(ctx, branch="BAKAARO", name="bak-only")
    with pytest.raises(PaymentError):
        start_payment(ctx, invoice, key="x", provider=bakaaro_gw)
    branch_gw = make_provider(ctx, branch="HODAN", name="hod-only")
    intent, _ = start_payment(ctx, invoice, key="y")  # resolves to the branch-specific provider
    assert intent.provider_id == branch_gw.pk


def test_intent_api_refuses_a_foreign_branch_invoice_as_not_found(ctx, provider):
    other_branch_invoice = make_invoice(ctx, "BAKAARO")
    user = add_user(ctx, username="hodan_cashier", branches=("HODAN",))
    client = auth_client_as(APIClient(), user)
    resp = client.post(
        f"{BASE}/payments/intents/", {"invoice_id": str(other_branch_invoice.pk), "idempotency_key": "z"}, format="json"
    )
    assert resp.status_code == 404 and not S.objects.exists()
    listing = client.get(f"{BASE}/payments/intents/").json()["data"]
    assert listing == []


def test_other_tenants_cannot_use_this_tenants_invoice_or_provider(ctx, provider, invoice):
    from apps.integrations.services import PaymentError as PE

    stranger = build_payment_ctx("pay-stranger", branches=("X",))
    with pytest.raises(PE):
        PaymentService.create_intent(tenant=stranger.tenant, invoice=invoice, idempotency_key="t1")
    own = make_invoice(stranger, "X")
    with pytest.raises(PE):
        PaymentService.create_intent(tenant=stranger.tenant, invoice=own, idempotency_key="t2", provider_id=provider.pk)

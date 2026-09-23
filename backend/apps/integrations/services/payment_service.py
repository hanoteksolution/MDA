"""Payment intents, webhook intake and settlement.

Rules the rest of the ERP relies on:

* An invoice becomes PAID (a ``Payment`` row + journal entry) **only** inside ``_settle``, which
  runs only from a webhook whose HMAC signature and timestamp were verified server-side.
  No API endpoint, frontend callback or unverified webhook can reach it.
* Intents are idempotent on ``(tenant, idempotency_key)``; webhooks are idempotent on the
  provider's ``event_id`` *and* on intent state, so duplicate or replayed deliveries settle once.
* Every webhook is stored raw first. Rejected/invalid ones change no financial state.
* Anything that does not add up (late success, amount mismatch, money the invoice cannot
  absorb) becomes a ``ReconciliationRecord`` for a human — it is never auto-corrected.
* Provider trouble is a result, never an exception into the caller: a failed create marks the
  intent ``failed``; a failed settlement marks the event ``error`` so the provider retries.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services.audit_write import write_audit
from apps.integrations.crypto import SecretDecryptError
from apps.integrations.models import (
    PaymentIntent,
    PaymentProviderConfig,
    PaymentWebhookEvent,
    ReconciliationRecord,
)
from apps.integrations.providers.payment_base import OK, verify_signature
from apps.integrations.providers.registry import get_payment_adapter_class
from apps.integrations.services.credential_service import CredentialService

logger = logging.getLogger(__name__)

MODULE = "integrations"
DEFAULT_TTL_MINUTES = 30
MAX_BODY_BYTES = 64 * 1024
_TOLERANCE = Decimal("0.005")
_CANCELLED_OR_UNPAYABLE = ("draft", "cancelled", "on_hold")


class PaymentError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"))


class PaymentService:
    # ── configuration ─────────────────────────────────────────────────────────
    @staticmethod
    def adapter(provider: PaymentProviderConfig, *, with_api_secret: bool = False):
        try:
            secret = CredentialService.reveal(provider.credential) if with_api_secret else None
        except (ImproperlyConfigured, SecretDecryptError) as exc:
            raise PaymentError("Provider credential is unavailable.") from exc
        return get_payment_adapter_class(provider.provider_type)(config=provider.config, secret=secret)

    @staticmethod
    def resolve_provider(*, tenant, branch, provider_id=None) -> PaymentProviderConfig:
        qs = PaymentProviderConfig.active_objects().filter(tenant=tenant, is_active=True)
        if provider_id:
            provider = qs.filter(pk=provider_id).first()
            if provider is None or (provider.branch_id and provider.branch_id != branch.pk):
                raise PaymentError("Payment provider not found for this branch.")
            return provider
        provider = qs.filter(branch=branch).first() or qs.filter(branch__isnull=True).first()
        if provider is None:
            raise PaymentError("No active payment provider is configured for this branch.")
        return provider

    # ── intents ───────────────────────────────────────────────────────────────
    @staticmethod
    def _transition(intent: PaymentIntent, new_status: str, **fields) -> PaymentIntent:
        if new_status not in PaymentIntent.TRANSITIONS[intent.status]:
            raise PaymentError(f"Illegal payment intent transition {intent.status} → {new_status}.")
        intent.status = new_status
        for name, value in fields.items():
            setattr(intent, name, value)
        intent.save(update_fields=["status", "updated_at", *fields])
        return intent

    @staticmethod
    def create_intent(*, tenant, invoice, idempotency_key, amount=None, provider_id=None,
                      method="mobile", user=None, request=None) -> tuple[PaymentIntent, bool]:
        """Returns ``(intent, created)``. Replaying a key returns the original intent unchanged."""
        key = (idempotency_key or "").strip()
        if not key or len(key) > 64:
            raise PaymentError("An idempotency key (1–64 characters) is required.")
        if invoice.tenant_id != tenant.pk:
            raise PaymentError("Invoice not found.")

        amount = _money(amount) if amount not in (None, "") else None
        existing = PaymentIntent.objects.filter(tenant=tenant, idempotency_key=key).first()
        if existing is not None:
            return PaymentService._replay(existing, invoice=invoice, amount=amount), False

        if invoice.status in _CANCELLED_OR_UNPAYABLE:
            raise PaymentError("This invoice cannot be paid in its current status.")
        from apps.finance.services.voucher_service import VoucherService

        balance = VoucherService.invoice_balance(invoice)
        amount = amount if amount is not None else balance
        if amount <= 0:
            raise PaymentError("Payment amount must be positive.")
        if amount > balance + _TOLERANCE:
            raise PaymentError(f"Amount ({amount}) exceeds the outstanding balance ({balance}).")
        provider = PaymentService.resolve_provider(tenant=tenant, branch=invoice.branch, provider_id=provider_id)
        ttl = int(provider.config.get("intent_ttl_minutes") or DEFAULT_TTL_MINUTES)

        try:
            with transaction.atomic():
                intent = PaymentIntent.objects.create(
                    tenant=tenant, invoice=invoice, branch=invoice.branch, provider=provider,
                    idempotency_key=key, amount=amount, method=method or "mobile",
                    currency=str(provider.config.get("currency") or "USD")[:3],
                    expires_at=timezone.now() + timedelta(minutes=ttl), created_by=user,
                )
        except IntegrityError:  # a concurrent request with the same key won the insert
            existing = PaymentIntent.objects.get(tenant=tenant, idempotency_key=key)
            return PaymentService._replay(existing, invoice=invoice, amount=amount), False

        PaymentService._call_provider(intent, provider)
        write_audit(
            action="create", module=MODULE, entity=intent, user=user, request=request, branch=intent.branch,
            new_values={"invoice": str(invoice.pk), "amount": str(intent.amount), "status": intent.status},
        )
        return intent, True

    @staticmethod
    def _replay(existing: PaymentIntent, *, invoice, amount) -> PaymentIntent:
        if existing.invoice_id != invoice.pk or (amount is not None and existing.amount != amount):
            raise PaymentError("This idempotency key was already used for a different payment request.")
        return existing

    @staticmethod
    def _call_provider(intent: PaymentIntent, provider: PaymentProviderConfig) -> None:
        """Ask the provider to start the payment. Never raises: failure = a ``failed`` intent."""
        try:
            result = PaymentService.adapter(provider, with_api_secret=True).create_payment(
                amount=intent.amount, currency=intent.currency, reference=str(intent.pk)
            )
        except PaymentError as exc:
            PaymentService._transition(intent, PaymentIntent.STATUS_FAILED, failure_reason=str(exc)[:300])
            return
        except Exception:  # noqa: BLE001 - an adapter bug must not break the caller
            logger.exception("payment adapter crashed for intent %s", intent.pk)
            PaymentService._transition(intent, PaymentIntent.STATUS_FAILED, failure_reason="Provider error.")
            return
        if result.outcome == OK and result.reference:
            PaymentService._transition(intent, PaymentIntent.STATUS_PENDING, provider_reference=result.reference)
        else:
            PaymentService._transition(
                intent, PaymentIntent.STATUS_FAILED, failure_reason=(result.error or "Provider error.")[:300]
            )

    @staticmethod
    def expire_due(now=None) -> int:
        now = now or timezone.now()
        expired = 0
        due = PaymentIntent.objects.filter(
            status__in=(PaymentIntent.STATUS_CREATED, PaymentIntent.STATUS_PENDING), expires_at__lte=now
        ).values_list("pk", flat=True)
        for pk in list(due):
            with transaction.atomic():
                intent = PaymentIntent.objects.select_for_update().get(pk=pk)
                if intent.status in (PaymentIntent.STATUS_CREATED, PaymentIntent.STATUS_PENDING):
                    PaymentService._transition(intent, PaymentIntent.STATUS_EXPIRED)
                    expired += 1
        return expired

    # ── webhooks ──────────────────────────────────────────────────────────────
    @staticmethod
    def receive_webhook(*, provider: PaymentProviderConfig, raw_body: bytes, signature: str,
                        timestamp: str, now: float | None = None) -> PaymentWebhookEvent:
        """Store, verify, then (only if verified) process. Never acts on an unverified body."""
        stored = raw_body[:MAX_BODY_BYTES].decode("utf-8", errors="replace")

        try:
            secret = CredentialService.reveal(provider.webhook_credential)
        except (ImproperlyConfigured, SecretDecryptError):
            secret = None
        reason = verify_signature(
            secret=secret, timestamp=timestamp or "", signature=signature or "", raw_body=raw_body,
            now=time.time() if now is None else now,
        )
        if reason:
            return PaymentWebhookEvent.objects.create(
                tenant=provider.tenant, provider=provider, raw_body=stored,
                status=PaymentWebhookEvent.STATUS_REJECTED, reason=reason,
            )

        try:
            parsed = PaymentService.adapter(provider).parse_webhook(json.loads(raw_body))
        except (ValueError, PaymentError):
            parsed = None
        if parsed is None:
            return PaymentWebhookEvent.objects.create(
                tenant=provider.tenant, provider=provider, raw_body=stored, signature_valid=True,
                status=PaymentWebhookEvent.STATUS_INVALID, reason="Unrecognised event body.",
            )

        try:
            with transaction.atomic():
                event = PaymentWebhookEvent.objects.create(
                    tenant=provider.tenant, provider=provider, event_id=parsed.event_id, raw_body=stored,
                    signature_valid=True,
                )
        except IntegrityError:  # duplicate delivery of an event we already hold
            event = PaymentWebhookEvent.objects.get(provider=provider, event_id=parsed.event_id)
        return PaymentService.process_event(event.pk)

    @staticmethod
    def process_event(event_id) -> PaymentWebhookEvent:
        """Apply a verified event once. Safe to call again: settled events are returned untouched,
        errored ones are retried."""
        try:
            with transaction.atomic():
                event = PaymentWebhookEvent.objects.select_for_update().get(pk=event_id)
                if event.status not in PaymentWebhookEvent.RETRIABLE or not event.signature_valid:
                    return event
                provider = PaymentProviderConfig.objects.get(pk=event.provider_id)
                parsed = PaymentService.adapter(provider).parse_webhook(json.loads(event.raw_body))
                intent = PaymentIntent.objects.select_for_update().filter(
                    provider=provider, provider_reference=parsed.reference
                ).first()
                if intent is None:
                    # SMS package purchases share this verified intake (never credited any other way).
                    from apps.integrations.services.sms_credit_service import SmsPurchaseService

                    note = SmsPurchaseService.apply_event(provider, parsed)
                    if note is not None:
                        return PaymentService._finish(event, PaymentWebhookEvent.STATUS_PROCESSED, note)
                    return PaymentService._finish(event, PaymentWebhookEvent.STATUS_IGNORED, "Unknown payment reference.")
                event.intent = intent
                if parsed.kind == "succeeded":
                    note = PaymentService._settle(intent, parsed.amount)
                elif parsed.kind == "failed":
                    note = PaymentService._apply_failure(intent)
                else:
                    return PaymentService._finish(event, PaymentWebhookEvent.STATUS_IGNORED, "Event type not handled.")
                return PaymentService._finish(event, PaymentWebhookEvent.STATUS_PROCESSED, note)
        except Exception as exc:  # noqa: BLE001 - settlement is rolled back; the provider will retry
            logger.exception("payment webhook %s failed", event_id)
            PaymentWebhookEvent.objects.filter(pk=event_id).update(
                status=PaymentWebhookEvent.STATUS_ERROR, reason=type(exc).__name__ + ": " + str(exc)[:250]
            )
            return PaymentWebhookEvent.objects.get(pk=event_id)

    @staticmethod
    def _finish(event, status, reason=""):
        event.status, event.reason = status, (reason or "")[:300]
        event.processed_at = timezone.now()
        event.save(update_fields=["status", "reason", "intent", "processed_at", "updated_at"])
        return event

    # ── settlement (the only path that pays an invoice) ───────────────────────
    @staticmethod
    def _flag(intent, kind, *, provider_status="", provider_amount=None, detail=""):
        return ReconciliationService.record(
            intent, kind, provider_status=provider_status, provider_amount=provider_amount, detail=detail
        )

    @staticmethod
    def _settle(intent: PaymentIntent, provider_amount) -> str:
        """Caller holds the intent row lock inside a transaction."""
        if intent.status == PaymentIntent.STATUS_SUCCEEDED:
            return "Already settled."
        if intent.status != PaymentIntent.STATUS_PENDING:
            PaymentService._flag(
                intent, ReconciliationRecord.KIND_LATE_SUCCESS, provider_status="succeeded",
                provider_amount=provider_amount,
                detail=f"Provider reports success but the intent is {intent.status}.",
            )
            return f"Intent is {intent.status}; flagged for reconciliation."
        if provider_amount is None or _money(provider_amount) != intent.amount:
            PaymentService._flag(
                intent, ReconciliationRecord.KIND_AMOUNT, provider_status="succeeded",
                provider_amount=provider_amount, detail="Confirmed amount differs from the intent.",
            )
            return "Amount mismatch; not settled."

        from apps.finance.services.posting_service import AccountingPostingService
        from apps.finance.services.voucher_service import VoucherService
        from apps.sales.models import Invoice, Payment

        invoice = Invoice.objects.select_for_update().get(pk=intent.invoice_id)
        balance = VoucherService.invoice_balance(invoice)
        if invoice.status in ("cancelled", "on_hold") or intent.amount > balance + _TOLERANCE:
            PaymentService._transition(
                intent, PaymentIntent.STATUS_SUCCEEDED, settled_at=timezone.now(),
                failure_reason="Invoice could not absorb the payment.",
            )
            PaymentService._flag(
                intent, ReconciliationRecord.KIND_UNAPPLIED, provider_status="succeeded",
                provider_amount=intent.amount,
                detail=f"Invoice is {invoice.status} with balance {balance}; money taken but not applied.",
            )
            return "Payment could not be applied; flagged for reconciliation."

        now = timezone.now()
        payment = Payment.objects.create(
            tenant_id=intent.tenant_id, invoice=invoice, branch=invoice.branch,
            method=intent.method if intent.method in dict(Payment.METHOD_CHOICES) else Payment.METHOD_MOBILE,
            amount=intent.amount, reference=intent.provider_reference[:100], paid_at=now,
        )
        invoice.amount_paid = _money(invoice.amount_paid) + intent.amount
        fields = ["amount_paid", "updated_at"]
        if invoice.amount_paid + _TOLERANCE >= _money(invoice.total_amount):
            invoice.status = Invoice.STATUS_PAID
            fields.append("status")
        invoice.save(update_fields=fields)
        AccountingPostingService.post_customer_payment(payment=payment, invoice=invoice)
        PaymentService._transition(intent, PaymentIntent.STATUS_SUCCEEDED, payment=payment, settled_at=now)
        write_audit(
            action="update", module=MODULE, entity=intent, branch=intent.branch,
            new_values={"event": "payment_settled", "invoice": str(invoice.pk), "amount": str(intent.amount)},
        )
        # ERP subscription checkouts activate here — inside the verified, locked settlement only.
        from apps.platform.services.subscription_billing_service import SubscriptionBillingService

        note = SubscriptionBillingService.on_intent_settled(intent)
        return f"Settled. {note}" if note else "Settled."

    @staticmethod
    def _apply_failure(intent: PaymentIntent) -> str:
        if intent.status == PaymentIntent.STATUS_SUCCEEDED:
            PaymentService._flag(
                intent, ReconciliationRecord.KIND_STATUS, provider_status="failed",
                detail="Provider reports failure for an intent already settled locally.",
            )
            return "Intent already succeeded; flagged for reconciliation."
        if intent.status == PaymentIntent.STATUS_PENDING:
            PaymentService._transition(intent, PaymentIntent.STATUS_FAILED, failure_reason="Provider reported failure.")
            return "Marked failed."
        return f"Intent already {intent.status}."


class ReconciliationService:
    @staticmethod
    def record(intent, kind, *, provider_status="", provider_amount=None, detail="") -> ReconciliationRecord | None:
        """One open row per (intent, kind). Re-detecting the same problem is a no-op."""
        row = ReconciliationRecord(
            tenant_id=intent.tenant_id, branch_id=intent.branch_id, provider_id=intent.provider_id,
            intent=intent, kind=kind, provider_status=provider_status,
            provider_amount=None if provider_amount is None else _money(provider_amount),
            ledger_status=intent.status,
            ledger_amount=_money(intent.payment.amount) if intent.payment_id else None,
            detail=detail[:300],
        )
        try:
            with transaction.atomic():
                row.save()
        except IntegrityError:
            return None
        return row

    @staticmethod
    def run(*, tenant, branch_ids=None, provider=None, limit: int = 500) -> dict:
        """Compare provider truth with the ledger and *report*. Never changes an intent, invoice
        or journal. ``branch_ids=None`` means every branch (caller has cross-branch scope)."""
        from apps.finance.models import JournalEntry

        qs = PaymentIntent.objects.filter(tenant=tenant).exclude(provider_reference="").select_related(
            "provider", "payment"
        )
        if branch_ids is not None:
            qs = qs.filter(branch_id__in=list(branch_ids))
        if provider is not None:
            qs = qs.filter(provider=provider)
        summary = {"checked": 0, "unreachable": 0, "new_records": []}
        adapters: dict = {}

        def flag(intent, kind, **kw):
            row = ReconciliationService.record(intent, kind, **kw)
            if row is not None:
                summary["new_records"].append(str(row.pk))

        for intent in qs.order_by("-created_at")[:limit]:
            summary["checked"] += 1
            if intent.provider_id not in adapters:
                try:
                    adapters[intent.provider_id] = PaymentService.adapter(intent.provider, with_api_secret=True)
                except PaymentError:
                    adapters[intent.provider_id] = None
            adapter = adapters[intent.provider_id]
            remote = adapter.fetch_status(intent.provider_reference) if adapter else None
            if remote is None or remote.outcome != OK:
                summary["unreachable"] += 1
            else:
                ReconciliationService._compare_remote(intent, remote, flag)
            if intent.status == PaymentIntent.STATUS_SUCCEEDED:
                if intent.payment_id is None:
                    if not intent.reconciliations.filter(kind=ReconciliationRecord.KIND_UNAPPLIED).exists():
                        flag(intent, ReconciliationRecord.KIND_MISSING_PAYMENT, detail="Succeeded with no payment row.")
                else:
                    if _money(intent.payment.amount) != intent.amount:
                        flag(intent, ReconciliationRecord.KIND_AMOUNT, detail="Payment row differs from the intent.")
                    from apps.finance.services.cutover_service import AccountingCutoverService

                    if AccountingCutoverService.is_posting_enabled(tenant_id=intent.tenant_id) and not (
                        JournalEntry.objects.filter(
                            tenant_id=intent.tenant_id,
                            idempotency_key=f"CUSTOMER_PAYMENT_RECEIVED:sales:payment:{intent.payment_id}",
                        ).exists()
                    ):
                        flag(intent, ReconciliationRecord.KIND_MISSING_JOURNAL, detail="No journal entry for the payment.")
        summary["mismatches"] = len(summary["new_records"])
        return summary

    @staticmethod
    def _compare_remote(intent, remote, flag) -> None:
        local, theirs = intent.status, remote.status
        kind = None
        if theirs == "succeeded" and local in (PaymentIntent.STATUS_FAILED, PaymentIntent.STATUS_EXPIRED):
            kind = ReconciliationRecord.KIND_LATE_SUCCESS
        elif theirs == "succeeded" and local != PaymentIntent.STATUS_SUCCEEDED:
            kind = ReconciliationRecord.KIND_STATUS
        elif local == PaymentIntent.STATUS_SUCCEEDED and theirs != "succeeded":
            kind = ReconciliationRecord.KIND_STATUS
        elif theirs == "failed" and local == PaymentIntent.STATUS_PENDING:
            kind = ReconciliationRecord.KIND_STATUS
        if kind:
            flag(intent, kind, provider_status=theirs, provider_amount=remote.amount,
                 detail=f"Provider says {theirs}; ledger says {local}.")
        if remote.amount is not None and _money(remote.amount) != intent.amount:
            flag(intent, ReconciliationRecord.KIND_AMOUNT, provider_status=theirs, provider_amount=remote.amount,
                 detail="Provider amount differs from the intent.")

    @staticmethod
    @transaction.atomic
    def resolve(*, record: ReconciliationRecord, user, note: str, request=None) -> ReconciliationRecord:
        """Close a record after a human dealt with it (refund, journal fix, …). Records only."""
        if record.status != ReconciliationRecord.STATUS_OPEN:
            raise PaymentError("Record is already resolved.")
        if not (note or "").strip():
            raise PaymentError("A resolution note is required.")
        record.status = ReconciliationRecord.STATUS_RESOLVED
        record.resolved_by, record.resolved_at = user, timezone.now()
        record.resolution_note = note.strip()[:300]
        record.save()
        write_audit(
            action="update", module=MODULE, entity=record, user=user, request=request, branch=record.branch,
            new_values={"event": "reconciliation_resolved", "kind": record.kind},
        )
        return record

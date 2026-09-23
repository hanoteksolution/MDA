"""ERP subscription checkout with verified, automatic activation/renewal.

Flow (no parallel payment system — everything reuses the shared payment framework):

    plan chosen → SubscriptionPayment (the subscription invoice/payment request)
               → sales Invoice in Safari's house tenant (the billing provider's tenant)
               → PaymentIntent (PaymentService.create_intent)
    customer pays → provider webhook → HMAC + timestamp verified, event-id deduped
               → PaymentService._settle: Payment row + AR receipt journal (under the intent row lock)
               → SubscriptionBillingService.on_intent_settled: verify, then activate/renew once

Nothing else can confirm a checkout: no API accepts "paid" from a client, the legacy unsigned
Waafi callback is retired, and manual confirmation is a separate audited platform recovery that
refuses checkout rows (they have a verified path and a reconciliation workflow).

Idempotency: the intent is settled at most once (row lock + state machine, event-id dedupe);
the SubscriptionPayment is locked and applied only while ``pending``; accounting uses the posting
service's idempotency keys (invoice / payment ids); ``intent`` is one-to-one with the payment.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services.audit_write import write_audit
from apps.platform.models import SubscriptionPayment, SubscriptionPlan, Tenant, TenantSubscription

logger = logging.getLogger(__name__)

MODULE = "platform"
CHECKOUT_TTL_DAYS = 3


class SubscriptionBillingError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"))


class SubscriptionBillingService:
    # ── configuration ─────────────────────────────────────────────────────────
    @staticmethod
    def config() -> dict:
        from apps.platform.services.platform_service import PlatformService

        return PlatformService.get_subscription_payment_config()

    @staticmethod
    def billing_provider():
        from apps.integrations.models import PaymentProviderConfig

        pid = str(SubscriptionBillingService.config().get("payment_provider_id") or "").strip()
        if not pid:
            return None
        from apps.integrations.billing_guard import usable_billing_provider

        try:
            provider = PaymentProviderConfig.active_objects().filter(pk=pid, is_active=True).select_related("tenant", "branch").first()
        except (ValueError, Exception):  # malformed id stored in settings
            return None
        return usable_billing_provider(provider)  # MOCK in production → None (fail safe, no fallback)

    @staticmethod
    def currency() -> str:
        return str(SubscriptionBillingService.config().get("currency") or "USD").upper()[:3]

    # ── plan rules (existing entitlement limits; no proration exists) ─────────
    @staticmethod
    def plan_problem(sub: TenantSubscription, plan: SubscriptionPlan) -> str:
        """Why ``plan`` cannot be bought now, or ``""``. Reuses the entitlement user/branch limits."""
        if not plan.is_active or plan.deleted_at:
            return "This plan is not available."
        if _money(plan.monthly_price) <= 0:
            return "Free plans do not need payment."
        if plan.pk != sub.plan_id:
            if sub.status == TenantSubscription.STATUS_ACTIVE and sub.expires_at and sub.expires_at >= timezone.localdate():
                return ("Plan changes take effect at renewal: proration of an active paid period is not supported. "
                        "Renew your current plan, or change plan after it expires.")
            from apps.authentication.models import User
            from apps.settings_app.models import Branch

            users = User.objects.filter(tenant=sub.tenant, is_active=True, deleted_at__isnull=True).count()
            branches = Branch.objects.filter(tenant=sub.tenant, deleted_at__isnull=True).count()
            if users > plan.max_users or branches > plan.max_branches:
                return (f"{plan.name} allows {plan.max_users} users and {plan.max_branches} branches; "
                        f"you have {users} users and {branches} branches.")
        return ""

    @staticmethod
    def amount_for(sub: TenantSubscription, plan: SubscriptionPlan) -> Decimal:
        # Same plan keeps any negotiated fee (effective_monthly_fee); a new plan uses its list price.
        return _money(sub.effective_monthly_fee if plan.pk == sub.plan_id else plan.monthly_price)

    # ── checkout ──────────────────────────────────────────────────────────────
    @staticmethod
    def checkout(*, tenant: Tenant, plan_id, idempotency_key: str, user=None, request=None) -> tuple[SubscriptionPayment, bool]:
        from apps.integrations.services.payment_service import PaymentError, PaymentService

        key = (idempotency_key or "").strip()
        if not key or len(key) > 64:
            raise SubscriptionBillingError("An idempotency key (1–64 characters) is required.")
        sub = TenantSubscription.active_objects().filter(tenant=tenant).select_related("plan", "tenant").first()
        if sub is None:
            raise SubscriptionBillingError("This workspace has no subscription record. Contact support.")
        replay = SubscriptionPayment.active_objects().filter(subscription=sub, idempotency_key=key).first()
        if replay is not None:
            if str(replay.plan_id) != str(plan_id):
                raise SubscriptionBillingError("This idempotency key was already used for a different checkout.")
            return replay, False
        if sub.status == TenantSubscription.STATUS_SUSPENDED:
            raise SubscriptionBillingError("This subscription is suspended. Contact support.")
        plan = SubscriptionPlan.active_objects().filter(pk=plan_id).first()
        if plan is None:
            raise SubscriptionBillingError("Plan not found.")
        problem = SubscriptionBillingService.plan_problem(sub, plan)
        if problem:
            raise SubscriptionBillingError(problem)
        provider = SubscriptionBillingService.billing_provider()
        if provider is None:
            raise SubscriptionBillingError("Online subscription payment is not available yet. Contact support.")
        currency = SubscriptionBillingService.currency()
        if str(provider.config.get("currency") or "USD").upper()[:3] != currency:
            raise SubscriptionBillingError("Subscription billing is misconfigured (currency). Contact support.")
        amount = SubscriptionBillingService.amount_for(sub, plan)

        with transaction.atomic():
            TenantSubscription.objects.select_for_update().get(pk=sub.pk)
            # One open checkout per subscription: an older one is superseded (its invoice cancelled,
            # so a late payment on it can never activate anything — it goes to reconciliation).
            for old in SubscriptionPayment.objects.select_for_update().filter(
                subscription=sub, status=SubscriptionPayment.STATUS_PENDING, intent__isnull=False
            ):
                SubscriptionBillingService._supersede(old)
            try:
                with transaction.atomic():
                    payment = SubscriptionPayment.objects.create(
                        subscription=sub, payment_reference=SubscriptionBillingService._reference(sub),
                        amount=amount, currency=currency, plan=plan, idempotency_key=key,
                        kind=SubscriptionPayment.KIND_RENEW if plan.pk == sub.plan_id else SubscriptionPayment.KIND_NEW_PLAN,
                        period_key=sub.payment_period_key(), status=SubscriptionPayment.STATUS_PENDING,
                        reported_by=user, created_by=user,
                    )
            except IntegrityError:
                return SubscriptionPayment.objects.get(subscription=sub, idempotency_key=key), False
            payment.invoice = SubscriptionBillingService._issue_invoice(payment, provider, sub, plan)
            payment.save(update_fields=["invoice", "updated_at"])

        try:
            intent, _ = PaymentService.create_intent(
                tenant=provider.tenant, invoice=payment.invoice, idempotency_key=f"sub-{payment.pk}",
                amount=amount, provider_id=provider.pk, user=None, request=request,
            )
        except PaymentError as exc:
            payment.status, payment.failure_reason = SubscriptionPayment.STATUS_FAILED, str(exc)[:300]
            payment.save(update_fields=["status", "failure_reason", "updated_at"])
            SubscriptionBillingService._cancel_invoice(payment)
            return payment, True
        payment.intent = intent
        fields = ["intent", "updated_at"]
        if intent.status == intent.STATUS_FAILED:
            payment.status, payment.failure_reason = SubscriptionPayment.STATUS_FAILED, (intent.failure_reason or "Provider error.")[:300]
            fields += ["status", "failure_reason"]
        payment.save(update_fields=fields)
        write_audit(
            action="create", module=MODULE, entity=payment, user=user, request=request,
            new_values={"event": "subscription_checkout", "subscription": sub.reference_code, "plan": plan.code,
                        "amount": str(amount), "currency": currency, "status": payment.status},
        )
        return payment, True

    @staticmethod
    def customer_code(tenant) -> str:
        """The house-tenant customer that represents one subscribing tenant."""
        return f"SUB-{tenant.pk}"[:50]

    @staticmethod
    def _reference(sub) -> str:
        base = f"{sub.reference_code}-{timezone.now():%Y%m%d%H%M%S}"[:58]
        ref, n = base, 1
        while SubscriptionPayment.objects.filter(payment_reference=ref).exists():
            ref, n = f"{base}-{n}", n + 1
        return ref

    @staticmethod
    def _issue_invoice(payment, provider, sub, plan):
        """A receivable in Safari's house-tenant books. Nothing is posted until verified payment."""
        from apps.customers.models import Customer
        from apps.sales.models import DocumentSequence, Invoice
        from apps.sales.services.sequence_service import DocumentSequenceService
        from apps.settings_app.models import Branch

        house = provider.tenant
        branch = provider.branch or Branch.objects.filter(tenant=house, deleted_at__isnull=True).order_by("-is_default", "created_at").first()
        if branch is None:
            raise SubscriptionBillingError("Subscription billing is misconfigured (no billing branch). Contact support.")
        customer, _ = Customer.objects.get_or_create(
            tenant=house, customer_code=SubscriptionBillingService.customer_code(sub.tenant),
            defaults={"full_name": sub.tenant.name[:255], "branch": branch},
        )
        number = DocumentSequenceService.allocate(branch=branch, kind=DocumentSequence.KIND_INVOICE)["number"]
        today = timezone.localdate()
        return Invoice.objects.create(
            tenant=house, branch=branch, customer=customer, invoice_number=number, status=Invoice.STATUS_SENT,
            issue_date=today, due_date=today + timedelta(days=CHECKOUT_TTL_DAYS), subtotal=payment.amount,
            total_amount=payment.amount, notes=f"ERP subscription {sub.reference_code} — {plan.name} ({payment.payment_reference})",
            idempotency_key=f"sub-{payment.pk}",
        )

    @staticmethod
    def _cancel_invoice(payment):
        from apps.sales.models import Invoice

        if payment.invoice_id:
            Invoice.objects.filter(pk=payment.invoice_id, amount_paid=0).exclude(status=Invoice.STATUS_PAID).update(
                status=Invoice.STATUS_CANCELLED, updated_at=timezone.now()
            )

    @staticmethod
    def _supersede(old: SubscriptionPayment):
        from apps.integrations.models import PaymentIntent
        from apps.integrations.services.payment_service import PaymentService

        old.status, old.failure_reason = SubscriptionPayment.STATUS_EXPIRED, "Superseded by a newer checkout."
        old.save(update_fields=["status", "failure_reason", "updated_at"])
        if old.intent_id:
            intent = PaymentIntent.objects.select_for_update().get(pk=old.intent_id)
            if intent.status in (intent.STATUS_CREATED, intent.STATUS_PENDING):
                PaymentService._transition(intent, intent.STATUS_EXPIRED)
        SubscriptionBillingService._cancel_invoice(old)

    @staticmethod
    def expire_stale(now=None) -> int:
        """Pending checkouts whose intent has expired can never activate; mark them so."""
        from apps.integrations.models import PaymentIntent

        count = 0
        for payment in SubscriptionPayment.objects.filter(
            status=SubscriptionPayment.STATUS_PENDING, intent__status__in=(PaymentIntent.STATUS_EXPIRED, PaymentIntent.STATUS_FAILED)
        ):
            with transaction.atomic():
                row = SubscriptionPayment.objects.select_for_update().get(pk=payment.pk)
                if row.status == SubscriptionPayment.STATUS_PENDING:
                    row.status = SubscriptionPayment.STATUS_EXPIRED if row.intent.status == PaymentIntent.STATUS_EXPIRED else SubscriptionPayment.STATUS_FAILED
                    row.save(update_fields=["status", "updated_at"])
                    SubscriptionBillingService._cancel_invoice(row)
                    count += 1
        return count

    # ── verified settlement hook (called only from PaymentService._settle) ────
    @staticmethod
    def on_intent_settled(intent) -> str | None:
        """Caller holds the intent row lock inside the settlement transaction, after the Payment row
        and AR receipt were created. ``None`` = the intent is not a subscription checkout."""
        payment = SubscriptionPayment.objects.select_for_update().filter(intent_id=intent.pk).first()
        if payment is None:
            return None
        if payment.status == SubscriptionPayment.STATUS_CONFIRMED:
            return "Subscription already applied."
        sub = TenantSubscription.objects.select_for_update(of=("self",)).select_related("plan", "tenant").get(pk=payment.subscription_id)
        problem = SubscriptionBillingService._verify(payment, intent, sub)
        if problem:
            return SubscriptionBillingService._review(payment, intent, problem)
        invoice = intent.invoice
        from apps.finance.services.posting_service import AccountingPostingService

        # Revenue for the paid invoice (Dr AR / Cr Revenue); _settle already posted Dr Cash / Cr AR.
        AccountingPostingService.post_sale(
            invoice=invoice, payment_method="on_account",
            tender_lines=[{"method": "on_account", "amount": str(invoice.total_amount), "reference": payment.payment_reference}],
        )
        before = {"plan": sub.plan.code, "status": sub.status, "expires_at": sub.expires_at.isoformat() if sub.expires_at else None}
        if payment.plan_id and payment.plan_id != sub.plan_id:
            sub.plan, sub.monthly_fee = payment.plan, None
            sub.save(update_fields=["plan", "monthly_fee", "updated_at"])
        from apps.platform.services.platform_service import PlatformService

        # Existing renewal policy: extend from the current expiry if still running, else from today.
        PlatformService.renew_subscription(subscription=sub, notes=f"Renewed by verified payment {payment.payment_reference}")
        payment.status, payment.confirmed_at, payment.auto_renewed = SubscriptionPayment.STATUS_CONFIRMED, timezone.now(), True
        payment.external_transaction_id = (intent.provider_reference or "")[:100]
        payment.save(update_fields=["status", "confirmed_at", "auto_renewed", "external_transaction_id", "updated_at"])
        write_audit(
            action="update", module=MODULE, entity=sub, old_values=before,
            new_values={"event": "subscription_activated_by_verified_payment", "payment": payment.payment_reference,
                        "intent": str(intent.pk), "plan": sub.plan.code, "status": sub.status,
                        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None},
        )
        SubscriptionBillingService._notify(sub, payment)
        return "Subscription activated."

    @staticmethod
    def _verify(payment, intent, sub) -> str:
        """Every identity and money check that must hold before activation."""
        provider = SubscriptionBillingService.billing_provider()
        if payment.status != SubscriptionPayment.STATUS_PENDING:
            return f"Subscription payment is {payment.status}."
        if provider is None or intent.provider_id != provider.pk:
            return "Payment came through a provider that is not the subscription billing provider."
        if intent.tenant_id != provider.tenant_id:
            return "Payment tenant does not match the billing account."
        if intent.status != intent.STATUS_SUCCEEDED or not intent.payment_id:
            return "Payment intent is not settled."
        if intent.invoice_id != payment.invoice_id:
            return "Payment is for a different invoice."
        if sub.tenant_id is None or intent.invoice.customer.customer_code != SubscriptionBillingService.customer_code(sub.tenant):
            return "Invoice customer does not match the subscribing tenant."
        if _money(intent.amount) != _money(payment.amount) or _money(intent.invoice.total_amount) != _money(payment.amount):
            return "Paid amount does not match the subscription price."
        if (intent.currency or "").upper() != (payment.currency or "").upper():
            return "Paid currency does not match the subscription currency."
        if sub.status == TenantSubscription.STATUS_SUSPENDED:
            return "Subscription is suspended."
        return ""

    @staticmethod
    def _review(payment, intent, problem) -> str:
        from apps.integrations.models import ReconciliationRecord
        from apps.integrations.services.payment_service import ReconciliationService

        payment.status, payment.failure_reason = SubscriptionPayment.STATUS_REVIEW, problem[:300]
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        ReconciliationService.record(
            intent, ReconciliationRecord.KIND_UNAPPLIED, provider_status="succeeded",
            provider_amount=intent.amount, detail=f"Subscription not activated: {problem}",
        )
        write_audit(
            action="update", module=MODULE, entity=payment,
            new_values={"event": "subscription_payment_review", "reason": problem[:300]},
        )
        return f"Subscription not activated: {problem}"

    @staticmethod
    def _notify(sub, payment):
        try:
            from apps.notifications.services.notification_service import NotificationService

            NotificationService.notify_tenant_permission(
                tenant=sub.tenant, permission_codename="billing.subscription.view",
                notification_type="subscription", title="Subscription payment received",
                message=f"{sub.plan.name} is active until {sub.expires_at:%Y-%m-%d}. Reference {payment.payment_reference}.",
                link="/billing", dedupe_key=f"subscription-paid:{payment.pk}",
            )
        except Exception:  # noqa: BLE001 - a notification problem must never roll back a settled payment
            logger.warning("subscription payment notification failed for %s", payment.pk)

    # ── manual recovery (platform only, audited, never for checkout rows) ────
    @staticmethod
    def manual_confirm(*, payment: SubscriptionPayment, reason: str, user, request=None, **fields) -> SubscriptionPayment:
        from apps.platform.services.platform_service import PlatformService

        reason = (reason or "").strip()
        if not reason:
            raise SubscriptionBillingError("A reason is required for manual confirmation.")
        if payment.intent_id:
            raise SubscriptionBillingError(
                "Online checkouts are confirmed only by the verified provider webhook. "
                "Use payment reconciliation for discrepancies."
            )
        before = {"status": payment.status}
        payment = PlatformService.confirm_subscription_payment(payment=payment, notes=f"Manual confirmation: {reason}", user=user, **fields)
        write_audit(
            action="update", module=MODULE, entity=payment, user=user, request=request, old_values=before,
            new_values={"event": "subscription_payment_manual_confirm", "reason": reason[:300], "status": payment.status},
        )
        return payment

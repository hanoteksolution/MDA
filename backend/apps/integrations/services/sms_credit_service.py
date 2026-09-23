"""SMS reseller credits: reserve on acceptance, charge on SENT, release on FAILED.

Invariants:

* Balance = remaining units in unexpired lots; it can never go negative (lots are
  ``PositiveIntegerField``; a reservation that does not fit fails the message instead).
* Every lot movement writes one immutable ``SmsCreditEntry`` inside the same transaction, while
  the tenant's ``SmsCreditAccount`` row is locked — concurrent sends cannot oversell.
* A purchase is credited only by ``SmsPurchaseService.apply_event`` (verified provider webhook),
  exactly once (``SmsCreditLot.purchase`` is one-to-one, plus a unique purchase ledger entry).
* Enforcement is controlled by ``settings.SMS_CREDITS_ENFORCED``.
"""

from __future__ import annotations

import logging
import math
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.audit.services.audit_write import write_audit
from apps.integrations.models import (
    PaymentProviderConfig,
    SmsBillingSettings,
    SmsCreditAccount,
    SmsCreditEntry,
    SmsCreditLot,
    SmsLog,
    SmsPackage,
    SmsPackagePurchase,
)
from apps.integrations.providers.payment_base import OK

logger = logging.getLogger(__name__)

MODULE = "integrations"
PURCHASE_TTL = timedelta(hours=24)
_GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\\[~]|€"
)


class SmsCreditError(ValueError):
    pass


def enforced() -> bool:
    return bool(getattr(settings, "SMS_CREDITS_ENFORCED", True))


def sms_segments(body: str) -> int:
    """Billable segments: GSM-7 160/153, otherwise UCS-2 70/67."""
    text = body or ""
    if all(ch in _GSM7 for ch in text):
        length = len(text) + sum(1 for ch in text if ch in "^{}\\[~]|€")  # extension chars cost 2
        single, multi = 160, 153
    else:
        length, single, multi = len(text), 70, 67
    if length <= single:
        return 1
    return math.ceil(length / multi)


class SmsCreditService:
    # ── reads ─────────────────────────────────────────────────────────────────
    @staticmethod
    def live_lots(tenant_id, now=None):
        now = now or timezone.now()
        return SmsCreditLot.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True, units_remaining__gt=0).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )

    @staticmethod
    def balance(tenant_id, now=None) -> int:
        return SmsCreditService.live_lots(tenant_id, now).aggregate(s=Sum("units_remaining"))["s"] or 0

    @staticmethod
    def summary(tenant_id) -> dict:
        now = timezone.now()
        since = now - timedelta(days=30)
        entries = SmsCreditEntry.objects.filter(tenant_id=tenant_id)
        charged = SmsLog.objects.filter(tenant_id=tenant_id, credit_state=SmsLog.CREDIT_CHARGED)
        return {
            "balance": SmsCreditService.balance(tenant_id, now),
            "reserved": SmsLog.objects.filter(tenant_id=tenant_id, credit_state=SmsLog.CREDIT_RESERVED)
            .aggregate(s=Sum("credit_units"))["s"] or 0,
            "used_30d": charged.filter(sent_at__gte=since).aggregate(s=Sum("credit_units"))["s"] or 0,
            "used_total": charged.aggregate(s=Sum("credit_units"))["s"] or 0,
            "purchased_total": entries.filter(kind=SmsCreditEntry.KIND_PURCHASE).aggregate(s=Sum("units"))["s"] or 0,
            "next_expiry": [
                {"units": lot.units_remaining, "expires_at": lot.expires_at.isoformat()}
                for lot in SmsCreditService.live_lots(tenant_id, now).exclude(expires_at__isnull=True).order_by("expires_at")[:5]
            ],
            "enforced": enforced(),
        }

    # ── core movements (caller must hold the account lock) ────────────────────
    @staticmethod
    def _lock(tenant_id) -> SmsCreditAccount:
        SmsCreditAccount.objects.get_or_create(tenant_id=tenant_id)
        return SmsCreditAccount.objects.select_for_update().get(tenant_id=tenant_id)

    @staticmethod
    def _entry(tenant_id, kind, units, **fields) -> SmsCreditEntry:
        return SmsCreditEntry.objects.create(
            tenant_id=tenant_id, kind=kind, units=units,
            balance_after=SmsCreditService.balance(tenant_id), **fields,
        )

    @staticmethod
    def _draw(tenant_id, units) -> dict:
        """Take ``units`` from live lots, soonest-expiring first. Raises when they do not fit."""
        lots = list(
            SmsCreditService.live_lots(tenant_id).select_for_update().order_by(
                models_nulls_last("expires_at"), "created_at"
            )
        )
        if sum(lot.units_remaining for lot in lots) < units:
            raise SmsCreditError("Insufficient SMS credits.")
        taken, need = {}, units
        for lot in lots:
            if not need:
                break
            n = min(lot.units_remaining, need)
            lot.units_remaining -= n
            lot.save(update_fields=["units_remaining", "updated_at"])
            taken[str(lot.pk)] = n
            need -= n
        return taken

    @staticmethod
    def _grant(tenant_id, units, *, expires_at=None, purchase=None, kind, reason="", user=None) -> SmsCreditEntry:
        lot = SmsCreditLot.objects.create(
            tenant_id=tenant_id, purchase=purchase, units_total=units, units_remaining=units,
            expires_at=expires_at, created_by=user,
        )
        return SmsCreditService._entry(
            tenant_id, kind, units, lot=lot, purchase=purchase, reason=reason[:300],
            allocations={str(lot.pk): units}, created_by=user,
        )

    # ── SMS lifecycle hooks (called by SmsService) ────────────────────────────
    @staticmethod
    def reserve(log: SmsLog) -> str:
        """Reserve credits for a QUEUED log. Returns an error string when it cannot be sent."""
        if not enforced():
            return ""
        units = sms_segments(log.body)
        with transaction.atomic():
            SmsCreditService._lock(log.tenant_id)
            try:
                taken = SmsCreditService._draw(log.tenant_id, units)
            except SmsCreditError as exc:
                return str(exc)
            log.credit_units, log.credit_state = units, SmsLog.CREDIT_RESERVED
            log.save(update_fields=["credit_units", "credit_state", "updated_at"])
            SmsCreditService._entry(
                log.tenant_id, SmsCreditEntry.KIND_RESERVE, -units, sms_log=log, allocations=taken,
                reason=f"SMS to {log.to_number[-4:].rjust(len(log.to_number), '•')}"[:300],
            )
        return ""

    @staticmethod
    def settle(log: SmsLog) -> None:
        """Called after a terminal result: SENT keeps the charge, FAILED returns it."""
        if log.credit_state != SmsLog.CREDIT_RESERVED:
            return
        if log.status == SmsLog.STATUS_SENT:
            log.credit_state = SmsLog.CREDIT_CHARGED
            log.save(update_fields=["credit_state", "updated_at"])
        elif log.status == SmsLog.STATUS_FAILED:
            SmsCreditService.release(log)

    @staticmethod
    def release(log: SmsLog) -> None:
        with transaction.atomic():
            SmsCreditService._lock(log.tenant_id)
            locked = SmsLog.objects.select_for_update().get(pk=log.pk)
            if locked.credit_state != SmsLog.CREDIT_RESERVED:
                return
            reserve = SmsCreditEntry.objects.get(sms_log=locked, kind=SmsCreditEntry.KIND_RESERVE)
            for lot_id, n in reserve.allocations.items():
                lot = SmsCreditLot.objects.select_for_update().get(pk=lot_id)
                lot.units_remaining += n  # back into the same lot; its expiry still applies
                lot.save(update_fields=["units_remaining", "updated_at"])
            locked.credit_state = SmsLog.CREDIT_RELEASED
            locked.save(update_fields=["credit_state", "updated_at"])
            log.credit_state = locked.credit_state
            SmsCreditService._entry(
                locked.tenant_id, SmsCreditEntry.KIND_RELEASE, locked.credit_units, sms_log=locked,
                allocations=reserve.allocations, reason="Not delivered; credits returned.",
            )

    # ── platform adjustments & expiry ─────────────────────────────────────────
    @staticmethod
    def adjust(*, tenant, units: int, reason: str, user, request=None, expires_at=None) -> SmsCreditEntry:
        reason = (reason or "").strip()
        if not reason:
            raise SmsCreditError("A reason is required for manual adjustments.")
        if not isinstance(units, int) or isinstance(units, bool) or units == 0:
            raise SmsCreditError("Units must be a non-zero whole number.")
        with transaction.atomic():
            SmsCreditService._lock(tenant.pk)
            if units > 0:
                entry = SmsCreditService._grant(
                    tenant.pk, units, expires_at=expires_at, kind=SmsCreditEntry.KIND_ADJUST_CREDIT, reason=reason, user=user,
                )
            else:
                taken = SmsCreditService._draw(tenant.pk, -units)  # never below zero
                entry = SmsCreditService._entry(
                    tenant.pk, SmsCreditEntry.KIND_ADJUST_DEBIT, units, allocations=taken, reason=reason[:300], created_by=user,
                )
            write_audit(
                action="update", module=MODULE, entity=entry, user=user, request=request,
                new_values={"event": "sms_credit_adjustment", "units": units, "reason": reason[:300],
                            "balance_after": entry.balance_after},
            )
        return entry

    @staticmethod
    def expire_due(now=None) -> int:
        now = now or timezone.now()
        expired = 0
        for tenant_id in set(
            SmsCreditLot.objects.filter(units_remaining__gt=0, expires_at__lte=now).values_list("tenant_id", flat=True)
        ):
            with transaction.atomic():
                SmsCreditService._lock(tenant_id)
                for lot in SmsCreditLot.objects.select_for_update().filter(
                    tenant_id=tenant_id, units_remaining__gt=0, expires_at__lte=now
                ):
                    units = lot.units_remaining
                    lot.units_remaining = 0
                    lot.save(update_fields=["units_remaining", "updated_at"])
                    SmsCreditService._entry(
                        tenant_id, SmsCreditEntry.KIND_EXPIRE, -units, lot=lot, allocations={str(lot.pk): units},
                        reason="Package validity ended.",
                    )
                    expired += units
        return expired


def models_nulls_last(field):
    from django.db.models import F

    return F(field).asc(nulls_last=True)


class SmsPurchaseService:
    @staticmethod
    def billing_provider() -> PaymentProviderConfig | None:
        from apps.integrations.billing_guard import usable_billing_provider

        return usable_billing_provider(SmsBillingSettings.load().payment_provider)

    @staticmethod
    def create(*, tenant, package_id, idempotency_key, user=None, request=None) -> tuple[SmsPackagePurchase, bool]:
        """Start a purchase. Replaying a key returns the original purchase unchanged. Never credits."""
        from apps.integrations.services.payment_service import PaymentError, PaymentService

        key = (idempotency_key or "").strip()
        if not key or len(key) > 64:
            raise SmsCreditError("An idempotency key (1–64 characters) is required.")
        existing = SmsPackagePurchase.objects.filter(tenant=tenant, idempotency_key=key).first()
        if existing is not None:
            if str(existing.package_id) != str(package_id):
                raise SmsCreditError("This idempotency key was already used for a different purchase.")
            return existing, False
        package = SmsPackage.active_objects().filter(pk=package_id, is_active=True).first()
        if package is None:
            raise SmsCreditError("Package not available.")
        provider = SmsPurchaseService.billing_provider()
        if provider is None:
            raise SmsCreditError("SMS package payments are not available yet. Contact support.")
        try:
            with transaction.atomic():
                purchase = SmsPackagePurchase.objects.create(
                    tenant=tenant, package=package, package_name=package.name, sms_quantity=package.sms_quantity,
                    price=package.price, currency=package.currency, validity_days=package.validity_days,
                    idempotency_key=key, provider=provider, created_by=user,
                )
        except IntegrityError:
            return SmsPackagePurchase.objects.get(tenant=tenant, idempotency_key=key), False
        try:
            result = PaymentService.adapter(provider, with_api_secret=True).create_payment(
                amount=purchase.price, currency=purchase.currency, reference=f"sms-{purchase.pk}"
            )
        except PaymentError as exc:
            result = None
            purchase.failure_reason = str(exc)[:300]
        except Exception:  # noqa: BLE001 - an adapter bug must not break the caller
            logger.exception("sms package payment create crashed for %s", purchase.pk)
            result = None
            purchase.failure_reason = "Provider error."
        if result is not None and result.outcome == OK and result.reference:
            purchase.provider_reference = result.reference[:190]
        else:
            purchase.status = SmsPackagePurchase.STATUS_FAILED
            purchase.failure_reason = purchase.failure_reason or ((result.error if result else "") or "Provider error.")[:300]
        purchase.save(update_fields=["provider_reference", "status", "failure_reason", "updated_at"])
        write_audit(
            action="create", module=MODULE, entity=purchase, user=user, request=request,
            new_values={"event": "sms_package_purchase", "package": package.code, "price": str(package.price),
                        "status": purchase.status},
        )
        return purchase, True

    @staticmethod
    def apply_event(provider, parsed) -> str | None:
        """Apply a *verified* provider event to an SMS purchase. ``None`` = not an SMS purchase.
        Caller (``PaymentService.process_event``) holds a transaction."""
        purchase = SmsPackagePurchase.objects.select_for_update().filter(
            provider=provider, provider_reference=parsed.reference
        ).first()
        if purchase is None:
            return None
        if parsed.kind == "failed":
            if purchase.status == SmsPackagePurchase.STATUS_PENDING:
                purchase.status, purchase.failure_reason = SmsPackagePurchase.STATUS_FAILED, "Provider reported failure."
                purchase.save(update_fields=["status", "failure_reason", "updated_at"])
                return "SMS purchase marked failed."
            return f"SMS purchase already {purchase.status}."
        if parsed.kind != "succeeded":
            return "Event type not handled."
        if purchase.status == SmsPackagePurchase.STATUS_CREDITED:
            return "SMS purchase already credited."
        if purchase.status != SmsPackagePurchase.STATUS_PENDING:
            SmsPurchaseService._review(purchase, f"Provider reports success but the purchase is {purchase.status}.")
            return "SMS purchase flagged for review."
        if parsed.amount is None or Decimal(str(parsed.amount)).quantize(Decimal("0.0001")) != purchase.price:
            SmsPurchaseService._review(purchase, "Confirmed amount differs from the package price.")
            return "SMS purchase amount mismatch; not credited."
        SmsCreditService._lock(purchase.tenant_id)
        expires = timezone.now() + timedelta(days=purchase.validity_days) if purchase.validity_days else None
        SmsCreditService._grant(
            purchase.tenant_id, purchase.sms_quantity, expires_at=expires, purchase=purchase,
            kind=SmsCreditEntry.KIND_PURCHASE, reason=f"Package {purchase.package_name}",
        )
        purchase.status, purchase.credited_at = SmsPackagePurchase.STATUS_CREDITED, timezone.now()
        purchase.save(update_fields=["status", "credited_at", "updated_at"])
        write_audit(
            action="update", module=MODULE, entity=purchase,
            new_values={"event": "sms_package_credited", "units": purchase.sms_quantity},
        )
        return "SMS purchase credited."

    @staticmethod
    def _review(purchase, reason):
        purchase.status, purchase.failure_reason = SmsPackagePurchase.STATUS_REVIEW, reason[:300]
        purchase.save(update_fields=["status", "failure_reason", "updated_at"])

    @staticmethod
    def expire_stale(now=None) -> int:
        now = now or timezone.now()
        return SmsPackagePurchase.objects.filter(
            status=SmsPackagePurchase.STATUS_PENDING, created_at__lte=now - PURCHASE_TTL
        ).update(status=SmsPackagePurchase.STATUS_EXPIRED, updated_at=now)

"""Platform Admin → Billing: read models over the existing subscription/payment architecture.

Nothing here creates money. Every figure comes from existing rows: ``TenantSubscription``,
``SubscriptionPayment`` (legacy requests and verified online checkouts), the house-tenant sales
``Invoice`` a checkout issues, ``ReconciliationRecord`` and ``AuditLog``. Revenue is reported only
where the ledger backs it (paid checkout invoices); manually confirmed legacy payments are shown
separately because they never posted to the books.

The one write is ``recover``: an exceptional Super Admin extension of a subscription. It is
reason-required and audited, and it never creates a payment, invoice or intent.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services.audit_write import write_audit
from apps.integrations.models import ReconciliationRecord
from apps.platform.models import SubscriptionPayment, SubscriptionPlan, Tenant, TenantSubscription

MODULE = "platform"

# Derived billing state of a subscription (not stored): most urgent first.
BILLING_REVIEW = "review"
BILLING_PENDING = "pending"
BILLING_OVERDUE = "overdue"
BILLING_DUE_SOON = "due_soon"
BILLING_FAILED = "failed"
BILLING_CURRENT = "current"
BILLING_NONE = "no_billing"
BILLING_STATUSES = (BILLING_REVIEW, BILLING_PENDING, BILLING_OVERDUE, BILLING_DUE_SOON, BILLING_FAILED, BILLING_CURRENT, BILLING_NONE)

PAYMENT_KINDS = {"checkout": True, "manual": False}


class PlatformBillingError(ValueError):
    pass


def is_super_admin(user) -> bool:
    """Super Admin proper — a Platform Admin role (also flagged superuser by bootstrap) is not enough."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    slug = user._role_slug() if hasattr(user, "_role_slug") else None
    if slug == "super_admin":
        return True
    return bool(getattr(user, "is_superuser", False)) and slug != "platform_admin"


def _money(value) -> str | None:
    return None if value is None else str(Decimal(value).quantize(Decimal("0.01")))


def _iso(value):
    return value.isoformat() if value else None


def _page(params, rows: list) -> dict:
    try:
        page = max(1, int(params.get("page") or 1))
        size = min(100, max(1, int(params.get("page_size") or 25)))
    except (TypeError, ValueError):
        page, size = 1, 25
    start = (page - 1) * size
    return {"count": len(rows), "page": page, "page_size": size, "results": rows[start:start + size]}


def _latest_payment_qs():
    return SubscriptionPayment.objects.filter(subscription=OuterRef("pk"), deleted_at__isnull=True).order_by("-created_at")


def _subscriptions():
    latest = _latest_payment_qs()
    confirmed = latest.filter(status=SubscriptionPayment.STATUS_CONFIRMED)
    return (
        TenantSubscription.objects.filter(deleted_at__isnull=True)
        .select_related("plan", "tenant", "tenant__shop_group")
        .annotate(
            latest_payment_status=Subquery(latest.values("status")[:1]),
            last_payment_amount=Subquery(confirmed.values("amount")[:1]),
            last_payment_at=Subquery(confirmed.values("confirmed_at")[:1]),
        )
    )


def billing_status(sub) -> str:
    latest = getattr(sub, "latest_payment_status", None)
    if latest == SubscriptionPayment.STATUS_REVIEW:
        return BILLING_REVIEW
    if latest == SubscriptionPayment.STATUS_PENDING:
        return BILLING_PENDING
    if sub.status != TenantSubscription.STATUS_SUSPENDED and sub.expires_at and sub.expires_at < timezone.localdate():
        return BILLING_OVERDUE
    if sub.needs_payment_alert:
        return BILLING_DUE_SOON
    if latest == SubscriptionPayment.STATUS_FAILED:
        return BILLING_FAILED
    if latest is None and not sub.last_paid_at:
        return BILLING_NONE
    return BILLING_CURRENT


def _expiring_soon(sub) -> bool:
    days = sub.days_until_expiry
    return (
        sub.status in (TenantSubscription.STATUS_ACTIVE, TenantSubscription.STATUS_TRIAL)
        and days is not None and 0 <= days <= max(sub.warning_days, 7)
    )


def subscription_row(sub) -> dict:
    tenant = sub.tenant if sub.tenant_id else None
    return {
        "id": str(sub.id),
        "reference_code": sub.reference_code,
        "tenant_id": str(tenant.id) if tenant else None,
        "tenant_name": tenant.name if tenant else None,
        "tenant_slug": tenant.slug if tenant else None,
        "workspace": tenant.shop_group.name if tenant and tenant.shop_group_id else None,
        "plan_code": sub.plan.code,
        "plan_name": sub.plan.name,
        "status": sub.status,
        "billing_status": billing_status(sub),
        "monthly_fee": _money(sub.effective_monthly_fee),
        "started_at": _iso(sub.started_at),
        "expires_at": _iso(sub.expires_at),
        # Existing renewal policy: the next charge falls due at expiry (suspended = nothing due).
        "next_billing_at": _iso(sub.expires_at) if sub.status != TenantSubscription.STATUS_SUSPENDED else None,
        "days_until_expiry": sub.days_until_expiry,
        "last_paid_at": _iso(sub.last_paid_at),
        "last_payment_amount": _money(getattr(sub, "last_payment_amount", None)),
        "last_payment_at": _iso(getattr(sub, "last_payment_at", None)),
        "is_usable": sub.is_usable,
    }


def payment_row(p: SubscriptionPayment) -> dict:
    sub = p.subscription
    inv = p.invoice if p.invoice_id else None
    return {
        "id": str(p.id),
        "payment_reference": p.payment_reference,
        "subscription_id": str(sub.id),
        "reference_code": sub.reference_code,
        "tenant_id": str(sub.tenant_id) if sub.tenant_id else None,
        "tenant_name": sub.tenant.name if sub.tenant_id else None,
        "plan_name": (p.plan or sub.plan).name,
        "kind": "checkout" if p.intent_id else "manual",
        "amount": _money(p.amount),
        "currency": p.currency or None,
        "status": p.status,
        "created_at": _iso(p.created_at),
        "confirmed_at": _iso(p.confirmed_at),
        "auto_renewed": p.auto_renewed,
        "external_transaction_id": p.external_transaction_id,
        "failure_reason": p.failure_reason,
        "invoice_number": inv.invoice_number if inv else None,
        "intent_status": p.intent.status if p.intent_id else None,
    }


def invoice_row(p: SubscriptionPayment) -> dict:
    inv = p.invoice
    sub = p.subscription
    return {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "payment_id": str(p.id),
        "payment_reference": p.payment_reference,
        "tenant_id": str(sub.tenant_id) if sub.tenant_id else None,
        "tenant_name": sub.tenant.name if sub.tenant_id else None,
        "plan_name": (p.plan or sub.plan).name,
        "status": inv.status,
        "issue_date": _iso(inv.issue_date),
        "due_date": _iso(inv.due_date),
        "total_amount": _money(inv.total_amount),
        "amount_paid": _money(inv.amount_paid),
        "currency": p.currency or None,
        "payment_status": p.status,
    }


def reconciliation_row(r: ReconciliationRecord) -> dict:
    p = getattr(r.intent, "subscription_payment", None)
    sub = p.subscription if p else None
    return {
        "id": str(r.id),
        "kind": r.kind,
        "kind_label": r.get_kind_display(),
        "status": r.status,
        "tenant_id": str(sub.tenant_id) if sub and sub.tenant_id else None,
        "tenant_name": sub.tenant.name if sub and sub.tenant_id else None,
        "payment_reference": p.payment_reference if p else None,
        "provider_status": r.provider_status,
        "provider_amount": _money(r.provider_amount),
        "ledger_status": r.ledger_status,
        "ledger_amount": _money(r.ledger_amount),
        "detail": r.detail,
        "created_at": _iso(r.created_at),
        "resolved_at": _iso(r.resolved_at),
        "resolution_note": r.resolution_note,
    }


def _payments():
    return (
        SubscriptionPayment.objects.filter(deleted_at__isnull=True)
        .select_related("subscription", "subscription__tenant", "subscription__plan", "plan", "invoice", "intent")
    )


def _reconciliations():
    # Only subscription-billing discrepancies; other tenants' payment reconciliation stays in Integrations.
    return (
        ReconciliationRecord.objects.filter(intent__subscription_payment__isnull=False)
        .select_related("intent__subscription_payment__subscription__tenant")
    )


def _search(qs, term: str, *fields):
    term = (term or "").strip()
    if not term:
        return qs
    q = Q()
    for f in fields:
        q |= Q(**{f"{f}__icontains": term})
    return qs.filter(q)


class PlatformBillingService:
    @staticmethod
    def overview() -> dict:
        subs = list(_subscriptions())
        by_status = defaultdict(int)
        by_billing = defaultdict(int)
        for s in subs:
            by_status[s.status] += 1
            by_billing[billing_status(s)] += 1
        pay_counts = dict(
            SubscriptionPayment.objects.filter(deleted_at__isnull=True).values_list("status").annotate(n=Count("id"))
        )
        # Ledger-backed revenue: paid invoices of verified checkouts (posted to the house tenant's books).
        verified = defaultdict(Decimal)
        manual = defaultdict(Decimal)
        for p in _payments().filter(status=SubscriptionPayment.STATUS_CONFIRMED):
            cur = p.currency or "—"
            if p.intent_id and p.invoice_id and p.invoice.status == "paid":
                verified[cur] += Decimal(p.invoice.amount_paid)
            elif not p.intent_id:
                manual[cur] += Decimal(p.amount)
        tenants = Tenant.objects.filter(deleted_at__isnull=True)
        return {
            "tenants": {
                "total": tenants.count(),
                "demo": tenants.filter(is_demo=True).count(),
                "without_subscription": tenants.filter(subscription__isnull=True).count(),
            },
            "subscriptions": {
                "total": len(subs),
                "active": by_status[TenantSubscription.STATUS_ACTIVE],
                "trial": by_status[TenantSubscription.STATUS_TRIAL],
                "expired": by_status[TenantSubscription.STATUS_EXPIRED],
                "suspended": by_status[TenantSubscription.STATUS_SUSPENDED],
                "unassigned": sum(1 for s in subs if not s.tenant_id),
                "expiring_soon": sum(1 for s in subs if _expiring_soon(s)),
                "overdue": by_billing[BILLING_OVERDUE],
            },
            "payments": {
                "pending": pay_counts.get(SubscriptionPayment.STATUS_PENDING, 0),
                "failed": pay_counts.get(SubscriptionPayment.STATUS_FAILED, 0),
                "review": pay_counts.get(SubscriptionPayment.STATUS_REVIEW, 0),
                "confirmed": pay_counts.get(SubscriptionPayment.STATUS_CONFIRMED, 0),
            },
            "reconciliation_open": _reconciliations().filter(status=ReconciliationRecord.STATUS_OPEN).count(),
            "revenue": {
                "verified": [{"currency": c, "amount": _money(a)} for c, a in sorted(verified.items())],
                "manual_unposted": [{"currency": c, "amount": _money(a)} for c, a in sorted(manual.items())],
                "note": "Verified = paid checkout invoices posted to the ledger. Manual = legacy confirmations, not posted.",
            },
        }

    @staticmethod
    def subscriptions(params) -> dict:
        qs = _search(_subscriptions(), params.get("search"), "reference_code", "tenant__name", "tenant__slug", "tenant__shop_group__name", "plan__name")
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("plan"):
            qs = qs.filter(plan__code=params["plan"])
        rows = [subscription_row(s) for s in qs.order_by("expires_at", "reference_code")]
        wanted = params.get("billing_status")
        if wanted == "expiring_soon":
            ids = {str(s.id) for s in qs if _expiring_soon(s)}
            rows = [r for r in rows if r["id"] in ids]
        elif wanted:
            rows = [r for r in rows if r["billing_status"] == wanted]
        return _page(params, rows)

    @staticmethod
    def payments(params) -> dict:
        qs = _search(_payments(), params.get("search"), "payment_reference", "external_transaction_id", "subscription__tenant__name", "subscription__reference_code")
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        kind = params.get("kind")
        if kind in PAYMENT_KINDS:
            qs = qs.filter(intent__isnull=not PAYMENT_KINDS[kind])
        return _page(params, [payment_row(p) for p in qs.order_by("-created_at")])

    @staticmethod
    def invoices(params) -> dict:
        qs = _search(_payments().filter(invoice__isnull=False), params.get("search"), "invoice__invoice_number", "payment_reference", "subscription__tenant__name")
        if params.get("status"):
            qs = qs.filter(invoice__status=params["status"])
        return _page(params, [invoice_row(p) for p in qs.order_by("-created_at")])

    @staticmethod
    def reconciliation(params) -> dict:
        qs = _search(_reconciliations(), params.get("search"), "detail", "intent__subscription_payment__payment_reference", "intent__subscription_payment__subscription__tenant__name")
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("kind"):
            qs = qs.filter(kind=params["kind"])
        return _page(params, [reconciliation_row(r) for r in qs.order_by("-created_at")])

    @staticmethod
    def plans() -> list[dict]:
        from apps.platform.services.platform_service import PlatformService

        counts = dict(
            TenantSubscription.objects.filter(deleted_at__isnull=True).values_list("plan_id").annotate(n=Count("id"))
        )
        rows = []
        for plan in SubscriptionPlan.objects.filter(deleted_at__isnull=True).order_by("monthly_price", "name"):
            row = PlatformService.plan_payload(plan)
            row["id"] = str(plan.id)
            row["monthly_price"] = _money(plan.monthly_price)
            row["subscriptions"] = counts.get(plan.id, 0)
            rows.append(row)
        return rows

    @staticmethod
    def tenant_detail(tenant: Tenant) -> dict:
        sub = _subscriptions().filter(tenant=tenant).first()
        payments = list(_payments().filter(subscription=sub).order_by("-created_at")) if sub else []
        entity_ids = [tenant.id] + ([sub.id] if sub else []) + [p.id for p in payments]
        audits = list(
            AuditLog.objects.filter(entity_id__in=entity_ids).select_related("user").order_by("-timestamp")[:100]
        )
        recon = list(_reconciliations().filter(intent__subscription_payment__in=[p.id for p in payments]).order_by("-created_at"))
        timeline = []
        if sub:
            timeline.append({"at": _iso(sub.started_at), "event": "started", "label": f"Subscription started on {sub.plan.name}"})
        for p in payments:
            timeline.append({"at": _iso(p.created_at), "event": f"payment_{p.status}",
                             "label": f"{'Checkout' if p.intent_id else 'Payment request'} {p.payment_reference} — {p.status}",
                             "amount": _money(p.amount)})
            if p.confirmed_at:
                timeline.append({"at": _iso(p.confirmed_at), "event": "renewed" if p.auto_renewed else "payment_confirmed",
                                 "label": f"{'Renewed by' if p.auto_renewed else 'Confirmed'} payment {p.payment_reference}",
                                 "amount": _money(p.amount)})
        history = []
        for a in audits:
            event = (a.new_values or {}).get("event") if isinstance(a.new_values, dict) else None
            if event in {"subscription_manual_renewal", "subscription_manual_recovery", "subscription_payment_manual_confirm",
                         "subscription_activated_by_verified_payment"}:
                reason = (a.new_values or {}).get("reason")
                timeline.append({"at": _iso(a.timestamp), "event": event, "label": event.replace("_", " ").capitalize()
                                 + (f": {reason}" if reason else ""), "by": a.user.username if a.user_id else None})
                history.append({"at": _iso(a.timestamp), "event": event, "reason": reason,
                                "by": a.user.username if a.user_id else None,
                                "expires_at": (a.new_values or {}).get("expires_at")})
        if sub and sub.expires_at:
            timeline.append({"at": _iso(sub.expires_at), "event": "expires", "label": "Current period ends"})
        timeline.sort(key=lambda e: e["at"] or "", reverse=True)
        return {
            "tenant": {
                "id": str(tenant.id), "name": tenant.name, "slug": tenant.slug, "status": tenant.status,
                "workspace": tenant.shop_group.name if tenant.shop_group_id else None,
                "contact_email": tenant.contact_email, "is_demo": tenant.is_demo,
            },
            "subscription": ({**subscription_row(sub), "billing_period_days": sub.billing_period_days,
                              "grace_period_days": sub.grace_period_days, "warning_days": sub.warning_days}
                             if sub else None),
            "plan": ({"code": sub.plan.code, "name": sub.plan.name, "monthly_price": _money(sub.plan.monthly_price),
                      "max_users": sub.plan.max_users, "max_branches": sub.plan.max_branches} if sub else None),
            "timeline": timeline,
            "invoices": [invoice_row(p) for p in payments if p.invoice_id],
            "payments": [payment_row(p) for p in payments],
            "renewal_history": history,
            "reconciliation": [reconciliation_row(r) for r in recon],
            "audit": [{
                "id": str(a.id), "at": _iso(a.timestamp), "action": a.action, "module": a.module,
                "entity_type": a.entity_type, "user": a.user.username if a.user_id else None,
                "event": (a.new_values or {}).get("event") if isinstance(a.new_values, dict) else None,
            } for a in audits],
        }

    @staticmethod
    @transaction.atomic
    def recover(*, subscription: TenantSubscription, reason: str, confirmed: bool, user, request=None) -> TenantSubscription:
        """Exceptional Super Admin recovery: extend one billing period. Creates no payment of any kind."""
        if not is_super_admin(user):
            raise PermissionError("Only a Super Admin can perform manual subscription recovery.")
        reason = (reason or "").strip()
        if len(reason) < 10:
            raise PlatformBillingError("A reason of at least 10 characters is required.")
        if confirmed is not True:
            raise PlatformBillingError("Explicit confirmation is required.")
        sub = TenantSubscription.objects.select_for_update(of=("self",)).select_related("plan", "tenant").get(pk=subscription.pk)
        if not sub.tenant_id:
            raise PlatformBillingError("Assign the subscription to a tenant before recovering it.")
        before = {"status": sub.status, "expires_at": _iso(sub.expires_at), "last_paid_at": _iso(sub.last_paid_at)}
        today = timezone.localdate()
        period = sub.billing_period_days or 30
        base = sub.expires_at if sub.expires_at and sub.expires_at >= today else today
        sub.expires_at = base + timedelta(days=period)
        sub.status = TenantSubscription.STATUS_ACTIVE
        sub.updated_by = user
        # Same extension rule as PlatformService.renew_subscription, but last_paid_at is left
        # untouched on purpose: no money was received.
        sub.save(update_fields=["expires_at", "status", "updated_by", "updated_at"])
        write_audit(
            action="update", module=MODULE, entity=sub, user=user, request=request, old_values=before,
            new_values={"event": "subscription_manual_recovery", "reason": reason[:300], "status": sub.status,
                        "expires_at": _iso(sub.expires_at), "payment_created": False},
        )
        return sub

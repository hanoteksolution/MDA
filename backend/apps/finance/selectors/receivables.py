"""Accounts receivable aging — open invoices reconciled to AR control account."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.finance.models import Account
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.sales.models import Invoice
from core.tenancy import apply_tenant_scope, stamp_tenant_id

BUCKETS = (
    ("current", "Current", 0, 0),
    ("1_30", "1–30 days", 1, 30),
    ("31_60", "31–60 days", 31, 60),
    ("61_90", "61–90 days", 61, 90),
    ("90_plus", "90+ days", 91, None),
)


def _bucket_key(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "1_30"
    if days_overdue <= 60:
        return "31_60"
    if days_overdue <= 90:
        return "61_90"
    return "90_plus"


class ReceivablesAgingSelector:
    @staticmethod
    def run(*, as_of=None, user=None, request=None) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        as_of = as_of or timezone.localdate()
        if isinstance(as_of, str):
            from django.utils.dateparse import parse_date

            as_of = parse_date(as_of) or timezone.localdate()

        empty_buckets = {b[0]: 0.0 for b in BUCKETS}
        if not tenant_id:
            return {
                "as_of": as_of.isoformat(),
                "rows": [],
                "buckets": empty_buckets,
                "totals": {"outstanding": 0.0, "control_balance": 0.0, "difference": 0.0},
                "reconciled": True,
            }

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)

        qs = apply_tenant_scope(
            Invoice.active_objects().select_related("customer", "branch"),
            user=user,
            request=request,
        ).filter(tenant_id=tenant_id).exclude(
            status__in=[Invoice.STATUS_DRAFT, Invoice.STATUS_CANCELLED, Invoice.STATUS_ON_HOLD]
        )

        rows = []
        bucket_totals = {b[0]: Decimal("0") for b in BUCKETS}
        outstanding_total = Decimal("0")

        for inv in qs:
            balance = Decimal(str(inv.total_amount)) - Decimal(str(inv.amount_paid))
            if hasattr(inv, "amount_refunded"):
                balance -= Decimal(str(inv.amount_refunded or 0))
            if balance <= Decimal("0.005"):
                continue

            due = inv.due_date or inv.issue_date
            days = (as_of - due).days
            key = _bucket_key(days)
            bucket_totals[key] += balance
            outstanding_total += balance
            rows.append(
                {
                    "invoice_id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                    "customer_id": str(inv.customer_id) if inv.customer_id else None,
                    "customer_name": inv.customer.full_name if inv.customer_id else "",
                    "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                    "due_date": due.isoformat() if due else None,
                    "status": inv.status,
                    "total_amount": float(inv.total_amount),
                    "amount_paid": float(inv.amount_paid),
                    "balance": float(balance),
                    "days_overdue": max(days, 0),
                    "bucket": key,
                }
            )

        rows.sort(key=lambda r: (-r["days_overdue"], r["invoice_number"]))

        control_balance = Decimal("0")
        try:
            ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
            control_balance = ChartService.account_balance(account=ar)
        except Exception:
            ar_acct = Account.active_objects().filter(tenant_id=tenant_id, code="1100").first()
            if ar_acct:
                control_balance = ChartService.account_balance(account=ar_acct)

        difference = outstanding_total - control_balance
        return {
            "as_of": as_of.isoformat(),
            "rows": rows,
            "buckets": {k: float(v) for k, v in bucket_totals.items()},
            "bucket_labels": {b[0]: b[1] for b in BUCKETS},
            "totals": {
                "outstanding": float(outstanding_total),
                "control_balance": float(control_balance),
                "difference": float(difference),
            },
            "reconciled": abs(difference) < Decimal("0.01"),
        }

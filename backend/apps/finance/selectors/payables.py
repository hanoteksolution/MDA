"""Accounts payable aging — received PO value less supplier payments vs AP control."""

from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.finance.models import Account
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.purchases.models import PurchaseOrder
from core.tenancy import apply_tenant_scope, stamp_tenant_id

BUCKETS = (
    ("current", "Current", 0, 0),
    ("1_30", "1–30 days", 1, 30),
    ("31_60", "31–60 days", 31, 60),
    ("61_90", "61–90 days", 61, 90),
    ("90_plus", "90+ days", 91, None),
)


def _bucket_key(days: int) -> str:
    if days <= 0:
        return "current"
    if days <= 30:
        return "1_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "90_plus"


class PayablesAgingSelector:
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

        qs = (
            apply_tenant_scope(
                PurchaseOrder.active_objects()
                .select_related("supplier", "branch")
                .prefetch_related("items", "supplier_payments"),
                user=user,
                request=request,
            )
            .filter(tenant_id=tenant_id)
            .exclude(status=PurchaseOrder.STATUS_CANCELLED)
        )

        rows = []
        bucket_totals = {b[0]: Decimal("0") for b in BUCKETS}
        outstanding_total = Decimal("0")

        for po in qs:
            received_value = Decimal("0")
            for item in po.items.all():
                qty = Decimal(str(item.quantity_received or 0))
                if qty <= 0:
                    continue
                received_value += qty * Decimal(str(item.unit_cost))
            if received_value <= Decimal("0.005"):
                continue

            paid = Decimal("0")
            for sp in po.supplier_payments.all():
                if sp.deleted_at is not None:
                    continue
                paid += Decimal(str(sp.amount))
            balance = received_value - paid
            if balance <= Decimal("0.005"):
                continue

            anchor = po.expected_date or po.order_date
            days = (as_of - anchor).days
            key = _bucket_key(days)
            bucket_totals[key] += balance
            outstanding_total += balance
            rows.append(
                {
                    "purchase_order_id": str(po.id),
                    "order_number": po.order_number,
                    "supplier_id": str(po.supplier_id) if po.supplier_id else None,
                    "supplier_name": po.supplier.company_name if po.supplier_id else "",
                    "order_date": po.order_date.isoformat() if po.order_date else None,
                    "expected_date": po.expected_date.isoformat() if po.expected_date else None,
                    "status": po.status,
                    "received_value": float(received_value),
                    "amount_paid": float(paid),
                    "balance": float(balance),
                    "days_outstanding": max(days, 0),
                    "bucket": key,
                }
            )

        rows.sort(key=lambda r: (-r["days_outstanding"], r["order_number"]))

        control_balance = Decimal("0")
        try:
            ap = MappingService.resolve(key="DEFAULT_PAYABLE", tenant_id=tenant_id, user=user)
            control_balance = ChartService.account_balance(account=ap)
        except Exception:
            ap_acct = Account.active_objects().filter(tenant_id=tenant_id, code="2000").first()
            if ap_acct:
                control_balance = ChartService.account_balance(account=ap_acct)

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

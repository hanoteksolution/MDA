"""General ledger / account statement — posted journal lines by account."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class GeneralLedgerSelector:
    """Account drill-down with opening balance, movements, and running balance."""

    @staticmethod
    def run(
        *,
        account_id=None,
        account_code=None,
        date_from=None,
        date_to=None,
        cost_center_id=None,
        business_unit_id=None,
        user=None,
        request=None,
        limit: int = 500,
    ) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        empty = {
            "account": None,
            "cost_center_id": str(cost_center_id) if cost_center_id else None,
            "business_unit_id": str(business_unit_id) if business_unit_id else None,
            "date_from": _iso(date_from),
            "date_to": _iso(date_to),
            "opening_balance": 0.0,
            "period_debit": 0.0,
            "period_credit": 0.0,
            "closing_balance": 0.0,
            "lines": [],
        }
        if not tenant_id:
            return empty

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        qs = apply_tenant_scope(Account.active_objects(), user=user, request=request)
        account = None
        if account_id:
            account = qs.filter(pk=account_id).first()
        elif account_code:
            account = qs.filter(code=account_code).first()
        if account is None:
            return {**empty, "error": "Account not found."}

        base = JournalLine.active_objects().filter(
            account=account,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
            entry__tenant_id=tenant_id,
        )
        if cost_center_id:
            base = base.filter(cost_center_id=cost_center_id)
        if business_unit_id:
            base = base.filter(business_unit_id=business_unit_id)

        opening = Decimal("0")
        if date_from:
            prior = base.filter(entry__entry_date__lt=date_from)
            agg = prior.aggregate(d=Sum("debit"), c=Sum("credit"))
            opening = _signed(account, agg["d"] or 0, agg["c"] or 0)

        period = base
        if date_from:
            period = period.filter(entry__entry_date__gte=date_from)
        if date_to:
            period = period.filter(entry__entry_date__lte=date_to)

        period_agg = period.aggregate(d=Sum("debit"), c=Sum("credit"))
        period_debit = period_agg["d"] or Decimal("0")
        period_credit = period_agg["c"] or Decimal("0")
        period_net = _signed(account, period_debit, period_credit)
        closing = opening + period_net

        rows = (
            period.select_related("entry", "account")
            .order_by("entry__entry_date", "entry__created_at", "created_at")[: max(1, min(limit, 2000))]
        )

        running = opening
        lines_out = []
        for line in rows:
            debit = line.debit or Decimal("0")
            credit = line.credit or Decimal("0")
            delta = _signed(account, debit, credit)
            running = running + delta
            entry = line.entry
            lines_out.append(
                {
                    "id": str(line.id),
                    "entry_id": str(entry.id),
                    "entry_number": entry.entry_number,
                    "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
                    "description": entry.description or "",
                    "source_type": entry.source_type,
                    "memo": line.memo or "",
                    "cost_center_id": str(line.cost_center_id) if line.cost_center_id else None,
                    "business_unit_id": str(line.business_unit_id)
                    if line.business_unit_id
                    else None,
                    "debit": float(debit),
                    "credit": float(credit),
                    "running_balance": float(running),
                }
            )

        return {
            "account": {
                "id": str(account.id),
                "code": account.code,
                "name": account.name,
                "type": account.account_type,
            },
            "cost_center_id": str(cost_center_id) if cost_center_id else None,
            "business_unit_id": str(business_unit_id) if business_unit_id else None,
            "date_from": _iso(date_from),
            "date_to": _iso(date_to),
            "opening_balance": float(opening),
            "period_debit": float(period_debit),
            "period_credit": float(period_credit),
            "closing_balance": float(closing),
            "lines": lines_out,
        }


def _signed(account: Account, debit, credit) -> Decimal:
    debit = Decimal(str(debit or 0))
    credit = Decimal(str(credit or 0))
    if account.normal_debit:
        return debit - credit
    return credit - debit


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

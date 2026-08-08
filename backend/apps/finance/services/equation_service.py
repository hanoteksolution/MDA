"""Accounting equation validator — Assets = Liabilities + Equity (via retained earnings).

Also checks the expanded identity:
  Assets + Expenses = Liabilities + Equity + Revenue
using posted ledger movements only.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.finance.domain.account_behavior import AccountClass, signed_balance
from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from core.tenancy import stamp_tenant_id

TOLERANCE = Decimal("0.01")


class AccountingEquationService:
    @staticmethod
    def evaluate(*, as_of=None, user=None, request=None, tenant_id=None) -> dict:
        if tenant_id is None:
            payload = stamp_tenant_id({}, user=user, request=request)
            tenant_id = payload.get("tenant_id")
        if as_of is None:
            as_of = timezone.localdate()
        elif isinstance(as_of, str):
            from django.utils.dateparse import parse_date

            as_of = parse_date(as_of) or timezone.localdate()

        empty = {
            "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of),
            "assets": Decimal("0"),
            "liabilities": Decimal("0"),
            "equity": Decimal("0"),
            "revenue": Decimal("0"),
            "expenses": Decimal("0"),
            "retained_earnings": Decimal("0"),
            "equity_with_earnings": Decimal("0"),
            "liabilities_plus_equity": Decimal("0"),
            "assets_plus_expenses": Decimal("0"),
            "liabilities_equity_revenue": Decimal("0"),
            "balance_sheet_ok": True,
            "expanded_ok": True,
            "ok": True,
            "difference_balance_sheet": Decimal("0"),
            "difference_expanded": Decimal("0"),
        }
        if not tenant_id:
            return {**empty, "ok": False, "message": "No tenant resolved."}

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        totals = {
            AccountClass.ASSET: Decimal("0"),
            AccountClass.LIABILITY: Decimal("0"),
            AccountClass.EQUITY: Decimal("0"),
            AccountClass.REVENUE: Decimal("0"),
            AccountClass.EXPENSE: Decimal("0"),
        }

        for account in Account.active_objects().filter(tenant_id=tenant_id, is_active=True):
            line_qs = JournalLine.active_objects().filter(
                account=account,
                entry__status=JournalEntry.STATUS_POSTED,
                entry__deleted_at__isnull=True,
                entry__tenant_id=tenant_id,
                entry__entry_date__lte=as_of,
            )
            agg = line_qs.aggregate(d=Sum("debit"), c=Sum("credit"))
            bal = signed_balance(
                account_class=account.account_type,
                debit=agg["d"] or 0,
                credit=agg["c"] or 0,
            )
            totals[account.account_type] = totals.get(account.account_type, Decimal("0")) + bal

        assets = totals[AccountClass.ASSET]
        liabilities = totals[AccountClass.LIABILITY]
        equity = totals[AccountClass.EQUITY]
        revenue = totals[AccountClass.REVENUE]
        expenses = totals[AccountClass.EXPENSE]
        retained = revenue - expenses
        equity_with = equity + retained
        lhs_bs = assets
        rhs_bs = liabilities + equity_with
        lhs_exp = assets + expenses
        rhs_exp = liabilities + equity + revenue

        diff_bs = (lhs_bs - rhs_bs).copy_abs()
        diff_exp = (lhs_exp - rhs_exp).copy_abs()
        bs_ok = diff_bs <= TOLERANCE
        exp_ok = diff_exp <= TOLERANCE

        return {
            "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of),
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "revenue": revenue,
            "expenses": expenses,
            "retained_earnings": retained,
            "equity_with_earnings": equity_with,
            "liabilities_plus_equity": rhs_bs,
            "assets_plus_expenses": lhs_exp,
            "liabilities_equity_revenue": rhs_exp,
            "balance_sheet_ok": bs_ok,
            "expanded_ok": exp_ok,
            "ok": bs_ok and exp_ok,
            "difference_balance_sheet": diff_bs,
            "difference_expanded": diff_exp,
            "message": (
                "Accounting equation holds."
                if bs_ok and exp_ok
                else "Accounting equation out of balance."
            ),
        }

    @staticmethod
    def serialize(result: dict) -> dict:
        def _n(v):
            if isinstance(v, Decimal):
                return float(v)
            return v

        return {k: _n(v) for k, v in result.items()}

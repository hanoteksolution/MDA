"""Profit & Loss — revenue and expense accounts from posted journal lines."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from core.tenancy import stamp_tenant_id


class ProfitLossSelector:
    @staticmethod
    def run(
        *,
        date_from=None,
        date_to=None,
        business_unit_id=None,
        cost_center_id=None,
        user=None,
        request=None,
    ) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        empty = {
            "revenue": [],
            "expenses": [],
            "totals": {"revenue": 0.0, "expenses": 0.0, "net_profit": 0.0},
            "business_unit_id": str(business_unit_id) if business_unit_id else None,
            "cost_center_id": str(cost_center_id) if cost_center_id else None,
        }
        if not tenant_id:
            return empty

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        def _section(account_type: str) -> tuple[list, Decimal]:
            rows = []
            section_total = Decimal("0")
            accounts = ChartService.list(
                account_type=account_type, is_active=True, user=user, request=request
            )
            for account in accounts:
                line_qs = JournalLine.active_objects().filter(
                    account=account,
                    entry__status=JournalEntry.STATUS_POSTED,
                    entry__deleted_at__isnull=True,
                    entry__tenant_id=tenant_id,
                )
                if date_from:
                    line_qs = line_qs.filter(entry__entry_date__gte=date_from)
                if date_to:
                    line_qs = line_qs.filter(entry__entry_date__lte=date_to)
                if business_unit_id:
                    line_qs = line_qs.filter(business_unit_id=business_unit_id)
                if cost_center_id:
                    line_qs = line_qs.filter(cost_center_id=cost_center_id)
                agg = line_qs.aggregate(d=Sum("debit"), c=Sum("credit"))
                debit = agg["d"] or Decimal("0")
                credit = agg["c"] or Decimal("0")
                if account.account_type == Account.TYPE_REVENUE:
                    amount = credit - debit
                else:
                    amount = debit - credit
                if amount == 0:
                    continue
                rows.append(
                    {
                        "account_id": str(account.id),
                        "code": account.code,
                        "name": account.name,
                        "amount": float(amount),
                    }
                )
                section_total += amount
            rows.sort(key=lambda r: r["code"])
            return rows, section_total

        revenue_rows, revenue_total = _section(Account.TYPE_REVENUE)
        expense_rows, expense_total = _section(Account.TYPE_EXPENSE)
        net = revenue_total - expense_total

        return {
            "date_from": date_from.isoformat() if hasattr(date_from, "isoformat") else date_from,
            "date_to": date_to.isoformat() if hasattr(date_to, "isoformat") else date_to,
            "business_unit_id": str(business_unit_id) if business_unit_id else None,
            "cost_center_id": str(cost_center_id) if cost_center_id else None,
            "revenue": revenue_rows,
            "expenses": expense_rows,
            "totals": {
                "revenue": float(revenue_total),
                "expenses": float(expense_total),
                "net_profit": float(net),
            },
        }

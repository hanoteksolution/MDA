"""Balance sheet — assets, liabilities, equity from posted journal lines."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from core.tenancy import stamp_tenant_id


class BalanceSheetSelector:
    @staticmethod
    def run(*, as_of=None, user=None, request=None) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        empty = {
            "assets": [],
            "liabilities": [],
            "equity": [],
            "totals": {
                "assets": 0.0,
                "liabilities": 0.0,
                "equity": 0.0,
                "liabilities_plus_equity": 0.0,
                "is_balanced": True,
            },
        }
        if not tenant_id:
            return empty

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        def _section(account_type: str) -> tuple[list, Decimal]:
            rows = []
            section_total = Decimal("0")
            for account in ChartService.list(
                account_type=account_type, is_active=True, user=user, request=request
            ):
                line_qs = JournalLine.active_objects().filter(
                    account=account,
                    entry__status=JournalEntry.STATUS_POSTED,
                    entry__deleted_at__isnull=True,
                    entry__tenant_id=tenant_id,
                )
                if as_of:
                    line_qs = line_qs.filter(entry__entry_date__lte=as_of)
                agg = line_qs.aggregate(d=Sum("debit"), c=Sum("credit"))
                debit = agg["d"] or Decimal("0")
                credit = agg["c"] or Decimal("0")
                if account.normal_debit:
                    balance = debit - credit
                else:
                    balance = credit - debit
                if balance == 0:
                    continue
                rows.append(
                    {
                        "account_id": str(account.id),
                        "code": account.code,
                        "name": account.name,
                        "balance": float(balance),
                    }
                )
                section_total += balance
            rows.sort(key=lambda r: r["code"])
            return rows, section_total

        assets, assets_total = _section(Account.TYPE_ASSET)
        liabilities, liabilities_total = _section(Account.TYPE_LIABILITY)
        equity, equity_total = _section(Account.TYPE_EQUITY)

        # Retained earnings approximation: revenue − expenses to date
        revenue = Decimal("0")
        expenses = Decimal("0")
        for account in ChartService.list(is_active=True, user=user, request=request):
            if account.account_type not in (Account.TYPE_REVENUE, Account.TYPE_EXPENSE):
                continue
            line_qs = JournalLine.active_objects().filter(
                account=account,
                entry__status=JournalEntry.STATUS_POSTED,
                entry__deleted_at__isnull=True,
                entry__tenant_id=tenant_id,
            )
            if as_of:
                line_qs = line_qs.filter(entry__entry_date__lte=as_of)
            agg = line_qs.aggregate(d=Sum("debit"), c=Sum("credit"))
            debit = agg["d"] or Decimal("0")
            credit = agg["c"] or Decimal("0")
            if account.account_type == Account.TYPE_REVENUE:
                revenue += credit - debit
            else:
                expenses += debit - credit
        retained = revenue - expenses
        if retained != 0:
            equity.append(
                {
                    "account_id": None,
                    "code": "RE",
                    "name": "Retained Earnings (current)",
                    "balance": float(retained),
                }
            )
            equity_total += retained

        liabilities_plus_equity = liabilities_total + equity_total
        return {
            "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else as_of,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "totals": {
                "assets": float(assets_total),
                "liabilities": float(liabilities_total),
                "equity": float(equity_total),
                "liabilities_plus_equity": float(liabilities_plus_equity),
                "is_balanced": abs(assets_total - liabilities_plus_equity) < Decimal("0.01"),
            },
        }

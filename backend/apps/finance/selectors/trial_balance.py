"""Trial balance report — derived from posted journal lines."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class TrialBalanceSelector:
    @staticmethod
    def run(*, date_from=None, date_to=None, user=None, request=None) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            return {"rows": [], "totals": {"debit": 0.0, "credit": 0.0}, "is_balanced": True}

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        rows = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        accounts = ChartService.list(is_active=True, user=user, request=request)
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

            agg = line_qs.aggregate(d=Sum("debit"), c=Sum("credit"))
            debit = agg["d"] or Decimal("0")
            credit = agg["c"] or Decimal("0")
            if debit == 0 and credit == 0:
                continue

            if account.normal_debit:
                balance = debit - credit
            else:
                balance = credit - debit

            rows.append(
                {
                    "account_id": str(account.id),
                    "code": account.code,
                    "name": account.name,
                    "type": account.account_type,
                    "debit": float(debit),
                    "credit": float(credit),
                    "balance": float(balance),
                }
            )
            total_debit += debit
            total_credit += credit

        rows.sort(key=lambda r: r["code"])
        return {
            "date_from": date_from.isoformat() if hasattr(date_from, "isoformat") else date_from,
            "date_to": date_to.isoformat() if hasattr(date_to, "isoformat") else date_to,
            "rows": rows,
            "totals": {
                "debit": float(total_debit),
                "credit": float(total_credit),
            },
            "is_balanced": total_debit == total_credit,
        }

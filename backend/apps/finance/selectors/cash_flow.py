"""Cash flow statement — simplified classification from cash account journal lines."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from core.tenancy import stamp_tenant_id


# source_type → cash-flow section
OPERATING_SOURCES = frozenset(
    {"invoice", "payment", "expense", "refund", "purchase", "manual"}
)
INVESTING_SOURCES = frozenset()  # reserved
FINANCING_SOURCES = frozenset()  # reserved


class CashFlowSelector:
    @staticmethod
    def _cash_account_ids(*, tenant_id, user=None, request=None) -> list:
        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)
        ids = set()
        for key in ("DEFAULT_CASH", "DEFAULT_BANK", "DEFAULT_MOBILE_MONEY"):
            try:
                acct = MappingService.resolve(key=key, tenant_id=tenant_id, user=user, request=request)
                ids.add(acct.id)
            except Exception:
                continue
        if not ids:
            cash = Account.active_objects().filter(tenant_id=tenant_id, code="1000").first()
            if cash:
                ids.add(cash.id)
        return list(ids)

    @staticmethod
    def run(*, date_from=None, date_to=None, user=None, request=None) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        empty = {
            "operating": {"inflows": [], "outflows": [], "net": 0.0},
            "investing": {"inflows": [], "outflows": [], "net": 0.0},
            "financing": {"inflows": [], "outflows": [], "net": 0.0},
            "net_change": 0.0,
            "opening_cash": 0.0,
            "closing_cash": 0.0,
        }
        if not tenant_id:
            return empty

        cash_ids = CashFlowSelector._cash_account_ids(
            tenant_id=tenant_id, user=user, request=request
        )
        if not cash_ids:
            return empty

        # Opening cash = balance before date_from
        opening = Decimal("0")
        if date_from:
            before = JournalLine.active_objects().filter(
                account_id__in=cash_ids,
                entry__status=JournalEntry.STATUS_POSTED,
                entry__deleted_at__isnull=True,
                entry__tenant_id=tenant_id,
                entry__entry_date__lt=date_from,
            ).aggregate(d=Sum("debit"), c=Sum("credit"))
            opening = (before["d"] or Decimal("0")) - (before["c"] or Decimal("0"))

        period_lines = JournalLine.active_objects().filter(
            account_id__in=cash_ids,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
            entry__tenant_id=tenant_id,
        ).select_related("entry", "account")
        if date_from:
            period_lines = period_lines.filter(entry__entry_date__gte=date_from)
        if date_to:
            period_lines = period_lines.filter(entry__entry_date__lte=date_to)

        sections = {
            "operating": {"inflows": {}, "outflows": {}, "net": Decimal("0")},
            "investing": {"inflows": {}, "outflows": {}, "net": Decimal("0")},
            "financing": {"inflows": {}, "outflows": {}, "net": Decimal("0")},
        }

        def _section_for(source_type: str) -> str:
            if source_type in INVESTING_SOURCES:
                return "investing"
            if source_type in FINANCING_SOURCES:
                return "financing"
            return "operating"

        net_change = Decimal("0")
        for line in period_lines:
            source_type = line.entry.source_type or "manual"
            section = _section_for(source_type)
            label = line.entry.description or source_type
            if line.debit > 0:
                bucket = sections[section]["inflows"]
                bucket[label] = bucket.get(label, Decimal("0")) + line.debit
                sections[section]["net"] += line.debit
                net_change += line.debit
            if line.credit > 0:
                bucket = sections[section]["outflows"]
                bucket[label] = bucket.get(label, Decimal("0")) + line.credit
                sections[section]["net"] -= line.credit
                net_change -= line.credit

        def _fmt(section: dict) -> dict:
            return {
                "inflows": [
                    {"label": k, "amount": float(v)}
                    for k, v in sorted(section["inflows"].items())
                ],
                "outflows": [
                    {"label": k, "amount": float(v)}
                    for k, v in sorted(section["outflows"].items())
                ],
                "net": float(section["net"]),
            }

        closing = opening + net_change
        return {
            "date_from": date_from.isoformat() if hasattr(date_from, "isoformat") else date_from,
            "date_to": date_to.isoformat() if hasattr(date_to, "isoformat") else date_to,
            "operating": _fmt(sections["operating"]),
            "investing": _fmt(sections["investing"]),
            "financing": _fmt(sections["financing"]),
            "net_change": float(net_change),
            "opening_cash": float(opening),
            "closing_cash": float(closing),
        }

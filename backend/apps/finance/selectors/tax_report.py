"""Sales tax collected / refunded vs Tax Payable control account."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from core.tenancy import stamp_tenant_id


class TaxReportSelector:
    @staticmethod
    def run(*, date_from=None, date_to=None, user=None, request=None) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        empty = {
            "date_from": date_from,
            "date_to": date_to,
            "tax_account": None,
            "collected": 0.0,
            "refunded": 0.0,
            "net_payable": 0.0,
            "control_balance": 0.0,
            "difference": 0.0,
            "reconciled": True,
            "rows": [],
        }
        if not tenant_id:
            return empty

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)

        try:
            tax_account = MappingService.resolve(
                key="DEFAULT_TAX_PAYABLE", tenant_id=tenant_id, user=user
            )
        except Exception:
            tax_account = Account.active_objects().filter(
                tenant_id=tenant_id, code="2100"
            ).first()
        if not tax_account:
            return empty

        qs = (
            JournalLine.active_objects()
            .filter(
                account=tax_account,
                entry__status=JournalEntry.STATUS_POSTED,
                entry__deleted_at__isnull=True,
                entry__tenant_id=tenant_id,
            )
            .select_related("entry")
            .order_by("entry__entry_date", "created_at")
        )
        if date_from:
            d = parse_date(str(date_from)) if not hasattr(date_from, "isoformat") else date_from
            if d:
                qs = qs.filter(entry__entry_date__gte=d)
        if date_to:
            d = parse_date(str(date_to)) if not hasattr(date_to, "isoformat") else date_to
            if d:
                qs = qs.filter(entry__entry_date__lte=d)

        collected = Decimal("0")
        refunded = Decimal("0")
        rows = []
        for line in qs:
            debit = Decimal(str(line.debit or 0))
            credit = Decimal(str(line.credit or 0))
            collected += credit
            refunded += debit
            rows.append(
                {
                    "journal_line_id": str(line.id),
                    "entry_id": str(line.entry_id),
                    "entry_number": line.entry.entry_number,
                    "entry_date": line.entry.entry_date.isoformat(),
                    "description": line.entry.description,
                    "source_reference": line.entry.source_reference or "",
                    "memo": line.memo or "",
                    "collected": float(credit),
                    "refunded": float(debit),
                }
            )

        net = collected - refunded
        control = ChartService.account_balance(account=tax_account)
        # Period net may differ from lifetime control balance when date filtered
        difference = net - control if not date_from and not date_to else Decimal("0")
        reconciled = abs(difference) < Decimal("0.01") if not date_from and not date_to else True

        return {
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "as_of": timezone.localdate().isoformat(),
            "tax_account": {
                "id": str(tax_account.id),
                "code": tax_account.code,
                "name": tax_account.name,
            },
            "collected": float(collected),
            "refunded": float(refunded),
            "net_payable": float(net),
            "control_balance": float(control),
            "difference": float(difference),
            "reconciled": reconciled,
            "rows": rows,
        }

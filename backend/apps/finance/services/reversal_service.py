"""Accounting reversal — create offsetting journals; never mutate posted entries."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.finance.models import AccountingEvent, JournalEntry, JournalLine
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.period_service import PeriodService


class ReversalError(ValueError):
    pass


class AccountingReversalService:
    @staticmethod
    @transaction.atomic
    def reverse_entry(*, entry: JournalEntry, user=None, reason: str = "") -> JournalEntry:
        if entry.status != JournalEntry.STATUS_POSTED:
            raise ReversalError("Only posted journals can be reversed.")
        if entry.reversal_entries.filter(deleted_at__isnull=True, status=JournalEntry.STATUS_POSTED).exists():
            raise ReversalError("Journal has already been reversed.")

        lines = list(
            JournalLine.active_objects()
            .filter(entry=entry)
            .select_related("account")
        )
        if not lines:
            raise ReversalError("Journal has no lines to reverse.")

        period = PeriodService.resolve(
            tenant_id=entry.tenant_id,
            on_date=timezone.localdate(),
            user=user,
        )

        reverse_lines = []
        for line in lines:
            reverse_lines.append(
                {
                    "account_id": str(line.account_id),
                    "debit": line.credit,
                    "credit": line.debit,
                    "memo": f"Reversal: {line.memo}" if line.memo else "Reversal",
                }
            )

        description = f"Reversal of {entry.entry_number}"
        if reason:
            description = f"{description}: {reason}"

        reversal = JournalService.create_entry(
            data={
                "tenant_id": entry.tenant_id,
                "entry_date": timezone.localdate(),
                "description": description,
                "source_type": entry.source_type,
                "source_module": entry.source_module or "",
                "source_id": entry.source_id,
                "source_reference": entry.source_reference or entry.entry_number,
                "idempotency_key": f"REVERSAL:{entry.id}",
                "branch_id": entry.branch_id,
                "financial_period_id": period.id,
                "notes": reason or f"Reverses {entry.entry_number}",
                "reverses_entry_id": entry.id,
                "lines": reverse_lines,
            },
            user=user,
        )

        AccountingEvent.active_objects().filter(
            journal_entry=entry,
            status=AccountingEvent.STATUS_POSTED,
        ).update(
            status=AccountingEvent.STATUS_REVERSED,
            processed_at=timezone.now(),
            updated_at=timezone.now(),
        )
        return reversal

    @staticmethod
    def find_posted_for_source(*, tenant_id, source_type: str, source_id) -> JournalEntry | None:
        reversed_ids = set(
            JournalEntry.active_objects()
            .filter(
                tenant_id=tenant_id,
                reverses_entry__isnull=False,
                status=JournalEntry.STATUS_POSTED,
            )
            .values_list("reverses_entry_id", flat=True)
        )
        qs = (
            JournalEntry.active_objects()
            .filter(
                tenant_id=tenant_id,
                source_type=source_type,
                source_id=source_id,
                status=JournalEntry.STATUS_POSTED,
                reverses_entry__isnull=True,
            )
            .order_by("-created_at")
        )
        for entry in qs:
            if entry.id not in reversed_ids:
                return entry
        return None

    @staticmethod
    @transaction.atomic
    def reverse_expense_journal(*, expense, user=None, reason: str = "") -> JournalEntry | None:
        tenant_id = expense.tenant_id or getattr(expense.branch, "tenant_id", None)
        if not tenant_id:
            return None
        entry = AccountingReversalService.find_posted_for_source(
            tenant_id=tenant_id,
            source_type=JournalEntry.SOURCE_EXPENSE,
            source_id=expense.id,
        )
        if entry is None:
            return None
        return AccountingReversalService.reverse_entry(
            entry=entry,
            user=user,
            reason=reason or f"Expense {expense.description} reversed",
        )

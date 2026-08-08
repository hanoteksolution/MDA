"""Bank / cash account reconciliation against statement balances."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.finance.models import (
    Account,
    BankReconciliation,
    BankStatementLine,
    JournalEntry,
    JournalLine,
)
from apps.finance.services.chart_service import ChartService
from core.tenancy import apply_tenant_scope, stamp_tenant_id

MONEY = Decimal("0.01")


class ReconciliationError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _as_date(value):
    if value is None:
        return timezone.localdate()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value
    return parse_date(str(value)) or timezone.localdate()


class ReconciliationService:
    @staticmethod
    def serialize_line(line: BankStatementLine) -> dict:
        jl = line.matched_journal_line
        return {
            "id": str(line.id),
            "line_date": line.line_date.isoformat(),
            "description": line.description,
            "reference": line.reference,
            "amount": float(line.amount),
            "is_matched": line.is_matched,
            "matched_journal_line_id": str(jl.id) if jl else None,
            "matched_entry_number": jl.entry.entry_number if jl else None,
            "matched_at": line.matched_at.isoformat() if line.matched_at else None,
        }

    @staticmethod
    def serialize(rec: BankReconciliation, *, include_lines=True) -> dict:
        summary = ReconciliationService.compute_summary(rec)
        data = {
            "id": str(rec.id),
            "account_id": str(rec.account_id),
            "account_code": rec.account.code if rec.account_id else "",
            "account_name": rec.account.name if rec.account_id else "",
            "statement_date": rec.statement_date.isoformat(),
            "statement_balance": float(rec.statement_balance),
            "book_balance": float(rec.book_balance),
            "status": rec.status,
            "notes": rec.notes or "",
            "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
            "summary": summary,
        }
        if include_lines:
            lines = (
                BankStatementLine.active_objects()
                .filter(reconciliation=rec)
                .select_related("matched_journal_line__entry")
                .order_by("line_date", "created_at")
            )
            data["statement_lines"] = [ReconciliationService.serialize_line(l) for l in lines]
        return data

    @staticmethod
    def book_balance_as_of(*, account: Account, as_of) -> Decimal:
        as_of = _as_date(as_of)
        agg = JournalLine.active_objects().filter(
            account=account,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
            entry__tenant_id=account.tenant_id,
            entry__entry_date__lte=as_of,
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        debit = agg["d"] or Decimal("0")
        credit = agg["c"] or Decimal("0")
        return _money(debit - credit)

    @staticmethod
    def compute_summary(rec: BankReconciliation) -> dict:
        """
        Adjusted book = book − unmatched book deposits + unmatched book withdrawals.
        Should equal statement_balance when fully reconciled.
        """
        account = rec.account
        matched_jl_ids = set(
            BankStatementLine.active_objects()
            .filter(reconciliation=rec, matched_journal_line_id__isnull=False)
            .values_list("matched_journal_line_id", flat=True)
        )

        book_lines = JournalLine.active_objects().filter(
            account=account,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
            entry__tenant_id=rec.tenant_id,
            entry__entry_date__lte=rec.statement_date,
        )
        unmatched_deposits = Decimal("0")
        unmatched_withdrawals = Decimal("0")
        unmatched_book_count = 0
        for jl in book_lines:
            if jl.id in matched_jl_ids:
                continue
            unmatched_book_count += 1
            debit = Decimal(str(jl.debit or 0))
            credit = Decimal(str(jl.credit or 0))
            if debit > 0:
                unmatched_deposits += debit
            if credit > 0:
                unmatched_withdrawals += credit

        statement_lines = BankStatementLine.active_objects().filter(reconciliation=rec)
        unmatched_stmt = statement_lines.filter(matched_journal_line_id__isnull=True)
        unmatched_stmt_count = unmatched_stmt.count()
        matched_stmt_count = statement_lines.filter(
            matched_journal_line_id__isnull=False
        ).count()

        adjusted = (
            Decimal(str(rec.book_balance))
            - _money(unmatched_deposits)
            + _money(unmatched_withdrawals)
        )
        difference = _money(Decimal(str(rec.statement_balance)) - adjusted)
        return {
            "unmatched_book_deposits": float(_money(unmatched_deposits)),
            "unmatched_book_withdrawals": float(_money(unmatched_withdrawals)),
            "unmatched_book_count": unmatched_book_count,
            "matched_statement_count": matched_stmt_count,
            "unmatched_statement_count": unmatched_stmt_count,
            "adjusted_book_balance": float(_money(adjusted)),
            "difference": float(difference),
            "is_balanced": abs(difference) < Decimal("0.01") and unmatched_stmt_count == 0,
        }

    @staticmethod
    def list(*, user=None, request=None, account_id=None, status=None):
        qs = apply_tenant_scope(
            BankReconciliation.active_objects().select_related("account"),
            user=user,
            request=request,
        )
        if account_id:
            qs = qs.filter(account_id=account_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-statement_date", "-created_at")

    @staticmethod
    def get(*, reconciliation_id, user=None, request=None) -> BankReconciliation:
        qs = apply_tenant_scope(
            BankReconciliation.active_objects().select_related("account"),
            user=user,
            request=request,
        )
        rec = qs.filter(pk=reconciliation_id).first()
        if not rec:
            raise ReconciliationError("Reconciliation not found.")
        return rec

    @staticmethod
    @transaction.atomic
    def create(
        *,
        account_id,
        statement_date,
        statement_balance,
        notes="",
        user=None,
        request=None,
    ) -> BankReconciliation:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise ReconciliationError("Tenant could not be resolved.")

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)
        account = apply_tenant_scope(
            Account.active_objects(), user=user, request=request
        ).filter(pk=account_id, tenant_id=tenant_id).first()
        if not account:
            raise ReconciliationError("Account not found.")
        if account.account_type != Account.TYPE_ASSET:
            raise ReconciliationError("Only asset (cash/bank) accounts can be reconciled.")

        statement_date = _as_date(statement_date)
        statement_balance = _money(statement_balance)
        book_balance = ReconciliationService.book_balance_as_of(
            account=account, as_of=statement_date
        )

        return BankReconciliation.objects.create(
            tenant_id=tenant_id,
            account=account,
            statement_date=statement_date,
            statement_balance=statement_balance,
            book_balance=book_balance,
            status=BankReconciliation.STATUS_IN_PROGRESS,
            notes=notes or "",
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def add_statement_line(
        *,
        reconciliation_id,
        line_date,
        amount,
        description="",
        reference="",
        user=None,
        request=None,
    ) -> BankStatementLine:
        rec = ReconciliationService.get(
            reconciliation_id=reconciliation_id, user=user, request=request
        )
        if rec.status == BankReconciliation.STATUS_COMPLETED:
            raise ReconciliationError("Cannot edit a completed reconciliation.")

        amount = _money(amount)
        if amount == 0:
            raise ReconciliationError("Statement line amount cannot be zero.")

        return BankStatementLine.objects.create(
            reconciliation=rec,
            line_date=_as_date(line_date),
            amount=amount,
            description=description or "",
            reference=reference or "",
            created_by=user,
        )

    @staticmethod
    def list_book_lines(
        *,
        account_id,
        as_of=None,
        unmatched_only=True,
        reconciliation_id=None,
        user=None,
        request=None,
    ) -> list[dict]:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        account = apply_tenant_scope(
            Account.active_objects(), user=user, request=request
        ).filter(pk=account_id).first()
        if not account:
            raise ReconciliationError("Account not found.")

        as_of = _as_date(as_of)
        matched_ids = set()
        if reconciliation_id:
            matched_ids = set(
                BankStatementLine.active_objects()
                .filter(
                    reconciliation_id=reconciliation_id,
                    matched_journal_line_id__isnull=False,
                )
                .values_list("matched_journal_line_id", flat=True)
            )
        else:
            # Any open reconciliation match for this account
            matched_ids = set(
                BankStatementLine.active_objects()
                .filter(
                    reconciliation__account_id=account_id,
                    reconciliation__deleted_at__isnull=True,
                    reconciliation__status=BankReconciliation.STATUS_COMPLETED,
                    matched_journal_line_id__isnull=False,
                )
                .values_list("matched_journal_line_id", flat=True)
            )

        qs = (
            JournalLine.active_objects()
            .filter(
                account=account,
                entry__status=JournalEntry.STATUS_POSTED,
                entry__deleted_at__isnull=True,
                entry__tenant_id=tenant_id or account.tenant_id,
                entry__entry_date__lte=as_of,
            )
            .select_related("entry")
            .order_by("entry__entry_date", "created_at")
        )
        rows = []
        for jl in qs:
            is_matched = jl.id in matched_ids
            if unmatched_only and is_matched:
                continue
            debit = float(jl.debit or 0)
            credit = float(jl.credit or 0)
            signed = debit - credit
            rows.append(
                {
                    "journal_line_id": str(jl.id),
                    "entry_id": str(jl.entry_id),
                    "entry_number": jl.entry.entry_number,
                    "entry_date": jl.entry.entry_date.isoformat(),
                    "description": jl.entry.description,
                    "memo": jl.memo or "",
                    "debit": debit,
                    "credit": credit,
                    "signed_amount": signed,
                    "is_matched": is_matched,
                    "source_reference": jl.entry.source_reference or "",
                }
            )
        return rows

    @staticmethod
    @transaction.atomic
    def match(
        *,
        reconciliation_id,
        statement_line_id,
        journal_line_id,
        user=None,
        request=None,
    ) -> BankStatementLine:
        rec = ReconciliationService.get(
            reconciliation_id=reconciliation_id, user=user, request=request
        )
        if rec.status == BankReconciliation.STATUS_COMPLETED:
            raise ReconciliationError("Cannot edit a completed reconciliation.")

        line = (
            BankStatementLine.active_objects()
            .filter(pk=statement_line_id, reconciliation=rec)
            .first()
        )
        if not line:
            raise ReconciliationError("Statement line not found.")

        jl = (
            JournalLine.active_objects()
            .filter(
                pk=journal_line_id,
                account_id=rec.account_id,
                entry__status=JournalEntry.STATUS_POSTED,
                entry__deleted_at__isnull=True,
            )
            .select_related("entry")
            .first()
        )
        if not jl:
            raise ReconciliationError("Journal line not found on this account.")

        # Amount must agree: statement +amount ↔ journal debit; −amount ↔ credit
        stmt = Decimal(str(line.amount))
        if stmt > 0:
            book = Decimal(str(jl.debit or 0))
        else:
            book = Decimal(str(jl.credit or 0))
        if abs(abs(stmt) - book) > Decimal("0.005"):
            raise ReconciliationError(
                f"Amount mismatch: statement {stmt} vs book {book}."
            )

        # Journal line not already matched in this rec
        taken = (
            BankStatementLine.active_objects()
            .filter(reconciliation=rec, matched_journal_line_id=jl.id)
            .exclude(pk=line.id)
            .exists()
        )
        if taken:
            raise ReconciliationError("Journal line already matched in this reconciliation.")

        line.matched_journal_line = jl
        line.matched_at = timezone.now()
        line.updated_by = user
        line.save(update_fields=["matched_journal_line", "matched_at", "updated_by", "updated_at"])
        return line

    @staticmethod
    @transaction.atomic
    def unmatch(
        *, reconciliation_id, statement_line_id, user=None, request=None
    ) -> BankStatementLine:
        rec = ReconciliationService.get(
            reconciliation_id=reconciliation_id, user=user, request=request
        )
        if rec.status == BankReconciliation.STATUS_COMPLETED:
            raise ReconciliationError("Cannot edit a completed reconciliation.")
        line = (
            BankStatementLine.active_objects()
            .filter(pk=statement_line_id, reconciliation=rec)
            .first()
        )
        if not line:
            raise ReconciliationError("Statement line not found.")
        line.matched_journal_line = None
        line.matched_at = None
        line.updated_by = user
        line.save(update_fields=["matched_journal_line", "matched_at", "updated_by", "updated_at"])
        return line

    @staticmethod
    @transaction.atomic
    def auto_match(*, reconciliation_id, user=None, request=None) -> dict:
        rec = ReconciliationService.get(
            reconciliation_id=reconciliation_id, user=user, request=request
        )
        if rec.status == BankReconciliation.STATUS_COMPLETED:
            raise ReconciliationError("Cannot edit a completed reconciliation.")

        unmatched_stmt = list(
            BankStatementLine.active_objects().filter(
                reconciliation=rec, matched_journal_line_id__isnull=True
            )
        )
        book_rows = ReconciliationService.list_book_lines(
            account_id=rec.account_id,
            as_of=rec.statement_date,
            unmatched_only=True,
            reconciliation_id=rec.id,
            user=user,
            request=request,
        )
        # Index book by absolute amount
        by_amount: dict[Decimal, list] = {}
        for row in book_rows:
            key = _money(abs(Decimal(str(row["signed_amount"]))))
            by_amount.setdefault(key, []).append(row)

        matched = 0
        for line in unmatched_stmt:
            amt = _money(abs(Decimal(str(line.amount))))
            candidates = by_amount.get(amt) or []
            pick = None
            for cand in candidates:
                # Prefer same sign direction and date within 3 days
                signed = Decimal(str(cand["signed_amount"]))
                if (line.amount > 0 and signed <= 0) or (line.amount < 0 and signed >= 0):
                    continue
                entry_date = parse_date(cand["entry_date"])
                if entry_date and abs((entry_date - line.line_date).days) > 3:
                    continue
                pick = cand
                break
            if not pick and candidates:
                # Fall back to first same-sign amount match
                for cand in candidates:
                    signed = Decimal(str(cand["signed_amount"]))
                    if (line.amount > 0 and signed > 0) or (line.amount < 0 and signed < 0):
                        pick = cand
                        break
            if not pick:
                continue
            try:
                ReconciliationService.match(
                    reconciliation_id=rec.id,
                    statement_line_id=line.id,
                    journal_line_id=pick["journal_line_id"],
                    user=user,
                    request=request,
                )
                matched += 1
                by_amount[amt] = [c for c in by_amount[amt] if c["journal_line_id"] != pick["journal_line_id"]]
            except ReconciliationError:
                continue

        return {"matched": matched, "remaining_unmatched": len(unmatched_stmt) - matched}

    @staticmethod
    @transaction.atomic
    def complete(*, reconciliation_id, user=None, request=None) -> BankReconciliation:
        rec = ReconciliationService.get(
            reconciliation_id=reconciliation_id, user=user, request=request
        )
        if rec.status == BankReconciliation.STATUS_COMPLETED:
            return rec

        # Refresh book balance snapshot
        rec.book_balance = ReconciliationService.book_balance_as_of(
            account=rec.account, as_of=rec.statement_date
        )
        summary = ReconciliationService.compute_summary(rec)
        if not summary["is_balanced"]:
            raise ReconciliationError(
                f"Reconciliation not balanced (difference={summary['difference']}, "
                f"unmatched statement lines={summary['unmatched_statement_count']})."
            )

        rec.status = BankReconciliation.STATUS_COMPLETED
        rec.completed_at = timezone.now()
        rec.completed_by = user
        rec.updated_by = user
        rec.save(
            update_fields=[
                "book_balance",
                "status",
                "completed_at",
                "completed_by",
                "updated_by",
                "updated_at",
            ]
        )
        return rec

"""Dedicated journal validation before posting (prompt Phase 10–11)."""

from __future__ import annotations

from decimal import Decimal

from apps.finance.models import Account
from apps.finance.services.chart_service import ChartService
from core.tenancy import apply_tenant_scope


class JournalValidationError(ValueError):
    """Raised with structured ``code`` / ``details`` for API mapping."""

    def __init__(self, message: str, *, code: str = "JOURNAL_INVALID", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class JournalValidationService:
    @staticmethod
    def validate_lines(lines) -> tuple[Decimal, Decimal]:
        if not lines or len(lines) < 2:
            raise JournalValidationError(
                "At least two journal lines are required.",
                code="JOURNAL_TOO_FEW_LINES",
            )
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for idx, row in enumerate(lines):
            debit = Decimal(str(row.get("debit") or 0))
            credit = Decimal(str(row.get("credit") or 0))
            if debit < 0 or credit < 0:
                raise JournalValidationError(
                    "Debit and credit must be non-negative.",
                    code="JOURNAL_NEGATIVE_AMOUNT",
                    details={"line_index": idx},
                )
            if debit > 0 and credit > 0:
                raise JournalValidationError(
                    "A line cannot have both debit and credit.",
                    code="JOURNAL_LINE_BOTH_SIDES",
                    details={"line_index": idx},
                )
            if debit == 0 and credit == 0:
                raise JournalValidationError(
                    "Each line needs a debit or credit amount.",
                    code="JOURNAL_LINE_ZERO",
                    details={"line_index": idx},
                )
            total_debit += debit
            total_credit += credit
        if total_debit != total_credit:
            raise JournalValidationError(
                "Journal entry is not balanced.",
                code="UNBALANCED_JOURNAL",
                details={
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit),
                    "difference": str((total_debit - total_credit).copy_abs()),
                },
            )
        return total_debit, total_credit

    @staticmethod
    def resolve_account(
        *,
        row: dict,
        tenant_id,
        user=None,
        request=None,
        allow_control_manual: bool = False,
    ) -> Account:
        account_id = row.get("account_id")
        account_code = row.get("account_code")
        if account_id:
            account = Account.active_objects().filter(
                pk=account_id, tenant_id=tenant_id
            ).first()
            if account is None and (user is not None or request is not None):
                # Confirm not a cross-tenant hit
                scoped = apply_tenant_scope(
                    Account.active_objects(), user=user, request=request
                ).filter(pk=account_id).first()
                if scoped is not None and str(scoped.tenant_id) != str(tenant_id):
                    account = None
        elif account_code:
            account = Account.active_objects().filter(
                tenant_id=tenant_id, code=account_code
            ).first()
            if account is None:
                try:
                    account = ChartService.get_by_code(
                        code=account_code,
                        tenant_id=tenant_id,
                        user=user,
                        request=request,
                    )
                except Exception:
                    account = None
        else:
            raise JournalValidationError(
                "Each line requires account_id or account_code.",
                code="JOURNAL_ACCOUNT_REQUIRED",
            )
        if account is None:
            raise JournalValidationError(
                "Account not found for this tenant.",
                code="JOURNAL_ACCOUNT_NOT_FOUND",
            )
        if not account.is_active:
            raise JournalValidationError(
                f"Account {account.code} is inactive.",
                code="JOURNAL_ACCOUNT_INACTIVE",
                details={"account_code": account.code},
            )
        if account.is_control_account and not account.allow_manual_posting:
            if not allow_control_manual:
                raise JournalValidationError(
                    f"Control account {account.code} does not allow manual posting.",
                    code="JOURNAL_CONTROL_ACCOUNT",
                    details={"account_code": account.code},
                )
        return account

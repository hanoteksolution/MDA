"""Centralized account class behavior — normal balance and increase/decrease rules.

KEEP existing lowercase DB values (`asset`, …) for compatibility with STEP 21/35 CoA.
"""

from __future__ import annotations

from enum import Enum

from django.db import models


class AccountClass(models.TextChoices):
    """Five primary accounting classes (prompt Phase 2)."""

    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"
    EQUITY = "equity", "Equity"
    REVENUE = "revenue", "Revenue"
    EXPENSE = "expense", "Expense"


class NormalBalance(models.TextChoices):
    DEBIT = "debit", "Debit"
    CREDIT = "credit", "Credit"


class Side(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


# Account class → normal balance (Phase 3)
_NORMAL_BALANCE: dict[str, str] = {
    AccountClass.ASSET: NormalBalance.DEBIT,
    AccountClass.EXPENSE: NormalBalance.DEBIT,
    AccountClass.LIABILITY: NormalBalance.CREDIT,
    AccountClass.EQUITY: NormalBalance.CREDIT,
    AccountClass.REVENUE: NormalBalance.CREDIT,
}


def normal_balance_for(account_class: str) -> str:
    try:
        return _NORMAL_BALANCE[account_class]
    except KeyError as exc:
        raise ValueError(f"Unknown account class: {account_class}") from exc


def is_debit_normal(account_class: str) -> bool:
    return normal_balance_for(account_class) == NormalBalance.DEBIT


def side_for_increase(account_class: str) -> Side:
    """Phase 4 — side that increases the account."""
    return Side.DEBIT if is_debit_normal(account_class) else Side.CREDIT


def side_for_decrease(account_class: str) -> Side:
    """Phase 4 — side that decreases the account."""
    return Side.CREDIT if is_debit_normal(account_class) else Side.DEBIT


def signed_balance(*, account_class: str, debit, credit):
    """Ledger balance in the account's normal-balance direction."""
    from decimal import Decimal

    d = Decimal(str(debit or 0))
    c = Decimal(str(credit or 0))
    if is_debit_normal(account_class):
        return d - c
    return c - d

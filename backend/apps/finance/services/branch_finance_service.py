"""Branch as a finance *dimension* — per-branch and consolidated views of the one ledger.

There is no second accounting engine: every figure here is a grouping of the same posted
``JournalLine`` rows the company trial balance and accounting-equation checks read.
Lines whose entry carries no branch stay in an explicit "Unassigned" bucket, so
Σ(branches) + Unassigned always reconciles to the consolidated figures (D8 / plan §4.6).
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.selectors.trial_balance import TrialBalanceSelector
from apps.finance.services.equation_service import AccountingEquationService
from apps.settings_app.models import Branch

UNASSIGNED = "unassigned"


def _f(value) -> float:
    return float(value)


class BranchFinanceService:
    @staticmethod
    def _tb_rows(grouped, accounts):
        rows, total_debit, total_credit = [], Decimal("0"), Decimal("0")
        for account_id, (debit, credit) in grouped.items():
            account = accounts.get(account_id)
            if account is None or (debit == 0 and credit == 0):
                continue
            balance = debit - credit if account.normal_debit else credit - debit
            rows.append(
                {
                    "account_id": str(account_id),
                    "code": account.code,
                    "name": account.name,
                    "type": account.account_type,
                    "debit": _f(debit),
                    "credit": _f(credit),
                    "balance": _f(balance),
                }
            )
            total_debit += debit
            total_credit += credit
        rows.sort(key=lambda r: r["code"])
        return rows, total_debit, total_credit

    @staticmethod
    def trial_balance_by_branch(
        *, tenant_id, date_from=None, date_to=None, branch_ids=None, user=None, request=None
    ) -> dict:
        """Per-branch trial balances, an Unassigned bucket, and the consolidated one.

        ``branch_ids`` limits which branches are listed (a restricted caller). The
        Unassigned bucket and the reconciliation are only meaningful company-wide, so
        they are returned only when ``branch_ids`` is None.
        """
        lines = JournalLine.active_objects().filter(
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
            entry__tenant_id=tenant_id,
        )
        if date_from:
            lines = lines.filter(entry__entry_date__gte=date_from)
        if date_to:
            lines = lines.filter(entry__entry_date__lte=date_to)
        accounts = {
            a.pk: a for a in Account.active_objects().filter(tenant_id=tenant_id, is_active=True)
        }

        buckets: dict = {}
        for row in lines.values("branch_id", "account_id").annotate(d=Sum("debit"), c=Sum("credit")):
            buckets.setdefault(row["branch_id"], {})[row["account_id"]] = (
                row["d"] or Decimal("0"),
                row["c"] or Decimal("0"),
            )

        branches = Branch.active_objects().filter(tenant_id=tenant_id).order_by("name")
        if branch_ids is not None:
            branches = branches.filter(pk__in=list(branch_ids))

        def _payload(key, grouped, **extra):
            rows, d, c = BranchFinanceService._tb_rows(grouped, accounts)
            return {
                **extra,
                "rows": rows,
                "totals": {"debit": _f(d), "credit": _f(c)},
                "is_balanced": d == c,
            }

        result = {
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "branches": [
                _payload(
                    b.pk,
                    buckets.get(b.pk, {}),
                    branch_id=str(b.pk),
                    branch_code=b.code,
                    branch_name=b.name,
                )
                for b in branches
            ],
        }
        if branch_ids is not None:
            return result

        result["unassigned"] = _payload(None, buckets.get(None, {}), branch_id=None)
        consolidated = TrialBalanceSelector.run(
            date_from=date_from, date_to=date_to, user=user, request=request
        )
        result["consolidated"] = consolidated

        # Reconcile independently: Σ every bucket per account vs. the company TB rows.
        summed: dict = {}
        for grouped in buckets.values():
            for account_id, (d, c) in grouped.items():
                sd, sc = summed.get(account_id, (Decimal("0"), Decimal("0")))
                summed[account_id] = (sd + d, sc + c)
        company = {
            r["account_id"]: (Decimal(str(r["debit"])), Decimal(str(r["credit"])))
            for r in consolidated["rows"]
        }
        mine = {
            str(k): (d, c)
            for k, (d, c) in summed.items()
            if k in accounts and (d != 0 or c != 0)
        }
        result["reconciles"] = {
            k: (round(v[0], 4), round(v[1], 4)) for k, v in mine.items()
        } == {k: (round(v[0], 4), round(v[1], 4)) for k, v in company.items()}
        return result

    @staticmethod
    def equation_by_branch(*, tenant_id, as_of=None, branch_ids=None, user=None, request=None) -> dict:
        """Accounting equation per branch (and, company-wide, Unassigned + consolidated)."""
        branches = Branch.active_objects().filter(tenant_id=tenant_id).order_by("name")
        if branch_ids is not None:
            branches = branches.filter(pk__in=list(branch_ids))

        def _one(branch_id):
            return AccountingEquationService.serialize(
                AccountingEquationService.evaluate(
                    as_of=as_of, user=user, request=request, tenant_id=tenant_id, branch_id=branch_id
                )
            )

        result = {
            "branches": [
                {"branch_id": str(b.pk), "branch_code": b.code, "branch_name": b.name, **_one(b.pk)}
                for b in branches
            ]
        }
        if branch_ids is None:
            result["unassigned"] = _one(UNASSIGNED)
            result["consolidated"] = _one(None)
        return result


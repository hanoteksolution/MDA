"""B5-7..B5-11: branch as a finance dimension over the single ledger."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.branch_finance_service import BranchFinanceService
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.reversal_service import AccountingReversalService
from apps.inventory.models import Inventory
from apps.inventory.services.branch_transfer_service import (
    BranchTransferService,
    TransferLineInput,
)
from apps.sales.models import Invoice
from apps.sales.services.pos_service import PosService
from tests.helpers.branch_factory import (
    add_owner,
    add_product,
    add_user,
    build_branch_tenant,
    set_inventory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    c = build_branch_tenant(slug="bfin-tenant", branch_codes=("HODAN", "BAKAARO"))
    ChartService.ensure_default_chart(tenant_id=c.tenant.pk)
    return c


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="bfin_owner")


def acct(ctx, code) -> Account:
    return Account.objects.get(tenant=ctx.tenant, code=code)


def post(ctx, owner, *, debit, credit, amount, branch=None, lines=None, source="invoice", **extra):
    """A balanced system entry. ``source`` is not manual so control accounts are allowed."""
    rows = lines or [
        {"account_id": str(acct(ctx, debit).pk), "debit": amount, "credit": 0},
        {"account_id": str(acct(ctx, credit).pk), "debit": 0, "credit": amount},
    ]
    return JournalService.create_entry(
        data={
            "tenant_id": ctx.tenant.pk,
            "description": "test",
            "source_type": source,
            "branch_id": ctx.branch(branch).pk if branch else None,
            "lines": rows,
            **extra,
        },
        user=owner,
    )


def tb(ctx, owner):
    return BranchFinanceService.trial_balance_by_branch(tenant_id=ctx.tenant.pk, user=owner)


def by_code(payload, code):
    return next((r for r in payload["branches"] if r["branch_code"] == code), None)


# --------------------------------------------------------------------------- #
# B5-7: the line carries the entry's branch
# --------------------------------------------------------------------------- #


def test_every_posted_line_carries_the_entrys_branch(ctx, owner):
    entry = post(ctx, owner, debit="1000", credit="4000", amount=50, branch="HODAN")
    lines = JournalLine.objects.filter(entry=entry)
    assert lines.count() == 2
    assert {line.branch_id for line in lines} == {ctx.branch("HODAN").pk}


def test_a_pos_sale_posts_lines_on_the_selling_branch(ctx, owner):
    product = add_product(ctx, sku="BFIN-POS", cost_price=Decimal("4"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("10"))
    PosService.checkout(
        data={
            "branch_id": str(ctx.branch("BAKAARO").pk),
            "customer_id": "walkin",
            "waiter_name": "Counter",
            "payment_method": "cash",
            "items": [{"product_id": str(product.pk), "quantity": "2", "unit_price": "10"}],
            "idempotency_key": "bfin-pos-1",
        },
        user=owner,
    )
    invoice = Invoice.objects.get(idempotency_key="bfin-pos-1")
    lines = JournalLine.objects.filter(entry__source_id=invoice.pk)
    assert lines.exists()
    assert {line.branch_id for line in lines} == {ctx.branch("BAKAARO").pk}


def test_a_reversal_keeps_each_lines_branch(ctx, owner):
    entry = post(ctx, owner, debit="1000", credit="4000", amount=20, branch="HODAN")
    reversal = AccountingReversalService.reverse_entry(entry=entry, user=owner, reason="test")
    assert {l.branch_id for l in JournalLine.objects.filter(entry=reversal)} == {ctx.branch("HODAN").pk}


def test_a_line_cannot_name_a_branch_of_another_tenant(ctx, owner):
    other = build_branch_tenant(slug="bfin-other", branch_codes=("HODAN",))
    with pytest.raises(JournalError) as exc:
        post(
            ctx,
            owner,
            debit="1000",
            credit="4000",
            amount=5,
            lines=[
                {"account_id": str(acct(ctx, "1000").pk), "debit": 5, "credit": 0,
                 "branch_id": other.branch("HODAN").pk},
                {"account_id": str(acct(ctx, "4000").pk), "debit": 0, "credit": 5,
                 "branch_id": other.branch("HODAN").pk},
            ],
        )
    assert exc.value.code == "JOURNAL_BRANCH_INVALID"


def test_a_multi_branch_entry_must_balance_within_each_branch(ctx, owner):
    h, b = ctx.branch("HODAN").pk, ctx.branch("BAKAARO").pk
    with pytest.raises(JournalError) as exc:
        post(
            ctx, owner, debit="1000", credit="4000", amount=10,
            lines=[
                {"account_id": str(acct(ctx, "1000").pk), "debit": 10, "credit": 0, "branch_id": h},
                {"account_id": str(acct(ctx, "4000").pk), "debit": 0, "credit": 10, "branch_id": b},
            ],
        )
    assert exc.value.code == "JOURNAL_BRANCH_IMBALANCE"


# --------------------------------------------------------------------------- #
# B5-8: per-branch and consolidated trial balance; Σ branches == company
# --------------------------------------------------------------------------- #


def test_trial_balance_balances_per_branch_and_sums_to_the_company(ctx, owner):
    post(ctx, owner, debit="1000", credit="4000", amount=100, branch="HODAN")
    post(ctx, owner, debit="1000", credit="4000", amount=40, branch="BAKAARO")
    post(ctx, owner, debit="6010", credit="1000", amount=15, branch="HODAN")

    result = tb(ctx, owner)
    hodan, bakaaro = by_code(result, "HODAN"), by_code(result, "BAKAARO")

    assert hodan["is_balanced"] and bakaaro["is_balanced"]
    assert hodan["totals"]["debit"] == 115.0 and bakaaro["totals"]["debit"] == 40.0
    assert result["consolidated"]["is_balanced"]
    assert result["consolidated"]["totals"]["debit"] == 155.0
    assert result["reconciles"] is True
    total = sum(r["totals"]["debit"] for r in result["branches"]) + result["unassigned"]["totals"]["debit"]
    assert total == result["consolidated"]["totals"]["debit"]


def test_the_trial_balance_can_be_read_for_one_branch(ctx, owner):
    from apps.finance.selectors.trial_balance import TrialBalanceSelector

    post(ctx, owner, debit="1000", credit="4000", amount=100, branch="HODAN")
    post(ctx, owner, debit="1000", credit="4000", amount=40, branch="BAKAARO")
    one = TrialBalanceSelector.run(user=owner, branch_id=str(ctx.branch("BAKAARO").pk))
    assert one["totals"]["debit"] == 40.0 and one["is_balanced"]


# --------------------------------------------------------------------------- #
# B5-9: an internal transfer is balance-sheet only (D8)
# --------------------------------------------------------------------------- #


def run_transfer(ctx, owner, product, qty="10"):
    svc = BranchTransferService
    req = svc.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk,
        destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal(qty))],
        user=owner,
    )
    svc.approve(request_id=req.pk, user=owner)
    svc.reserve(request_id=req.pk, user=owner)
    svc.dispatch(request_id=req.pk, user=owner)
    return req


def balance(ctx, code, branch=None):
    qs = JournalLine.objects.filter(
        account=acct(ctx, code), entry__status=JournalEntry.STATUS_POSTED
    )
    if branch:
        qs = qs.filter(branch=ctx.branch(branch))
    d = sum((l.debit for l in qs), Decimal("0"))
    c = sum((l.credit for l in qs), Decimal("0"))
    return d - c


def test_a_transfer_posts_no_revenue_or_pnl_and_keeps_company_inventory(ctx, owner):
    product = add_product(ctx, sku="BFIN-TR", cost_price=Decimal("3"))
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("100"))
    # Opening inventory value 300 on Hodan (Dr Inventory / Cr Equity).
    post(ctx, owner, debit="1200", credit="3000", amount=300, branch="HODAN")
    company_before = balance(ctx, "1200") + balance(ctx, "1210")

    req = run_transfer(ctx, owner, product, "10")  # 10 x 3 = 30 in transit
    assert balance(ctx, "1200", "HODAN") == Decimal("270")
    assert balance(ctx, "1210", "HODAN") == Decimal("30")
    assert balance(ctx, "1200", "BAKAARO") == 0  # nothing credited before receipt

    BranchTransferService.receive(request_id=req.pk, user=owner)

    assert balance(ctx, "1200", "HODAN") == Decimal("270")
    assert balance(ctx, "1200", "BAKAARO") == Decimal("30")
    assert balance(ctx, "1210") == 0  # clearing nets to zero company-wide
    assert balance(ctx, "1200") + balance(ctx, "1210") == company_before  # value unchanged

    posted = JournalLine.objects.filter(entry__source_module="inventory")
    assert posted.count() == 4  # two entries, two lines each
    assert not posted.filter(account__account_type__in=["revenue", "expense"]).exists()
    result = tb(ctx, owner)
    assert result["reconciles"] and all(b["is_balanced"] for b in result["branches"])
    # Stock actually moved too.
    assert Inventory.objects.get(product=product, warehouse=ctx.warehouse("BAKAARO")).quantity == Decimal("10")


def test_a_short_receipt_leaves_the_shortfall_visible_in_transit(ctx, owner):
    product = add_product(ctx, sku="BFIN-SHORT", cost_price=Decimal("2"))
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("50"))
    req = run_transfer(ctx, owner, product, "10")
    BranchTransferService.receive(
        request_id=req.pk, user=owner,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("8"))],
    )
    # 2 units x 2 stay in Inventory in Transit: not silently written off, no P&L.
    assert balance(ctx, "1210") == Decimal("4")
    assert not JournalLine.objects.filter(
        entry__source_module="inventory", account__account_type__in=["revenue", "expense"]
    ).exists()


# --------------------------------------------------------------------------- #
# B5-10: accounting equation per branch and consolidated
# --------------------------------------------------------------------------- #


def test_accounting_equation_holds_per_branch_and_consolidated(ctx, owner):
    post(ctx, owner, debit="1000", credit="3000", amount=500, branch="HODAN")
    post(ctx, owner, debit="1000", credit="4000", amount=80, branch="HODAN")
    post(ctx, owner, debit="5000", credit="1200", amount=30, branch="HODAN")
    post(ctx, owner, debit="1000", credit="3000", amount=200, branch="BAKAARO")
    post(ctx, owner, debit="6010", credit="1000", amount=25, branch="BAKAARO")
    post(ctx, owner, debit="1000", credit="3000", amount=10)  # unassigned

    result = BranchFinanceService.equation_by_branch(tenant_id=ctx.tenant.pk, user=owner)
    assert all(row["ok"] for row in result["branches"])
    assert result["unassigned"]["ok"] and result["consolidated"]["ok"]


# --------------------------------------------------------------------------- #
# B5-11: Unassigned bucket keeps the consolidated totals reconciled
# --------------------------------------------------------------------------- #


def test_unassigned_lines_have_a_bucket_and_totals_still_reconcile(ctx, owner):
    post(ctx, owner, debit="1000", credit="4000", amount=60, branch="HODAN")
    legacy = post(ctx, owner, debit="1000", credit="4000", amount=25)  # no branch
    assert {l.branch_id for l in JournalLine.objects.filter(entry=legacy)} == {None}

    result = tb(ctx, owner)
    assert result["unassigned"]["totals"]["debit"] == 25.0
    assert result["unassigned"]["is_balanced"]
    assert result["consolidated"]["totals"]["debit"] == 85.0
    assert result["reconciles"] is True


def test_a_branch_limited_caller_never_receives_company_level_buckets(ctx, owner):
    post(ctx, owner, debit="1000", credit="4000", amount=60, branch="HODAN")
    limited = BranchFinanceService.trial_balance_by_branch(
        tenant_id=ctx.tenant.pk, branch_ids=[ctx.branch("HODAN").pk], user=owner
    )
    assert "consolidated" not in limited and "unassigned" not in limited
    assert [b["branch_code"] for b in limited["branches"]] == ["HODAN"]


# --------------------------------------------------------------------------- #
# API: an inaccessible branch is a 403, never an empty success
# --------------------------------------------------------------------------- #


def test_trial_balance_api_refuses_a_branch_the_user_cannot_see(ctx, owner):
    accountant = add_user(ctx, username="bfin_acct", role_slug="admin", branches=("HODAN",))
    client = APIClient()
    client.force_authenticate(accountant)
    ok = client.get("/api/v1/finance/reports/trial-balance/", {"branch_id": str(ctx.branch("HODAN").pk)})
    denied = client.get(
        "/api/v1/finance/reports/trial-balance/", {"branch_id": str(ctx.branch("BAKAARO").pk)}
    )
    assert ok.status_code == 200
    assert denied.status_code == 403

"""B6-1, B6-2, B6-4: branch-aware reports and dashboards; consolidated == Σ branches."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.finance.models import Account
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.reports.services.branch_report_service import (
    REPORTS,
    BranchReportService,
    resolve_report_scope,
)
from apps.sales.services.pos_service import PosService
from apps.sales.services.refund_service import RefundService
from tests.helpers.branch_factory import (
    add_owner,
    add_product,
    add_user,
    build_branch_tenant,
    grant,
    make_profile,
    set_inventory,
)
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    c = build_branch_tenant(slug="brep-tenant", branch_codes=("HODAN", "BAKAARO", "DEGMO"))
    ChartService.ensure_default_chart(tenant_id=c.tenant.pk)
    return c


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="brep_owner")


@pytest.fixture
def seeded(ctx, owner):
    """Different activity in every branch, plus one Unassigned journal entry."""
    product = add_product(ctx, sku="BREP-1", cost_price=Decimal("4"))
    plan = {"HODAN": ("5", "50"), "BAKAARO": ("2", "20"), "DEGMO": ("0", "7")}  # (units sold, stock)
    invoices = {}
    for code, (sold, stock) in plan.items():
        set_inventory(ctx, product=product, branch_code=code, quantity=Decimal(stock))
        if Decimal(sold):
            result = PosService.checkout(
                data={
                    "branch_id": str(ctx.branch(code).pk),
                    "customer_id": "walkin",
                    "waiter_name": "Counter",
                    "payment_method": "cash",
                    "items": [{"product_id": str(product.pk), "quantity": sold, "unit_price": "10"}],
                    "idempotency_key": f"brep-{code}",
                },
                user=owner,
            )
            invoices[code] = result["invoice"]["id"]
    RefundService.refund_invoice(
        invoice_id=invoices["HODAN"],
        items=[{"product_id": str(product.pk), "quantity": "1"}],
        reason="test",
        user=owner,
    )

    def acct(code):
        return str(Account.objects.get(tenant=ctx.tenant, code=code).pk)

    for code, amount in (("HODAN", 30), ("BAKAARO", 12)):
        JournalService.create_entry(
            data={
                "tenant_id": ctx.tenant.pk, "description": "rent", "source_type": "expense",
                "branch_id": ctx.branch(code).pk,
                "lines": [
                    {"account_id": acct("6020"), "debit": amount, "credit": 0},
                    {"account_id": acct("1000"), "debit": 0, "credit": amount},
                ],
            },
            user=owner,
        )
    JournalService.create_entry(  # Unassigned (no branch)
        data={
            "tenant_id": ctx.tenant.pk, "description": "legacy", "source_type": "invoice",
            "lines": [
                {"account_id": acct("1000"), "debit": 9, "credit": 0},
                {"account_id": acct("4000"), "debit": 0, "credit": 9},
            ],
        },
        user=owner,
    )
    return product


def scope_for(owner, ctx, requested):
    from types import SimpleNamespace

    return resolve_report_scope(request=SimpleNamespace(user=owner, headers={}, query_params={}),
                                user=owner, requested=requested)


def run(owner, ctx, report, requested=None):
    return BranchReportService.run(report=report, scope=scope_for(owner, ctx, requested))


# --------------------------------------------------------------------------- #
# B6-1: single, multi and consolidated scope for every report
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("report", REPORTS)
def test_every_report_accepts_single_multi_and_consolidated_scope(ctx, owner, seeded, report):
    h, b = str(ctx.branch("HODAN").pk), str(ctx.branch("BAKAARO").pk)
    single = run(owner, ctx, report, h)
    multi = run(owner, ctx, report, f"{h},{b}")
    consolidated = run(owner, ctx, report, "all")

    assert (single["mode"], multi["mode"], consolidated["mode"]) == ("single", "multi", "consolidated")
    assert [r["branch_code"] for r in single["branches"]] == ["HODAN"]
    assert {r["branch_code"] for r in multi["branches"]} == {"HODAN", "BAKAARO"}
    assert {r["branch_code"] for r in consolidated["branches"]} == {"HODAN", "BAKAARO", "DEGMO"}
    assert single["reconciles"] and multi["reconciles"] and consolidated["reconciles"]


def test_a_branch_the_user_cannot_see_is_refused_in_any_scope(ctx, seeded):
    profile = make_profile(tenant=ctx.tenant, code="REP", name="Reports", codenames=["reports.view"])
    analyst = add_user(ctx, username="brep_analyst", role_slug="admin")
    grant(ctx, user=analyst, branch_code="HODAN", profile=profile, is_default=True)
    bakaaro = str(ctx.branch("BAKAARO").pk)
    hodan = str(ctx.branch("HODAN").pk)
    with pytest.raises(PermissionDenied):
        scope_for(analyst, ctx, bakaaro)
    with pytest.raises(PermissionDenied):
        scope_for(analyst, ctx, f"{hodan},{bakaaro}")  # one bad id poisons the whole request
    # "all" quietly means "everything I may see" — never a widening.
    only_mine = scope_for(analyst, ctx, "all")
    assert only_mine.branch_ids == (hodan,) and not only_mine.covers_all


# --------------------------------------------------------------------------- #
# B6-2 (hard gate): consolidated == Σ branches for sales, stock value, P&L, cash
# --------------------------------------------------------------------------- #


def total_of(result, key):
    rows = sum(r[key] for r in result["branches"])
    return rows + result.get("unassigned", {}).get(key, 0)


def test_consolidated_sales_equals_sum_of_branches(ctx, owner, seeded):
    r = run(owner, ctx, "sales")
    by = {x["branch_code"]: x for x in r["branches"]}
    assert (by["HODAN"]["gross"], by["HODAN"]["refunded"], by["HODAN"]["net"]) == (50.0, 10.0, 40.0)
    assert by["BAKAARO"]["gross"] == 20.0 and by["DEGMO"]["invoices"] == 0
    assert r["consolidated"]["gross"] == 70.0 == total_of(r, "gross")
    assert r["consolidated"]["net"] == 60.0 == total_of(r, "net")
    assert r["reconciles"]


def test_consolidated_stock_value_equals_sum_of_branches(ctx, owner, seeded):
    r = run(owner, ctx, "stock-value")
    by = {x["branch_code"]: x for x in r["branches"]}
    # Stock after sales (+1 unit refunded back in Hodan): 46, 18, 7 units at cost 4.
    assert by["HODAN"]["units"] == 46.0 and by["HODAN"]["value"] == 184.0
    assert r["consolidated"]["value"] == total_of(r, "value") == (46 + 18 + 7) * 4
    assert r["reconciles"]


def test_consolidated_profit_and_loss_equals_branches_plus_unassigned(ctx, owner, seeded):
    r = run(owner, ctx, "profit-loss")
    by = {x["branch_code"]: x for x in r["branches"]}
    # Expenses = rent journal + the COGS each POS sale posted (Hodan: 30 + 5x4 - 1x4 refunded).
    assert by["HODAN"]["expenses"] == 46.0 and by["BAKAARO"]["expenses"] == 12.0 + 2 * 4
    assert r["unassigned"]["revenue"] == 9.0  # legacy entry: visible, not dropped
    assert r["consolidated"]["expenses"] == total_of(r, "expenses") == 66.0
    assert r["consolidated"]["revenue"] == total_of(r, "revenue")
    assert r["consolidated"]["net_profit"] == pytest.approx(total_of(r, "net_profit"))
    assert r["reconciles"]


def test_consolidated_cash_equals_sum_of_branches(ctx, owner, seeded):
    r = run(owner, ctx, "cash")
    by = {x["branch_code"]: x for x in r["branches"]}
    assert by["HODAN"]["cash_received"] == 50.0 and by["HODAN"]["cash_refunded"] == 10.0
    assert by["HODAN"]["net_cash"] == 40.0
    assert r["consolidated"]["cash_received"] == total_of(r, "cash_received") == 70.0
    assert r["consolidated"]["net_cash"] == total_of(r, "net_cash") == 60.0
    assert r["reconciles"]


def test_a_partial_scope_reconciles_without_the_unassigned_bucket(ctx, owner, seeded):
    r = run(owner, ctx, "profit-loss", f"{ctx.branch('HODAN').pk},{ctx.branch('BAKAARO').pk}")
    assert "unassigned" not in r  # company-level data only for a full consolidated view
    assert r["consolidated"]["expenses"] == 46.0 + 20.0 and r["reconciles"]


def test_date_filter_applies_to_branches_and_consolidated_alike(ctx, owner, seeded):
    from django.utils import timezone

    tomorrow = timezone.localdate().replace(year=timezone.localdate().year + 1)
    r = BranchReportService.run(report="sales", scope=scope_for(owner, ctx, "all"), date_from=tomorrow)
    assert r["consolidated"]["gross"] == 0 and all(x["gross"] == 0 for x in r["branches"])
    assert r["reconciles"]


# --------------------------------------------------------------------------- #
# B6-4: dashboard widgets follow the active branch
# --------------------------------------------------------------------------- #


def sale_branches(response):
    data = response.json()["data"]
    rows = data["results"] if isinstance(data, dict) else data
    return {row["id"].split("-")[1] for row in rows}


def api(user, branch_id=None):
    client = auth_client_as(APIClient(), user)
    if branch_id:
        client.credentials(**{**client._credentials, "HTTP_X_BRANCH_ID": str(branch_id)})
    return client


def test_dashboard_recent_sales_follow_the_active_branch(ctx, owner, seeded):
    hodan = api(owner, ctx.branch("HODAN").pk).get("/api/v1/dashboard/recent-sales/")
    bakaaro = api(owner, ctx.branch("BAKAARO").pk).get("/api/v1/dashboard/recent-sales/")
    assert hodan.status_code == bakaaro.status_code == 200
    assert sale_branches(hodan) == {"HODAN"}
    assert sale_branches(bakaaro) == {"BAKAARO"}


def test_dashboard_consolidated_view_spans_branches_for_a_full_access_user(ctx, owner, seeded):
    assert sale_branches(api(owner, "all").get("/api/v1/dashboard/recent-sales/")) == {"HODAN", "BAKAARO"}


def test_dashboard_refuses_a_branch_or_consolidation_the_user_cannot_have(ctx, seeded):
    profile = make_profile(
        tenant=ctx.tenant, code="DASH", name="Dash", codenames=["dashboard.view", "reports.view"]
    )
    viewer = add_user(ctx, username="brep_dash", role_slug="admin")
    grant(ctx, user=viewer, branch_code="HODAN", profile=profile, is_default=True)
    assert api(viewer, ctx.branch("BAKAARO").pk).get("/api/v1/dashboard/recent-sales/").status_code == 403
    assert api(viewer, "all").get("/api/v1/dashboard/recent-sales/").status_code == 403
    assert api(viewer, ctx.branch("HODAN").pk).get("/api/v1/dashboard/recent-sales/").status_code == 200

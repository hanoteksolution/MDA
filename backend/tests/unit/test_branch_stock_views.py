"""B3-6, B3-8: branch/warehouse aggregation and cross-branch availability.

Aggregation is derived (no second mutable figure); cross-branch visibility is a
number, gated by its own permission, independent of operate permission.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.inventory.services.branch_stock_service import (
    aggregate_branch_stock,
    aggregate_warehouse_stock,
    branch_stock_dashboard,
    in_transit_quantity,
    product_availability,
    stock_status,
)
from tests.helpers.branch_factory import (
    add_owner,
    add_product,
    add_user,
    build_branch_tenant,
    grant,
    set_inventory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="stock-view-tenant")


@pytest.fixture
def product(ctx):
    return add_product(ctx, sku="AVAIL-1", minimum_stock=5)


def test_branch_aggregation_sums_every_warehouse_in_the_branch(ctx, product):
    """MAIN has one warehouse in this fixture; add a second to prove summation,
    not just pass-through of a single warehouse's numbers."""
    from apps.inventory.models import Warehouse

    extra_wh = Warehouse.objects.create(
        tenant=ctx.tenant, branch=ctx.branch("MAIN"), name="Main Annex", code="WH-MAIN-2"
    )
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=Decimal("10"), reserved=Decimal("2"))
    from apps.inventory.models import Inventory

    Inventory.objects.create(
        tenant=ctx.tenant, product=product, warehouse=extra_wh, quantity=Decimal("5"), reserved_quantity=Decimal("1")
    )

    result = aggregate_branch_stock(branch=ctx.branch("MAIN"), product=product)
    assert result["on_hand"] == Decimal("15")
    assert result["reserved"] == Decimal("3")
    assert result["available"] == Decimal("12")


def test_branch_aggregation_is_derived_not_a_stored_field(ctx, product):
    """Changing the underlying Inventory row changes the aggregate immediately —
    there is no cache to go stale (BRANCH_INVENTORY.md §4)."""
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    before = aggregate_branch_stock(branch=ctx.branch("HODAN"), product=product)
    assert before["on_hand"] == Decimal("10")

    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("40"))
    after = aggregate_branch_stock(branch=ctx.branch("HODAN"), product=product)
    assert after["on_hand"] == Decimal("40")


def test_branch_with_no_inventory_rows_reports_zero_not_none(ctx, product):
    result = aggregate_branch_stock(branch=ctx.branch("BAKAARO"), product=product)
    assert result["on_hand"] == Decimal("0")
    assert result["reserved"] == Decimal("0")
    assert result["available"] == Decimal("0")


def test_warehouse_aggregation_matches_the_single_inventory_row(ctx, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("7"), reserved=Decimal("2"))
    result = aggregate_warehouse_stock(warehouse=ctx.warehouse("HODAN"), product=product)
    assert result["on_hand"] == Decimal("7")
    assert result["available"] == Decimal("5")


def test_company_total_equals_sum_of_branch_totals(ctx, product):
    """B3-6: company total == Σ branch on-hand + in-transit (in-transit is 0 in
    Phase 3, per BRANCH_INVENTORY.md §2)."""
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=Decimal("18"))
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("0"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("6"))

    branch_totals = sum(
        aggregate_branch_stock(branch=ctx.branch(code), product=product)["on_hand"]
        for code in ctx.branches
    )
    company_total = sum(
        aggregate_warehouse_stock(warehouse=w, product=product)["on_hand"]
        for w in [ctx.warehouse(c) for c in ctx.branches]
    )
    assert branch_totals == company_total == Decimal("24")
    assert in_transit_quantity(product=product) == Decimal("0")


def test_product_availability_shape_matches_the_worked_example(ctx, product):
    """Hodan: 0 local, Main: 18, Bakaaro: 6 — the brief's exact scenario."""
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("0"))
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=Decimal("18"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("6"))

    data = product_availability(
        product=product, current_branch=ctx.branch("HODAN"), tenant=ctx.tenant
    )
    assert data["current_branch"]["available"] == Decimal("0")
    assert data["current_branch"]["in_transit"] == Decimal("0")
    others = {row["branch_id"]: row["available"] for row in data["other_branches"]}
    assert others[str(ctx.branch("MAIN").pk)] == Decimal("18")
    assert others[str(ctx.branch("BAKAARO").pk)] == Decimal("6")


def test_availability_excludes_other_branches_when_permission_withheld(ctx, product):
    """B3-8: inventory.cross_branch_view gates the list independently."""
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=Decimal("18"))
    data = product_availability(
        product=product,
        current_branch=ctx.branch("HODAN"),
        tenant=ctx.tenant,
        include_other_branches=False,
    )
    assert data["other_branches"] == []
    # Current-branch figures are still returned — visibility of your own branch's
    # stock is not gated by the cross-branch permission.
    assert "available" in data["current_branch"]


def test_availability_never_shows_another_tenants_branches(ctx, product):
    other = build_branch_tenant(slug="stock-view-other", branch_codes=("REMOTE",))
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=Decimal("5"))
    data = product_availability(
        product=product, current_branch=ctx.branch("HODAN"), tenant=ctx.tenant
    )
    ids = {row["branch_id"] for row in data["other_branches"]}
    assert str(other.branch("REMOTE").pk) not in ids


def test_stock_status_uses_the_existing_minimum_stock_threshold():
    assert stock_status(on_hand=0, minimum_stock=5) == "OUT_OF_STOCK"
    assert stock_status(on_hand=5, minimum_stock=5) == "LOW_STOCK"
    assert stock_status(on_hand=6, minimum_stock=5) == "IN_STOCK"


def test_branch_dashboard_reports_sku_and_stock_state_counts(ctx, product):
    low_product = add_product(ctx, sku="AVAIL-LOW", minimum_stock=10)
    out_product = add_product(ctx, sku="AVAIL-OUT", minimum_stock=5)
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("50"))
    set_inventory(ctx, product=low_product, branch_code="HODAN", quantity=Decimal("3"))
    set_inventory(ctx, product=out_product, branch_code="HODAN", quantity=Decimal("0"))

    dashboard = branch_stock_dashboard(branch=ctx.branch("HODAN"))
    assert dashboard["total_skus"] == 3
    assert dashboard["low_stock_count"] == 1
    assert dashboard["out_of_stock_count"] == 1


# --------------------------------------------------------------------------- #
# RBAC: cross_branch_view is independent of inventory.view / inventory.adjust
# --------------------------------------------------------------------------- #


def test_cashier_role_gains_cross_branch_view_without_inventory_view(ctx):
    """The brief's concrete POS scenario: a cashier who cannot open the inventory
    list can still check availability elsewhere."""
    cashier = add_user(ctx, username="stock_view_cashier", role_slug="cashier")
    assert cashier.has_permission("inventory.view") is False
    assert cashier.has_permission("inventory.cross_branch_view") is True

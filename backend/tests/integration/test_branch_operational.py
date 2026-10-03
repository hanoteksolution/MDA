"""Branch operational completion: AM Electronics with Hodan / Bakaaro / KM4.

Covers independent branch stock, POS pinned to the acting branch, cross-branch visibility and
search, destination-initiated transfer requests, the extended branch reports (reconciling with
the consolidated total), the branch overview, branch-manager restriction and tenant isolation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import BranchTransferRequest, Inventory
from apps.purchases.models import PurchaseOrder
from apps.sales.models import Expense
from apps.suppliers.models import Supplier
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
INV = "/api/v1/inventory"
REP = "/api/v1/reports"
MANAGER_CODES = ["dashboard.view", "reports.view", "inventory.view", "inventory.transfer", "inventory.cross_branch_view",
                 "pos.access", "sales.view", "sales.create"]


@pytest.fixture
def am():
    ctx = build_branch_tenant(slug="am-electronics", branch_codes=("HODAN", "BAKAARO", "KM4"))
    iphone = add_product(ctx, sku="IP17PRO", name="iPhone 17 Pro", cost_price=Decimal("900"), selling_price=Decimal("1200"), minimum_stock=2)
    set_inventory(ctx, product=iphone, branch_code="HODAN", quantity=0)
    set_inventory(ctx, product=iphone, branch_code="BAKAARO", quantity=12)
    set_inventory(ctx, product=iphone, branch_code="KM4", quantity=4, reserved=1)
    owner = add_owner(ctx, username="am_owner")
    manager_profile = make_profile(tenant=ctx.tenant, code="MGR", name="Branch manager", codenames=MANAGER_CODES, is_manager=True)
    hodan_mgr = add_user(ctx, username="hodan_mgr", role_slug="admin")
    grant(ctx, user=hodan_mgr, branch_code="HODAN", profile=manager_profile, is_default=True)
    bak_mgr = add_user(ctx, username="bak_mgr", role_slug="admin")
    grant(ctx, user=bak_mgr, branch_code="BAKAARO", profile=manager_profile, is_default=True)
    return {"ctx": ctx, "iphone": iphone, "owner": auth_client_as(APIClient(), owner),
            "hodan": auth_client_as(APIClient(), hodan_mgr), "bakaaro": auth_client_as(APIClient(), bak_mgr)}


def bid(am, code):
    return str(am["ctx"].branch(code).pk)


def qty(am, code):
    return Inventory.objects.get(product=am["iphone"], warehouse=am["ctx"].warehouse(code)).quantity


def sale(client, branch_id, product, *, header=None, quantity="1"):
    kw = {"HTTP_X_BRANCH_ID": header} if header else {}
    return client.post("/api/v1/pos/checkout/", {
        "branch_id": branch_id, "customer_id": "walkin", "waiter_name": "Counter", "payment_method": "cash",
        "items": [{"product_id": str(product.pk), "quantity": quantity, "unit_price": "1200"}],
    }, format="json", **kw)


# --- inventory & POS -------------------------------------------------------------------------

def test_stock_is_independent_per_branch_and_never_summed_locally(am):
    r = am["hodan"].get(f"{INV}/products/{am['iphone'].pk}/availability/", HTTP_X_BRANCH_ID=bid(am, "HODAN"))
    assert r.status_code == 200, r.content
    data = r.json()["data"]
    assert Decimal(str(data["current_branch"]["available"])) == 0  # Hodan never "has 16"
    others = {b["branch_code"]: b for b in data["other_branches"]}
    assert Decimal(str(others["BAKAARO"]["available"])) == 12
    assert Decimal(str(others["KM4"]["on_hand"])) == 4 and Decimal(str(others["KM4"]["reserved"])) == 1
    assert Decimal(str(others["KM4"]["available"])) == 3
    # Warehouse breakdown only where the caller may view inventory (Hodan manager: not in Bakaaro/KM4).
    assert others["BAKAARO"]["warehouses"] is None and data["current_branch"]["warehouses"]
    owner = am["owner"].get(f"{INV}/products/{am['iphone'].pk}/availability/", HTTP_X_BRANCH_ID=bid(am, "HODAN")).json()["data"]
    assert all(b["warehouses"] for b in owner["other_branches"])


def test_pos_deducts_only_the_acting_branch(am):
    iphone = am["iphone"]
    r = sale(am["bakaaro"], bid(am, "BAKAARO"), iphone, header=bid(am, "BAKAARO"), quantity="2")
    assert r.status_code == 201, r.content
    assert (qty(am, "HODAN"), qty(am, "BAKAARO"), qty(am, "KM4")) == (0, 10, 4)


def test_pos_cannot_sell_from_another_branch(am):
    iphone = am["iphone"]
    # Body names Bakaaro, header says Hodan -> refused (no silent re-pointing).
    assert sale(am["hodan"], bid(am, "BAKAARO"), iphone, header=bid(am, "HODAN")).status_code == 400
    # Body names Bakaaro, no header: Hodan manager has no POS access there -> 403.
    assert sale(am["hodan"], bid(am, "BAKAARO"), iphone).status_code == 403
    # "all" is never a branch to sell in.
    assert sale(am["owner"], "", iphone, header="all").status_code == 400
    assert qty(am, "BAKAARO") == 12


def test_pos_without_branch_uses_the_callers_default_branch(am):
    r = sale(am["bakaaro"], "", am["iphone"])
    assert r.status_code == 201, r.content
    assert r.json()["data"]["invoice"]["branch_id"] == bid(am, "BAKAARO") and qty(am, "BAKAARO") == 11


def test_cross_branch_search(am):
    r = am["hodan"].get(f"{INV}/cross-branch-search/", {"search": "iphone"}, HTTP_X_BRANCH_ID=bid(am, "HODAN"))
    assert r.status_code == 200, r.content
    data = r.json()["data"]
    assert data["can_view_other_branches"] is True and data["branch_name"] == "Hodan"
    row = data["results"][0]
    assert row["product_sku"] == "IP17PRO"
    assert {b["branch_code"]: Decimal(str(b["available"])) for b in row["other_branches"]} == {"BAKAARO": 12, "KM4": 3}
    assert am["hodan"].get(f"{INV}/cross-branch-search/", {"search": "i"}, HTTP_X_BRANCH_ID=bid(am, "HODAN")).status_code == 400
    # Acting in a branch the caller cannot access -> 403.
    assert am["hodan"].get(f"{INV}/cross-branch-search/", {"search": "iphone"}, HTTP_X_BRANCH_ID=bid(am, "KM4")).status_code == 403


def test_cross_branch_visibility_needs_the_permission_in_the_acting_branch(am):
    ctx = am["ctx"]
    cashier = add_user(ctx, username="hodan_cashier", role_slug="admin")
    grant(ctx, user=cashier, branch_code="HODAN", profile=make_profile(tenant=ctx.tenant, code="CASH", name="Cashier", codenames=["pos.access", "inventory.view"]))
    data = auth_client_as(APIClient(), cashier).get(f"{INV}/cross-branch-search/", {"search": "iphone"}, HTTP_X_BRANCH_ID=bid(am, "HODAN")).json()["data"]
    assert data["can_view_other_branches"] is False and data["results"][0]["other_branches"] == []


# --- transfers ---------------------------------------------------------------------------------

def test_destination_requests_source_approves_and_stock_moves_only_through_the_workflow(am):
    hodan, bakaaro = am["hodan"], am["bakaaro"]
    r = hodan.post(f"{INV}/branch-transfers/", {
        "source_branch_id": bid(am, "BAKAARO"), "destination_branch_id": bid(am, "HODAN"),
        "lines": [{"product_id": str(am["iphone"].pk), "quantity": "3"}], "notes": "Customer waiting",
    }, format="json", HTTP_X_BRANCH_ID=bid(am, "HODAN"))
    assert r.status_code == 201, r.content
    t = r.json()["data"]
    assert t["status"] == "REQUESTED" and t["requested_by"] == "hodan_mgr" and t["lines"][0]["product_name"] == "iPhone 17 Pro"
    assert t["source_warehouse_name"] == "Bakaaro WH" and t["total_quantity"] == 3
    assert qty(am, "BAKAARO") == 12  # a request moves nothing
    # The requesting (destination) branch cannot approve its own request.
    assert hodan.post(f"{INV}/branch-transfers/{t['id']}/approve/", HTTP_X_BRANCH_ID=bid(am, "HODAN")).status_code == 403
    # Bakaaro sees it and runs the source side.
    listed = bakaaro.get(f"{INV}/branch-transfers/", HTTP_X_BRANCH_ID=bid(am, "BAKAARO")).json()["data"]["results"]
    assert [x["id"] for x in listed] == [t["id"]]
    for action in ("approve", "reserve", "dispatch"):
        r = bakaaro.post(f"{INV}/branch-transfers/{t['id']}/{action}/", HTTP_X_BRANCH_ID=bid(am, "BAKAARO"))
        assert r.status_code == 200, (action, r.content)
    assert qty(am, "BAKAARO") == 9 and qty(am, "HODAN") == 0
    r = hodan.post(f"{INV}/branch-transfers/{t['id']}/receive/", {"idempotency_key": "rcv-1"}, format="json", HTTP_X_BRANCH_ID=bid(am, "HODAN"))
    assert r.status_code == 200, r.content
    assert qty(am, "HODAN") == 3
    detail = hodan.get(f"{INV}/branch-transfers/{t['id']}/", HTTP_X_BRANCH_ID=bid(am, "HODAN")).json()["data"]
    assert detail["approved_by"] == "bak_mgr" and detail["dispatched_by"] == "bak_mgr" and detail["received_by"] == "hodan_mgr"
    assert BranchTransferRequest.objects.count() == 1


def test_requester_needs_transfer_permission_at_one_end(am):
    ctx = am["ctx"]
    km4_viewer = add_user(ctx, username="km4_viewer", role_slug="admin")
    grant(ctx, user=km4_viewer, branch_code="KM4", profile=make_profile(tenant=ctx.tenant, code="VIEW", name="Viewer", codenames=["inventory.view", "inventory.transfer"]))
    r = auth_client_as(APIClient(), km4_viewer).post(f"{INV}/branch-transfers/", {
        "source_branch_id": bid(am, "BAKAARO"), "destination_branch_id": bid(am, "HODAN"),
        "lines": [{"product_id": str(am["iphone"].pk), "quantity": "1"}],
    }, format="json", HTTP_X_BRANCH_ID=bid(am, "KM4"))
    assert r.status_code == 403


# --- reports, overview, RBAC -------------------------------------------------------------------

def _seed_activity(am):
    ctx = am["ctx"]
    sale(am["bakaaro"], bid(am, "BAKAARO"), am["iphone"], header=bid(am, "BAKAARO"), quantity="2")
    supplier = Supplier.objects.create(tenant=ctx.tenant, supplier_code="SUP-1", company_name="Apple Dist")
    for code, total in (("HODAN", "500"), ("KM4", "300")):
        PurchaseOrder.objects.create(tenant=ctx.tenant, order_number=f"PO-{code}", supplier=supplier, branch=ctx.branch(code),
                                     status=PurchaseOrder.STATUS_ORDERED, total_amount=Decimal(total))
    Expense.objects.create(tenant=ctx.tenant, branch=ctx.branch("KM4"), description="Rent", amount=Decimal("150"))


@pytest.mark.parametrize("report", ["sales", "stock-value", "cash", "profit-loss", "purchases", "inventory", "expenses", "transfers"])
def test_every_branch_report_reconciles_with_its_consolidated_total(am, report):
    _seed_activity(am)
    r = am["owner"].get(f"{REP}/branch/{report}/", {"branch_id": "all"})
    assert r.status_code == 200, r.content
    data = r.json()["data"]
    assert data["mode"] == "consolidated" and data["reconciles"] is True
    assert {b["branch_code"] for b in data["branches"]} == {"HODAN", "BAKAARO", "KM4"}


def test_branch_report_figures(am):
    _seed_activity(am)
    owner = am["owner"]
    purchases = owner.get(f"{REP}/branch/purchases/", {"branch_id": "all"}).json()["data"]
    assert purchases["consolidated"]["ordered_total"] == 800 and purchases["consolidated"]["open_orders"] == 2
    inv = {b["branch_code"]: b for b in owner.get(f"{REP}/branch/inventory/", {"branch_id": "all"}).json()["data"]["branches"]}
    assert inv["HODAN"]["out_of_stock"] == 1 and inv["BAKAARO"]["units"] == 10 and inv["KM4"]["reserved"] == 1
    expenses = owner.get(f"{REP}/branch/expenses/", {"branch_id": bid(am, "KM4")}).json()["data"]
    assert expenses["mode"] == "single" and expenses["consolidated"]["amount"] == 150
    sales = {b["branch_code"]: b for b in owner.get(f"{REP}/branch/sales/", {"branch_id": "all"}).json()["data"]["branches"]}
    assert sales["BAKAARO"]["gross"] == 2400 and sales["HODAN"]["gross"] == 0


def test_branch_overview_for_tenant_admin_and_branch_manager(am):
    _seed_activity(am)
    rows = {r["code"]: r for r in am["owner"].get(f"{REP}/branch-overview/").json()["data"]["branches"]}
    assert set(rows) == {"HODAN", "BAKAARO", "KM4"}
    assert rows["BAKAARO"]["sales_net"] == 2400 and rows["BAKAARO"]["warehouses"] == 1
    assert rows["HODAN"]["managers"] == ["hodan_mgr"] and rows["HODAN"]["out_of_stock"] == 1
    assert rows["BAKAARO"]["stock_value"] == 9000  # 10 x cost 900, from the stock-value report
    # Shop / Company parentage is visible on every branch row (Shop <-> Branch UX completion).
    company = am["ctx"].company
    for code in ("HODAN", "BAKAARO", "KM4"):
        assert rows[code]["company_id"] == str(company.pk)
        assert rows[code]["company_name"] == company.name
    # A branch manager sees only their branch, and is refused anything else.
    mine = am["hodan"].get(f"{REP}/branch-overview/").json()["data"]["branches"]
    assert [r["code"] for r in mine] == ["HODAN"]
    assert am["hodan"].get(f"{REP}/branch/sales/", {"branch_id": bid(am, "BAKAARO")}).status_code == 403
    assert am["hodan"].get(f"{REP}/branch-overview/", {"branch_id": bid(am, "KM4")}).status_code == 403


def test_no_cross_tenant_leakage(am):
    other = build_branch_tenant(slug="rival-shop", branch_codes=("MAIN",))
    rival = auth_client_as(APIClient(), add_owner(other, username="rival_owner"))
    rows = rival.get(f"{REP}/branch-overview/").json()["data"]["branches"]
    assert [r["code"] for r in rows] == ["MAIN"]
    assert rival.get(f"{REP}/branch/sales/", {"branch_id": bid(am, "HODAN")}).status_code == 403
    assert rival.get(f"{INV}/products/{am['iphone'].pk}/availability/", HTTP_X_BRANCH_ID=str(other.branch("MAIN").pk)).status_code == 404
    search = rival.get(f"{INV}/cross-branch-search/", {"search": "iphone"}, HTTP_X_BRANCH_ID=str(other.branch("MAIN").pk)).json()["data"]
    assert search["results"] == []
    assert sale(rival, bid(am, "HODAN"), am["iphone"]).status_code == 403
    assert rival.post(f"{INV}/branch-transfers/", {
        "source_branch_id": bid(am, "BAKAARO"), "destination_branch_id": str(other.branch("MAIN").pk),
        "lines": [{"product_id": str(am["iphone"].pk), "quantity": "1"}]}, format="json").status_code in (400, 403, 404)
    assert qty(am, "BAKAARO") == 12


def test_product_stock_figures_are_branch_scoped(am):
    def stock(client, **headers):
        r = client.get("/api/v1/products/", {"search": "IP17PRO"}, **headers)
        assert r.status_code == 200, r.content
        data = r.json()["data"]
        rows = data["results"] if isinstance(data, dict) else data
        return Decimal(str(next(p for p in rows if p["sku"] == "IP17PRO")["total_stock"]))

    assert stock(am["hodan"]) == 0  # Hodan never appears to hold Bakaaro/KM4 stock
    assert stock(am["hodan"], HTTP_X_BRANCH_ID=bid(am, "HODAN")) == 0
    assert stock(am["bakaaro"]) == 12
    assert stock(am["owner"], HTTP_X_BRANCH_ID=bid(am, "KM4")) == 3
    assert stock(am["owner"], HTTP_X_BRANCH_ID="all") == 15  # consolidated: 0 + 12 + (4 - 1 reserved)
    assert am["hodan"].get("/api/v1/products/", HTTP_X_BRANCH_ID=bid(am, "KM4")).status_code == 403

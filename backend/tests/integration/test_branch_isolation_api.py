"""B2-10 / B2-11 / SEC-5: branch and tenant isolation at the HTTP boundary.

A forged ``X-Branch-Id`` — header, query string or body — must never widen what an
API call returns. These tests drive the real URLconf, middleware and permissions.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.organization.models import StockLocation
from tests.helpers.branch_factory import (
    add_owner,
    add_product,
    add_user,
    build_ahmed,
    build_branch_tenant,
    grant,
    set_inventory,
)
from tests.helpers.shop_factory import auth_client_as

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]

MY_BRANCHES = "/api/v1/organization/my-branches/"
CONTEXT = "/api/v1/organization/context/"
LOCATIONS = "/api/v1/organization/stock-locations/"
REGISTERS = "/api/v1/organization/cash-registers/"
BRANCH_ACCESS = "/api/v1/organization/branch-access/"
INVENTORY_LIST = "/api/v1/inventory/"
BRANCH_DASHBOARD = "/api/v1/inventory/branch-dashboard/"


@pytest.fixture
def ctx(db):
    return build_branch_tenant(slug="iso-tenant")


@pytest.fixture
def other_ctx(db):
    return build_branch_tenant(slug="iso-other", branch_codes=("REMOTE",))


def client_for(user):
    return auth_client_as(APIClient(), user)


def test_my_branches_lists_only_accessible_branches(ctx):
    """B2-11: the branch switcher cannot show a branch the user has no access to."""
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(MY_BRANCHES)
    assert response.status_code == 200
    codes = {b["code"] for b in response.data["data"]["branches"]}
    assert codes == {"HODAN", "BAKAARO"}
    assert "MAIN" not in codes


def test_my_branches_reports_per_branch_permissions(ctx):
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(MY_BRANCHES)
    by_code = {b["code"]: b for b in response.data["data"]["branches"]}
    assert "pos.access" in by_code["HODAN"]["permissions"]
    assert "pos.access" not in by_code["BAKAARO"]["permissions"]
    assert "inventory.view" in by_code["BAKAARO"]["permissions"]


def test_forged_branch_header_is_rejected(ctx):
    """SEC-5: changing the header to a branch the user lacks returns 403, not data."""
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(CONTEXT, HTTP_X_BRANCH_ID=str(ctx.branch("MAIN").pk))
    assert response.status_code == 403


def test_forged_cross_tenant_branch_header_is_rejected(ctx, other_ctx):
    """B2-10: a foreign tenant's branch id leaks nothing — same 403 as an unknown id."""
    ahmed = build_ahmed(ctx)
    client = client_for(ahmed)
    foreign = client.get(CONTEXT, HTTP_X_BRANCH_ID=str(other_ctx.branch("REMOTE").pk))
    unknown = client.get(CONTEXT, HTTP_X_BRANCH_ID=str(uuid.uuid4()))
    assert foreign.status_code == 403
    assert unknown.status_code == 403
    assert foreign.status_code == unknown.status_code


def test_malformed_branch_header_is_a_validation_error(ctx):
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(CONTEXT, HTTP_X_BRANCH_ID="'; DROP TABLE branches;--")
    assert response.status_code == 400


def test_location_list_is_scoped_to_accessible_branches(ctx):
    """B2-11: list endpoints never expose another branch's rows."""
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(LOCATIONS)
    assert response.status_code == 200
    branch_ids = {row["branch_id"] for row in response.data["data"]}
    assert str(ctx.branch("MAIN").pk) not in branch_ids
    assert branch_ids <= {str(ctx.branch("HODAN").pk), str(ctx.branch("BAKAARO").pk)}


def test_location_list_narrows_to_an_explicitly_selected_branch(ctx):
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(
        LOCATIONS, HTTP_X_BRANCH_ID=str(ctx.branch("HODAN").pk)
    )
    assert response.status_code == 200
    assert {row["branch_id"] for row in response.data["data"]} == {str(ctx.branch("HODAN").pk)}


def test_location_detail_of_an_inaccessible_branch_is_not_readable(ctx):
    ahmed = build_ahmed(ctx)
    hidden = StockLocation.active_objects().filter(warehouse=ctx.warehouse("MAIN")).first()
    response = client_for(ahmed).get(f"{LOCATIONS}{hidden.pk}/")
    assert response.status_code in (403, 404)


def test_cross_tenant_location_is_not_readable(ctx, other_ctx):
    ahmed = build_ahmed(ctx)
    foreign = StockLocation.active_objects().filter(warehouse=other_ctx.warehouse("REMOTE")).first()
    response = client_for(ahmed).get(f"{LOCATIONS}{foreign.pk}/")
    assert response.status_code in (403, 404)


def test_creating_a_location_in_an_inaccessible_branch_is_rejected(ctx):
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).post(
        LOCATIONS,
        {"warehouse_id": str(ctx.warehouse("MAIN").pk), "code": "SNEAK", "name": "Sneak"},
        format="json",
    )
    assert response.status_code == 403
    assert not StockLocation.objects.filter(code="SNEAK").exists()


def test_creating_a_location_in_another_tenant_is_rejected(ctx, other_ctx):
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).post(
        LOCATIONS,
        {"warehouse_id": str(other_ctx.warehouse("REMOTE").pk), "code": "SNEAK2", "name": "Sneak"},
        format="json",
    )
    assert response.status_code == 403
    assert not StockLocation.objects.filter(code="SNEAK2").exists()


def test_branch_permission_is_enforced_per_branch_on_writes(ctx):
    """Ahmed may adjust inventory in Hodan but only view it in Bakaaro."""
    ahmed = build_ahmed(ctx)
    client = client_for(ahmed)

    allowed = client.post(
        LOCATIONS,
        {"warehouse_id": str(ctx.warehouse("HODAN").pk), "code": "OK-1", "name": "Allowed"},
        format="json",
        HTTP_X_BRANCH_ID=str(ctx.branch("HODAN").pk),
    )
    assert allowed.status_code == 201

    refused = client.post(
        LOCATIONS,
        {"warehouse_id": str(ctx.warehouse("BAKAARO").pk), "code": "NO-1", "name": "Refused"},
        format="json",
        HTTP_X_BRANCH_ID=str(ctx.branch("BAKAARO").pk),
    )
    assert refused.status_code == 403
    assert not StockLocation.objects.filter(code="NO-1").exists()


def test_branch_access_grant_across_tenants_is_rejected(ctx, other_ctx):
    owner = add_user(ctx, username="iso_owner", role_slug="admin")
    for code in ctx.branches:
        grant(ctx, user=owner, branch_code=code)
    stranger = add_user(other_ctx, username="stranger", role_slug="cashier")

    response = client_for(owner).post(
        BRANCH_ACCESS,
        {"user_id": str(stranger.pk), "branch_id": str(other_ctx.branch("REMOTE").pk)},
        format="json",
    )
    assert response.status_code == 403


def test_branch_access_list_is_scoped(ctx):
    owner = add_user(ctx, username="iso_lister", role_slug="admin")
    grant(ctx, user=owner, branch_code="HODAN")
    build_ahmed(ctx)

    response = client_for(owner).get(BRANCH_ACCESS)
    assert response.status_code == 200
    branch_ids = {row["branch_id"] for row in response.data["data"]}
    assert branch_ids <= {str(ctx.branch("HODAN").pk)}


def test_unauthenticated_requests_are_rejected():
    assert APIClient().get(MY_BRANCHES).status_code in (401, 403)


def test_user_without_any_branch_sees_an_empty_list(ctx):
    orphan = add_user(ctx, username="iso_orphan", role_slug="cashier")
    response = client_for(orphan).get(MY_BRANCHES)
    assert response.status_code == 200
    assert response.data["data"]["branches"] == []


def test_registers_are_scoped_per_branch(ctx):
    from apps.organization.services import CashRegisterService

    owner = add_user(ctx, username="iso_reg_owner", role_slug="admin")
    for code in ctx.branches:
        grant(ctx, user=owner, branch_code=code)
        CashRegisterService.create_register(
            branch=ctx.branch(code), data={"code": f"REG-{code}", "name": code}, actor=owner
        )

    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(REGISTERS)
    assert response.status_code in (200, 403)
    if response.status_code == 200:
        codes = {row["code"] for row in response.data["data"]}
        assert "REG-MAIN" not in codes


# --------------------------------------------------------------------------- #
# B3-7: Phase 3 inventory endpoints resolve branch scope via core.branching,
# never the legacy request.user.branch, and never leak another branch's stock.
# --------------------------------------------------------------------------- #


def test_inventory_list_is_scoped_to_accessible_branches(ctx):
    owner = add_owner(ctx, username="iso_inv_owner")
    product = add_product(ctx, sku="ISO-INV-1")
    for code in ctx.branches:
        set_inventory(ctx, product=product, branch_code=code, quantity=1)

    ahmed = build_ahmed(ctx)  # Hodan + Bakaaro only, no Main
    response = client_for(ahmed).get(INVENTORY_LIST)
    assert response.status_code == 200
    warehouse_ids = {row["warehouse_id"] for row in response.data["data"]["results"]}
    assert str(ctx.warehouse("MAIN").pk) not in warehouse_ids


def test_inventory_list_with_no_branch_access_is_empty_not_unfiltered(ctx):
    """The concrete bug Phase 3 fixes: a user with only UserBranchAccess grants (no
    legacy User.branch) used to see an entirely unfiltered list because the old view
    read request.user.branch directly and got None."""
    product = add_product(ctx, sku="ISO-INV-2")
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=5)

    orphan = add_user(ctx, username="iso_inv_orphan", role_slug="admin")  # no grants at all
    response = client_for(orphan).get(INVENTORY_LIST)
    assert response.status_code == 200
    assert response.data["data"]["results"] == []


def test_branch_dashboard_requires_a_single_resolved_branch(ctx):
    owner = add_owner(ctx, username="iso_dash_owner")
    response = client_for(owner).get(BRANCH_DASHBOARD)
    # Owner has 3 branches in scope and sent no selector: ambiguous, must be refused.
    assert response.status_code == 400

    scoped = client_for(owner).get(BRANCH_DASHBOARD, HTTP_X_BRANCH_ID=str(ctx.branch("HODAN").pk))
    assert scoped.status_code == 200
    assert scoped.data["data"]["branch_id"] == str(ctx.branch("HODAN").pk)


def test_branch_dashboard_rejects_a_branch_the_user_cannot_access(ctx):
    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(BRANCH_DASHBOARD, HTTP_X_BRANCH_ID=str(ctx.branch("MAIN").pk))
    assert response.status_code == 403


def test_availability_endpoint_hides_other_branches_without_the_permission(ctx):
    """Ahmed's Bakaaro profile (VIEW_ONLY) lists only inventory.view — it narrows out
    inventory.cross_branch_view even though his admin role holds it globally. This is
    the branch-scoped check (has_branch_permission), not a bare global one: a profile
    narrows every permission consistently, including this one."""
    product = add_product(ctx, sku="ISO-AVAIL-1")
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=20)
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=0)

    ahmed = build_ahmed(ctx)
    response = client_for(ahmed).get(
        f"/api/v1/inventory/products/{product.pk}/availability/",
        HTTP_X_BRANCH_ID=str(ctx.branch("BAKAARO").pk),
    )
    assert response.status_code == 200
    assert response.data["data"]["current_branch"]["available"] == 0.0
    assert response.data["data"]["other_branches"] == []


def test_cashier_without_inventory_view_can_still_check_availability(ctx):
    """The brief's concrete scenario, end-to-end: a cashier who cannot open the
    inventory list (no inventory.view) can still reach the availability endpoint and
    see other branches, because inventory.cross_branch_view alone is sufficient."""
    product = add_product(ctx, sku="ISO-AVAIL-CASHIER")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=0)
    set_inventory(ctx, product=product, branch_code="MAIN", quantity=15)

    cashier = add_user(ctx, username="iso_avail_cashier", role_slug="cashier")
    grant(ctx, user=cashier, branch_code="HODAN", is_default=True)  # no profile: no narrowing
    assert cashier.has_permission("inventory.view") is False

    response = client_for(cashier).get(
        f"/api/v1/inventory/products/{product.pk}/availability/",
        HTTP_X_BRANCH_ID=str(ctx.branch("HODAN").pk),
    )
    assert response.status_code == 200
    assert response.data["data"]["current_branch"]["available"] == 0.0
    others = {row["branch_id"]: row["available"] for row in response.data["data"]["other_branches"]}
    assert others[str(ctx.branch("MAIN").pk)] == 15.0


def test_availability_endpoint_requires_a_single_branch(ctx):
    owner = add_owner(ctx, username="iso_avail_owner")
    product = add_product(ctx, sku="ISO-AVAIL-2")
    response = client_for(owner).get(f"/api/v1/inventory/products/{product.pk}/availability/")
    assert response.status_code == 400


def test_cross_tenant_product_availability_is_not_reachable(ctx):
    other = build_branch_tenant(slug="iso-avail-other", branch_codes=("REMOTE",))
    other_product = add_product(other, sku="ISO-AVAIL-REMOTE")

    owner = add_owner(ctx, username="iso_avail_cross_owner")
    response = client_for(owner).get(
        f"/api/v1/inventory/products/{other_product.pk}/availability/",
        HTTP_X_BRANCH_ID=str(ctx.branch("HODAN").pk),
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Phase 6 — B6-3: a report for a branch the user cannot access is a 403
# --------------------------------------------------------------------------- #


@pytest.fixture
def analyst(ctx):
    from tests.helpers.branch_factory import make_profile

    profile = make_profile(
        tenant=ctx.tenant, code="ANALYST", name="Analyst", codenames=["reports.view", "dashboard.view"]
    )
    user = add_user(ctx, username="b63_analyst", role_slug="admin")
    grant(ctx, user=user, branch_code="HODAN", profile=profile, is_default=True)
    return user


def test_report_for_an_inaccessible_branch_is_403_not_an_empty_success(ctx, analyst, other_ctx):
    client = client_for(analyst)
    classic = "/api/v1/reports/data/?category=sales&report=Daily%20Sales&branch_id={}"
    branch_report = "/api/v1/reports/branch/sales/?branch_id={}"

    for forbidden in (ctx.branch("BAKAARO").pk, ctx.branch("MAIN").pk, other_ctx.branch("REMOTE").pk):
        assert client.get(classic.format(forbidden)).status_code == 403, forbidden
        assert client.get(branch_report.format(forbidden)).status_code == 403, forbidden
        assert client.get(
            "/api/v1/reports/branch/cash/", HTTP_X_BRANCH_ID=str(forbidden)
        ).status_code == 403  # a forged header is no different from the query string

    own = ctx.branch("HODAN").pk
    assert client.get(classic.format(own)).status_code == 200
    assert client.get(branch_report.format(own)).status_code == 200


def test_consolidated_report_never_widens_beyond_the_callers_branches(ctx, analyst):
    body = client_for(analyst).get("/api/v1/reports/branch/stock-value/?branch_id=all").json()["data"]
    assert [b["branch_code"] for b in body["branches"]] == ["HODAN"]
    assert body["reconciles"] is True


def test_notification_feed_refuses_an_inaccessible_branch(ctx, analyst):
    client = client_for(analyst)
    assert client.get(f"/api/v1/notifications/?branch_id={ctx.branch('BAKAARO').pk}").status_code == 403
    assert client.get(f"/api/v1/notifications/?branch_id={ctx.branch('HODAN').pk}").status_code == 200

"""Branch final gaps: destination-side cancellation and push ("send stock to branch") transfers,
both on the one BranchTransferRequest state machine."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.inventory.models import BranchTransferRequest, Inventory
from apps.notifications.models import Notification
from tests.helpers.branch_factory import add_owner, add_product, add_user, build_branch_tenant, grant, make_profile, set_inventory
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db
T = "/api/v1/inventory/branch-transfers"
MGR = ["inventory.view", "inventory.transfer", "inventory.cross_branch_view", "reports.view"]


@pytest.fixture
def am():
    ctx = build_branch_tenant(slug="am-gaps", branch_codes=("HODAN", "BAKAARO", "KM4"))
    phone = add_product(ctx, sku="GAP-IP17", name="iPhone 17 Pro")
    set_inventory(ctx, product=phone, branch_code="HODAN", quantity=0)
    set_inventory(ctx, product=phone, branch_code="BAKAARO", quantity=12)
    set_inventory(ctx, product=phone, branch_code="KM4", quantity=4)
    profile = make_profile(tenant=ctx.tenant, code="MGR", name="Manager", codenames=MGR, is_manager=True)
    users = {}
    for code in ("HODAN", "BAKAARO", "KM4"):
        u = add_user(ctx, username=f"gap_{code.lower()}", role_slug="admin")
        grant(ctx, user=u, branch_code=code, profile=profile, is_default=True)
        users[code] = auth_client_as(APIClient(), u)
    return {"ctx": ctx, "phone": phone, **users}


def bid(am, code):
    return str(am["ctx"].branch(code).pk)


def qty(am, code, field="quantity"):
    return getattr(Inventory.objects.get(product=am["phone"], warehouse=am["ctx"].warehouse(code)), field)


def act(am, who, t, action, **body):
    return am[who].post(f"{T}/{t}/{action}/", body, format="json", HTTP_X_BRANCH_ID=bid(am, who))


def pull(am, quantity="3"):
    """Hodan asks Bakaaro for stock."""
    r = am["HODAN"].post(T + "/", {"source_branch_id": bid(am, "BAKAARO"), "destination_branch_id": bid(am, "HODAN"),
                                   "lines": [{"product_id": str(am["phone"].pk), "quantity": quantity}]},
                         format="json", HTTP_X_BRANCH_ID=bid(am, "HODAN"))
    assert r.status_code == 201, r.content
    return r.json()["data"]["id"]


# --- 1. destination cancellation -------------------------------------------------------------

@pytest.mark.parametrize("stage", ["REQUESTED", "APPROVED", "RESERVED"])
def test_destination_cancels_its_own_request_before_dispatch_and_reservation_is_released(am, stage):
    t = pull(am)
    if stage in ("APPROVED", "RESERVED"):
        assert act(am, "BAKAARO", t, "approve").status_code == 200
    if stage == "RESERVED":
        assert act(am, "BAKAARO", t, "reserve").status_code == 200
        assert qty(am, "BAKAARO", "reserved_quantity") == 3
    Notification.objects.all().delete()
    r = act(am, "HODAN", t, "cancel", reason="Customer bought elsewhere")
    assert r.status_code == 200, r.content
    assert r.json()["data"]["status"] == "CANCELLED"
    assert qty(am, "BAKAARO") == 12 and qty(am, "BAKAARO", "reserved_quantity") == 0 and qty(am, "HODAN") == 0
    detail = am["HODAN"].get(f"{T}/{t}/", HTTP_X_BRANCH_ID=bid(am, "HODAN")).json()["data"]
    assert detail["cancelled_by"] == "gap_hodan" and detail["cancel_reason"] == "Customer bought elsewhere" and detail["cancelled_at"]
    log = AuditLog.objects.get(entity_id=t, new_values__event="transfer_cancelled")
    assert log.old_values == {"status": stage}
    # The source branch is told; the canceller is not notified about their own action.
    notified = set(Notification.objects.filter(entity_id=t).values_list("user__username", flat=True))
    assert "gap_bakaaro" in notified and "gap_hodan" not in notified
    # Idempotent: repeating the cancel changes nothing and writes no second audit row.
    assert act(am, "HODAN", t, "cancel").status_code == 200
    assert AuditLog.objects.filter(entity_id=t, new_values__event="transfer_cancelled").count() == 1
    assert qty(am, "BAKAARO", "reserved_quantity") == 0


@pytest.mark.parametrize("stage", ["IN_TRANSIT", "RECEIVED", "COMPLETED"])
def test_cannot_cancel_once_stock_has_left_the_source(am, stage):
    t = pull(am)
    for a in ("approve", "reserve", "dispatch"):
        assert act(am, "BAKAARO", t, a).status_code == 200
    if stage in ("RECEIVED", "COMPLETED"):
        assert act(am, "HODAN", t, "receive", idempotency_key=f"rcv-{t}").status_code == 200
    if stage == "COMPLETED":
        act(am, "HODAN", t, "complete")
    before = (qty(am, "BAKAARO"), qty(am, "HODAN"))
    for who in ("HODAN", "BAKAARO"):
        assert act(am, who, t, "cancel").status_code == 400
    assert (qty(am, "BAKAARO"), qty(am, "HODAN")) == before
    assert BranchTransferRequest.objects.get(pk=t).status != "CANCELLED"


def test_uninvolved_branch_and_other_tenant_cannot_cancel(am):
    t = pull(am)
    assert act(am, "KM4", t, "cancel").status_code in (403, 404)  # not a party to the transfer
    rival_ctx = build_branch_tenant(slug="rival-gaps", branch_codes=("MAIN",))
    rival = auth_client_as(APIClient(), add_owner(rival_ctx, username="rival_gaps"))
    assert rival.post(f"{T}/{t}/cancel/", {}, format="json").status_code == 404
    assert BranchTransferRequest.objects.get(pk=t).status == "REQUESTED"


# --- 2. push transfers -------------------------------------------------------------------------

def push(am, *, approve=True, who="BAKAARO", source="BAKAARO", dest="HODAN", quantity="2", **extra):
    return am[who].post(T + "/", {"source_branch_id": bid(am, source), "destination_branch_id": bid(am, dest),
                                  "lines": [{"product_id": str(am["phone"].pk), "quantity": quantity}],
                                  "approve": approve, **extra}, format="json", HTTP_X_BRANCH_ID=bid(am, who))


def test_push_follows_the_same_lifecycle_and_never_adds_stock_early(am):
    r = push(am)
    assert r.status_code == 201, r.content
    t = r.json()["data"]
    assert t["status"] == "APPROVED" and t["requested_by"] == "gap_bakaaro" and t["approved_by"] == "gap_bakaaro"
    assert (qty(am, "BAKAARO"), qty(am, "HODAN")) == (12, 0)  # nothing moved at creation
    assert act(am, "BAKAARO", t["id"], "reserve").status_code == 200
    assert (qty(am, "HODAN"), qty(am, "BAKAARO", "reserved_quantity")) == (0, 2)
    assert act(am, "BAKAARO", t["id"], "dispatch").status_code == 200
    assert (qty(am, "BAKAARO"), qty(am, "HODAN")) == (10, 0)  # in transit, not yet at Hodan
    # Only the destination can receive.
    assert act(am, "BAKAARO", t["id"], "receive", idempotency_key="x").status_code == 403
    assert act(am, "HODAN", t["id"], "receive", idempotency_key="push-rcv").status_code == 200
    assert act(am, "HODAN", t["id"], "receive", idempotency_key="push-rcv").status_code == 200  # replay is a no-op
    assert qty(am, "HODAN") == 2


def test_push_without_approval_starts_requested(am):
    r = push(am, approve=False)
    assert r.status_code == 201 and r.json()["data"]["status"] == "REQUESTED"


def test_push_requires_source_permission_and_leaves_nothing_behind(am):
    # Hodan cannot push Bakaaro's stock: approval is a source-branch right, so the whole create rolls back.
    r = push(am, who="HODAN", source="BAKAARO", dest="HODAN")
    assert r.status_code == 403
    assert not BranchTransferRequest.objects.exists()
    # KM4 is not a party at all.
    assert push(am, who="KM4", source="BAKAARO", dest="HODAN", approve=False).status_code == 403


def test_push_to_a_chosen_destination_warehouse_must_belong_to_that_branch(am):
    wrong = str(am["ctx"].warehouse("KM4").pk)
    assert push(am, destination_warehouse_id=wrong).status_code == 400
    right = str(am["ctx"].warehouse("HODAN").pk)
    assert push(am, destination_warehouse_id=right).status_code == 201


def test_destination_list_names_all_company_branches_but_warehouses_only_where_permitted(am):
    rows = {r["code"]: r for r in am["BAKAARO"].get(f"{T}/destinations/", HTTP_X_BRANCH_ID=bid(am, "BAKAARO")).json()["data"]}
    assert set(rows) == {"HODAN", "BAKAARO", "KM4"}
    assert rows["BAKAARO"]["warehouses"] and rows["HODAN"]["warehouses"] is None
    rival_ctx = build_branch_tenant(slug="rival-dest", branch_codes=("MAIN",))
    rival = auth_client_as(APIClient(), add_owner(rival_ctx, username="rival_dest"))
    assert {r["code"] for r in rival.get(f"{T}/destinations/").json()["data"]} == {"MAIN"}

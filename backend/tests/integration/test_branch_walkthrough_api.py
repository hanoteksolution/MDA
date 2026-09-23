"""BR-1 (API level): login -> switch branch -> POS sale -> transfer -> receive -> report.

No browser runner exists in this repo, so the browser walkthrough itself is manual. This drives
the exact HTTP calls the UI makes, with the ``X-Branch-Id`` header a branch switch sets, and
asserts the stock and report consequences at every step.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import Inventory
from tests.helpers.branch_factory import add_product, add_user, build_branch_tenant, set_inventory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

HOST = "walk-tenant.erp.safaritechno.com"


def qty(product, ctx, code):
    return Inventory.objects.get(product=product, warehouse=ctx.warehouse(code)).quantity


def test_login_switch_sell_transfer_receive_report():
    ctx = build_branch_tenant(slug="walk-tenant", branch_codes=("HODAN", "BAKAARO"))
    add_user(ctx, username="walker", role_slug="admin", branches=("HODAN", "BAKAARO"))
    product = add_product(ctx, sku="WALK-1")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("100"))
    hodan, bakaaro = str(ctx.branch("HODAN").pk), str(ctx.branch("BAKAARO").pk)

    # 1. login
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/", {"username": "walker", "password": "pass12345"}, format="json", HTTP_HOST=HOST
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['data']['access']}", HTTP_HOST=HOST)

    # 2. the switcher offers exactly the caller's branches; switching sets the context header
    mine = client.get("/api/v1/organization/my-branches/").json()["data"]
    codes = {b["code"] for b in (mine["branches"] if isinstance(mine, dict) else mine)}
    assert codes == {"HODAN", "BAKAARO"}
    assert client.get("/api/v1/organization/context/", HTTP_X_BRANCH_ID=hodan).status_code == 200

    # 3. POS sale in HODAN (no terminal configured -> legacy path, no shift needed)
    sale = client.post(
        "/api/v1/pos/checkout/",
        {
            "branch_id": hodan, "customer_id": "walkin", "waiter_name": "Counter", "payment_method": "cash",
            "items": [{"product_id": str(product.pk), "quantity": "2", "unit_price": "10"}],
            "idempotency_key": "walk-sale-1",
        },
        format="json",
        HTTP_X_BRANCH_ID=hodan,
    )
    assert sale.status_code == 201, sale.content
    assert qty(product, ctx, "HODAN") == Decimal("98")

    # 4. transfer HODAN -> BAKAARO through every stage
    created = client.post(
        "/api/v1/inventory/branch-transfers/",
        {
            "source_branch_id": hodan, "destination_branch_id": bakaaro,
            "source_warehouse_id": str(ctx.warehouse("HODAN").pk),
            "destination_warehouse_id": str(ctx.warehouse("BAKAARO").pk),
            "lines": [{"product_id": str(product.pk), "quantity": "10"}],
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    base = f"/api/v1/inventory/branch-transfers/{created.json()['data']['id']}/"
    for action in ("approve", "reserve", "dispatch"):
        step = client.post(f"{base}{action}/", {}, format="json")
        assert step.status_code == 200, (action, step.content)
    assert qty(product, ctx, "HODAN") == Decimal("88")
    assert not Inventory.objects.filter(product=product, warehouse=ctx.warehouse("BAKAARO"), quantity__gt=0).exists()

    # 5. receive at BAKAARO, then complete
    detail = client.get(base).json()["data"]
    received = client.post(
        f"{base}receive/",
        {"lines": [{"product_id": ln["product_id"], "quantity": "10"} for ln in detail["lines"]]},
        format="json",
    )
    assert received.status_code == 200, received.content
    assert client.post(f"{base}complete/", {}, format="json").status_code == 200
    assert qty(product, ctx, "HODAN") == Decimal("88")
    assert qty(product, ctx, "BAKAARO") == Decimal("10")  # conserved: 88 + 10 + 2 sold = 100

    # 6. reports: each branch, then the consolidated view that must reconcile
    for branch_id in (hodan, bakaaro):
        report = client.get(f"/api/v1/reports/branch/stock-value/?branch_id={branch_id}")
        assert report.status_code == 200, report.content
    consolidated = client.get("/api/v1/reports/branch/stock-value/?branch_id=all").json()["data"]
    assert consolidated["reconciles"] is True

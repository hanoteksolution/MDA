"""Branch operational completion — concurrency gates on real PostgreSQL (skip loudly elsewhere).

    cd backend && DJANGO_SETTINGS_MODULE=config.settings.branch_verification \
        python3 -m pytest tests/unit/test_branch_operational_postgresql.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import connection, connections
from rest_framework.test import APIClient

from apps.inventory.models import BranchTransferRequest, Inventory
from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput
from tests.helpers.branch_factory import add_owner, add_product, add_user, build_branch_tenant, set_inventory
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def am():
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL transactions and row locking.")
    ctx = build_branch_tenant(slug="pg-am", branch_codes=("HODAN", "BAKAARO", "KM4"))
    product = add_product(ctx, sku="PG-IP17")
    for code, q in (("HODAN", 5), ("BAKAARO", 12), ("KM4", 4)):
        set_inventory(ctx, product=product, branch_code=code, quantity=Decimal(q))
    return ctx, product


def _qty(ctx, product, code):
    return Inventory.objects.get(product=product, warehouse=ctx.warehouse(code)).quantity


def test_concurrent_pos_sales_in_different_branches_touch_only_their_own_stock(am):
    ctx, product = am
    users = {code: add_user(ctx, username=f"pg_cashier_{code.lower()}", branches=(code,)) for code in ("HODAN", "BAKAARO", "KM4")}
    # No warm-up: concurrent *first* postings are safe since ChartService.ensure_finance_ready.
    barrier = Barrier(6)

    def sell(code):
        try:
            client = auth_client_as(APIClient(), users[code])
            barrier.wait(timeout=15)
            r = client.post("/api/v1/pos/checkout/", {
                "branch_id": str(ctx.branch(code).pk), "customer_id": "walkin", "waiter_name": "Counter",
                "payment_method": "cash", "items": [{"product_id": str(product.pk), "quantity": "1", "unit_price": "10"}],
            }, format="json", HTTP_X_BRANCH_ID=str(ctx.branch(code).pk))
            return r.status_code if r.status_code == 201 else (r.status_code, r.content[:300])
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = [pool.submit(sell, c) for c in ("HODAN", "BAKAARO", "KM4", "HODAN", "BAKAARO", "KM4")]
        statuses = [f.result() for f in codes]
    assert statuses == [201] * 6
    assert (_qty(ctx, product, "HODAN"), _qty(ctx, product, "BAKAARO"), _qty(ctx, product, "KM4")) == (3, 10, 2)


def test_concurrent_approve_and_cancel_of_one_request_leave_one_consistent_outcome(am):
    ctx, product = am
    owner = add_owner(ctx, username="pg_am_owner")
    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("BAKAARO").pk, destination_branch_id=ctx.branch("HODAN").pk,
        source_warehouse_id=None, destination_warehouse_id=None,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("3"))], user=owner,
    )
    barrier = Barrier(2)
    outcomes = []

    def act(action):
        try:
            barrier.wait(timeout=15)
            getattr(BranchTransferService, action)(request_id=req.pk, user=owner)
            outcomes.append(action)
        except Exception as exc:  # the loser must fail cleanly, never corrupt state
            outcomes.append(f"refused:{type(exc).__name__}")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(act, "approve"), pool.submit(act, "cancel")]]

    final = BranchTransferRequest.objects.get(pk=req.pk).status
    assert final in (BranchTransferRequest.STATUS_APPROVED, BranchTransferRequest.STATUS_CANCELLED)
    assert _qty(ctx, product, "BAKAARO") == 12 and _qty(ctx, product, "HODAN") == 5  # nothing moved


def test_concurrent_reservations_from_two_requesting_branches_never_exceed_source_stock(am):
    ctx, product = am
    owner = add_owner(ctx, username="pg_am_owner2")

    def approved(dest):
        req = BranchTransferService.request_transfer(
            source_branch_id=ctx.branch("KM4").pk, destination_branch_id=ctx.branch(dest).pk,
            source_warehouse_id=None, destination_warehouse_id=None,
            lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("3"))], user=owner,
        )
        return BranchTransferService.approve(request_id=req.pk, user=owner)

    a, b = approved("HODAN"), approved("BAKAARO")  # 3 + 3 > 4 available at KM4
    barrier = Barrier(2)
    results = []

    def reserve(req_id):
        try:
            barrier.wait(timeout=15)
            BranchTransferService.reserve(request_id=req_id, user=owner)
            results.append("ok")
        except Exception as exc:
            results.append(type(exc).__name__)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(reserve, a.pk), pool.submit(reserve, b.pk)]]

    inv = Inventory.objects.get(product=product, warehouse=ctx.warehouse("KM4"))
    assert results.count("ok") == 1
    assert inv.reserved_quantity == Decimal("3") and inv.quantity == Decimal("4")

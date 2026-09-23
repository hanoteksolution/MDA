"""B4-1..B4-7: inter-branch transfer workflow lifecycle, ledger, and invariants."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied

from apps.inventory.models import BranchTransferRequest, Inventory, StockMovement
from apps.inventory.services.branch_transfer_service import (
    BranchTransferError,
    BranchTransferService,
    TransferLineInput,
)
from apps.inventory.services.inventory_service import InventoryService
from apps.inventory.services.transfer_service import StockTransferService, TransferError
from apps.inventory.services.transfer_service import TransferLineInput as LegacyTransferLineInput
from tests.helpers.branch_factory import add_owner, add_product, build_branch_tenant, set_inventory

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="btr-tenant")


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="btr_owner")


@pytest.fixture
def product(ctx):
    return add_product(ctx, sku="BTR-1")


def make_request(ctx, owner, product, qty=Decimal("10")):
    return BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk,
        destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=qty)],
        user=owner,
    )


def movements(product, warehouse, movement_type=None):
    qs = StockMovement.objects.filter(product=product, warehouse=warehouse)
    return qs.filter(movement_type=movement_type) if movement_type else qs


def inv(ctx, product, branch_code):
    return Inventory.objects.get(product=product, warehouse=ctx.warehouse(branch_code))


# --------------------------------------------------------------------------- #
# B4-1 / B4-2 / B4-3: lifecycle produces the right ledger rows at the right time
# --------------------------------------------------------------------------- #


def test_full_lifecycle_produces_expected_ledger_at_each_step(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("20"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("0"))
    req = make_request(ctx, owner, product, qty=Decimal("6"))
    assert req.status == BranchTransferRequest.STATUS_REQUESTED

    # No stock movement at request time.
    assert movements(product, ctx.warehouse("HODAN")).count() == 0

    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    assert req.status == BranchTransferRequest.STATUS_APPROVED
    # B4-2: approval reserves nothing yet, no on-hand change.
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("0")

    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    assert req.status == BranchTransferRequest.STATUS_RESERVED
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("6")
    assert inv(ctx, product, "HODAN").quantity == Decimal("20")  # on-hand unchanged
    assert movements(product, ctx.warehouse("HODAN")).count() == 0  # still no movement

    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)
    assert req.status == BranchTransferRequest.STATUS_IN_TRANSIT
    assert inv(ctx, product, "HODAN").quantity == Decimal("14")
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("0")
    out_movement = movements(product, ctx.warehouse("HODAN"), "transfer_out").get()
    assert out_movement.quantity == Decimal("-6")
    # B4-3: destination not credited yet.
    assert inv(ctx, product, "BAKAARO").quantity == Decimal("0")

    req = BranchTransferService.receive(request_id=req.pk, user=owner)
    assert req.status == BranchTransferRequest.STATUS_RECEIVED
    assert inv(ctx, product, "BAKAARO").quantity == Decimal("6")
    in_movement = movements(product, ctx.warehouse("BAKAARO"), "transfer_in").get()
    assert in_movement.quantity == Decimal("6")

    req = BranchTransferService.complete(request_id=req.pk, user=owner)
    assert req.status == BranchTransferRequest.STATUS_COMPLETED


# --------------------------------------------------------------------------- #
# B4-4: partial receipt
# --------------------------------------------------------------------------- #


def test_partial_receipt_records_discrepancy_and_leaves_transfer_in_transit(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("20"))
    req = make_request(ctx, owner, product, qty=Decimal("10"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)

    req = BranchTransferService.receive(
        request_id=req.pk, user=owner, lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("4"))]
    )
    assert req.status == BranchTransferRequest.STATUS_IN_TRANSIT  # not fully received
    line = req.lines.get(product=product)
    assert line.quantity_received == Decimal("4")
    assert line.discrepancy_quantity == Decimal("6")
    assert line.in_transit_quantity == Decimal("6")
    assert inv(ctx, product, "BAKAARO").quantity == Decimal("4")

    req = BranchTransferService.receive(request_id=req.pk, user=owner)  # receive the rest
    assert req.status == BranchTransferRequest.STATUS_RECEIVED
    line.refresh_from_db()
    assert line.discrepancy_quantity == Decimal("0")
    assert inv(ctx, product, "BAKAARO").quantity == Decimal("10")


def test_over_receipt_is_rejected(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = make_request(ctx, owner, product, qty=Decimal("5"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)

    with pytest.raises(BranchTransferError):
        BranchTransferService.receive(
            request_id=req.pk, user=owner,
            lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("6"))],
        )


# --------------------------------------------------------------------------- #
# B4-5: cancel/reject release the reservation exactly once
# --------------------------------------------------------------------------- #


def test_cancel_after_reserve_releases_the_reservation(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = make_request(ctx, owner, product, qty=Decimal("4"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("4")

    req = BranchTransferService.cancel(request_id=req.pk, user=owner)
    assert req.status == BranchTransferRequest.STATUS_CANCELLED
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("0")
    assert inv(ctx, product, "HODAN").quantity == Decimal("10")  # never left


def test_cancel_is_idempotent(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = make_request(ctx, owner, product, qty=Decimal("4"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    BranchTransferService.cancel(request_id=req.pk, user=owner)
    BranchTransferService.cancel(request_id=req.pk, user=owner)  # second call: no-op
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("0")


def test_reject_releases_nothing_extra_and_is_idempotent(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = make_request(ctx, owner, product, qty=Decimal("4"))
    req = BranchTransferService.reject(request_id=req.pk, reason="not needed", user=owner)
    assert req.status == BranchTransferRequest.STATUS_REJECTED
    BranchTransferService.reject(request_id=req.pk, reason="again", user=owner)  # idempotent
    assert inv(ctx, product, "HODAN").reserved_quantity == Decimal("0")


def test_cannot_cancel_after_dispatch(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = make_request(ctx, owner, product, qty=Decimal("4"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)
    with pytest.raises(BranchTransferError):
        BranchTransferService.cancel(request_id=req.pk, user=owner)


# --------------------------------------------------------------------------- #
# B4-6: source + destination + in-transit == constant across the lifecycle
# --------------------------------------------------------------------------- #


def test_total_stock_conserved_across_the_lifecycle(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("15"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("3"))
    total_before = Decimal("18")

    req = make_request(ctx, owner, product, qty=Decimal("5"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)

    def total():
        h = inv(ctx, product, "HODAN").quantity
        b = inv(ctx, product, "BAKAARO").quantity
        line = req.lines.get(product=product)
        return h + b + line.in_transit_quantity

    assert total() == total_before
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)
    assert total() == total_before  # 5 left on-hand, now "in transit"
    req = BranchTransferService.receive(request_id=req.pk, user=owner)
    assert total() == total_before


# --------------------------------------------------------------------------- #
# B4-7: same-branch StockTransfer stays same-branch (D4)
# --------------------------------------------------------------------------- #


def test_same_branch_stock_transfer_still_works(ctx, owner, product):
    from apps.inventory.models import Warehouse

    second_wh = Warehouse.objects.create(
        tenant=ctx.tenant, branch=ctx.branch("HODAN"), name="Hodan Annex", code="WH-HODAN-2"
    )
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    transfer = StockTransferService.create_draft(
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=second_wh.pk,
        user=owner,
        lines=[LegacyTransferLineInput(product_id=product.pk, quantity=Decimal("3"))],
    )
    confirmed = StockTransferService.confirm(transfer_id=transfer.pk, user=owner)
    assert confirmed.status == "confirmed"


def test_cross_branch_stock_transfer_is_rejected(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    transfer = StockTransferService.create_draft(
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        user=owner,
        lines=[LegacyTransferLineInput(product_id=product.pk, quantity=Decimal("3"))],
    )
    with pytest.raises(TransferError):
        StockTransferService.confirm(transfer_id=transfer.pk, user=owner)


def test_historical_cross_branch_stock_transfer_is_not_touched(ctx, owner, product):
    """A confirmed cross-branch StockTransfer that predates the guard must not be
    rewritten or reversed — the guard only blocks new confirmations."""
    from apps.inventory.models import StockTransfer, StockTransferLine

    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    historical = StockTransfer.objects.create(
        tenant=ctx.tenant, transfer_number="TR-HIST-1",
        source_warehouse=ctx.warehouse("HODAN"), destination_warehouse=ctx.warehouse("BAKAARO"),
        branch=ctx.branch("HODAN"), status=StockTransfer.STATUS_CONFIRMED,
    )
    StockTransferLine.objects.create(transfer=historical, product=product, quantity=Decimal("2"))
    # Re-confirming an already-confirmed transfer is the existing idempotent no-op —
    # it must not raise even though it is (historically) cross-branch.
    result = StockTransferService.confirm(transfer_id=historical.pk, user=owner)
    assert result.status == "confirmed"


# --------------------------------------------------------------------------- #
# RBAC / validation
# --------------------------------------------------------------------------- #


def test_request_requires_permission_at_source_branch(ctx, product):
    from tests.helpers.branch_factory import add_user

    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    viewer = add_user(ctx, username="btr_viewer", role_slug="read_only")
    from tests.helpers.branch_factory import grant

    grant(ctx, user=viewer, branch_code="HODAN")
    with pytest.raises(PermissionDenied):
        make_request(ctx, viewer, product)


def test_request_rejects_same_branch(ctx, owner, product):
    with pytest.raises(BranchTransferError):
        BranchTransferService.request_transfer(
            source_branch_id=ctx.branch("HODAN").pk,
            destination_branch_id=ctx.branch("HODAN").pk,
            source_warehouse_id=ctx.warehouse("HODAN").pk,
            destination_warehouse_id=ctx.warehouse("HODAN").pk,
            lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("1"))],
            user=owner,
        )


def test_reserve_rejects_insufficient_available(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("2"))
    req = make_request(ctx, owner, product, qty=Decimal("5"))
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    with pytest.raises(ValueError):
        BranchTransferService.reserve(request_id=req.pk, user=owner)

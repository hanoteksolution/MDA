"""B5-6: purchases receive into a branch warehouse and stamp the branch everywhere."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.finance.models import JournalEntry, JournalLine
from apps.inventory.models import Inventory, StockMovement
from apps.inventory.services.receiving_service import (
    PurchaseReceivingService,
    ReceiveLineInput,
    ReceivingError,
)
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.suppliers.models import Supplier
from tests.helpers.branch_factory import add_owner, add_product, build_branch_tenant

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="bpur-tenant", branch_codes=("HODAN", "BAKAARO"))


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="bpur_owner")


def make_po(ctx, product, *, branch_code="HODAN", qty="10", cost="4"):
    supplier, _ = Supplier.objects.get_or_create(
        tenant=ctx.tenant, supplier_code="SUP-1", defaults={"company_name": "Supply Co"}
    )
    po = PurchaseOrder.objects.create(
        tenant=ctx.tenant,
        order_number=f"PO-{branch_code}-1",
        supplier=supplier,
        branch=ctx.branch(branch_code),
        status=PurchaseOrder.STATUS_ORDERED,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity_ordered=Decimal(qty),
        unit_cost=Decimal(cost),
    )
    return po


def test_receipt_stamps_branch_on_stock_ledger_and_journal(ctx, owner):
    product = add_product(ctx, sku="BPUR-1")
    po = make_po(ctx, product)

    PurchaseReceivingService.receive(
        purchase_order_id=po.pk,
        warehouse_id=ctx.warehouse("HODAN").pk,
        lines=[ReceiveLineInput(product_id=product.pk, quantity_received=Decimal("10"))],
        user=owner,
    )

    assert Inventory.objects.get(product=product, warehouse=ctx.warehouse("HODAN")).quantity == Decimal("10")
    movement = StockMovement.objects.get(reference_id=po.pk, movement_type="purchase")
    assert movement.branch_id == ctx.branch("HODAN").pk
    assert movement.warehouse_id == ctx.warehouse("HODAN").pk
    assert movement.location_id is not None  # the warehouse's default location

    entry = JournalEntry.objects.get(source_id=po.pk)
    assert entry.branch_id == ctx.branch("HODAN").pk
    lines = JournalLine.objects.filter(entry=entry)
    assert lines.count() == 2
    assert {line.branch_id for line in lines} == {ctx.branch("HODAN").pk}


def test_cannot_receive_into_another_branchs_warehouse(ctx, owner):
    product = add_product(ctx, sku="BPUR-2")
    po = make_po(ctx, product, branch_code="HODAN")

    with pytest.raises(ReceivingError, match="branch"):
        PurchaseReceivingService.receive(
            purchase_order_id=po.pk,
            warehouse_id=ctx.warehouse("BAKAARO").pk,
            lines=[ReceiveLineInput(product_id=product.pk, quantity_received=Decimal("1"))],
            user=owner,
        )
    assert not Inventory.objects.filter(product=product, warehouse=ctx.warehouse("BAKAARO")).exists()
    assert not StockMovement.objects.filter(reference_id=po.pk).exists()

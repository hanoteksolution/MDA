"""STEP 11 — purchase receiving and warehouse transfers."""

from decimal import Decimal

import pytest

from apps.inventory.models import Inventory, StockTransfer, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.inventory.services.receiving_service import (
    PurchaseReceivingService,
    ReceiveLineInput,
    ReceivingError,
)
from apps.inventory.services.transfer_service import (
    StockTransferService,
    TransferError,
    TransferLineInput,
)
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.project_management.models import Project, ProjectInventoryAllocation
from apps.settings_app.models import Branch, Company
from apps.suppliers.models import Supplier


@pytest.fixture
def inv_env(db):
    tenant = Tenant.objects.create(name="Inv Co", slug="inv-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Inv Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    wh_a = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="A", code="WHA", is_default=True
    )
    wh_b = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="B", code="WHB", is_default=False
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="SKU-TR-1",
        name="Transfer Item",
        category=category,
        unit=unit,
        cost_price=Decimal("5.00"),
        selling_price=Decimal("8.00"),
        minimum_stock=2,
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=wh_a)
    inv.quantity = Decimal("20")
    inv.reserved_quantity = Decimal("0")
    inv.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
    supplier = Supplier.objects.create(
        tenant=tenant,
        supplier_code="SUP-1",
        company_name="Acme Supply",
    )
    po = PurchaseOrder.objects.create(
        tenant=tenant,
        order_number="PO-MAIN-00001",
        supplier=supplier,
        branch=branch,
        status=PurchaseOrder.STATUS_ORDERED,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity_ordered=Decimal("10"),
        quantity_received=Decimal("0"),
        unit_cost=Decimal("5.00"),
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "wh_a": wh_a,
        "wh_b": wh_b,
        "product": product,
        "po": po,
        "inv_a": inv,
    }


@pytest.mark.django_db
def test_receive_posts_ap_journal(inv_env):
    from apps.finance.models import AccountingEvent, JournalEntry
    from apps.finance.services.journal_service import JournalService

    product = inv_env["product"]
    wh = inv_env["wh_a"]
    po = inv_env["po"]

    PurchaseReceivingService.receive(
        purchase_order_id=po.id,
        warehouse_id=wh.id,
        lines=[ReceiveLineInput(product_id=product.id, quantity_received=Decimal("4"))],
    )
    journal = JournalEntry.active_objects().get(source_type="purchase")
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 20.0  # 4 * 5.00 unit cost

    event = AccountingEvent.active_objects().get(event_type="PURCHASE_RECEIVED")
    assert event.status == AccountingEvent.STATUS_POSTED


@pytest.mark.django_db
def test_receive_increases_stock(inv_env):
    product = inv_env["product"]
    wh = inv_env["wh_a"]
    po = inv_env["po"]
    before = Inventory.active_objects().get(product=product, warehouse=wh).quantity

    result = PurchaseReceivingService.receive(
        purchase_order_id=po.id,
        warehouse_id=wh.id,
        lines=[ReceiveLineInput(product_id=product.id, quantity_received=Decimal("4"))],
    )
    after = Inventory.active_objects().get(product=product, warehouse=wh).quantity
    assert after == before + Decimal("4")
    assert result["fully_received"] is False
    po.refresh_from_db()
    assert po.status == PurchaseOrder.STATUS_ORDERED
    item = po.items.get(product=product)
    assert item.quantity_received == Decimal("4")


@pytest.mark.django_db
def test_project_purchase_receipt_creates_inventory_allocation(inv_env):
    project = Project.objects.create(
        tenant=inv_env["tenant"], branch=inv_env["branch"],
        project_code="PRJ-GRN-1", name="Receipt project",
    )
    po = inv_env["po"]
    po.project = project
    po.save(update_fields=["project", "updated_at"])
    PurchaseReceivingService.receive(
        purchase_order_id=po.id,
        warehouse_id=inv_env["wh_a"].id,
        lines=[ReceiveLineInput(product_id=inv_env["product"].id, quantity_received=Decimal("4"))],
    )
    allocation = ProjectInventoryAllocation.active_objects().get(project=project, product=inv_env["product"])
    assert allocation.quantity == Decimal("4")
    assert allocation.source_type == "grn"
    assert allocation.source_id == po.id


@pytest.mark.django_db
def test_receive_marks_po_received_when_complete(inv_env):
    product = inv_env["product"]
    wh = inv_env["wh_a"]
    po = inv_env["po"]
    PurchaseReceivingService.receive(
        purchase_order_id=po.id,
        warehouse_id=wh.id,
        lines=[ReceiveLineInput(product_id=product.id, quantity_received=Decimal("10"))],
    )
    po.refresh_from_db()
    assert po.status == PurchaseOrder.STATUS_RECEIVED


@pytest.mark.django_db
def test_receive_rejects_over_receive(inv_env):
    with pytest.raises(ReceivingError, match="remaining"):
        PurchaseReceivingService.receive(
            purchase_order_id=inv_env["po"].id,
            warehouse_id=inv_env["wh_a"].id,
            lines=[
                ReceiveLineInput(
                    product_id=inv_env["product"].id,
                    quantity_received=Decimal("99"),
                )
            ],
        )


@pytest.mark.django_db
def test_transfer_conserves_quantity(inv_env):
    product = inv_env["product"]
    wh_a = inv_env["wh_a"]
    wh_b = inv_env["wh_b"]
    qty_a = Inventory.active_objects().get(product=product, warehouse=wh_a).quantity

    transfer = StockTransferService.create_draft(
        source_warehouse_id=wh_a.id,
        destination_warehouse_id=wh_b.id,
        branch_id=inv_env["branch"].id,
        lines=[TransferLineInput(product_id=product.id, quantity=Decimal("7"))],
    )
    StockTransferService.confirm(transfer_id=transfer.id)

    a = Inventory.active_objects().get(product=product, warehouse=wh_a)
    b = InventoryService.ensure_inventory_record(product=product, warehouse=wh_b)
    b.refresh_from_db()
    assert a.quantity == qty_a - Decimal("7")
    assert b.quantity == Decimal("7")
    assert a.quantity + b.quantity == qty_a
    transfer.refresh_from_db()
    assert transfer.status == StockTransfer.STATUS_CONFIRMED


@pytest.mark.django_db
def test_transfer_blocks_insufficient_available(inv_env):
    product = inv_env["product"]
    inv = Inventory.active_objects().get(product=product, warehouse=inv_env["wh_a"])
    inv.reserved_quantity = Decimal("18")
    inv.save(update_fields=["reserved_quantity", "updated_at"])

    transfer = StockTransferService.create_draft(
        source_warehouse_id=inv_env["wh_a"].id,
        destination_warehouse_id=inv_env["wh_b"].id,
        lines=[TransferLineInput(product_id=product.id, quantity=Decimal("5"))],
    )
    with pytest.raises(TransferError, match="Insufficient available"):
        StockTransferService.confirm(transfer_id=transfer.id)


@pytest.mark.django_db
def test_transfer_cancel_draft(inv_env):
    transfer = StockTransferService.create_draft(
        source_warehouse_id=inv_env["wh_a"].id,
        destination_warehouse_id=inv_env["wh_b"].id,
        lines=[TransferLineInput(product_id=inv_env["product"].id, quantity=Decimal("1"))],
    )
    StockTransferService.cancel(transfer_id=transfer.id)
    transfer.refresh_from_db()
    assert transfer.status == StockTransfer.STATUS_CANCELLED
    # stock unchanged
    assert Inventory.active_objects().get(
        product=inv_env["product"], warehouse=inv_env["wh_a"]
    ).quantity == Decimal("20")


@pytest.mark.django_db
def test_receive_preview(inv_env):
    data = PurchaseReceivingService.preview(purchase_order_id=inv_env["po"].id)
    assert data["lines"][0]["quantity_remaining"] == 10.0


@pytest.mark.django_db
def test_transfer_line_input_shape():
    from uuid import uuid4

    line = TransferLineInput(product_id=uuid4(), quantity=Decimal("2.5"))
    assert line.quantity == Decimal("2.5")


@pytest.mark.django_db
def test_locked_inventory_is_select_for_update_safe(inv_env):
    """Concurrent-safety primitive: locked row can be updated under transaction."""
    from django.db import transaction

    product = inv_env["product"]
    wh = inv_env["wh_a"]
    with transaction.atomic():
        inv = InventoryService._locked_inventory(product=product, warehouse=wh)
        inv.quantity = inv.quantity + Decimal("1")
        inv.save(update_fields=["quantity", "updated_at"])
    assert Inventory.active_objects().get(product=product, warehouse=wh).quantity == Decimal("21")

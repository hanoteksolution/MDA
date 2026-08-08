from decimal import Decimal

import pytest

from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company


@pytest.fixture
def stock_env(db):
    company = Company.objects.create(name="Smoke Co")
    branch = Branch.objects.create(company=company, name="Main", code="MAIN", is_default=True)
    warehouse = Warehouse.objects.create(
        branch=branch, name="Main WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General")
    unit = Unit.objects.create(name="Piece", abbreviation="pc")
    product = Product.objects.create(
        sku="SKU-RESERVE-1",
        name="Reserve Test Item",
        category=category,
        unit=unit,
        cost_price=Decimal("1.00"),
        selling_price=Decimal("2.00"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("10")
    inv.reserved_quantity = Decimal("0")
    inv.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
    return {"product": product, "warehouse": warehouse, "inventory": inv}


@pytest.mark.django_db
def test_reserve_and_unreserve_quantity(stock_env):
    product = stock_env["product"]
    warehouse = stock_env["warehouse"]

    InventoryService.reserve_quantity(
        product=product,
        warehouse=warehouse,
        quantity=Decimal("3"),
        notes="hold test",
    )
    inv = Inventory.active_objects().get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("10")
    assert inv.reserved_quantity == Decimal("3")
    assert inv.available_quantity == Decimal("7")

    InventoryService.unreserve_quantity(
        product=product,
        warehouse=warehouse,
        quantity=Decimal("3"),
        notes="cancel hold",
    )
    inv.refresh_from_db()
    assert inv.reserved_quantity == Decimal("0")
    assert inv.quantity == Decimal("10")


@pytest.mark.django_db
def test_reserve_rejects_over_available(stock_env):
    with pytest.raises(ValueError, match="Insufficient available stock"):
        InventoryService.reserve_quantity(
            product=stock_env["product"],
            warehouse=stock_env["warehouse"],
            quantity=Decimal("11"),
        )


@pytest.mark.django_db
def test_consume_reserved_deducts_on_hand(stock_env):
    product = stock_env["product"]
    warehouse = stock_env["warehouse"]
    InventoryService.reserve_quantity(
        product=product, warehouse=warehouse, quantity=Decimal("2")
    )
    InventoryService.consume_reserved(
        product=product, warehouse=warehouse, quantity=Decimal("2"), notes="checkout"
    )
    inv = Inventory.active_objects().get(product=product, warehouse=warehouse)
    assert inv.reserved_quantity == Decimal("0")
    assert inv.quantity == Decimal("8")

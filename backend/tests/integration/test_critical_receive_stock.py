"""STEP 32 — critical purchase receive stock via HTTP API."""

from decimal import Decimal

import pytest

from apps.inventory.models import Inventory
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.suppliers.models import Supplier


pytestmark = [pytest.mark.integration, pytest.mark.critical]


@pytest.mark.django_db
def test_receive_stock_api_increases_inventory(api_client, retail_shop, auth_client):
    shop = retail_shop
    product = shop.product  # type: ignore[attr-defined]
    client = auth_client(shop.user)

    supplier = Supplier.objects.create(
        tenant=shop.tenant,
        supplier_code="SUP-INT",
        company_name="Supply Co",
    )
    po = PurchaseOrder.objects.create(
        tenant=shop.tenant,
        order_number="PO-INT-00001",
        supplier=supplier,
        branch=shop.branch,
        status=PurchaseOrder.STATUS_ORDERED,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity_ordered=Decimal("10"),
        quantity_received=Decimal("0"),
        unit_cost=Decimal("1"),
    )

    before = Inventory.active_objects().get(product=product, warehouse=shop.warehouse).quantity
    response = client.post(
        f"/api/v1/purchases/{po.id}/receive/",
        {
            "warehouse_id": str(shop.warehouse.id),
            "lines": [
                {
                    "product_id": str(product.id),
                    "quantity_received": "4",
                    "unit_cost": "1",
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["fully_received"] is False

    after = Inventory.active_objects().get(product=product, warehouse=shop.warehouse).quantity
    assert after == before + 4

    item = PurchaseOrderItem.objects.get(purchase_order=po, product=product)
    assert item.quantity_received == Decimal("4")

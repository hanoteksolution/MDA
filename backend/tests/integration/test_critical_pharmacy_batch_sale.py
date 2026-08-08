"""STEP 32 — critical pharmacy batch sale (FEFO) via HTTP API."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.inventory.models import Inventory
from apps.pharmacy.models import ProductBatch


pytestmark = [pytest.mark.integration, pytest.mark.critical]


@pytest.mark.django_db
def test_pharmacy_batch_sale_via_pos_api(api_client, pharmacy_shop, auth_client):
    shop = pharmacy_shop
    product = shop.product  # type: ignore[attr-defined]
    client = auth_client(shop.user)
    today = date.today()

    early = client.post(
        "/api/v1/pharmacy/batches/",
        {
            "product_id": str(product.id),
            "warehouse_id": str(shop.warehouse.id),
            "quantity": "5",
            "batch_number": "EARLY-LOT",
            "expiry_date": (today + timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    late = client.post(
        "/api/v1/pharmacy/batches/",
        {
            "product_id": str(product.id),
            "warehouse_id": str(shop.warehouse.id),
            "quantity": "5",
            "batch_number": "LATE-LOT",
            "expiry_date": (today + timedelta(days=90)).isoformat(),
        },
        format="json",
    )
    assert early.status_code == 201
    assert late.status_code == 201

    inv = Inventory.active_objects().get(product=product, warehouse=shop.warehouse)
    inv.quantity = Decimal("10")
    inv.save(update_fields=["quantity", "updated_at"])

    preview = client.get(
        "/api/v1/pharmacy/batches/fefo-preview/",
        {"product_id": str(product.id), "warehouse_id": str(shop.warehouse.id), "quantity": "7"},
    )
    assert preview.status_code == 200
    plan = preview.json()["data"]
    assert plan[0]["batch_number"] == "EARLY-LOT"
    assert plan[0]["quantity"] == 5.0
    assert plan[1]["batch_number"] == "LATE-LOT"
    assert plan[1]["quantity"] == 2.0

    sale = client.post(
        "/api/v1/pos/checkout/",
        {
            "branch_id": str(shop.branch.id),
            "customer_id": "walkin",
            "waiter_name": "Counter",
            "payment_method": "cash",
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": "7",
                    "unit_price": "10",
                }
            ],
            "idempotency_key": "int-pharm-fefo-1",
        },
        format="json",
    )
    assert sale.status_code == 201

    early_batch = ProductBatch.active_objects().get(batch_number="EARLY-LOT")
    late_batch = ProductBatch.active_objects().get(batch_number="LATE-LOT")
    assert early_batch.quantity == Decimal("0")
    assert late_batch.quantity == Decimal("3")
    assert Inventory.active_objects().get(product=product, warehouse=shop.warehouse).quantity == Decimal("3")

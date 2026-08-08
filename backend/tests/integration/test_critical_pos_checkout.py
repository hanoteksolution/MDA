"""STEP 32 — critical POS checkout via HTTP API."""

import pytest

from apps.inventory.models import Inventory
from apps.sales.models import Invoice


pytestmark = [pytest.mark.integration, pytest.mark.critical]


@pytest.mark.django_db
def test_pos_checkout_api_reduces_stock(api_client, retail_shop, auth_client):
    shop = retail_shop
    product = shop.product  # type: ignore[attr-defined]
    client = auth_client(shop.user)

    before = Inventory.active_objects().get(product=product, warehouse=shop.warehouse).quantity
    response = client.post(
        "/api/v1/pos/checkout/",
        {
            "branch_id": str(shop.branch.id),
            "customer_id": "walkin",
            "waiter_name": "Counter",
            "payment_method": "cash",
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": "2",
                    "unit_price": "10",
                }
            ],
            "idempotency_key": "int-pos-checkout-1",
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["invoice"]["status"] == Invoice.STATUS_PAID

    after = Inventory.active_objects().get(product=product, warehouse=shop.warehouse).quantity
    assert after == before - 2


@pytest.mark.django_db
def test_pos_checkout_idempotency_via_api(api_client, retail_shop, auth_client):
    shop = retail_shop
    product = shop.product  # type: ignore[attr-defined]
    client = auth_client(shop.user)
    payload = {
        "branch_id": str(shop.branch.id),
        "customer_id": "walkin",
        "waiter_name": "Counter",
        "payment_method": "cash",
        "items": [{"product_id": str(product.id), "quantity": "1", "unit_price": "10"}],
        "idempotency_key": "int-pos-idem-1",
    }
    first = client.post("/api/v1/pos/checkout/", payload, format="json")
    second = client.post("/api/v1/pos/checkout/", payload, format="json")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["invoice"]["id"] == second.json()["data"]["invoice"]["id"]
    assert second.json()["data"].get("idempotent_replay") is True
    assert Invoice.objects.filter(idempotency_key="int-pos-idem-1").count() == 1

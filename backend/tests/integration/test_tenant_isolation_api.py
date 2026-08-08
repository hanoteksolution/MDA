"""STEP 32 — tenant isolation enforced at HTTP API boundary."""

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.isolation]


@pytest.mark.django_db
def test_product_list_scoped_via_api(api_client, two_shops, auth_client):
    a, b = two_shops
    client = auth_client(a.user)
    response = client.get("/api/v1/products/?page_size=100")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["data"]["results"]}
    assert str(a.product.id) in ids  # type: ignore[attr-defined]
    assert str(b.product.id) not in ids  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_barcode_lookup_blocks_cross_tenant(api_client, two_shops, auth_client):
    a, b = two_shops
    client = auth_client(a.user)
    response = client.get(f"/api/v1/products/barcode/{b.product.barcode}/")  # type: ignore[attr-defined]
    assert response.status_code == 404
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_purchase_order_receive_blocks_cross_tenant_po(api_client, two_shops, auth_client):
    from decimal import Decimal

    from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
    from apps.suppliers.models import Supplier

    a, b = two_shops
    supplier = Supplier.objects.create(
        tenant=b.tenant,
        supplier_code="SUP-B",
        company_name="B Supply",
    )
    po = PurchaseOrder.objects.create(
        tenant=b.tenant,
        order_number="PO-B-00001",
        supplier=supplier,
        branch=b.branch,
        status=PurchaseOrder.STATUS_ORDERED,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=b.product,  # type: ignore[attr-defined]
        quantity_ordered=Decimal("5"),
        quantity_received=Decimal("0"),
        unit_cost=Decimal("1"),
    )

    client = auth_client(a.user)
    response = client.post(
        f"/api/v1/purchases/{po.id}/receive/",
        {
            "warehouse_id": str(a.warehouse.id),
            "lines": [
                {
                    "product_id": str(b.product.id),  # type: ignore[attr-defined]
                    "quantity_received": "1",
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 404

"""Desktop sync authenticated to tenant — isolation + credential checks."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.customers.models import Customer
from apps.platform.models import Tenant
from apps.platform.services.platform_service import PlatformService
from apps.platform.services.sync_catalog import CatalogSyncEngine
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice
from apps.settings_app.models import Branch, Company


@pytest.fixture
def two_tenant_sync(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})

    a, _ = PlatformService.create_shop(
        data={
            "name": "Tenant A Shop",
            "subdomain": "tenanta-sync",
            "business_type_code": "retail",
            "owner": {"username": "owner_a_sync", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    a.sync_secret = "secret-tenant-a"
    a.save(update_fields=["sync_secret", "updated_at"])

    b, _ = PlatformService.create_shop(
        data={
            "name": "Tenant B Shop",
            "subdomain": "tenantb-sync",
            "business_type_code": "retail",
            "owner": {"username": "owner_b_sync", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    b.sync_secret = "secret-tenant-b"
    b.save(update_fields=["sync_secret", "updated_at"])

    cat_a = Category.objects.create(name="A Cat", tenant=a)
    unit_a = Unit.objects.create(name="Piece", abbreviation="pc", tenant=a)
    product_a = Product.objects.create(
        tenant=a,
        sku="SKU-A-ONLY",
        name="Product A",
        category=cat_a,
        unit=unit_a,
        cost_price=Decimal("1"),
        selling_price=Decimal("5"),
    )

    cat_b = Category.objects.create(name="B Cat", tenant=b)
    unit_b = Unit.objects.create(name="Piece", abbreviation="pc", tenant=b)
    product_b = Product.objects.create(
        tenant=b,
        sku="SKU-B-ONLY",
        name="Product B",
        category=cat_b,
        unit=unit_b,
        cost_price=Decimal("2"),
        selling_price=Decimal("9"),
    )

    return {
        "a": a,
        "b": b,
        "product_a": product_a,
        "product_b": product_b,
    }


@pytest.mark.django_db
def test_wrong_sync_secret_rejected(two_tenant_sync):
    tenant = two_tenant_sync["a"]
    client = APIClient()
    res = client.get(
        "/api/v1/sync/shop-pull/",
        HTTP_X_TENANT_SLUG=tenant.slug,
        HTTP_X_SYNC_SECRET="wrong-secret",
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_shop_verify_ok_and_bad(two_tenant_sync):
    tenant = two_tenant_sync["a"]
    client = APIClient()
    ok = client.get(
        "/api/v1/sync/shop-verify/",
        HTTP_X_TENANT_SLUG=tenant.slug,
        HTTP_X_SYNC_SECRET=tenant.sync_secret,
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["tenant_slug"] == tenant.slug

    bad = client.post(
        "/api/v1/sync/shop-verify/",
        {},
        format="json",
        HTTP_X_TENANT_SLUG=tenant.slug,
        HTTP_X_SYNC_SECRET="nope",
    )
    assert bad.status_code == 403


@pytest.mark.django_db
def test_pull_is_tenant_isolated(two_tenant_sync):
    a = two_tenant_sync["a"]
    client = APIClient()
    res = client.get(
        "/api/v1/sync/shop-pull/",
        HTTP_X_TENANT_SLUG=a.slug,
        HTTP_X_SYNC_SECRET=a.sync_secret,
    )
    assert res.status_code == 200
    skus = {p["sku"] for p in res.json()["data"]["products"]}
    assert "SKU-A-ONLY" in skus
    assert "SKU-B-ONLY" not in skus


@pytest.mark.django_db
def test_push_stamps_tenant_on_customer_and_invoice(two_tenant_sync):
    a = two_tenant_sync["a"]
    product = two_tenant_sync["product_a"]
    client = APIClient()
    payload = {
        "device_id": "dev-1",
        "customers": [
            {
                "customer_code": "CUST-A1",
                "full_name": "Alice Sync",
                "email": "",
                "phone": "",
                "address": "",
                "customer_type": "retail",
                "credit_limit": "0",
                "is_active": True,
            }
        ],
        "invoices": [
            {
                "local_id": "local-1",
                "invoice_number": "INV-TENANT-A-1",
                "idempotency_key": "idem-tenant-a-1",
                "issue_date": "2026-08-07",
                "status": "paid",
                "subtotal": 5.0,
                "discount_amount": 0,
                "tax_amount": 0,
                "total_amount": 5.0,
                "amount_paid": 5.0,
                "customer_code": "CUST-A1",
                "customer_name": "Alice Sync",
                "items": [
                    {
                        "sku": product.sku,
                        "quantity": 1,
                        "unit_price": 5.0,
                        "line_total": 5.0,
                    }
                ],
            }
        ],
    }
    res = client.post(
        "/api/v1/sync/shop-push/",
        payload,
        format="json",
        HTTP_X_TENANT_SLUG=a.slug,
        HTTP_X_SYNC_SECRET=a.sync_secret,
    )
    assert res.status_code == 200
    assert res.json()["data"]["applied"]["customers"] == 1
    assert res.json()["data"]["applied"]["invoices"] == 1

    cust = Customer.active_objects().get(customer_code="CUST-A1")
    assert cust.tenant_id == a.id
    inv = Invoice.active_objects().get(invoice_number="INV-TENANT-A-1")
    assert inv.tenant_id == a.id
    assert inv.items.first().product_id == product.id


@pytest.mark.django_db
def test_push_does_not_attach_foreign_sku(two_tenant_sync):
    a = two_tenant_sync["a"]
    foreign_sku = two_tenant_sync["product_b"].sku
    stats = CatalogSyncEngine.apply_shop_push(
        tenant=a,
        payload={
            "device_id": "dev-2",
            "inventory": [{"sku": foreign_sku, "quantity": 99}],
            "invoices": [
                {
                    "invoice_number": "INV-SKIP-FOREIGN",
                    "idempotency_key": "idem-skip-foreign",
                    "issue_date": "2026-08-07",
                    "status": "paid",
                    "subtotal": 9,
                    "total_amount": 9,
                    "amount_paid": 9,
                    "customer_name": "Walk-in",
                    "items": [
                        {
                            "sku": foreign_sku,
                            "quantity": 1,
                            "unit_price": 9,
                            "line_total": 9,
                        }
                    ],
                }
            ],
        },
    )
    assert stats["skipped_foreign_skus"] >= 1
    inv = Invoice.active_objects().get(invoice_number="INV-SKIP-FOREIGN")
    assert inv.tenant_id == a.id
    assert inv.items.count() == 0
    assert not Product.active_objects().filter(tenant=a, sku=foreign_sku).exists()

"""STEP 29 — offline POS sync outbox + idempotent cloud ingest."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.customers.models import Customer
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import SyncIngestReceipt, SyncOutboxEntry, Tenant
from apps.platform.services.platform_service import PlatformService
from apps.platform.services.sync_catalog import CatalogSyncEngine
from apps.platform.services.sync_finance_policy import SyncFinancePolicy
from apps.platform.services.sync_outbox_service import SyncOutboxService
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pos_env(db):
    tenant = Tenant.objects.create(name="POS Co", slug="pos-co-sync", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="POS Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    from apps.inventory.models import Warehouse

    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="Main WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="POS-1",
        name="Hold Item",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("10")
    inv.reserved_quantity = Decimal("0")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "reserved_quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant,
        customer_code="WALK",
        full_name="Walk-in Customer",
        branch=branch,
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="pos_cashier_sync",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {"tenant": tenant, "branch": branch, "product": product, "user": user}


def _cart(product, qty="2"):
    return [{"product_id": str(product.id), "quantity": qty, "unit_price": "10"}]


@pytest.fixture
def sync_cloud_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Sync Shop",
            "subdomain": "syncshop",
            "business_type_code": "retail",
            "owner": {"username": "sync_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    tenant.sync_secret = "sync-test-secret"
    tenant.save(update_fields=["sync_secret", "updated_at"])
    company = Company.active_objects().filter(tenant=tenant).first()
    branch = Branch.active_objects().filter(company=company).first()
    category = Category.objects.create(name="Sync Cat", tenant=tenant)
    unit = Unit.objects.create(name="Each", abbreviation="ea", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="SYNC-SKU-1",
        name="Sync Product",
        category=category,
        unit=unit,
        cost_price=Decimal("5"),
        selling_price=Decimal("12"),
    )
    return {"tenant": tenant, "branch": branch, "product": product}


def _invoice_payload(*, product, idempotency_key="sync-idem-001"):
    return {
        "device_id": "device-test-1",
        "invoices": [
            {
                "local_id": "local-inv-1",
                "invoice_number": "INV-SYNC-001",
                "idempotency_key": idempotency_key,
                "issue_date": "2026-08-07",
                "status": "paid",
                "subtotal": 12.0,
                "discount_amount": 0,
                "tax_amount": 0,
                "total_amount": 12.0,
                "amount_paid": 12.0,
                "customer_name": "Walk-in Customer",
                "items": [
                    {
                        "sku": product.sku,
                        "quantity": 1,
                        "unit_price": 12.0,
                        "line_total": 12.0,
                    }
                ],
            }
        ],
    }


@pytest.mark.django_db
def test_shop_push_idempotent_invoice_replay(sync_cloud_env):
    tenant = sync_cloud_env["tenant"]
    product = sync_cloud_env["product"]
    client = APIClient()
    payload = _invoice_payload(product=product)
    headers = {
        "HTTP_X_TENANT_SLUG": tenant.slug,
        "HTTP_X_SYNC_SECRET": tenant.sync_secret,
    }

    first = client.post("/api/v1/sync/shop-push/", payload, format="json", **headers)
    assert first.status_code == 200
    assert first.json()["data"]["applied"]["invoices"] == 1

    second = client.post("/api/v1/sync/shop-push/", payload, format="json", **headers)
    assert second.status_code == 200
    assert second.json()["data"]["idempotent_replays"] == 1
    assert second.json()["data"]["applied"]["invoices"] == 0

    assert Invoice.active_objects().filter(invoice_number="INV-SYNC-001").count() == 1
    assert SyncIngestReceipt.objects.filter(tenant=tenant, idempotency_key="sync-idem-001").count() == 1


@pytest.mark.django_db
def test_finance_keys_rejected_from_push(sync_cloud_env):
    tenant = sync_cloud_env["tenant"]
    product = sync_cloud_env["product"]
    payload = _invoice_payload(product=product)
    payload["journal_entries"] = [{"account": "cash", "amount": 100}]
    payload["expenses"] = [{"amount": 50}]

    stats = CatalogSyncEngine.apply_shop_push(tenant=tenant, payload=dict(payload))
    assert "journal_entries" in stats["finance_keys_rejected"]
    assert stats["invoices"] == 1


@pytest.mark.django_db
def test_finance_policy_sanitize():
    cleaned = SyncFinancePolicy.sanitize_push_payload(
        {"invoices": [], "journal_entries": [], "customers": []}
    )
    assert "journal_entries" not in cleaned
    assert "customers" in cleaned


@pytest.mark.django_db
def test_outbox_enqueue_and_mark_synced(pos_env):
    invoice_result = PosService.checkout(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Sam",
            "payment_method": "cash",
            "idempotency_key": "pos-outbox-key",
            "items": _cart(pos_env["product"]),
        },
        user=pos_env["user"],
    )
    invoice_id = invoice_result["invoice"]["id"]
    assert SyncOutboxEntry.objects.filter(resource_id=invoice_id, status="pending").count() == 1

    marked = SyncOutboxService.mark_invoices_synced(invoice_ids=[invoice_id])
    assert marked == 1
    assert SyncOutboxEntry.objects.get(resource_id=invoice_id).status == "synced"


@pytest.mark.django_db
def test_sync_queue_endpoint(pos_env):
    PosService.checkout(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Sam",
            "payment_method": "cash",
            "idempotency_key": "queue-key-1",
            "items": _cart(pos_env["product"]),
        },
        user=pos_env["user"],
    )
    client = APIClient()
    client.force_authenticate(user=pos_env["user"])
    response = client.get("/api/v1/sync/queue/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["pending"] >= 1
    assert data["finance_rules"]["push_forbidden"]

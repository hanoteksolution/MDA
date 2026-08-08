"""STEP 54 — Pharmacy POS sales post PHARMACY_SALE_COMPLETED + PHARM BU."""

from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model

from apps.customers.models import Customer
from apps.finance.events import event_types
from apps.finance.models import AccountingEvent, BusinessUnit, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pharm_gl_env(db):
    tenant = Tenant.objects.create(
        name="Pharm GL", slug="pharm-gl", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Pharm GL Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Dispense", code="RX", is_default=True
    )
    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="RX WH", code="RX1", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pos", "inventory", "sales", "purchases", "pharmacy"],
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)

    category = Category.objects.create(name="Meds", tenant=tenant)
    unit = Unit.objects.create(name="Tablet", abbreviation="tab", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="PARA-GL",
        name="Paracetamol",
        category=category,
        unit=unit,
        cost_price=Decimal("2"),
        selling_price=Decimal("5"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("50")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])

    Customer.objects.create(
        tenant=tenant,
        customer_code="WALK",
        full_name="Walk-in Customer",
        branch=branch,
    )
    user = get_user_model().objects.create_user(
        username="pharm_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "product": product,
        "user": user,
        "warehouse": warehouse,
    }


@pytest.mark.django_db
def test_pharmacy_pos_posts_pharmacy_sale_event(pharm_gl_env):
    result = PosService.checkout(
        data={
            "branch_id": str(pharm_gl_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Pharmacist",
            "payment_method": "cash",
            "items": [
                {
                    "product_id": str(pharm_gl_env["product"].id),
                    "quantity": "4",
                    "unit_price": "5",
                }
            ],
        },
        user=pharm_gl_env["user"],
    )
    invoice_id = result["invoice"]["id"]
    journal = JournalEntry.active_objects().get(
        source_type="invoice",
        source_id=invoice_id,
        source_module="pharmacy",
    )
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    # revenue 20 + COGS 8
    assert data["total_debit"] == 28.0
    assert all(line.get("business_unit_code") == "PHARM" for line in data["lines"])

    event = AccountingEvent.active_objects().get(journal_entry_id=journal.id)
    assert event.event_type == event_types.PHARMACY_SALE_COMPLETED
    assert event.source_module == "pharmacy"
    assert event.status == AccountingEvent.STATUS_POSTED

    assert BusinessUnit.active_objects().filter(
        tenant_id=pharm_gl_env["tenant"].id, code="PHARM"
    ).exists()


@pytest.mark.django_db
def test_pharmacy_sale_idempotent(pharm_gl_env):
    payload = {
        "branch_id": str(pharm_gl_env["branch"].id),
        "customer_id": "walkin",
        "waiter_name": "Pharmacist",
        "payment_method": "cash",
        "items": [
            {
                "product_id": str(pharm_gl_env["product"].id),
                "quantity": "1",
                "unit_price": "5",
            }
        ],
        "idempotency_key": "pharm-cae-key-1",
    }
    PosService.checkout(data=payload, user=pharm_gl_env["user"])
    PosService.checkout(data=payload, user=pharm_gl_env["user"])
    assert (
        AccountingEvent.active_objects()
        .filter(event_type=event_types.PHARMACY_SALE_COMPLETED)
        .count()
        == 1
    )

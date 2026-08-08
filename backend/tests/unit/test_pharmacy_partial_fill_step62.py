"""STEP 62 — Rx partial-fill by line + demo expire scheduled task."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.notifications.tasks.scheduled import expire_demo_tenants
from apps.pharmacy.models import Prescription
from apps.pharmacy.services.prescription_service import PrescriptionService
from apps.platform.models import Tenant
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company
from django.utils import timezone
from datetime import timedelta


@pytest.fixture
def fill_env(db):
    tenant = Tenant.objects.create(
        name="Fill Rx", slug="fill-rx", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Fill Rx Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pharmacy", "inventory", "pos", "sales"],
        validate_dependencies=False,
    )
    category = Category.objects.create(name="Meds", tenant=tenant)
    unit = Unit.objects.create(name="Tab", abbreviation="tab", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="FILL-AMOX",
        name="Amox Fill",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("4"),
        requires_prescription=True,
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("100")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    user = get_user_model().objects.create_user(
        username="fill_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {"tenant": tenant, "user": user, "product": product, "warehouse": warehouse}


@pytest.mark.django_db
def test_partial_fill_by_line_keeps_rx_active(fill_env):
    user = fill_env["user"]
    product = fill_env["product"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Partial Patient",
            "lines": [
                {"product_id": str(product.id), "drug_name": product.name, "quantity": 10},
                {"drug_name": "Free text syrup", "quantity": 2},
            ],
        },
        user=user,
    )
    line_product = next(l for l in rx.lines.all() if l.product_id)
    line_text = next(l for l in rx.lines.all() if not l.product_id)

    PrescriptionService.dispense(
        prescription_id=rx.id,
        user=user,
        deduct_stock=True,
        fill_lines={str(line_product.id): Decimal("4"), str(line_text.id): Decimal("0")},
    )
    rx.refresh_from_db()
    line_product.refresh_from_db()
    line_text.refresh_from_db()
    assert float(line_product.quantity_dispensed) == 4
    assert float(line_text.quantity_dispensed) == 0
    assert rx.status == Prescription.STATUS_ACTIVE

    PrescriptionService.dispense(
        prescription_id=rx.id,
        user=user,
        deduct_stock=True,
        fill_lines={
            str(line_product.id): Decimal("6"),
            str(line_text.id): Decimal("2"),
        },
    )
    rx.refresh_from_db()
    assert rx.status == Prescription.STATUS_DISPENSED


@pytest.mark.django_db
def test_expire_demo_tenants_task(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, _ = DemoTenantService.create(
        data={
            "name": "Expiring Demo Task",
            "business_type_code": "retail",
            "duration_days": 7,
            "generate_data": False,
        }
    )
    tenant.demo_expires_at = timezone.now() - timedelta(hours=2)
    tenant.save(update_fields=["demo_expires_at", "updated_at"])
    result = expire_demo_tenants()
    assert result["expired"] >= 1
    tenant.refresh_from_db()
    assert tenant.demo_status == Tenant.DEMO_EXPIRED

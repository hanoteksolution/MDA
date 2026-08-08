"""STEP 60 — Rx dispense FEFO stock + quantity remaining caps."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model

from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.pharmacy.models import BatchDispense, Prescription, ProductBatch
from apps.pharmacy.services.batch_service import BatchService
from apps.pharmacy.services.prescription_service import PrescriptionError, PrescriptionService
from apps.pharmacy.services.rx_pos_service import RxPosError, RxPosService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company


@pytest.fixture
def fefo_rx_env(db):
    tenant = Tenant.objects.create(
        name="FEFO Rx", slug="fefo-rx", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="FEFO Rx Co", tenant=tenant)
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
        sku="AMOX-FEFO",
        name="Amoxicillin FEFO",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("5"),
        requires_prescription=True,
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("0")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])

    today = date.today()
    BatchService.receive_stock(
        product=product,
        warehouse=warehouse,
        quantity=Decimal("5"),
        batch_number="NEAR",
        expiry_date=today + timedelta(days=20),
        user=None,
    )
    BatchService.receive_stock(
        product=product,
        warehouse=warehouse,
        quantity=Decimal("10"),
        batch_number="FAR",
        expiry_date=today + timedelta(days=200),
        user=None,
    )
    user = get_user_model().objects.create_user(
        username="fefo_rx_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "warehouse": warehouse,
        "product": product,
        "user": user,
    }


@pytest.mark.django_db
def test_manual_dispense_deducts_fefo_and_inventory(fefo_rx_env):
    user = fefo_rx_env["user"]
    product = fefo_rx_env["product"]
    wh = fefo_rx_env["warehouse"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Patient A",
            "lines": [
                {"product_id": str(product.id), "drug_name": product.name, "quantity": 7}
            ],
        },
        user=user,
    )
    before = Inventory.active_objects().get(product=product, warehouse=wh).quantity
    PrescriptionService.dispense(prescription_id=rx.id, user=user, deduct_stock=True)
    rx.refresh_from_db()
    assert rx.status == Prescription.STATUS_DISPENSED
    line = rx.lines.first()
    assert float(line.quantity_dispensed) == 7
    after = Inventory.active_objects().get(product=product, warehouse=wh).quantity
    assert after == before - Decimal("7")
    near = ProductBatch.active_objects().get(product=product, batch_number="NEAR")
    far = ProductBatch.active_objects().get(product=product, batch_number="FAR")
    assert near.quantity == Decimal("0")
    assert far.quantity == Decimal("8")
    assert BatchDispense.active_objects().filter(
        reference_type="prescription", reference_id=rx.id
    ).exists()


@pytest.mark.django_db
def test_dispense_fails_when_batch_short(fefo_rx_env):
    user = fefo_rx_env["user"]
    product = fefo_rx_env["product"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Patient B",
            "lines": [
                {"product_id": str(product.id), "drug_name": product.name, "quantity": 99}
            ],
        },
        user=user,
    )
    with pytest.raises(PrescriptionError, match="Insufficient batch"):
        PrescriptionService.dispense(prescription_id=rx.id, user=user, deduct_stock=True)


@pytest.mark.django_db
def test_pos_qty_cap_rejects_overfill(fefo_rx_env):
    user = fefo_rx_env["user"]
    product = fefo_rx_env["product"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Patient C",
            "lines": [
                {"product_id": str(product.id), "drug_name": product.name, "quantity": 3}
            ],
        },
        user=user,
    )
    with pytest.raises(RxPosError, match="exceeds Rx remaining"):
        RxPosService.validate_cart(
            items=[
                {
                    "product_id": str(product.id),
                    "quantity": Decimal("5"),
                    "unit_price": Decimal("5"),
                }
            ],
            prescription_id=rx.id,
            user=user,
            profile={
                "code": "PHARMACY",
                "enabled_modules": ["pharmacy"],
                "capabilities": {"rx": True},
            },
        )


@pytest.mark.django_db
def test_pos_fill_without_double_stock_deduct(fefo_rx_env):
    user = fefo_rx_env["user"]
    product = fefo_rx_env["product"]
    wh = fefo_rx_env["warehouse"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Patient D",
            "lines": [
                {"product_id": str(product.id), "drug_name": product.name, "quantity": 4}
            ],
        },
        user=user,
    )
    before = Inventory.active_objects().get(product=product, warehouse=wh).quantity
    InventoryService.apply_sale_delta(
        product=product,
        warehouse=wh,
        quantity_delta=Decimal("-2"),
        reference_type="invoice",
        reference_id=uuid4(),
        user=user,
    )
    mid = Inventory.active_objects().get(product=product, warehouse=wh).quantity
    assert mid == before - Decimal("2")

    PrescriptionService.dispense(
        prescription_id=rx.id,
        user=user,
        deduct_stock=False,
        fill_quantities={str(product.id): Decimal("2")},
        notes="POS sim",
    )
    after = Inventory.active_objects().get(product=product, warehouse=wh).quantity
    assert after == mid
    rx.refresh_from_db()
    assert float(rx.lines.first().quantity_dispensed) == 2
    assert rx.status == Prescription.STATUS_ACTIVE

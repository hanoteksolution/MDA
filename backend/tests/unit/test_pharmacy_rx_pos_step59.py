"""STEP 59 — Product.requires_prescription + POS Rx gate."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.customers.models import Customer
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.pharmacy.models import Prescription
from apps.pharmacy.services.prescription_service import PrescriptionService
from apps.pharmacy.services.rx_pos_service import RxPosError, RxPosService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def rx_pos_env(db):
    tenant = Tenant.objects.create(
        name="Rx POS Co", slug="rx-pos", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Rx POS Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pharmacy", "inventory", "pos", "sales", "purchases"],
        validate_dependencies=False,
    )
    category = Category.objects.create(name="Rx Meds", tenant=tenant)
    unit = Unit.objects.create(name="Tab", abbreviation="tab", tenant=tenant)
    otc = Product.objects.create(
        tenant=tenant,
        sku="OTC-1",
        name="Vitamin C",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("2"),
        requires_prescription=False,
    )
    rx_drug = Product.objects.create(
        tenant=tenant,
        sku="RX-AMOX",
        name="Amoxicillin 500",
        category=category,
        unit=unit,
        cost_price=Decimal("3"),
        selling_price=Decimal("8"),
        requires_prescription=True,
    )
    for product, qty in ((otc, Decimal("20")), (rx_drug, Decimal("20"))):
        inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
        inv.quantity = qty
        inv.tenant_id = tenant.id
        inv.save(update_fields=["quantity", "tenant_id", "updated_at"])

    Customer.objects.create(
        tenant=tenant,
        customer_code="WALK",
        full_name="Walk-in Customer",
        branch=branch,
    )
    user = get_user_model().objects.create_user(
        username="rx_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "user": user,
        "otc": otc,
        "rx_drug": rx_drug,
    }


def _checkout(env, *, product, prescription_id=None):
    data = {
        "branch_id": str(env["branch"].id),
        "customer_id": "walkin",
        "waiter_name": "Pharmacist",
        "payment_method": "cash",
        "items": [
            {
                "product_id": str(product.id),
                "quantity": "1",
                "unit_price": str(product.selling_price),
            }
        ],
    }
    if prescription_id:
        data["prescription_id"] = str(prescription_id)
    return PosService.checkout(data=data, user=env["user"])


@pytest.mark.django_db
def test_otc_sale_without_rx(rx_pos_env):
    result = _checkout(rx_pos_env, product=rx_pos_env["otc"])
    assert result["invoice"]["id"]


@pytest.mark.django_db
def test_rx_product_requires_prescription(rx_pos_env):
    with pytest.raises(ValueError, match="Prescription required"):
        _checkout(rx_pos_env, product=rx_pos_env["rx_drug"])


@pytest.mark.django_db
def test_rx_sale_with_covering_prescription(rx_pos_env):
    user = rx_pos_env["user"]
    product = rx_pos_env["rx_drug"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Fatima",
            "prescribed_by": "Dr. X",
            "lines": [
                {
                    "product_id": str(product.id),
                    "drug_name": product.name,
                    "quantity": 10,
                }
            ],
        },
        user=user,
    )
    result = _checkout(rx_pos_env, product=product, prescription_id=rx.id)
    assert result["invoice"]["id"]
    notes = result["invoice"].get("notes") or ""
    assert rx.rx_number in notes
    rx.refresh_from_db()
    line = rx.lines.first()
    line.refresh_from_db()
    assert float(line.quantity_dispensed) == 1
    # Line qty was 10 — remaining stays active for refills
    assert rx.status == Prescription.STATUS_ACTIVE
    assert "POS invoice" in (rx.notes or "")


@pytest.mark.django_db
def test_rx_sale_rejects_unrelated_prescription(rx_pos_env):
    user = rx_pos_env["user"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Other",
            "drug_name": "Unrelated Drug XYZ",
            "quantity": 1,
        },
        user=user,
    )
    with pytest.raises(ValueError, match="does not cover"):
        _checkout(rx_pos_env, product=rx_pos_env["rx_drug"], prescription_id=rx.id)


@pytest.mark.django_db
def test_gate_skipped_without_pharmacy_module(rx_pos_env):
    sync_tenant_modules(
        tenant=rx_pos_env["tenant"],
        enabled_codes=["pos", "inventory", "sales"],
        validate_dependencies=False,
        disable_missing=True,
    )
    assert (
        RxPosService.validate_cart(
            items=[
                {
                    "product_id": str(rx_pos_env["rx_drug"].id),
                    "quantity": Decimal("1"),
                    "unit_price": Decimal("8"),
                }
            ],
            prescription_id=None,
            user=rx_pos_env["user"],
            profile={"code": "RETAIL", "enabled_modules": ["pos"], "capabilities": {}},
        )
        is None
    )
    result = _checkout(rx_pos_env, product=rx_pos_env["rx_drug"])
    assert result["invoice"]["id"]

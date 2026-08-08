"""STEP 65 — Pharmacy categories UX (inventory Category, no parallel catalog)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Permission, UserPermission
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.pharmacy.services.batch_service import BatchService
from apps.pharmacy.services.prescription_service import PrescriptionService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company


@pytest.fixture
def cat_env(db):
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(
        name="Cat Pharm", slug="cat-pharm", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Cat Pharm Co", tenant=tenant)
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
    analgesics = Category.objects.create(name="Analgesics", tenant=tenant)
    antibiotics = Category.objects.create(name="Antibiotics", tenant=tenant)
    unit = Unit.objects.create(name="Tab", abbreviation="tab", tenant=tenant)
    para = Product.objects.create(
        tenant=tenant,
        sku="PARA-CAT",
        name="Paracetamol",
        category=analgesics,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("2"),
    )
    amox = Product.objects.create(
        tenant=tenant,
        sku="AMOX-CAT",
        name="Amoxicillin",
        category=antibiotics,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("5"),
        requires_prescription=True,
    )
    for product, qty, days in (
        (para, Decimal("40"), 30),
        (amox, Decimal("20"), 60),
    ):
        inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
        inv.quantity = Decimal("0")
        inv.tenant_id = tenant.id
        inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
        BatchService.receive_stock(
            product=product,
            warehouse=warehouse,
            quantity=qty,
            batch_number=f"{product.sku}-B1",
            expiry_date=date.today() + timedelta(days=days),
        )
    user = get_user_model().objects.create_user(
        username="cat_pharm_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    perm = Permission.objects.filter(codename="pharmacy.view").first()
    if perm:
        UserPermission.objects.get_or_create(user=user, permission=perm)
    return {
        "tenant": tenant,
        "user": user,
        "analgesics": analgesics,
        "antibiotics": antibiotics,
        "para": para,
        "amox": amox,
    }


@pytest.mark.django_db
def test_list_batches_filters_by_category(cat_env):
    user = cat_env["user"]
    analgesic_batches = list(
        BatchService.list_batches(user=user, category_id=cat_env["analgesics"].id)
    )
    antibiotic_batches = list(
        BatchService.list_batches(user=user, category_id=cat_env["antibiotics"].id)
    )
    assert len(analgesic_batches) == 1
    assert analgesic_batches[0].product_id == cat_env["para"].id
    assert len(antibiotic_batches) == 1
    assert antibiotic_batches[0].product_id == cat_env["amox"].id
    ser = BatchService.serialize(analgesic_batches[0])
    assert ser["category_name"] == "Analgesics"
    assert ser["category_id"] == str(cat_env["analgesics"].id)


@pytest.mark.django_db
def test_list_prescriptions_filters_by_category(cat_env):
    user = cat_env["user"]
    PrescriptionService.create(
        data={
            "patient_name": "Amina",
            "product_id": str(cat_env["para"].id),
            "drug_name": cat_env["para"].name,
            "quantity": 10,
        },
        user=user,
    )
    PrescriptionService.create(
        data={
            "patient_name": "Hassan",
            "product_id": str(cat_env["amox"].id),
            "drug_name": cat_env["amox"].name,
            "quantity": 14,
        },
        user=user,
    )
    analgesic_rx = list(
        PrescriptionService.list(user=user, category_id=cat_env["analgesics"].id)
    )
    antibiotic_rx = list(
        PrescriptionService.list(user=user, category_id=cat_env["antibiotics"].id)
    )
    assert len(analgesic_rx) == 1
    assert analgesic_rx[0].patient_name == "Amina"
    assert len(antibiotic_rx) == 1
    assert antibiotic_rx[0].patient_name == "Hassan"
    ser = PrescriptionService.serialize(analgesic_rx[0])
    assert ser["lines"][0]["category_name"] == "Analgesics"


@pytest.mark.django_db
def test_pharmacy_categories_api_and_summary(cat_env):
    user = cat_env["user"]
    cats = BatchService.list_categories(user=user)
    names = {c["name"] for c in cats}
    assert names == {"Analgesics", "Antibiotics"}
    summary = BatchService.summary(user=user)
    assert {c["name"] for c in summary["categories"]} == names

    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/pharmacy/categories/")
    assert response.status_code == 200, response.content
    api_names = {c["name"] for c in response.json()["data"]}
    assert api_names == names

    batches = client.get(
        f"/api/v1/pharmacy/batches/?category_id={cat_env['analgesics'].id}"
    )
    assert batches.status_code == 200
    results = batches.json()["data"]["results"]
    assert len(results) == 1
    assert results[0]["product_sku"] == "PARA-CAT"
    assert results[0]["category_name"] == "Analgesics"

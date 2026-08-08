"""STEP 67 — Pharmacy module features: batches, prescriptions, expiry_alerts."""

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
from apps.pharmacy.services.rx_pos_service import RxPosService
from apps.platform.models import Tenant, TenantModule
from apps.platform.services.module_feature_service import ModuleFeatureService
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company


@pytest.fixture
def feat_env(db):
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(
        name="Feat Pharm", slug="feat-pharm", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Feat Pharm Co", tenant=tenant)
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
        sku="FEAT-PARA",
        name="Paracetamol",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("2"),
        requires_prescription=True,
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("0")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    BatchService.receive_stock(
        product=product,
        warehouse=warehouse,
        quantity=Decimal("20"),
        batch_number="FEAT-B1",
        expiry_date=date.today() + timedelta(days=10),
    )
    user = get_user_model().objects.create_user(
        username="feat_pharm_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    for code in ("pharmacy.view", "pharmacy.manage", "pharmacy.dispense"):
        perm = Permission.objects.filter(codename=code).first()
        if perm:
            UserPermission.objects.get_or_create(user=user, permission=perm)
    return {"tenant": tenant, "user": user, "product": product}


@pytest.mark.django_db
def test_sync_seeds_pharmacy_features(feat_env):
    link = TenantModule.active_objects().get(
        tenant=feat_env["tenant"], module__code="pharmacy"
    )
    features = (link.configuration or {}).get("features") or {}
    assert features.get("batches") is True
    assert features.get("prescriptions") is True
    assert features.get("expiry_alerts") is True
    resolved = ModuleFeatureService.resolve_features("pharmacy", user=feat_env["user"])
    assert resolved == {"batches": True, "prescriptions": True, "expiry_alerts": True}


@pytest.mark.django_db
def test_disable_prescriptions_blocks_rx_api(feat_env):
    ModuleFeatureService.set_features(
        tenant=feat_env["tenant"],
        module_code="pharmacy",
        features={"prescriptions": False},
        user=feat_env["user"],
    )
    assert (
        ModuleFeatureService.tenant_has_feature(
            "pharmacy", "prescriptions", user=feat_env["user"]
        )
        is False
    )
    client = APIClient()
    token = str(RefreshToken.for_user(feat_env["user"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/pharmacy/prescriptions/")
    assert response.status_code == 403
    body = response.json()
    assert body.get("code") == "MODULE_FEATURE_DISABLED"
    assert body.get("details", {}).get("feature") == "prescriptions"

    batches = client.get("/api/v1/pharmacy/batches/")
    assert batches.status_code == 200


@pytest.mark.django_db
def test_disable_batches_blocks_batches_and_expiry(feat_env):
    ModuleFeatureService.set_features(
        tenant=feat_env["tenant"],
        module_code="pharmacy",
        features={"batches": False, "expiry_alerts": True},
        user=feat_env["user"],
    )
    resolved = ModuleFeatureService.resolve_features("pharmacy", user=feat_env["user"])
    assert resolved["batches"] is False
    assert resolved["expiry_alerts"] is False
    client = APIClient()
    token = str(RefreshToken.for_user(feat_env["user"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert client.get("/api/v1/pharmacy/batches/").status_code == 403
    assert client.get("/api/v1/pharmacy/batches/expiring/").status_code == 403
    assert client.get("/api/v1/pharmacy/prescriptions/").status_code == 200


@pytest.mark.django_db
def test_rx_pos_gate_respects_prescriptions_feature(feat_env):
    user = feat_env["user"]
    product = feat_env["product"]
    assert RxPosService.pharmacy_gate_applies(user=user) is True
    ModuleFeatureService.set_features(
        tenant=feat_env["tenant"],
        module_code="pharmacy",
        features={"prescriptions": False},
        user=user,
    )
    assert RxPosService.pharmacy_gate_applies(user=user) is False
    # OTC-only cart still fine when gate off
    RxPosService.validate_cart(
        items=[{"product_id": str(product.id), "quantity": 1, "name": product.name}],
        user=user,
        profile={"code": "PHARMACY", "enabled_modules": ["pharmacy"]},
    )


@pytest.mark.django_db
def test_summary_includes_features(feat_env):
    client = APIClient()
    token = str(RefreshToken.for_user(feat_env["user"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/pharmacy/summary/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["features"]["batches"] is True
    assert data["features"]["prescriptions"] is True
    ModuleFeatureService.set_features(
        tenant=feat_env["tenant"],
        module_code="pharmacy",
        features={"expiry_alerts": False},
        user=feat_env["user"],
    )
    data2 = client.get("/api/v1/pharmacy/summary/").json()["data"]
    assert data2["features"]["expiry_alerts"] is False
    assert data2["expiring_count"] == 0

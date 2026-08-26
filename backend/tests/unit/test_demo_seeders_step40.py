"""PHASE 11 — gym/pharmacy demo seeders produce real rows."""

import pytest

from apps.gym.models import Attendance, Member, MembershipPlan, MembershipSubscription
from apps.pharmacy.models import Prescription, ProductBatch
from apps.platform.demo import generate_demo_data
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product


@pytest.fixture
def platform_ready(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()


@pytest.mark.django_db
def test_gym_demo_seeder_creates_members(platform_ready):
    tenant, report = DemoTenantService.create(
        data={
            "name": "Seed Gym Demo",
            "business_type_code": "gym",
            "preset_code": "gym",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    gym = report["results"]["gym"]
    assert gym.get("seeded") is True
    assert gym.get("members", 0) >= 5
    assert Member.active_objects().filter(tenant=tenant).count() >= 5
    assert MembershipPlan.active_objects().filter(tenant=tenant, code="demo_monthly").exists()
    assert (
        MembershipSubscription.active_objects()
        .filter(tenant=tenant, status=MembershipSubscription.STATUS_ACTIVE)
        .count()
        >= 5
    )
    assert Attendance.active_objects().filter(tenant=tenant).count() >= 3

    # Idempotent re-run
    again = generate_demo_data(tenant=tenant, modules=["gym"])
    assert again["results"]["gym"].get("idempotent") is True


@pytest.mark.django_db
def test_pharmacy_demo_seeder_creates_batches(platform_ready):
    tenant, report = DemoTenantService.create(
        data={
            "name": "Seed Pharm Demo",
            "business_type_code": "pharmacy",
            "preset_code": "pharmacy",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    ph = report["results"]["pharmacy"]
    assert ph.get("seeded") is True
    assert Product.active_objects().filter(tenant=tenant, sku__startswith="DEMO-RX-").count() >= 3
    assert ProductBatch.active_objects().filter(tenant=tenant).count() >= 4
    assert (ph.get("expired_count") or 0) >= 1
    assert (ph.get("expiring_count") or 0) >= 1
    assert Prescription.active_objects().filter(
        tenant=tenant, rx_number__startswith="DEMO-RX-"
    ).count() >= 2
    assert (ph.get("prescriptions") or 0) >= 2
    amox = Product.active_objects().get(tenant=tenant, sku="DEMO-RX-AMOX250")
    assert amox.requires_prescription is True
    assert amox.category.name == "Antibiotics"
    para = Product.active_objects().get(tenant=tenant, sku="DEMO-RX-PARA500")
    assert para.category.name == "Analgesics"
    assert Category.active_objects().filter(
        tenant=tenant, name__in=["Analgesics", "Antibiotics"]
    ).count() == 2
    assert Prescription.active_objects().filter(
        tenant=tenant, rx_number="DEMO-RX-003"
    ).exists()
    assert (
        Prescription.active_objects()
        .filter(tenant=tenant, rx_number="DEMO-RX-001", lines__product=amox)
        .exists()
    )

    again = generate_demo_data(tenant=tenant, modules=["pharmacy"])
    assert again["results"]["pharmacy"].get("idempotent") is True
    assert again["results"]["pharmacy"].get("prescriptions") >= 2


@pytest.mark.django_db
def test_gym_demo_also_seeds_pos_catalog(platform_ready):
    tenant, report = DemoTenantService.create(
        data={
            "name": "Seed Gym POS",
            "business_type_code": "gym",
            "preset_code": "gym",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    pos = report["results"].get("pos") or {}
    catalog = report["results"].get("catalog") or report["results"].get("inventory") or {}
    assert pos.get("seeded") is True
    assert catalog.get("seeded") is True
    assert Product.active_objects().filter(tenant=tenant, sku__startswith="DEMO-POS-").count() >= 4
    from apps.sales.models import Invoice

    assert Invoice.active_objects().filter(tenant=tenant, idempotency_key="demo-pos-seed-v1").exists()


@pytest.mark.django_db
def test_multi_module_demo_seeds_gym_and_restaurant(platform_ready):
    tenant, report = DemoTenantService.create(
        data={
            "name": "Kisima Multi",
            "slug": "demo-kisima-test",
            "business_type_code": "gym",
            "modules": ["gym", "restaurant", "pos", "inventory", "sales"],
            "duration_days": 14,
            "generate_data": True,
        }
    )
    assert report["results"]["gym"].get("seeded") is True
    assert report["results"]["restaurant"].get("seeded") is True
    assert report["results"]["pos"].get("seeded") is True
    from apps.gym.models import Member
    from apps.restaurant.models import MenuItem

    assert Member.active_objects().filter(tenant=tenant).count() >= 5
    assert MenuItem.active_objects().filter(tenant=tenant).count() >= 4
    from apps.platform.models import TenantDomain

    aliases = set(
        TenantDomain.active_objects().filter(tenant=tenant).values_list("subdomain", flat=True)
    )
    assert "kisima-test" in aliases

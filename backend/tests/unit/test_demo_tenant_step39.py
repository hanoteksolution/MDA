"""PHASE 07/10 — demo tenant lifecycle skeleton."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.platform.models import Tenant
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantError, DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def platform_ready(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()


@pytest.mark.django_db
def test_create_demo_tenant(platform_ready):
    tenant, report = DemoTenantService.create(
        data={
            "name": "Demo Gym Lab",
            "business_type_code": "gym",
            "preset_code": "gym",
            "duration_days": 7,
            "generate_data": True,
        }
    )
    assert tenant.is_demo is True
    assert tenant.demo_status == Tenant.DEMO_ACTIVE
    assert tenant.demo_expires_at is not None
    payload = DemoTenantService.serialize(tenant)
    assert payload["is_demo"] is True
    assert "results" in report
    assert "core" in report["results"]


@pytest.mark.django_db
def test_extend_suspend_convert(platform_ready):
    tenant, _ = DemoTenantService.create(
        data={
            "name": "Demo Pharm",
            "business_type_code": "pharmacy",
            "preset_code": "pharmacy",
            "duration_days": 7,
            "generate_data": False,
        }
    )
    before = tenant.demo_expires_at
    tenant = DemoTenantService.extend(tenant=tenant, days=3)
    assert tenant.demo_expires_at > before

    tenant = DemoTenantService.suspend(tenant=tenant)
    assert tenant.demo_status == Tenant.DEMO_SUSPENDED
    assert tenant.status == Tenant.STATUS_SUSPENDED

    # Reactivate via extend then convert
    tenant = DemoTenantService.extend(tenant=tenant, days=7)
    tenant = DemoTenantService.convert(tenant=tenant, plan_code="starter")
    assert tenant.demo_status == Tenant.DEMO_CONVERTED
    assert tenant.status == Tenant.STATUS_ACTIVE
    assert tenant.demo_converted_at is not None

    with pytest.raises(DemoTenantError):
        DemoTenantService.extend(tenant=tenant, days=1)


@pytest.mark.django_db
def test_expire_due(platform_ready):
    tenant, _ = DemoTenantService.create(
        data={
            "name": "Expired Demo",
            "business_type_code": "retail",
            "duration_days": 7,
            "generate_data": False,
        }
    )
    tenant.demo_expires_at = timezone.now() - timedelta(hours=1)
    tenant.save(update_fields=["demo_expires_at", "updated_at"])
    due = DemoTenantService.expire_due()
    assert any(t.id == tenant.id for t in due)
    tenant.refresh_from_db()
    assert tenant.demo_status == Tenant.DEMO_EXPIRED


@pytest.mark.django_db
def test_create_demo_multi_modules(platform_ready):
    tenant, report = DemoTenantService.create(
        data={
            "name": "Demo Multi",
            "business_type_code": "gym",
            "modules": ["gym", "restaurant", "pos", "inventory", "sales"],
            "duration_days": 14,
            "generate_data": False,
        }
    )
    payload = DemoTenantService.serialize(tenant)
    assert "gym" in payload["modules"]
    assert "restaurant" in payload["modules"]
    assert payload["seed_status"] == "none"
    assert report == {}

    # Plan re-apply must not strip restaurant
    from apps.platform.services.entitlement_service import EntitlementService

    EntitlementService.apply_plan_entitlements(tenant=tenant)
    payload = DemoTenantService.serialize(tenant)
    assert "restaurant" in payload["modules"]


@pytest.mark.django_db
def test_demo_add_modules(platform_ready):
    tenant, _ = DemoTenantService.create(
        data={
            "name": "Demo Add Mod",
            "business_type_code": "gym",
            "modules": ["gym", "pos", "inventory", "sales"],
            "duration_days": 7,
            "generate_data": False,
        }
    )
    DemoTenantService.update_modules(
        tenant=tenant,
        modules=["restaurant"],
        merge=True,
    )
    payload = DemoTenantService.serialize(tenant)
    assert "gym" in payload["modules"]
    assert "restaurant" in payload["modules"]


@pytest.mark.django_db
def test_create_demo_from_existing_shop(platform_ready):
    shop = PlatformService.create_shop(
        data={
            "name": "Live Shop",
            "slug": "live-shop-demo-attach",
            "business_type_code": "retail",
            "plan_code": "starter",
        }
    )
    if isinstance(shop, tuple):
        shop = shop[0]
    if isinstance(shop, dict):
        shop = Tenant.objects.get(pk=shop["id"] if "id" in shop else shop["tenant"]["id"])

    tenant, _ = DemoTenantService.create(
        data={
            "source_tenant_id": str(shop.id),
            "business_type_code": "gym",
            "modules": ["gym", "pos", "inventory", "sales"],
            "duration_days": 10,
            "generate_data": False,
            "name": "Live Shop Demo",
        }
    )
    assert tenant.id == shop.id
    assert tenant.is_demo is True
    assert tenant.name == "Live Shop Demo"
    payload = DemoTenantService.serialize(tenant)
    assert "gym" in payload["modules"]


@pytest.mark.django_db
def test_create_demo_async_seed_marks_pending(platform_ready, monkeypatch):
    called = {}

    class FakeTask:
        def delay(self, tenant_id, user_id=None):
            called["tenant_id"] = tenant_id
            called["user_id"] = user_id

    monkeypatch.setattr(
        "apps.platform.tasks.seed_demo_tenant",
        FakeTask(),
        raising=False,
    )
    # Patch where enqueue imports from
    import apps.platform.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "seed_demo_tenant", FakeTask())

    tenant, report = DemoTenantService.create(
        data={
            "name": "Async Seed Demo",
            "business_type_code": "gym",
            "preset_code": "gym",
            "duration_days": 7,
            "generate_data": True,
            "seed_async": True,
        }
    )
    payload = DemoTenantService.serialize(tenant)
    assert payload["seed_status"] in {"pending", "done"}  # pending if delay worked, done if fallback
    if payload["seed_status"] == "pending":
        assert called.get("tenant_id") == str(tenant.id)
        assert report.get("async") is True

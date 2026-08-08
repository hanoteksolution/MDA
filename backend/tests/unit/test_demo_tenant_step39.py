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

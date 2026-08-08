"""PHASE 03–06 — module metadata, dependencies, business presets."""

import pytest

from apps.platform.models import BusinessPreset, Module, Tenant, TenantModule
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.module_dependency_service import (
    ModuleDependencyError,
    ModuleDependencyService,
)
from apps.platform.services.module_service import (
    ensure_default_modules,
    sync_tenant_modules,
)
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def tenant_env(db):
    PlatformService.ensure_default_business_types()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    bt = PlatformService.resolve_business_type(code="pharmacy")
    tenant = Tenant.objects.create(
        name="City Pharmacy",
        slug="city-pharm-mod",
        status=Tenant.STATUS_ACTIVE,
        business_type=bt,
        is_active=True,
    )
    PlatformService.provision_tenant_defaults(tenant=tenant)
    return tenant


@pytest.mark.django_db
def test_module_seeds_include_dependencies():
    ensure_default_modules()
    ph = Module.active_objects().get(code="pharmacy")
    assert "inventory" in ph.dependencies
    assert "pos" in ph.dependencies
    assert ph.route == "/pharmacy"


@pytest.mark.django_db
def test_dependency_auto_expand():
    ensure_default_modules()
    expanded = ModuleDependencyService.validate_enable_set(["pharmacy"])
    assert {"pharmacy", "inventory", "pos"} <= expanded


@pytest.mark.django_db
def test_sync_enables_pharmacy_deps(tenant_env):
    sync_tenant_modules(
        tenant=tenant_env,
        enabled_codes=["pharmacy"],
        disable_missing=True,
        validate_dependencies=True,
    )
    enabled = set(
        TenantModule.active_objects()
        .filter(tenant=tenant_env, enabled=True)
        .values_list("module__code", flat=True)
    )
    assert {"pharmacy", "inventory", "pos"} <= enabled


@pytest.mark.django_db
def test_cannot_disable_required_dependency(tenant_env):
    sync_tenant_modules(
        tenant=tenant_env,
        enabled_codes=["pharmacy", "inventory", "pos"],
        disable_missing=True,
    )
    # Direct check: pharmacy without inventory is invalid
    with pytest.raises(ModuleDependencyError):
        ModuleDependencyService.validate_disable(enabled_after={"pharmacy", "pos"})
    # API sync auto-expands deps, so inventory stays on
    sync_tenant_modules(
        tenant=tenant_env,
        enabled_codes=["pharmacy", "pos"],
        disable_missing=True,
        validate_dependencies=True,
    )
    enabled = set(
        TenantModule.active_objects()
        .filter(tenant=tenant_env, enabled=True)
        .values_list("module__code", flat=True)
    )
    assert "inventory" in enabled


@pytest.mark.django_db
def test_presets_seeded_from_business_types():
    BusinessPresetService.ensure_default_presets()
    pharmacy = BusinessPreset.active_objects().get(code="pharmacy")
    codes = BusinessPresetService.module_codes(pharmacy)
    assert "pharmacy" in codes
    assert BusinessPreset.active_objects().filter(code="gym_cafeteria").exists()
    assert BusinessPreset.active_objects().filter(code="custom").exists()


@pytest.mark.django_db
def test_apply_preset_snapshots(tenant_env):
    preset = BusinessPresetService.resolve(code="gym")
    codes = BusinessPresetService.apply_to_tenant(tenant=tenant_env, preset=preset)
    assert "gym" in codes
    tenant_env.refresh_from_db()
    settings = tenant_env.settings
    assert settings.extras.get("preset_used_code") == "gym"

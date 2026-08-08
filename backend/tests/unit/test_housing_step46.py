"""PHASE 19 — housing rental leases on property core."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.housing_rental.models import Lease, LeaseCharge
from apps.housing_rental.services import HousingError, HousingService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.property_management.models import PropertyUnit
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def housing_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, report = DemoTenantService.create(
        data={
            "name": "Housing Demo",
            "business_type_code": "property",
            "preset_code": "property_residential",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_housing_demo_seeder(housing_env):
    tenant = housing_env["tenant"]
    report = housing_env["report"]["results"]
    assert report.get("property_management", {}).get("seeded") is True
    assert report.get("housing_rental", {}).get("seeded") is True
    assert Lease.active_objects().filter(tenant=tenant, status=Lease.STATUS_ACTIVE).exists()
    assert LeaseCharge.active_objects().filter(tenant=tenant).exists()


@pytest.mark.django_db
def test_activate_occupies_terminate_frees(housing_env):
    tenant = housing_env["tenant"]
    branch = housing_env["branch"]
    today = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        from apps.property_management.services import PropertyService

        building = PropertyService.list_buildings(branch_id=branch.id).first()
        assert building is not None
        unit = PropertyService.create_unit(
            data={
                "branch_id": branch.id,
                "building_id": building.id,
                "code": "T-VAC-1",
                "kind": "residential",
                "rent_amount": "300",
                "deposit_amount": "300",
            }
        )
        lease = HousingService.create_lease(
            data={
                "branch_id": branch.id,
                "unit_id": unit.id,
                "tenant_name": "Test Renter",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=30)).isoformat(),
            }
        )
        assert lease.status == Lease.STATUS_DRAFT
        HousingService.activate_lease(lease=lease)
        lease.refresh_from_db()
        unit.refresh_from_db()
        assert lease.status == Lease.STATUS_ACTIVE
        assert unit.status == PropertyUnit.STATUS_OCCUPIED
        assert lease.deposit_held is True

        HousingService.terminate_lease(lease=lease)
        lease.refresh_from_db()
        unit.refresh_from_db()
        assert lease.status == Lease.STATUS_TERMINATED
        assert unit.status == PropertyUnit.STATUS_VACANT


@pytest.mark.django_db
def test_double_active_lease_blocked(housing_env):
    tenant = housing_env["tenant"]
    branch = housing_env["branch"]
    today = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        active = Lease.active_objects().filter(
            tenant=tenant, status=Lease.STATUS_ACTIVE
        ).first()
        assert active is not None
        with pytest.raises(HousingError, match="already has an open lease"):
            HousingService.create_lease(
                data={
                    "branch_id": branch.id,
                    "unit_id": active.unit_id,
                    "tenant_name": "Second Renter",
                    "start_date": today.isoformat(),
                }
            )

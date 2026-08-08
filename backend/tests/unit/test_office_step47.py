"""PHASE 20 — office rental leases on property core."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.office_rental.models import OfficeLease, OfficeLeaseCharge
from apps.office_rental.services import OfficeError, OfficeService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.property_management.models import PropertyUnit
from apps.property_management.services import PropertyService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def office_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, report = DemoTenantService.create(
        data={
            "name": "Office Demo",
            "business_type_code": "property",
            "preset_code": "property_commercial",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_office_demo_seeder(office_env):
    tenant = office_env["tenant"]
    report = office_env["report"]["results"]
    assert report.get("property_management", {}).get("seeded") is True
    assert report.get("office_rental", {}).get("seeded") is True
    assert OfficeLease.active_objects().filter(
        tenant=tenant, status=OfficeLease.STATUS_ACTIVE
    ).exists()
    assert OfficeLeaseCharge.active_objects().filter(tenant=tenant).exists()


@pytest.mark.django_db
def test_activate_occupies_terminate_frees(office_env):
    tenant = office_env["tenant"]
    branch = office_env["branch"]
    today = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        building = PropertyService.list_buildings(branch_id=branch.id).first()
        assert building is not None
        unit = PropertyService.create_unit(
            data={
                "branch_id": branch.id,
                "building_id": building.id,
                "code": "O-VAC-1",
                "kind": "office",
                "rent_amount": "700",
                "deposit_amount": "1400",
            }
        )
        lease = OfficeService.create_lease(
            data={
                "branch_id": branch.id,
                "unit_id": unit.id,
                "company_name": "Test Co",
                "contact_name": "Alex",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=90)).isoformat(),
                "service_charge": Decimal("75"),
            }
        )
        assert lease.status == OfficeLease.STATUS_DRAFT
        OfficeService.activate_lease(lease=lease)
        lease.refresh_from_db()
        unit.refresh_from_db()
        assert lease.status == OfficeLease.STATUS_ACTIVE
        assert unit.status == PropertyUnit.STATUS_OCCUPIED
        assert lease.deposit_held is True
        assert lease.monthly_total == Decimal("775")

        OfficeService.terminate_lease(lease=lease)
        lease.refresh_from_db()
        unit.refresh_from_db()
        assert lease.status == OfficeLease.STATUS_TERMINATED
        assert unit.status == PropertyUnit.STATUS_VACANT


@pytest.mark.django_db
def test_rejects_residential_unit(office_env):
    tenant = office_env["tenant"]
    branch = office_env["branch"]
    today = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        unit = (
            PropertyUnit.active_objects()
            .filter(tenant=tenant, kind=PropertyUnit.KIND_RESIDENTIAL)
            .first()
        )
        assert unit is not None
        with pytest.raises(OfficeError, match="Housing units"):
            OfficeService.create_lease(
                data={
                    "branch_id": branch.id,
                    "unit_id": unit.id,
                    "company_name": "Wrong Kind",
                    "start_date": today.isoformat(),
                }
            )

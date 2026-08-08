"""PHASE 18 — property management shared core."""

import pytest

from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.property_management.models import MaintenanceRequest, PropertyAsset, PropertyUnit
from apps.property_management.services import PropertyService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def property_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, report = DemoTenantService.create(
        data={
            "name": "Property Demo",
            "business_type_code": "property",
            "preset_code": "property",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_property_demo_seeder(property_env):
    tenant = property_env["tenant"]
    report = property_env["report"]["results"]["property_management"]
    assert report.get("seeded") is True
    assert PropertyAsset.active_objects().filter(tenant=tenant).count() >= 1
    assert PropertyUnit.active_objects().filter(tenant=tenant).count() >= 4
    assert MaintenanceRequest.active_objects().filter(tenant=tenant).exists()


@pytest.mark.django_db
def test_maintenance_marks_unit_and_completes(property_env):
    tenant = property_env["tenant"]
    branch = property_env["branch"]
    with tenant_context(tenant, enforce=True):
        unit = (
            PropertyUnit.active_objects()
            .filter(tenant=tenant, status=PropertyUnit.STATUS_VACANT)
            .first()
        )
        assert unit is not None
        ticket = PropertyService.create_maintenance(
            data={
                "branch_id": branch.id,
                "unit_id": unit.id,
                "title": "Broken window",
                "priority": "high",
            }
        )
        unit.refresh_from_db()
        assert unit.status == PropertyUnit.STATUS_MAINTENANCE
        assert ticket.status == MaintenanceRequest.STATUS_OPEN

        PropertyService.update_maintenance_status(
            request_row=ticket, status=MaintenanceRequest.STATUS_DONE
        )
        unit.refresh_from_db()
        ticket.refresh_from_db()
        assert ticket.status == MaintenanceRequest.STATUS_DONE
        assert unit.status == PropertyUnit.STATUS_VACANT


@pytest.mark.django_db
def test_create_hierarchy(property_env):
    tenant = property_env["tenant"]
    branch = property_env["branch"]
    with tenant_context(tenant, enforce=True):
        prop = PropertyService.create_property(
            data={
                "branch_id": branch.id,
                "name": "Harbor Towers",
                "kind": "commercial",
            }
        )
        building = PropertyService.create_building(
            data={
                "branch_id": branch.id,
                "property_id": prop.id,
                "name": "Tower 1",
                "floors": 5,
            }
        )
        unit = PropertyService.create_unit(
            data={
                "branch_id": branch.id,
                "building_id": building.id,
                "code": "T1-501",
                "kind": "office",
                "rent_amount": "900",
            }
        )
        assert unit.building_id == building.id
        assert unit.status == PropertyUnit.STATUS_VACANT

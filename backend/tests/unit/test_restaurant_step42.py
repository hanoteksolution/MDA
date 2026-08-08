"""PHASE 15 — restaurant app skeleton."""

import pytest

from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.restaurant.models import DiningTable, MenuCategory, MenuItem, RestaurantOrder
from apps.restaurant.services import RestaurantService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def restaurant_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, report = DemoTenantService.create(
        data={
            "name": "Cafe Demo",
            "business_type_code": "restaurant",
            "preset_code": "restaurant",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_restaurant_demo_seeder(restaurant_env):
    tenant = restaurant_env["tenant"]
    report = restaurant_env["report"]["results"]["restaurant"]
    assert report.get("seeded") is True
    assert MenuCategory.active_objects().filter(tenant=tenant).count() >= 2
    assert MenuItem.active_objects().filter(tenant=tenant).count() >= 4
    assert DiningTable.active_objects().filter(tenant=tenant).count() >= 4
    assert RestaurantOrder.active_objects().filter(tenant=tenant).exists()


@pytest.mark.django_db
def test_create_order_occupies_table(restaurant_env):
    tenant = restaurant_env["tenant"]
    branch = restaurant_env["branch"]
    with tenant_context(tenant, enforce=True):
        table = DiningTable.active_objects().filter(tenant=tenant, status="free").first()
        item = MenuItem.active_objects().filter(tenant=tenant).first()
        assert table and item
        order = RestaurantService.create_order(
            data={
                "branch_id": branch.id,
                "table_id": table.id,
                "lines": [{"menu_item_id": item.id, "quantity": 1}],
            }
        )
        table.refresh_from_db()
        assert table.status == DiningTable.STATUS_OCCUPIED
        assert order.subtotal > 0
        RestaurantService.update_order_status(order=order, status=RestaurantOrder.STATUS_PAID)
        table.refresh_from_db()
        assert table.status == DiningTable.STATUS_FREE

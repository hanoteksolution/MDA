import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Permission, UserPermission
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.restaurant.models import DiningTable, MenuItem, RestaurantOrder
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


def _client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return c


@pytest.fixture
def rest_env(db):
    from django.contrib.auth import get_user_model
    from apps.authentication.models import Role

    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    bootstrap_roles_and_permissions()
    tenant, _ = DemoTenantService.create(
        data={
            "name": "Restaurant Workflow Demo",
            "business_type_code": "restaurant",
            "preset_code": "restaurant",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    User = get_user_model()
    waiter = User.objects.create_user(
        username="rest_waiter",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=Role.objects.filter(slug="waiter").first(),
    )
    # Explicitly grant new fine-grained order permissions to survive pre-existing seed data.
    for code in ("restaurant.orders.create", "restaurant.orders.update", "restaurant.orders.cancel"):
        perm = Permission.objects.get(codename=code)
        UserPermission.objects.get_or_create(user=waiter, permission=perm)
    return {"tenant": tenant, "branch": branch, "waiter": waiter}


@pytest.mark.django_db
def test_restaurant_order_transition_graph(rest_env):
    client = _client(rest_env["waiter"])
    with tenant_context(rest_env["tenant"], enforce=True):
        table = DiningTable.active_objects().filter(status=DiningTable.STATUS_FREE).first()
        item = MenuItem.active_objects().filter(is_available=True).first()
        assert table is not None and item is not None

    created = client.post(
        "/api/v1/restaurant/orders/",
        {
            "branch_id": str(rest_env["branch"].id),
            "table_id": str(table.id),
            "lines": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    order_id = created.json()["data"]["id"]

    assert client.post(f"/api/v1/restaurant/orders/{order_id}/submit/", {}, format="json").status_code == 200
    assert client.post(
        f"/api/v1/restaurant/orders/{order_id}/status/",
        {"status": "preparing"},
        format="json",
    ).status_code == 200
    assert client.post(
        f"/api/v1/restaurant/orders/{order_id}/status/",
        {"status": "ready"},
        format="json",
    ).status_code == 200
    assert client.post(
        f"/api/v1/restaurant/orders/{order_id}/status/",
        {"status": "served"},
        format="json",
    ).status_code == 200
    assert client.post(
        f"/api/v1/restaurant/orders/{order_id}/status/",
        {"status": "completed"},
        format="json",
    ).status_code == 200

    paid = client.post(
        f"/api/v1/restaurant/orders/{order_id}/status/",
        {"status": "paid"},
        format="json",
    )
    assert paid.status_code == 200, paid.content
    assert paid.json()["data"]["status"] == RestaurantOrder.STATUS_PAID


@pytest.mark.django_db
def test_cannot_create_order_on_occupied_table(rest_env):
    client = _client(rest_env["waiter"])
    with tenant_context(rest_env["tenant"], enforce=True):
        table = DiningTable.active_objects().filter(status=DiningTable.STATUS_FREE).first()
        item = MenuItem.active_objects().filter(is_available=True).first()
        assert table is not None and item is not None
        table.status = DiningTable.STATUS_OCCUPIED
        table.save(update_fields=["status", "updated_at"])

    blocked = client.post(
        "/api/v1/restaurant/orders/",
        {
            "branch_id": str(rest_env["branch"].id),
            "table_id": str(table.id),
            "lines": [{"menu_item_id": str(item.id), "quantity": 1}],
        },
        format="json",
    )
    assert blocked.status_code == 400
    assert "not available" in blocked.json()["message"].lower()

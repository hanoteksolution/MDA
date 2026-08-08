"""PHASE 13 — universal POS profile codes + restaurant pay-table bridge."""

from decimal import Decimal

import pytest

from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.restaurant.models import DiningTable, RestaurantOrder
from apps.restaurant.services import RestaurantService
from apps.sales.models import Invoice
from apps.sales.services.pos_profile import (
    get_pos_capabilities,
    resolve_pos_profile_code,
)
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.mark.django_db
@pytest.mark.parametrize(
    "modules,expected",
    [
        (["pos", "inventory", "sales"], "RETAIL"),
        (["restaurant", "pos"], "RESTAURANT"),
        (["pharmacy", "pos"], "PHARMACY"),
        (["gym", "pos"], "GYM"),
        (["restaurant", "pharmacy", "pos"], "RESTAURANT"),
    ],
)
def test_resolve_pos_profile_from_modules(modules, expected):
    assert resolve_pos_profile_code(enabled_modules=modules) == expected
    caps = get_pos_capabilities(enabled_modules=modules)
    assert caps["code"] == expected
    if expected == "RESTAURANT":
        assert caps["capabilities"]["tables"] is True
        assert caps["capabilities"]["kitchen_ticket"] is True


@pytest.mark.django_db
def test_explicit_profile_overrides_modules():
    assert (
        resolve_pos_profile_code(
            enabled_modules=["restaurant"], explicit_code="RETAIL"
        )
        == "RETAIL"
    )


@pytest.fixture
def restaurant_pos_env(db):
    from django.contrib.auth import get_user_model

    from apps.authentication.bootstrap import bootstrap_roles_and_permissions
    from apps.authentication.models import Role
    from apps.customers.models import Customer

    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    bootstrap_roles_and_permissions()
    tenant, _report = DemoTenantService.create(
        data={
            "name": "Pay Table Demo",
            "business_type_code": "restaurant",
            "preset_code": "restaurant",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    User = get_user_model()
    role = Role.objects.filter(slug="cashier").first() or Role.objects.first()
    user = User.objects.create_user(
        username="paytable_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=role,
    )
    with tenant_context(tenant, enforce=True):
        if not Customer.active_objects().filter(
            tenant=tenant, full_name__iexact="Walk-in Customer"
        ).exists():
            Customer.objects.create(
                tenant=tenant,
                customer_code="WALK",
                full_name="Walk-in Customer",
                branch=branch,
            )
    return {"tenant": tenant, "branch": branch, "user": user}


@pytest.mark.django_db
def test_pay_table_checkout_marks_order_paid_and_frees_table(restaurant_pos_env):
    tenant = restaurant_pos_env["tenant"]
    branch = restaurant_pos_env["branch"]
    user = restaurant_pos_env["user"]

    with tenant_context(tenant, enforce=True):
        order = (
            RestaurantOrder.active_objects()
            .filter(tenant=tenant)
            .exclude(status=RestaurantOrder.STATUS_PAID)
            .first()
        )
        assert order is not None
        table = order.table
        assert table is not None
        table.refresh_from_db()
        assert table.status == DiningTable.STATUS_OCCUPIED

        payload = RestaurantService.serialize_order_for_pos(order=order, user=user)
        items = [
            {
                "product_id": i["product_id"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
            }
            for i in payload["items"]
        ]
        assert items
        assert all(i["product_id"] for i in items)

        order.refresh_from_db()
        for line in order.lines.filter(deleted_at__isnull=True):
            assert line.product_id is not None
            line.menu_item.refresh_from_db()
            assert line.menu_item.product_id is not None

        result = PosService.checkout(
            data={
                "branch_id": str(branch.id),
                "customer_id": "walkin",
                "waiter_name": order.waiter_name or "Floor",
                "payment_method": "cash",
                "items": items,
                "restaurant_order_id": str(order.id),
                "idempotency_key": f"pay-table-{order.id}",
            },
            user=user,
        )

        assert result["invoice"]["status"] == Invoice.STATUS_PAID
        assert result["restaurant_order"]["status"] == RestaurantOrder.STATUS_PAID
        assert Decimal(str(result["invoice"]["total_amount"])) > 0

        order.refresh_from_db()
        table.refresh_from_db()
        assert order.status == RestaurantOrder.STATUS_PAID
        assert table.status == DiningTable.STATUS_FREE

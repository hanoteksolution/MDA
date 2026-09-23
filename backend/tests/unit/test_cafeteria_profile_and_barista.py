"""Cafeteria profile, barista queue, and recipe consumption tests."""

from decimal import Decimal

import pytest

from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product, Unit
from apps.restaurant.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    RestaurantOrder,
)
from apps.restaurant.services import (
    BaristaService,
    CafeteriaProfileService,
    RecipeConsumptionService,
    RestaurantService,
)
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def cafeteria_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, report = DemoTenantService.create(
        data={
            "name": "Cafeteria Demo",
            "business_type_code": "cafeteria",
            "preset_code": "cafeteria",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_cafeteria_profile_upsert(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        row = CafeteriaProfileService.upsert(
            data={
                "branch_id": str(branch.id),
                "business_name": "Safari Café",
                "order_prefix": "CF",
                "recipe_deduction_enabled": True,
            }
        )
        assert row.business_name == "Safari Café"
        again = CafeteriaProfileService.get_for_branch(branch_id=branch.id)
        assert again is not None
        assert again.id == row.id
        data = CafeteriaProfileService.serialize(again)
        assert data["order_prefix"] == "CF"
        assert data["recipe_deduction_enabled"] is True


@pytest.mark.django_db
def test_barista_queue_transitions(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        cat = RestaurantService.create_category(
            data={"branch_id": str(branch.id), "name": "Coffee Board"}
        )
        item = RestaurantService.create_item(
            data={
                "branch_id": str(branch.id),
                "category_id": str(cat.id),
                "name": "Flat White",
                "unit_price": "3.50",
            }
        )
        order = RestaurantService.create_order(
            data={
                "branch_id": str(branch.id),
                "service_type": "quick_sale",
                "lines": [{"menu_item_id": str(item.id), "quantity": 1}],
            }
        )
        RestaurantService.update_order_status(
            order=order, status=RestaurantOrder.STATUS_SUBMITTED
        )
        order.refresh_from_db()
        board = BaristaService.queue(branch_id=branch.id)
        assert any(t["id"] == str(order.id) for t in board["columns"]["NEW"])
        BaristaService.accept(order=order)
        order.refresh_from_db()
        assert order.status == RestaurantOrder.STATUS_PREPARING
        BaristaService.ready(order=order)
        order.refresh_from_db()
        assert order.status == RestaurantOrder.STATUS_READY


@pytest.mark.django_db
def test_recipe_consumption_deducts_stock(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        CafeteriaProfileService.upsert(
            data={
                "branch_id": str(branch.id),
                "business_name": "Beans & Brew",
                "recipe_deduction_enabled": True,
                "negative_stock_allowed": False,
            }
        )
        wh = (
            Warehouse.active_objects().filter(branch=branch, is_default=True).first()
            or Warehouse.active_objects().filter(branch=branch).first()
        )
        if not wh:
            wh = Warehouse.objects.create(
                name="Main",
                code="MAIN-CF",
                branch=branch,
                is_default=True,
                tenant_id=tenant.id,
            )
        category = Category.objects.create(name="Ingredients CF", tenant=tenant)
        unit = Unit.objects.create(name="Gram", abbreviation="g", tenant=tenant)
        product = Product.objects.create(
            name="Espresso Beans CF",
            sku="BEAN-CF-1",
            category=category,
            unit=unit,
            selling_price=Decimal("10"),
            cost_price=Decimal("5"),
            minimum_stock=0,
            tenant_id=tenant.id,
            module_code="restaurant",
        )
        inv = InventoryService.ensure_inventory_record(product=product, warehouse=wh)
        inv.quantity = Decimal("1000")
        inv.save(update_fields=["quantity"])

        cat = RestaurantService.create_category(
            data={"branch_id": str(branch.id), "name": "Espresso Cat"}
        )
        item = RestaurantService.create_item(
            data={
                "branch_id": str(branch.id),
                "category_id": str(cat.id),
                "name": "Espresso Shot",
                "unit_price": "2.50",
            }
        )
        ingredient = Ingredient.objects.create(
            tenant_id=tenant.id,
            branch=branch,
            product=product,
            name="Espresso Beans",
            code="BEAN-CF",
            unit="g",
            unit_cost=Decimal("0.05"),
            conversion_rate=Decimal("1"),
        )
        recipe = Recipe.objects.create(
            tenant_id=tenant.id,
            branch=branch,
            menu_item=item,
            name="Espresso shot",
            version="v1",
            status=Recipe.STATUS_ACTIVE,
            yield_qty=Decimal("1"),
        )
        RecipeIngredient.objects.create(
            tenant_id=tenant.id,
            recipe=recipe,
            ingredient=ingredient,
            quantity=Decimal("18"),
            unit="g",
            unit_cost=Decimal("0.05"),
        )
        order = RestaurantService.create_order(
            data={
                "branch_id": str(branch.id),
                "service_type": "quick_sale",
                "lines": [{"menu_item_id": str(item.id), "quantity": 2}],
            }
        )
        result = RecipeConsumptionService.consume_order_recipes(
            order=order, warehouse=wh
        )
        assert result["skipped"] is False
        inv.refresh_from_db()
        assert inv.quantity == Decimal("964")

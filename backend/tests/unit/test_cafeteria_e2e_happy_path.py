"""Cafeteria E2E happy path — profile → menu → order → promo → barista → paid."""

from decimal import Decimal

import pytest

from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.restaurant.models import MenuItemVariant, Modifier, ModifierGroup, RestaurantOrder
from apps.restaurant.services import (
    BaristaService,
    CafeteriaProfileService,
    CommerceService,
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
            "name": "Cafe E2E",
            "business_type_code": "cafeteria",
            "preset_code": "cafeteria",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_cafeteria_e2e_happy_path(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]

    with tenant_context(tenant, enforce=True):
        # 1) Settings profile
        profile = CafeteriaProfileService.upsert(
            data={
                "branch_id": str(branch.id),
                "business_name": "Live Café",
                "tips_enabled": True,
                "service_charge_enabled": True,
                "loyalty_enabled": True,
                "recipe_deduction_enabled": True,
            }
        )
        assert profile.business_name == "Live Café"

        # 2) Menu + variant + modifier
        cat = RestaurantService.create_category(
            data={"branch_id": str(branch.id), "name": "Coffee"}
        )
        item = RestaurantService.create_item(
            data={
                "branch_id": str(branch.id),
                "category_id": str(cat.id),
                "name": "Flat White",
                "unit_price": "4.00",
                "is_available": True,
            }
        )
        RestaurantService.ensure_menu_item_product(item=item)
        item.refresh_from_db()
        variant = MenuItemVariant.objects.create(
            tenant_id=tenant.id,
            menu_item=item,
            name="Large",
            price_adjustment=Decimal("1.00"),
            is_available=True,
        )
        group = ModifierGroup.objects.create(
            tenant_id=tenant.id,
            branch=branch,
            name="Extras",
            code="extras",
            min_select=0,
            max_select=2,
        )
        mod = Modifier.objects.create(
            tenant_id=tenant.id,
            branch=branch,
            group=group,
            name="Extra shot",
            code="shot",
            price_delta=Decimal("0.50"),
        )
        CommerceService.link_modifier_group(
            menu_item_id=item.id, modifier_group_id=group.id
        )
        customize = RestaurantService.get_item_customize_payload(product_id=item.product_id)
        assert customize["menu_item"] is not None
        assert len(customize["variants"]) >= 1
        assert len(customize["modifier_groups"]) >= 1

        # 3) Commerce: promo + combo + loyalty
        promo = CommerceService.create_promotion(
            data={
                "branch_id": str(branch.id),
                "name": "Cafe 10",
                "code": "CAFE10",
                "coupon_code": "CAFE10",
                "promotion_type": "percent",
                "percent_off": "10",
            }
        )
        cookie = RestaurantService.create_item(
            data={
                "branch_id": str(branch.id),
                "category_id": str(cat.id),
                "name": "Cookie",
                "unit_price": "1.50",
            }
        )
        combo = CommerceService.create_combo(
            data={
                "branch_id": str(branch.id),
                "name": "Coffee Combo",
                "code": "CF-CMB",
                "combo_price": "5.00",
                "items": [
                    {"menu_item_id": str(item.id), "quantity": 1},
                    {"menu_item_id": str(cookie.id), "quantity": 1},
                ],
            }
        )
        assert combo.items.count() == 2
        CommerceService.update_combo(
            combo=combo, data={"combo_price": "4.75", "is_active": True}
        )
        combo.refresh_from_db()
        assert Decimal(str(combo.combo_price)) == Decimal("4.75")

        program = CommerceService.get_or_create_program(branch_id=branch.id)
        CommerceService.update_loyalty_program(
            program=program, data={"points_per_currency": "2"}
        )
        program.refresh_from_db()
        assert Decimal(str(program.points_per_currency)) == Decimal("2")

        # 4) Order with modifiers + tip/service
        order = RestaurantService.create_order(
            data={"branch_id": str(branch.id), "service_type": "takeaway"}
        )
        line = RestaurantService.add_line(
            order=order,
            data={
                "menu_item_id": str(item.id),
                "quantity": 1,
                "variant_id": str(variant.id),
                "modifiers": [{"modifier_id": str(mod.id)}],
            },
        )
        assert Decimal(str(line.unit_price)) == Decimal("5.50")  # 4 + 1 + 0.5
        order = RestaurantService.update_order_charges(
            order=order, tip_amount="1.00", service_charge_amount="0.25"
        )
        RestaurantService.update_order_status(
            order=order, status=RestaurantOrder.STATUS_SUBMITTED
        )
        order.refresh_from_db()

        # 5) Promo resolve
        resolved, discount = CommerceService.resolve_active_promotion(
            code="CAFE10",
            branch_id=branch.id,
            amount=order.subtotal,
        )
        assert resolved is not None and resolved.id == promo.id
        assert discount == (Decimal(str(order.subtotal)) * Decimal("0.10")).quantize(
            Decimal("0.01")
        )

        # 6) Barista queue transitions
        BaristaService.accept(order=order)
        order.refresh_from_db()
        assert order.status == RestaurantOrder.STATUS_PREPARING
        BaristaService.ready(order=order)
        order.refresh_from_db()
        assert order.status == RestaurantOrder.STATUS_READY
        BaristaService.complete(order=order)
        order.refresh_from_db()
        assert order.status == RestaurantOrder.STATUS_SERVED

        # 7) Mark paid (recipe + tip/service posting best-effort)
        order = RestaurantService.update_order_status(
            order=order, status=RestaurantOrder.STATUS_PAID
        )
        assert order.status == RestaurantOrder.STATUS_PAID
        assert order.closed_at is not None

        # 8) Archive promo
        from apps.restaurant.services.commerce_service import CommerceError

        CommerceService.archive_promotion(promotion=promo)
        with pytest.raises(CommerceError):
            CommerceService.resolve_active_promotion(
                code="CAFE10", branch_id=branch.id, amount=Decimal("10")
            )

"""Cafeteria production paths: modifiers, tips, waste, commerce."""

from decimal import Decimal

import pytest

from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product, Unit
from apps.restaurant.models import (
    MenuItemVariant,
    Modifier,
    ModifierGroup,
    OrderLineModifier,
    RestaurantOrder,
)
from apps.restaurant.services import (
    CommerceService,
    RestaurantService,
    WasteService,
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
            "name": "Cafeteria Live",
            "business_type_code": "cafeteria",
            "preset_code": "cafeteria",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


def _menu_item(branch, name="Latte", price="4.50"):
    cat = RestaurantService.create_category(
        data={"branch_id": str(branch.id), "name": f"Cat-{name}"}
    )
    return RestaurantService.create_item(
        data={
            "branch_id": str(branch.id),
            "category_id": str(cat.id),
            "name": name,
            "unit_price": price,
            "is_available": True,
        }
    )


@pytest.mark.django_db
def test_order_line_variant_and_modifiers(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        item = _menu_item(branch, "Cappuccino", "5.00")
        variant = MenuItemVariant.objects.create(
            tenant_id=tenant.id,
            menu_item=item,
            name="Large",
            price_adjustment=Decimal("1.50"),
            is_available=True,
        )
        group = ModifierGroup.objects.create(
            tenant_id=tenant.id,
            branch=branch,
            name="Milk",
            code="milk",
            min_select=0,
            max_select=2,
        )
        oat = Modifier.objects.create(
            tenant_id=tenant.id,
            branch=branch,
            group=group,
            name="Oat milk",
            code="oat",
            price_delta=Decimal("0.75"),
        )
        order = RestaurantService.create_order(
            data={"branch_id": str(branch.id), "service_type": "takeaway"},
        )
        line = RestaurantService.add_line(
            order=order,
            data={
                "menu_item_id": str(item.id),
                "quantity": 1,
                "variant_id": str(variant.id),
                "modifiers": [{"modifier_id": str(oat.id), "quantity": 1}],
            },
        )
        assert line.variant_id == variant.id
        assert Decimal(str(line.unit_price)) == Decimal("7.25")  # 5 + 1.5 + 0.75
        assert OrderLineModifier.objects.filter(order_line=line).count() == 1
        payload = RestaurantService.get_item_customize_payload(product_id=item.product_id)
        # product may be none until ensure — still returns structure
        assert "variants" in payload
        assert "modifier_groups" in payload


@pytest.mark.django_db
def test_order_charges_and_paid_status(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        item = _menu_item(branch, "Espresso", "3.00")
        order = RestaurantService.create_order(
            data={
                "branch_id": str(branch.id),
                "lines": [{"menu_item_id": str(item.id), "quantity": 1}],
            }
        )
        order = RestaurantService.update_order_charges(
            order=order, tip_amount="1.25", service_charge_amount="0.50"
        )
        assert Decimal(str(order.tip_amount)) == Decimal("1.25")
        assert Decimal(str(order.service_charge_amount)) == Decimal("0.50")
        order = RestaurantService.update_order_status(
            order=order, status=RestaurantOrder.STATUS_PAID
        )
        assert order.status == RestaurantOrder.STATUS_PAID
        assert order.closed_at is not None


@pytest.mark.django_db
def test_waste_create_and_approve(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        unit = Unit.active_objects().filter(tenant=tenant).first()
        if unit is None:
            unit = Unit.objects.create(tenant_id=tenant.id, name="Unit", code="u", abbreviation="u")
        cat = Category.active_objects().filter(tenant=tenant).first()
        if cat is None:
            cat = Category.objects.create(tenant_id=tenant.id, name="Ing", is_active=True)
        product = Product.objects.create(
            tenant_id=tenant.id,
            category=cat,
            unit=unit,
            name="Milk",
            sku="MILK-W",
            selling_price=Decimal("1"),
            cost_price=Decimal("0.5"),
            is_active=True,
        )
        waste = WasteService.create(
            data={
                "branch_id": str(branch.id),
                "product_id": str(product.id),
                "quantity": "2",
                "unit_cost": "0.5",
                "reason": "Spill",
                "waste_type": "spoilage",
            }
        )
        assert waste.approval_status == waste.APPROVAL_DRAFT
        approved = WasteService.approve(waste=waste)
        assert approved.approval_status == waste.APPROVAL_APPROVED
        assert approved.inventory_adjustment_id is not None


@pytest.mark.django_db
def test_commerce_combo_promo_loyalty(cafeteria_env):
    tenant = cafeteria_env["tenant"]
    branch = cafeteria_env["branch"]
    with tenant_context(tenant, enforce=True):
        a = _menu_item(branch, "Tea", "2.00")
        b = _menu_item(branch, "Cookie", "1.50")
        combo = CommerceService.create_combo(
            data={
                "branch_id": str(branch.id),
                "name": "Tea + Cookie",
                "code": "TEA-CK",
                "combo_price": "3.00",
                "items": [
                    {"menu_item_id": str(a.id), "quantity": 1},
                    {"menu_item_id": str(b.id), "quantity": 1},
                ],
            }
        )
        assert combo.name == "Tea + Cookie"
        assert combo.items.count() == 2

        promo = CommerceService.create_promotion(
            data={
                "branch_id": str(branch.id),
                "name": "10% off",
                "code": "TEN",
                "promotion_type": "percent",
                "percent_off": "10",
            }
        )
        discount = CommerceService.apply_promotion_discount(
            amount=Decimal("50"), promotion=promo
        )
        assert discount == Decimal("5.00")

        resolved, resolved_amt = CommerceService.resolve_active_promotion(
            code="TEN", branch_id=branch.id, amount=Decimal("50")
        )
        assert resolved is not None
        assert resolved_amt == Decimal("5.00")
        CommerceService.update_promotion(
            promotion=promo, data={"is_active": False}
        )
        CommerceService.archive_promotion(promotion=promo)

        program = CommerceService.get_or_create_program(branch_id=branch.id)
        assert program.tiers.count() >= 1
        from apps.customers.models import Customer

        customer = Customer.objects.create(
            tenant_id=tenant.id,
            customer_code="CG-001",
            full_name="Cafe Guest",
            phone="100",
            is_active=True,
        )
        member = CommerceService.enroll_member(
            program_id=program.id, customer_id=customer.id
        )
        CommerceService.earn_points(member=member, spend_amount=Decimal("20"))
        member.refresh_from_db()
        assert Decimal(str(member.points_balance)) > 0

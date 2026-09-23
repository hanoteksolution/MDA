"""Recipe → inventory consumption adapter (shared Inventory engine)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.audit.services import write_audit
from apps.inventory.services.inventory_service import InventoryService
from apps.restaurant.models import CafeteriaProfile, Recipe, RestaurantOrder
from apps.restaurant.services.cafeteria_profile_service import CafeteriaProfileService


class RecipeConsumptionError(ValueError):
    pass


class RecipeConsumptionService:
    @staticmethod
    def _active_recipe(*, menu_item_id, variant_id=None, user=None, request=None):
        qs = Recipe.active_objects().filter(
            menu_item_id=menu_item_id,
            status=Recipe.STATUS_ACTIVE,
            deleted_at__isnull=True,
        )
        from core.tenancy import apply_tenant_scope

        qs = apply_tenant_scope(qs, user=user, request=request)
        # Variant-specific recipes land in a later migration; active item recipe for now.
        return qs.order_by("-created_at").first()

    @staticmethod
    @transaction.atomic
    def consume_order_recipes(
        *,
        order: RestaurantOrder,
        warehouse=None,
        user=None,
        request=None,
    ) -> dict:
        profile = CafeteriaProfileService.get_for_branch(
            branch_id=order.branch_id, user=user, request=request
        )
        if profile and not profile.recipe_deduction_enabled:
            return {"skipped": True, "reason": "recipe_deduction_disabled", "movements": []}

        wh = warehouse
        if wh is None and profile and profile.default_warehouse_id:
            wh = profile.default_warehouse
        if wh is None:
            wh = InventoryService.resolve_warehouse_for_branch(branch=order.branch)
        if wh is None:
            raise RecipeConsumptionError("No warehouse available for recipe deduction.")

        allow_negative = bool(profile.negative_stock_allowed) if profile else False
        movements = []
        lines = order.lines.filter(deleted_at__isnull=True).exclude(
            status=order.lines.model.STATUS_CANCELLED
        )

        for line in lines.select_related("menu_item", "variant"):
            recipe = RecipeConsumptionService._active_recipe(
                menu_item_id=line.menu_item_id,
                variant_id=line.variant_id,
                user=user,
                request=request,
            )
            if not recipe:
                continue
            multiplier = Decimal("1")
            if line.variant_id and line.variant_id:
                multiplier = Decimal(str(line.variant.recipe_qty_multiplier or 1))
            sell_qty = Decimal(str(line.quantity or 0)) * multiplier

            for ri in recipe.ingredients.filter(deleted_at__isnull=True).select_related(
                "ingredient", "ingredient__product"
            ):
                ingredient = ri.ingredient
                if not ingredient or not ingredient.product_id:
                    continue
                qty = Decimal(str(ri.quantity or 0)) * sell_qty
                if recipe.waste_percent:
                    qty *= Decimal("1") + (
                        Decimal(str(recipe.waste_percent)) / Decimal("100")
                    )
                # Normalize purchase-unit stock if conversion_rate set on ingredient.
                rate = Decimal(str(ingredient.conversion_rate or 1)) or Decimal("1")
                stock_qty = qty / rate if rate != 1 else qty
                if stock_qty <= 0:
                    continue

                if not allow_negative:
                    inv = InventoryService.ensure_inventory_record(
                        product=ingredient.product, warehouse=wh, user=user
                    )
                    if Decimal(str(inv.quantity or 0)) < stock_qty:
                        raise RecipeConsumptionError(
                            f"Insufficient stock for {ingredient.name}: "
                            f"need {stock_qty}, have {inv.quantity}."
                        )

                InventoryService.apply_sale_delta(
                    product=ingredient.product,
                    warehouse=wh,
                    quantity_delta=-stock_qty,
                    reference_id=order.id,
                    reference_type="restaurant_order",
                    user=user,
                    notes=f"Recipe consume {recipe.name} / {line.name}",
                )
                movements.append(
                    {
                        "ingredient_id": str(ingredient.id),
                        "product_id": str(ingredient.product_id),
                        "quantity": float(stock_qty),
                        "line_id": str(line.id),
                        "recipe_id": str(recipe.id),
                    }
                )

        write_audit(
            action="update",
            module="restaurant",
            entity=order,
            user=user,
            request=request,
            new_values={"recipe_consumption": movements},
        )
        return {"skipped": False, "movements": movements}

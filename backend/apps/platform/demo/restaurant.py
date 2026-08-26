"""Restaurant demo seeder — menu, tables, sample open order."""

from __future__ import annotations

from decimal import Decimal

from apps.restaurant.models import DiningTable, MenuCategory, MenuItem
from apps.restaurant.services import RestaurantService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


def seed(*, tenant, user=None) -> dict:
    with tenant_context(tenant, enforce=True):
        branch = (
            Branch.active_objects()
            .filter(tenant=tenant, is_default=True)
            .first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        if branch is None:
            return {"restaurant": {"seeded": False, "reason": "no branch"}}

        drinks = MenuCategory.active_objects().filter(tenant=tenant, name="Demo Drinks").first()
        mains = MenuCategory.active_objects().filter(tenant=tenant, name="Demo Mains").first()
        if drinks is None:
            drinks = RestaurantService.create_category(
                data={"name": "Demo Drinks", "branch_id": branch.id, "sort_order": 10},
                user=user,
            )
        if mains is None:
            mains = RestaurantService.create_category(
                data={"name": "Demo Mains", "branch_id": branch.id, "sort_order": 20},
                user=user,
            )

        items = []
        for spec in (
            {"category_id": drinks.id, "name": "Fresh Juice", "unit_price": "2.50", "sku": "DEMO-JUICE"},
            {"category_id": drinks.id, "name": "Soda", "unit_price": "1.50", "sku": "DEMO-SODA"},
            {"category_id": mains.id, "name": "Grilled Chicken", "unit_price": "8.00", "sku": "DEMO-CHKN"},
            {"category_id": mains.id, "name": "Veggie Pasta", "unit_price": "6.50", "sku": "DEMO-PASTA"},
        ):
            item = MenuItem.active_objects().filter(tenant=tenant, sku=spec["sku"]).first()
            if item is None:
                item = RestaurantService.create_item(
                    data={**spec, "branch_id": branch.id},
                    user=user,
                )
            items.append(item)

        # Materialize Product rows so Restaurant POS/products stay module-scoped.
        from decimal import Decimal as D

        from apps.inventory.models import Warehouse
        from apps.inventory.services.inventory_service import InventoryService

        warehouse = (
            Warehouse.active_objects().filter(tenant=tenant, branch=branch, is_default=True).first()
            or Warehouse.active_objects().filter(tenant=tenant, branch=branch).first()
            or Warehouse.active_objects().filter(tenant=tenant).first()
        )
        for item in items:
            RestaurantService.ensure_menu_item_product(item=item, user=user)
            if warehouse and item.product_id:
                inv = InventoryService.ensure_inventory_record(
                    product=item.product, warehouse=warehouse, user=user
                )
                if inv.quantity == 0:
                    inv.quantity = D("30")
                    inv.save(update_fields=["quantity", "updated_at"])

        tables = []
        for code in ("T1", "T2", "T3", "T4"):
            table = DiningTable.active_objects().filter(
                tenant=tenant, branch=branch, code=code
            ).first()
            if table is None:
                table = RestaurantService.create_table(
                    data={
                        "branch_id": branch.id,
                        "code": code,
                        "label": f"Table {code[1:]}",
                        "capacity": 4,
                    },
                    user=user,
                )
            tables.append(table)

        from apps.restaurant.models import RestaurantOrder

        existing_order = RestaurantOrder.active_objects().filter(
            tenant=tenant, waiter_name="Demo Waiter"
        ).first()
        if existing_order is None and items and tables:
            order = RestaurantService.create_order(
                data={
                    "branch_id": branch.id,
                    "table_id": tables[0].id,
                    "waiter_name": "Demo Waiter",
                    "guest_count": 2,
                    "lines": [
                        {"menu_item_id": items[0].id, "quantity": 2},
                        {"menu_item_id": items[2].id, "quantity": 1},
                    ],
                },
                user=user,
            )
            RestaurantService.update_order_status(
                order=order, status=order.STATUS_SENT, user=user
            )
            open_order = order.order_number
            orders = 1
        else:
            open_order = existing_order.order_number if existing_order else None
            orders = 1 if existing_order else 0

        return {
            "restaurant": {
                "seeded": True,
                "categories": 2,
                "menu_items": len(items),
                "tables": len(tables),
                "orders": orders,
                "open_order": open_order,
            }
        }

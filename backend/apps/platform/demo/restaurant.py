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

        existing = MenuCategory.active_objects().filter(
            tenant=tenant, name="Demo Mains"
        ).count()
        if existing:
            return {
                "restaurant": {
                    "seeded": True,
                    "idempotent": True,
                    "categories": MenuCategory.active_objects().filter(tenant=tenant).count(),
                    "tables": DiningTable.active_objects().filter(tenant=tenant).count(),
                }
            }

        drinks = RestaurantService.create_category(
            data={"name": "Demo Drinks", "branch_id": branch.id, "sort_order": 10},
            user=user,
        )
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
            items.append(
                RestaurantService.create_item(
                    data={**spec, "branch_id": branch.id},
                    user=user,
                )
            )

        tables = []
        for code in ("T1", "T2", "T3", "T4"):
            tables.append(
                RestaurantService.create_table(
                    data={
                        "branch_id": branch.id,
                        "code": code,
                        "label": f"Table {code[1:]}",
                        "capacity": 4,
                    },
                    user=user,
                )
            )

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

        return {
            "restaurant": {
                "seeded": True,
                "categories": 2,
                "menu_items": len(items),
                "tables": len(tables),
                "orders": 1,
                "open_order": order.order_number,
            }
        }

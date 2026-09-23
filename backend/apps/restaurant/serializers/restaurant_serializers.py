def serialize_category(row) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "code": getattr(row, "code", "") or "",
        "description": getattr(row, "description", "") or "",
        "image_url": getattr(row, "image_url", "") or "",
        "color_accent": getattr(row, "color_accent", "") or "",
        "parent_id": str(row.parent_id) if getattr(row, "parent_id", None) else None,
        "kitchen_station_id": str(row.kitchen_station_id)
        if getattr(row, "kitchen_station_id", None)
        else None,
        "tax_group": getattr(row, "tax_group", "") or "",
        "pos_visible": getattr(row, "pos_visible", True),
        "mobile_visible": getattr(row, "mobile_visible", True),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "sort_order": row.sort_order,
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_item(row) -> dict:
    return {
        "id": str(row.id),
        "category_id": str(row.category_id),
        "category_name": row.category.name if row.category_id else "",
        "branch_id": str(row.branch_id),
        "product_id": str(row.product_id) if row.product_id else None,
        "kitchen_station_id": str(row.kitchen_station_id)
        if getattr(row, "kitchen_station_id", None)
        else None,
        "name": row.name,
        "sku": row.sku or "",
        "description": row.description or "",
        "unit_price": float(row.unit_price or 0),
        "base_cost": float(getattr(row, "base_cost", 0) or 0),
        "preparation_time_minutes": getattr(row, "preparation_time_minutes", 5) or 5,
        "is_available": row.is_available,
        "is_featured": getattr(row, "is_featured", False),
        "is_popular": getattr(row, "is_popular", False),
        "pos_visible": getattr(row, "pos_visible", True),
        "mobile_visible": getattr(row, "mobile_visible", True),
        "track_inventory": getattr(row, "track_inventory", True),
        "allow_modifiers": getattr(row, "allow_modifiers", True),
        "allow_notes": getattr(row, "allow_notes", True),
        "available_dine_in": getattr(row, "available_dine_in", True),
        "available_takeaway": getattr(row, "available_takeaway", True),
        "available_delivery": getattr(row, "available_delivery", False),
        "coffee_attrs": getattr(row, "coffee_attrs", None) or {},
        "sort_order": row.sort_order,
    }


def serialize_variant(row) -> dict:
    return {
        "id": str(row.id),
        "menu_item_id": str(row.menu_item_id),
        "name": row.name,
        "sku": row.sku or "",
        "barcode": row.barcode or "",
        "price_adjustment": float(row.price_adjustment or 0),
        "final_price": float(row.final_price),
        "recipe_qty_multiplier": float(row.recipe_qty_multiplier or 1),
        "is_default": row.is_default,
        "is_available": row.is_available,
        "sort_order": row.sort_order,
    }


def serialize_table(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "code": row.code,
        "label": row.label or row.code,
        "capacity": row.capacity,
        "status": row.status,
        "is_active": row.is_active,
        "notes": row.notes or "",
        "floor_id": str(row.floor_id) if row.floor_id else None,
    }


def serialize_line(row) -> dict:
    mods = []
    if hasattr(row, "modifiers"):
        mods = [
            {
                "id": str(m.id),
                "modifier_id": str(m.modifier_id) if m.modifier_id else None,
                "name": m.name,
                "price_delta": float(m.price_delta or 0),
                "quantity": float(m.quantity or 1),
            }
            for m in row.modifiers.filter(deleted_at__isnull=True)
        ]
    return {
        "id": str(row.id),
        "menu_item_id": str(row.menu_item_id),
        "variant_id": str(row.variant_id) if getattr(row, "variant_id", None) else None,
        "kitchen_station_id": str(row.kitchen_station_id)
        if getattr(row, "kitchen_station_id", None)
        else None,
        "product_id": str(row.product_id) if row.product_id else None,
        "name": row.name,
        "quantity": float(row.quantity or 0),
        "unit_price": float(row.unit_price or 0),
        "line_total": float(row.line_total or 0),
        "status": row.status,
        "notes": row.notes or "",
        "modifiers": mods,
    }


def serialize_order(row, *, include_lines=True) -> dict:
    data = {
        "id": str(row.id),
        "order_number": row.order_number,
        "queue_number": getattr(row, "queue_number", "") or "",
        "priority": getattr(row, "priority", "normal") or "normal",
        "branch_id": str(row.branch_id),
        "table_id": str(row.table_id) if row.table_id else None,
        "table_code": row.table.code if row.table_id else None,
        "status": row.status,
        "service_type": row.service_type,
        "waiter_user_id": str(row.waiter_user_id) if row.waiter_user_id else None,
        "waiter_name": row.waiter_name or "",
        "barista_user_id": str(row.barista_user_id)
        if getattr(row, "barista_user_id", None)
        else None,
        "guest_count": row.guest_count,
        "subtotal": float(row.subtotal or 0),
        "tip_amount": float(getattr(row, "tip_amount", 0) or 0),
        "service_charge_amount": float(getattr(row, "service_charge_amount", 0) or 0),
        "notes": row.notes or "",
        "opened_at": row.opened_at.isoformat() if row.opened_at else None,
        "accepted_at": row.accepted_at.isoformat()
        if getattr(row, "accepted_at", None)
        else None,
        "ready_at": row.ready_at.isoformat() if getattr(row, "ready_at", None) else None,
        "served_at": row.served_at.isoformat()
        if getattr(row, "served_at", None)
        else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
    }
    if include_lines:
        lines = list(
            row.lines.filter(deleted_at__isnull=True).prefetch_related("modifiers")
        )
        data["lines"] = [serialize_line(l) for l in lines]
        data["line_count"] = len(lines)
    return data


def serialize_floor(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "name": row.name,
        "code": row.code,
        "sort_order": row.sort_order,
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_station(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "name": row.name,
        "code": row.code,
        "station_type": getattr(row, "station_type", "kitchen") or "kitchen",
        "sort_order": row.sort_order,
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_modifier_group(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "name": row.name,
        "code": row.code,
        "required": row.required,
        "min_select": row.min_select,
        "max_select": row.max_select,
        "sort_order": row.sort_order,
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_modifier(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "group_id": str(row.group_id),
        "group_name": row.group.name if row.group_id else "",
        "name": row.name,
        "code": row.code,
        "price_delta": float(row.price_delta or 0),
        "sort_order": row.sort_order,
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_ingredient(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "product_id": str(row.product_id) if row.product_id else None,
        "name": row.name,
        "code": row.code,
        "unit": row.unit,
        "purchase_unit": getattr(row, "purchase_unit", "") or "",
        "consumption_unit": getattr(row, "consumption_unit", "") or "",
        "conversion_rate": float(getattr(row, "conversion_rate", 1) or 1),
        "unit_cost": float(row.unit_cost or 0),
        "average_cost": float(getattr(row, "average_cost", 0) or 0),
        "last_cost": float(getattr(row, "last_cost", 0) or 0),
        "min_stock": float(getattr(row, "min_stock", 0) or 0),
        "max_stock": float(getattr(row, "max_stock", 0) or 0),
        "reorder_level": float(getattr(row, "reorder_level", 0) or 0),
        "expiry_tracking": getattr(row, "expiry_tracking", False),
        "batch_tracking": getattr(row, "batch_tracking", False),
        "storage_location": getattr(row, "storage_location", "") or "",
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_recipe_ingredient(row) -> dict:
    return {
        "id": str(row.id),
        "ingredient_id": str(row.ingredient_id),
        "ingredient_name": row.ingredient.name if row.ingredient_id else "",
        "quantity": float(row.quantity or 0),
        "unit": row.unit,
        "unit_cost": float(row.unit_cost or 0),
        "notes": row.notes or "",
    }


def serialize_recipe(row, *, include_ingredients=True) -> dict:
    total = float(row.total_cost() or 0)
    sell = float(row.menu_item.unit_price or 0) if row.menu_item_id else 0
    yield_qty = float(row.yield_qty or 1) or 1
    cost_per = total / yield_qty
    gp = sell - cost_per
    margin = (gp / sell * 100) if sell else 0
    data = {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "menu_item_id": str(row.menu_item_id),
        "menu_item_name": row.menu_item.name if row.menu_item_id else "",
        "name": row.name,
        "version": row.version,
        "status": getattr(row, "status", "draft") or "draft",
        "yield_qty": float(row.yield_qty or 0),
        "waste_percent": float(row.waste_percent or 0),
        "is_active": row.is_active,
        "notes": row.notes or "",
        "total_cost": total,
        "cost_per_serving": cost_per,
        "selling_price": sell,
        "gross_profit": gp,
        "gross_margin_pct": round(margin, 2),
    }
    if include_ingredients:
        rows = list(
            row.ingredients.filter(deleted_at__isnull=True).select_related("ingredient")
        )
        data["ingredients"] = [serialize_recipe_ingredient(i) for i in rows]
    return data

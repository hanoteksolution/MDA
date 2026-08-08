def serialize_category(row) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
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
        "name": row.name,
        "sku": row.sku or "",
        "description": row.description or "",
        "unit_price": float(row.unit_price or 0),
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
    }


def serialize_line(row) -> dict:
    return {
        "id": str(row.id),
        "menu_item_id": str(row.menu_item_id),
        "product_id": str(row.product_id) if row.product_id else None,
        "name": row.name,
        "quantity": float(row.quantity or 0),
        "unit_price": float(row.unit_price or 0),
        "line_total": float(row.line_total or 0),
        "status": row.status,
        "notes": row.notes or "",
    }


def serialize_order(row, *, include_lines=True) -> dict:
    data = {
        "id": str(row.id),
        "order_number": row.order_number,
        "branch_id": str(row.branch_id),
        "table_id": str(row.table_id) if row.table_id else None,
        "table_code": row.table.code if row.table_id else None,
        "status": row.status,
        "service_type": row.service_type,
        "waiter_user_id": str(row.waiter_user_id) if row.waiter_user_id else None,
        "waiter_name": row.waiter_name or "",
        "guest_count": row.guest_count,
        "subtotal": float(row.subtotal or 0),
        "notes": row.notes or "",
        "opened_at": row.opened_at.isoformat() if row.opened_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
    }
    if include_lines:
        lines = list(row.lines.filter(deleted_at__isnull=True))
        data["lines"] = [serialize_line(l) for l in lines]
        data["line_count"] = len(lines)
    return data

from apps.products.models import Brand, Category, Product, Unit
from apps.products.services.attribute_service import AttributeService


def stock_totals_for_products(product_ids) -> dict[str, dict]:
    """Aggregate inventory in one query for a batch of products."""
    if not product_ids:
        return {}
    from django.db.models import Sum

    from apps.inventory.models import Inventory

    rows = (
        Inventory.active_objects()
        .filter(product_id__in=product_ids)
        .values("product_id")
        .annotate(on_hand=Sum("quantity"), reserved=Sum("reserved_quantity"))
    )
    out = {}
    for row in rows:
        on_hand = float(row["on_hand"] or 0)
        reserved = float(row["reserved"] or 0)
        pid = str(row["product_id"])
        out[pid] = {
            "on_hand_stock": on_hand,
            "reserved_stock": reserved,
            "total_stock": on_hand - reserved,
        }
    return out


def _apply_stock_fields(data: dict, stock_row: dict | None) -> None:
    if not stock_row:
        data["total_stock"] = 0.0
        data["on_hand_stock"] = 0.0
        data["reserved_stock"] = 0.0
        data["warehouse_id"] = None
        data["warehouse_name"] = None
        data["available_quantity"] = 0.0
        return
    data["total_stock"] = stock_row["total_stock"]
    data["on_hand_stock"] = stock_row["on_hand_stock"]
    data["reserved_stock"] = stock_row["reserved_stock"]
    data["warehouse_id"] = stock_row.get("warehouse_id")
    data["warehouse_name"] = stock_row.get("warehouse_name")
    data["available_quantity"] = stock_row["total_stock"]


def serialize_unit(u: Unit) -> dict:
    return {"id": str(u.id), "name": u.name, "abbreviation": u.abbreviation, "is_active": u.is_active}


def serialize_category(c: Category) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "parent_id": str(c.parent_id) if c.parent_id else None,
        "description": c.description,
        "is_active": c.is_active,
    }


def serialize_brand(b: Brand) -> dict:
    return {"id": str(b.id), "name": b.name, "description": b.description, "is_active": b.is_active}


def serialize_product(
    p: Product,
    include_stock=False,
    request=None,
    include_attributes=True,
    stock_map=None,
) -> dict:
    from core.utils.media import resolve_product_image_url

    data = {
        "id": str(p.id),
        "sku": p.sku,
        "barcode": p.barcode or "",
        "name": p.name,
        "category_id": str(p.category_id),
        "category_name": p.category.name,
        "brand_id": str(p.brand_id) if p.brand_id else None,
        "brand_name": p.brand.name if p.brand else None,
        "unit_id": str(p.unit_id),
        "unit_name": p.unit.name,
        "cost_price": float(p.cost_price),
        "selling_price": float(p.selling_price),
        "minimum_stock": p.minimum_stock,
        "description": p.description,
        "image": resolve_product_image_url(p.image, request),
        "is_active": p.is_active,
        "requires_prescription": bool(getattr(p, "requires_prescription", False)),
        "created_at": p.created_at.isoformat(),
    }
    if include_attributes:
        data["attributes"] = AttributeService.values_for_product(p)
    if include_stock:
        stock_row = (stock_map or {}).get(str(p.id))
        if stock_row is not None:
            _apply_stock_fields(data, stock_row)
        else:
            from apps.inventory.models import Inventory

            inv_rows = list(
                Inventory.active_objects()
                .filter(product=p)
                .select_related("warehouse")
                .order_by("-quantity")
            )
            on_hand = float(sum((row.quantity or 0) for row in inv_rows))
            reserved = float(sum((row.reserved_quantity or 0) for row in inv_rows))
            primary = inv_rows[0] if inv_rows else None
            _apply_stock_fields(
                data,
                {
                    "on_hand_stock": on_hand,
                    "reserved_stock": reserved,
                    "total_stock": on_hand - reserved,
                    "warehouse_id": str(primary.warehouse_id) if primary else None,
                    "warehouse_name": primary.warehouse.name if primary else None,
                },
            )
    return data


def serialize_products_batch(
    products,
    *,
    include_stock=False,
    request=None,
    include_attributes=True,
) -> list[dict]:
    items = list(products)
    stock_map = stock_totals_for_products([p.id for p in items]) if include_stock else None
    return [
        serialize_product(
            p,
            include_stock=include_stock,
            request=request,
            include_attributes=include_attributes,
            stock_map=stock_map,
        )
        for p in items
    ]

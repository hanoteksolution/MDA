from apps.products.models import Brand, Category, Product, Unit


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


def serialize_product(p: Product, include_stock=False, request=None) -> dict:
    from django.db.models import Sum

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
        "created_at": p.created_at.isoformat(),
    }
    if include_stock:
        from apps.inventory.models import Inventory

        inv_rows = list(
            Inventory.active_objects()
            .filter(product=p)
            .select_related("warehouse")
            .order_by("-quantity")
        )
        data["total_stock"] = float(sum((row.quantity or 0) for row in inv_rows))
        primary = inv_rows[0] if inv_rows else None
        data["warehouse_id"] = str(primary.warehouse_id) if primary else None
        data["warehouse_name"] = primary.warehouse.name if primary else None
    return data

"""Restaurant / cafeteria report pack — floor, orders, menu."""

from django.db.models import Count, Sum

from apps.restaurant.models import DiningTable, MenuItem, RestaurantOrder
from core.tenancy import apply_tenant_scope


def run(*, report, branch_id=None, date_from=None, date_to=None, user=None, request=None):
    if report == "Table Status":
        qs = apply_tenant_scope(
            DiningTable.active_objects().select_related("branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        qs = qs.filter(is_active=True)
        rows = [
            {
                "table": t.code,
                "name": t.label or t.code,
                "status": t.status,
                "seats": t.capacity,
                "branch": t.branch.name if t.branch_id else "—",
            }
            for t in qs.order_by("code")[:100]
        ]
        return {
            "columns": ["table", "name", "status", "seats", "branch"],
            "rows": rows,
        }

    if report == "Open Orders":
        qs = apply_tenant_scope(
            RestaurantOrder.active_objects()
            .exclude(
                status__in=[
                    RestaurantOrder.STATUS_PAID,
                    RestaurantOrder.STATUS_CANCELLED,
                ]
            )
            .select_related("table", "branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "order": o.order_number,
                "table": o.table.code if o.table_id else "Takeaway",
                "status": o.status,
                "waiter": o.waiter_name or "—",
                "subtotal": float(o.subtotal or 0),
                "opened": o.opened_at.isoformat() if o.opened_at else "—",
            }
            for o in qs.order_by("-opened_at")[:100]
        ]
        return {
            "columns": ["order", "table", "status", "waiter", "subtotal", "opened"],
            "rows": rows,
        }

    if report == "Orders by Status":
        qs = apply_tenant_scope(
            RestaurantOrder.active_objects(),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(opened_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(opened_at__date__lte=date_to)
        grouped = (
            qs.values("status")
            .annotate(count=Count("id"), revenue=Sum("subtotal"))
            .order_by("status")
        )
        rows = [
            {
                "status": r["status"],
                "count": r["count"],
                "revenue": float(r["revenue"] or 0),
            }
            for r in grouped
        ]
        return {"columns": ["status", "count", "revenue"], "rows": rows}

    if report == "Menu Catalog":
        qs = apply_tenant_scope(
            MenuItem.active_objects().select_related("category", "product"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "item": m.name,
                "category": m.category.name if m.category_id else "—",
                "price": float(m.unit_price or 0),
                "available": m.is_available,
                "sku": m.sku or (m.product.sku if m.product_id else "—"),
            }
            for m in qs.order_by("category__name", "name")[:100]
        ]
        return {
            "columns": ["item", "category", "price", "available", "sku"],
            "rows": rows,
        }

    return {"columns": [], "rows": []}

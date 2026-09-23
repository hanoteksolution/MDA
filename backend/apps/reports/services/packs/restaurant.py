"""Restaurant / cafeteria report pack — floor, orders, menu, barista, waste."""

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.restaurant.models import (
    DiningTable,
    MenuItem,
    OrderLine,
    RestaurantOrder,
    WasteRecord,
)
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
                    RestaurantOrder.STATUS_VOIDED,
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

    if report == "Sales by Product":
        qs = apply_tenant_scope(
            OrderLine.active_objects()
            .filter(order__status=RestaurantOrder.STATUS_PAID, deleted_at__isnull=True)
            .select_related("menu_item", "order"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(order__branch_id=branch_id)
        if date_from:
            qs = qs.filter(order__opened_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(order__opened_at__date__lte=date_to)
        grouped = (
            qs.values("name")
            .annotate(qty=Sum("quantity"), revenue=Sum("line_total"), tickets=Count("order_id", distinct=True))
            .order_by("-revenue")[:100]
        )
        rows = [
            {
                "product": r["name"],
                "qty": float(r["qty"] or 0),
                "revenue": float(r["revenue"] or 0),
                "tickets": r["tickets"],
            }
            for r in grouped
        ]
        return {"columns": ["product", "qty", "revenue", "tickets"], "rows": rows}

    if report == "Sales by Order Type":
        qs = apply_tenant_scope(
            RestaurantOrder.active_objects().filter(status=RestaurantOrder.STATUS_PAID),
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
            qs.values("service_type")
            .annotate(count=Count("id"), revenue=Sum("subtotal"), tips=Sum("tip_amount"))
            .order_by("service_type")
        )
        rows = [
            {
                "order_type": r["service_type"],
                "count": r["count"],
                "revenue": float(r["revenue"] or 0),
                "tips": float(r["tips"] or 0),
            }
            for r in grouped
        ]
        return {"columns": ["order_type", "count", "revenue", "tips"], "rows": rows}

    if report == "Barista Performance":
        qs = apply_tenant_scope(
            RestaurantOrder.active_objects()
            .exclude(accepted_at__isnull=True)
            .exclude(ready_at__isnull=True),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(opened_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(opened_at__date__lte=date_to)
        qs = qs.annotate(
            prep_seconds=ExpressionWrapper(
                F("ready_at") - F("accepted_at"), output_field=DurationField()
            )
        )
        grouped = (
            qs.values("barista_user_id", "barista_user__username")
            .annotate(
                orders=Count("id"),
                avg_prep=Avg("prep_seconds"),
                revenue=Sum("subtotal"),
            )
            .order_by("-orders")[:50]
        )
        rows = []
        for r in grouped:
            avg = r["avg_prep"]
            avg_sec = int(avg.total_seconds()) if avg else 0
            rows.append(
                {
                    "barista": r["barista_user__username"] or str(r["barista_user_id"] or "—"),
                    "orders": r["orders"],
                    "avg_prep_sec": avg_sec,
                    "revenue": float(r["revenue"] or 0),
                }
            )
        return {"columns": ["barista", "orders", "avg_prep_sec", "revenue"], "rows": rows}

    if report == "Waste Report":
        qs = apply_tenant_scope(
            WasteRecord.active_objects().select_related("ingredient", "branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(waste_date__gte=date_from)
        if date_to:
            qs = qs.filter(waste_date__lte=date_to)
        rows = [
            {
                "date": w.waste_date.isoformat() if w.waste_date else "—",
                "type": w.waste_type,
                "item": (w.ingredient.name if w.ingredient_id else "—"),
                "qty": float(w.quantity or 0),
                "cost": float(w.total_cost or 0),
                "status": w.approval_status,
            }
            for w in qs.order_by("-waste_date")[:100]
        ]
        return {"columns": ["date", "type", "item", "qty", "cost", "status"], "rows": rows}

    if report == "Daily Sales Summary":
        today = timezone.localdate()
        d_from = date_from or today
        d_to = date_to or today
        qs = apply_tenant_scope(
            RestaurantOrder.active_objects().filter(
                status=RestaurantOrder.STATUS_PAID,
                opened_at__date__gte=d_from,
                opened_at__date__lte=d_to,
            ),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        agg = qs.aggregate(
            orders=Count("id"),
            gross=Sum("subtotal"),
            tips=Sum("tip_amount"),
            service=Sum("service_charge_amount"),
        )
        rows = [
            {
                "from": str(d_from),
                "to": str(d_to),
                "orders": agg["orders"] or 0,
                "gross_sales": float(agg["gross"] or 0),
                "tips": float(agg["tips"] or 0),
                "service_charges": float(agg["service"] or 0),
                "aov": round(float(agg["gross"] or 0) / (agg["orders"] or 1), 2)
                if agg["orders"]
                else 0,
            }
        ]
        return {
            "columns": [
                "from",
                "to",
                "orders",
                "gross_sales",
                "tips",
                "service_charges",
                "aov",
            ],
            "rows": rows,
        }

    return {"columns": [], "rows": []}

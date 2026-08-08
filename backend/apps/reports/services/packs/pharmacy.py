"""Pharmacy report pack (STEP 22)."""

from datetime import timedelta

from django.utils import timezone

from apps.pharmacy.models import BatchDispense, ProductBatch
from core.tenancy import apply_tenant_scope


def run(*, report, branch_id=None, date_from=None, date_to=None, user=None, request=None):
    qs = apply_tenant_scope(
        ProductBatch.active_objects().select_related("product", "warehouse"),
        user=user,
        request=request,
    )
    if branch_id:
        qs = qs.filter(warehouse__branch_id=branch_id)

    if report == "Batch Stock":
        rows = [
            {
                "product": b.product.name if b.product_id else "—",
                "batch": b.batch_number,
                "expiry": b.expiry_date.isoformat() if b.expiry_date else "—",
                "qty": float(b.quantity),
                "warehouse": b.warehouse.name if b.warehouse_id else "—",
            }
            for b in qs.filter(is_active=True).order_by("expiry_date")[:100]
        ]
        return {"columns": ["product", "batch", "expiry", "qty", "warehouse"], "rows": rows}

    if report == "Expiring Soon":
        horizon = timezone.localdate() + timedelta(days=90)
        rows = [
            {
                "product": b.product.name if b.product_id else "—",
                "batch": b.batch_number,
                "expiry": b.expiry_date.isoformat() if b.expiry_date else "—",
                "days_left": (b.expiry_date - timezone.localdate()).days if b.expiry_date else None,
                "qty": float(b.quantity),
            }
            for b in qs.filter(
                is_active=True,
                expiry_date__isnull=False,
                expiry_date__lte=horizon,
                quantity__gt=0,
            ).order_by("expiry_date")[:100]
        ]
        return {"columns": ["product", "batch", "expiry", "days_left", "qty"], "rows": rows}

    if report == "FEFO Dispenses":
        disp = BatchDispense.active_objects().select_related("batch", "batch__product")
        tenant_id = None
        if user is not None or request is not None:
            from core.tenancy import resolve_acting_tenant

            tenant = resolve_acting_tenant(user=user, request=request)
            tenant_id = getattr(tenant, "pk", None) if tenant else None
        if tenant_id:
            disp = disp.filter(batch__tenant_id=tenant_id)
        if date_from:
            disp = disp.filter(created_at__date__gte=date_from)
        if date_to:
            disp = disp.filter(created_at__date__lte=date_to)
        rows = [
            {
                "product": d.batch.product.name if d.batch_id and d.batch.product_id else "—",
                "batch": d.batch.batch_number if d.batch_id else "—",
                "qty": float(d.quantity),
                "reference": str(d.reference_id) if d.reference_id else "—",
                "when": d.created_at.isoformat() if d.created_at else "—",
            }
            for d in disp.order_by("-created_at")[:100]
        ]
        return {"columns": ["product", "batch", "qty", "reference", "when"], "rows": rows}

    return {"columns": [], "rows": []}

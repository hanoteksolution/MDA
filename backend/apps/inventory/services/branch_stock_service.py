"""Branch-level stock aggregation and cross-branch availability (Phase 3).

Everything here is **read-only** and **derived**: branch stock is always computed as
``SUM`` over the branch's warehouses' ``Inventory`` rows, never stored as a second
mutable figure (BRANCH_INVENTORY.md §4). Cross-branch visibility is a number, never a
mutation capability (§7) — nothing in this module writes to ``Inventory``.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.inventory.models import Inventory, Warehouse
from apps.settings_app.models import Branch


def _zero_if_none(value) -> Decimal:
    return value if value is not None else Decimal("0")


def aggregate_branch_stock(*, branch, product=None) -> dict:
    """Σ on-hand / Σ reserved over every active warehouse of ``branch``.

    Available is computed once, in Python, from the two SQL sums — not by summing the
    per-row ``available_quantity`` property, which would require pulling every row
    into Python for what is otherwise a single aggregate query (§4).
    """
    qs = Inventory.active_objects().filter(
        warehouse__branch_id=branch.pk, warehouse__is_active=True, warehouse__deleted_at__isnull=True
    )
    if product is not None:
        qs = qs.filter(product=product)
    agg = qs.aggregate(on_hand=Sum("quantity"), reserved=Sum("reserved_quantity"))
    on_hand = _zero_if_none(agg["on_hand"])
    reserved = _zero_if_none(agg["reserved"])
    return {
        "branch_id": str(branch.pk),
        "branch_name": branch.name,
        "on_hand": on_hand,
        "reserved": reserved,
        "available": on_hand - reserved,
    }


def aggregate_warehouse_stock(*, warehouse, product=None) -> dict:
    """Same shape as :func:`aggregate_branch_stock`, for one warehouse."""
    qs = Inventory.active_objects().filter(warehouse_id=warehouse.pk)
    if product is not None:
        qs = qs.filter(product=product)
    agg = qs.aggregate(on_hand=Sum("quantity"), reserved=Sum("reserved_quantity"))
    on_hand = _zero_if_none(agg["on_hand"])
    reserved = _zero_if_none(agg["reserved"])
    return {
        "warehouse_id": str(warehouse.pk),
        "warehouse_name": warehouse.name,
        "branch_id": str(warehouse.branch_id),
        "on_hand": on_hand,
        "reserved": reserved,
        "available": on_hand - reserved,
    }


def in_transit_quantity(*, product, branch=None) -> Decimal:
    """Σ dispatched − Σ received across open ``BranchTransferLine`` rows (D5).

    Phase 4: real data. A line is "in transit" while its request hasn't reached a
    terminal status (RECEIVED/COMPLETED/REJECTED/CANCELLED) — dispatched-but-not-yet-
    fully-received.
    """
    from apps.inventory.models import BranchTransferLine, BranchTransferRequest

    qs = BranchTransferLine.objects.filter(
        product=product,
        request__status=BranchTransferRequest.STATUS_IN_TRANSIT,
        request__deleted_at__isnull=True,
    )
    if branch is not None:
        qs = qs.filter(request__destination_branch=branch)
    agg = qs.aggregate(dispatched=Sum("quantity_dispatched"), received=Sum("quantity_received"))
    return _zero_if_none(agg["dispatched"]) - _zero_if_none(agg["received"])


def product_availability(*, product, current_branch, tenant, include_other_branches=True) -> dict:
    """The shape the availability API returns (BRANCH_INVENTORY.md §7).

    ``current_branch`` figures always come first and are always computed regardless of
    permission — a caller who can see their own branch's stock always could. Whether
    ``other_branches`` is populated is entirely the caller's (the view's) decision,
    driven by ``inventory.cross_branch_view`` — this function itself performs no
    authorisation, matching every other Phase 2/3 service (auth is a view concern).
    """
    current = aggregate_branch_stock(branch=current_branch, product=product)
    other_branches = []
    if include_other_branches:
        others = (
            Branch.active_objects()
            .filter(tenant_id=tenant.pk if tenant else None)
            .exclude(pk=current_branch.pk)
            .filter(is_active=True)
        )
        for branch in others:
            row = aggregate_branch_stock(branch=branch, product=product)
            other_branches.append(
                {
                    "branch_id": row["branch_id"],
                    "branch_name": row["branch_name"],
                    "available": row["available"],
                }
            )
    return {
        "product_id": str(product.pk),
        "product_sku": product.sku,
        "product_name": product.name,
        "current_branch": {
            "branch_id": current["branch_id"],
            "branch_name": current["branch_name"],
            "on_hand": current["on_hand"],
            "reserved": current["reserved"],
            "available": current["available"],
            "in_transit": in_transit_quantity(product=product, branch=current_branch),
        },
        "other_branches": other_branches,
    }


def stock_status(*, on_hand, minimum_stock) -> str:
    """The canonical IN_STOCK / LOW_STOCK / OUT_OF_STOCK classification.

    Uses the existing ``Product.minimum_stock`` threshold — no duplicate configuration
    is introduced (BRANCH_INVENTORY.md §1, "Low Stock / Out of Stock Foundation").
    """
    on_hand = Decimal(str(on_hand))
    minimum_stock = Decimal(str(minimum_stock or 0))
    if on_hand <= 0:
        return "OUT_OF_STOCK"
    if on_hand <= minimum_stock:
        return "LOW_STOCK"
    return "IN_STOCK"


def branch_stock_dashboard(*, branch, module_code=None) -> dict:
    """Aggregate figures for a branch inventory dashboard: SKUs, value, low/out-of-stock,
    reserved, recent movement count. One query per figure, no N+1 over products."""
    from django.db.models import DecimalField, ExpressionWrapper, F

    from apps.inventory.services.inventory_service import _module_scope_inventory

    qs = Inventory.active_objects().filter(
        warehouse__branch_id=branch.pk, product__deleted_at__isnull=True
    ).select_related("product")
    qs = _module_scope_inventory(qs, module_code=module_code)

    total_skus = qs.values("product_id").distinct().count()
    value_agg = qs.aggregate(
        inventory_value=Sum(
            ExpressionWrapper(
                F("quantity") * F("product__selling_price"),
                output_field=DecimalField(max_digits=38, decimal_places=4),
            )
        ),
        reserved=Sum("reserved_quantity"),
    )
    low_stock = qs.filter(quantity__gt=0, quantity__lte=F("product__minimum_stock")).count()
    out_of_stock = qs.filter(quantity__lte=0).count()

    from apps.inventory.models import StockMovement

    recent_movements = StockMovement.objects.filter(
        branch_id=branch.pk, deleted_at__isnull=True
    ).count()

    return {
        "branch_id": str(branch.pk),
        "total_skus": total_skus,
        "inventory_value": float(value_agg["inventory_value"] or 0),
        "low_stock_count": low_stock,
        "out_of_stock_count": out_of_stock,
        "reserved_quantity": float(value_agg["reserved"] or 0),
        "recent_movements_count": recent_movements,
    }

from apps.inventory.models import (
    Inventory,
    InventoryAdjustment,
    StockMovement,
    StockTransfer,
    Warehouse,
)
from core.utils.media import resolve_product_image_url


def serialize_warehouse(w: Warehouse) -> dict:
    return {
        "id": str(w.id),
        "name": w.name,
        "code": w.code,
        "branch_id": str(w.branch_id),
        "branch_name": w.branch.name,
        "address": w.address,
        "is_active": w.is_active,
        "is_default": w.is_default,
    }


def serialize_inventory(inv: Inventory) -> dict:
    product = inv.product
    return {
        "id": str(inv.id),
        "product_id": str(inv.product_id),
        "product_name": product.name,
        "product_sku": product.sku,
        "product_image": resolve_product_image_url(product.image or ""),
        "warehouse_id": str(inv.warehouse_id),
        "warehouse_name": inv.warehouse.name,
        "quantity": float(inv.quantity),
        "reserved_quantity": float(inv.reserved_quantity),
        "damaged_quantity": float(inv.damaged_quantity),
        "returned_quantity": float(inv.returned_quantity),
        "available_quantity": float(inv.available_quantity),
        "minimum_stock": product.minimum_stock,
        "is_low_stock": float(inv.quantity) <= product.minimum_stock,
        "is_out_of_stock": float(inv.quantity) <= 0,
    }


def serialize_adjustment(adj: InventoryAdjustment) -> dict:
    return {
        "id": str(adj.id),
        "adjustment_number": adj.adjustment_number,
        "warehouse_id": str(adj.warehouse_id),
        "warehouse_name": adj.warehouse.name,
        "branch_id": str(adj.branch_id),
        "reason": adj.reason,
        "status": adj.status,
        "items_count": adj.items.count(),
        "created_at": adj.created_at.isoformat(),
    }


def serialize_transfer(transfer: StockTransfer, *, include_lines=False) -> dict:
    data = {
        "id": str(transfer.id),
        "transfer_number": transfer.transfer_number,
        "source_warehouse_id": str(transfer.source_warehouse_id),
        "source_warehouse_name": transfer.source_warehouse.name,
        "destination_warehouse_id": str(transfer.destination_warehouse_id),
        "destination_warehouse_name": transfer.destination_warehouse.name,
        "branch_id": str(transfer.branch_id),
        "branch_name": transfer.branch.name,
        "status": transfer.status,
        "notes": transfer.notes,
        "confirmed_at": transfer.confirmed_at.isoformat() if transfer.confirmed_at else None,
        "confirmed_by": transfer.confirmed_by.username if transfer.confirmed_by_id else None,
        "lines_count": transfer.lines.count(),
        "created_at": transfer.created_at.isoformat(),
    }
    if include_lines:
        data["lines"] = [
            {
                "id": str(line.id),
                "product_id": str(line.product_id),
                "product_name": line.product.name,
                "product_sku": line.product.sku,
                "quantity": float(line.quantity),
            }
            for line in transfer.lines.select_related("product")
        ]
    return data


def serialize_movement(m: StockMovement) -> dict:
    return {
        "id": str(m.id),
        "movement_type": m.movement_type,
        "product_id": str(m.product_id),
        "product_sku": m.product.sku,
        "warehouse_id": str(m.warehouse_id),
        "warehouse_name": m.warehouse.name,
        "branch_id": str(m.branch_id) if m.branch_id else None,
        "location_id": str(m.location_id) if m.location_id else None,
        "location_name": m.location.name if m.location_id else None,
        "destination_warehouse_id": str(m.destination_warehouse_id) if m.destination_warehouse_id else None,
        "quantity": float(m.quantity),
        "unit_cost": float(m.unit_cost) if m.unit_cost is not None else None,
        "reference_type": m.reference_type,
        "reference_id": str(m.reference_id) if m.reference_id else None,
        "performed_by": m.performed_by.username if m.performed_by_id else None,
        "notes": m.notes,
        "created_at": m.created_at.isoformat(),
    }


def serialize_branch_transfer(t, *, include_lines=True) -> dict:
    data = {
        "id": str(t.id),
        "request_number": t.request_number,
        "status": t.status,
        "source_branch_id": str(t.source_branch_id),
        "source_branch_name": t.source_branch.name,
        "destination_branch_id": str(t.destination_branch_id),
        "destination_branch_name": t.destination_branch.name,
        "source_warehouse_id": str(t.source_warehouse_id),
        "destination_warehouse_id": str(t.destination_warehouse_id),
        "notes": t.notes,
        "rejection_reason": t.rejection_reason,
        "requested_by": t.requested_by.username if t.requested_by_id else None,
        "approved_by": t.approved_by.username if t.approved_by_id else None,
        "dispatched_by": t.dispatched_by.username if t.dispatched_by_id else None,
        "received_by": t.received_by.username if t.received_by_id else None,
        "source_warehouse_name": t.source_warehouse.name,
        "destination_warehouse_name": t.destination_warehouse.name,
        "line_count": len(t.lines.all()),
        "total_quantity": float(sum((l.quantity_requested for l in t.lines.all()), 0)),
        "approved_at": t.approved_at.isoformat() if t.approved_at else None,
        "reserved_at": t.reserved_at.isoformat() if t.reserved_at else None,
        "dispatched_at": t.dispatched_at.isoformat() if t.dispatched_at else None,
        "received_at": t.received_at.isoformat() if t.received_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "created_at": t.created_at.isoformat(),
    }
    if include_lines:
        data["lines"] = [
            {
                "id": str(l.id),
                "product_id": str(l.product_id),
                "product_sku": l.product.sku,
                "product_name": l.product.name,
                "quantity_requested": float(l.quantity_requested),
                "quantity_reserved": float(l.quantity_reserved),
                "quantity_dispatched": float(l.quantity_dispatched),
                "quantity_received": float(l.quantity_received),
                "discrepancy_quantity": float(l.discrepancy_quantity),
                "in_transit_quantity": float(l.in_transit_quantity),
            }
            for l in t.lines.select_related("product")
        ]
    return data

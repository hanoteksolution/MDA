from apps.inventory.models import Inventory, InventoryAdjustment, Warehouse


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
    return {
        "id": str(inv.id),
        "product_id": str(inv.product_id),
        "product_name": inv.product.name,
        "product_sku": inv.product.sku,
        "warehouse_id": str(inv.warehouse_id),
        "warehouse_name": inv.warehouse.name,
        "quantity": float(inv.quantity),
        "reserved_quantity": float(inv.reserved_quantity),
        "damaged_quantity": float(inv.damaged_quantity),
        "returned_quantity": float(inv.returned_quantity),
        "available_quantity": float(inv.available_quantity),
        "minimum_stock": inv.product.minimum_stock,
        "is_low_stock": float(inv.quantity) <= inv.product.minimum_stock,
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

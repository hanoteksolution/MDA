from apps.purchases.models import PurchaseOrder, PurchaseOrderItem


def serialize_po_item(item: PurchaseOrderItem) -> dict:
    return {
        "id": str(item.id),
        "product_id": str(item.product_id),
        "product_name": item.product.name,
        "product_sku": item.product.sku,
        "quantity_ordered": float(item.quantity_ordered),
        "quantity_received": float(item.quantity_received),
        "unit_cost": float(item.unit_cost),
        "line_total": float(item.line_total),
    }


def serialize_purchase_order(po: PurchaseOrder, *, include_items=False) -> dict:
    supplier = po.supplier
    branch = po.branch
    data = {
        "id": str(po.id),
        "order_number": po.order_number,
        "supplier_id": str(po.supplier_id),
        "supplier_name": supplier.company_name,
        "supplier_address": supplier.address or "",
        "supplier_phone": supplier.phone or "",
        "supplier_email": supplier.email or "",
        "supplier_payment_terms": supplier.payment_terms,
        "branch_id": str(po.branch_id),
        "branch_name": branch.name,
        "branch_address": branch.address or "",
        "status": po.status,
        "order_date": po.order_date.isoformat(),
        "expected_date": po.expected_date.isoformat() if po.expected_date else None,
        "subtotal": float(po.subtotal),
        "tax_amount": float(po.tax_amount),
        "total_amount": float(po.total_amount),
        "notes": po.notes,
        "ordered_by": po.ordered_by.username if po.ordered_by else None,
        "item_count": po.items.count(),
        "created_at": po.created_at.isoformat(),
    }
    if include_items:
        data["items"] = [serialize_po_item(i) for i in po.items.select_related("product")]
    return data

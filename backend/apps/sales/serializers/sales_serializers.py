from apps.sales.models import Invoice, InvoiceItem, Quotation, QuotationItem


def _serialize_item(item, *, product_fields) -> dict:
    return {
        "id": str(item.id),
        "product_id": str(item.product_id),
        "product_name": product_fields["name"],
        "product_sku": product_fields["sku"],
        "quantity": float(item.quantity),
        "unit_price": float(item.unit_price),
        "line_total": float(item.line_total),
    }


def serialize_quotation(q: Quotation, *, include_items=False) -> dict:
    data = {
        "id": str(q.id),
        "number": q.quotation_number,
        "customer_id": str(q.customer_id),
        "customer_name": q.customer.full_name,
        "branch_id": str(q.branch_id),
        "branch_name": q.branch.name,
        "status": q.status,
        "valid_until": q.valid_until.isoformat() if q.valid_until else None,
        "subtotal": float(q.subtotal),
        "discount_amount": float(q.discount_amount),
        "tax_amount": float(q.tax_amount),
        "total_amount": float(q.total_amount),
        "notes": q.notes,
        "date": q.created_at.date().isoformat(),
        "item_count": q.items.count(),
        "created_at": q.created_at.isoformat(),
    }
    if include_items:
        data["items"] = [
            _serialize_item(i, product_fields={"name": i.product.name, "sku": i.product.sku})
            for i in q.items.select_related("product")
        ]
    return data


def serialize_invoice(inv: Invoice, *, include_items=False) -> dict:
    data = {
        "id": str(inv.id),
        "number": inv.invoice_number,
        "customer_id": str(inv.customer_id),
        "customer_name": inv.customer.full_name,
        "branch_id": str(inv.branch_id),
        "branch_name": inv.branch.name,
        "status": inv.status,
        "issue_date": inv.issue_date.isoformat(),
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "subtotal": float(inv.subtotal),
        "discount_amount": float(inv.discount_amount),
        "tax_amount": float(inv.tax_amount),
        "total_amount": float(inv.total_amount),
        "amount_paid": float(inv.amount_paid),
        "notes": inv.notes,
        "date": inv.issue_date.isoformat(),
        "item_count": inv.items.count(),
        "created_at": inv.created_at.isoformat(),
    }
    if include_items:
        data["items"] = [
            _serialize_item(i, product_fields={"name": i.product.name, "sku": i.product.sku})
            for i in inv.items.select_related("product")
        ]
    return data

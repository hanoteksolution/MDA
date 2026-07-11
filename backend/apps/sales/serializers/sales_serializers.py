import re

from apps.sales.models import Invoice, InvoiceItem, Quotation, QuotationItem


def _parse_waiter(notes: str) -> str:
    if not notes:
        return ""
    match = re.search(r"Waiter:\s*([^|\n]+)", notes, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_payment_method(notes: str) -> str:
    if not notes:
        return ""
    match = re.search(r"Payment:\s*([a-z_]+)", notes, re.IGNORECASE)
    return match.group(1).lower() if match else ""


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
    waiter = ""
    served_by_user_id = None
    if getattr(inv, "served_by_user", None):
        served_by_user_id = str(inv.served_by_user_id)
        waiter = inv.served_by_user.get_full_name() or inv.served_by_user.username
    if not waiter:
        waiter = _parse_waiter(inv.notes or "")
    payment_method = _parse_payment_method(inv.notes or "") or None
    balance_due = float(inv.total_amount - inv.amount_paid)

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
        "balance_due": balance_due,
        "is_paid": inv.status == Invoice.STATUS_PAID,
        "payment_method": payment_method,
        "waiter_name": waiter,
        "served_by_user_id": served_by_user_id,
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

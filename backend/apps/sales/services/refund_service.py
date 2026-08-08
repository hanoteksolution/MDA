"""POS sale refunds — partial returns with stock restore."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum

from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.sales.models import Invoice, InvoiceItem, SaleRefund, SaleRefundItem
from apps.sales.services.cashier_session_service import CashierSessionService
from apps.sales.services.sequence_service import DocumentSequenceService
from apps.sales.models import DocumentSequence
from core.tenancy import apply_tenant_scope, stamp_tenant_id

MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


class RefundError(ValueError):
    pass


class RefundService:
    @staticmethod
    def serialize(refund: SaleRefund, *, include_items=False) -> dict:
        data = {
            "id": str(refund.id),
            "refund_number": refund.refund_number,
            "original_invoice_id": str(refund.original_invoice_id),
            "original_invoice_number": refund.original_invoice.invoice_number,
            "branch_id": str(refund.branch_id),
            "cashier_session_id": str(refund.cashier_session_id) if refund.cashier_session_id else None,
            "reason": refund.reason,
            "total_amount": float(refund.total_amount),
            "processed_by_id": str(refund.processed_by_id) if refund.processed_by_id else None,
            "created_at": refund.created_at.isoformat(),
        }
        if include_items:
            data["items"] = [
                {
                    "product_id": str(item.product_id),
                    "product_name": item.product.name,
                    "quantity": float(item.quantity),
                    "unit_price": float(item.unit_price),
                    "line_total": float(item.line_total),
                }
                for item in refund.items.select_related("product")
            ]
        return data

    @staticmethod
    def _refunded_qty_by_product(invoice: Invoice) -> dict:
        rows = (
            SaleRefundItem.active_objects()
            .filter(refund__original_invoice=invoice, refund__deleted_at__isnull=True)
            .values("product_id")
            .annotate(qty=Sum("quantity"))
        )
        return {row["product_id"]: Decimal(str(row["qty"] or 0)) for row in rows}

    @staticmethod
    @transaction.atomic
    def refund_invoice(*, invoice_id, items, reason="", user=None, cashier_session_id=None):
        invoice = (
            apply_tenant_scope(Invoice.active_objects(), user=user)
            .select_related("branch")
            .prefetch_related("items__product")
            .get(pk=invoice_id)
        )
        if invoice.status != Invoice.STATUS_PAID:
            raise RefundError("Only paid invoices can be refunded.")
        if not items:
            raise RefundError("At least one refund line is required.")

        sold_by_product = {
            item.product_id: Decimal(str(item.quantity))
            for item in invoice.items.all()
        }
        price_by_product = {
            item.product_id: Decimal(str(item.unit_price))
            for item in invoice.items.all()
        }
        already_refunded = RefundService._refunded_qty_by_product(invoice)

        parsed_lines = []
        for row in items:
            product_id = row.get("product_id")
            if not product_id:
                raise RefundError("product_id is required on each refund line.")
            qty = _money(row.get("quantity") or 0)
            if qty <= 0:
                raise RefundError("Refund quantity must be positive.")
            pid = product_id if isinstance(product_id, type(invoice.id)) else product_id
            try:
                pid_key = next(k for k in sold_by_product if str(k) == str(product_id))
            except StopIteration:
                raise RefundError(f"Product {product_id} was not on the original invoice.")
            sold = sold_by_product[pid_key]
            prior = already_refunded.get(pid_key, Decimal("0"))
            if qty + prior > sold:
                raise RefundError(
                    f"Cannot refund {qty} — only {sold - prior} remaining for this product."
                )
            unit_price = row.get("unit_price")
            price = _money(unit_price if unit_price is not None else price_by_product[pid_key])
            parsed_lines.append({"product_id": pid_key, "quantity": qty, "unit_price": price})

        session = None
        if cashier_session_id:
            session = CashierSessionService.resolve_for_checkout(
                user=user, session_id=cashier_session_id, branch_id=invoice.branch_id
            )

        refund_number = DocumentSequenceService.allocate(
            branch=invoice.branch,
            kind=DocumentSequence.KIND_INVOICE,
            width=5,
            prefix="RF",
        )["number"]

        total = sum((line["quantity"] * line["unit_price"] for line in parsed_lines), Decimal("0"))
        total = _money(total)
        remaining_refundable = _money(invoice.total_amount - invoice.amount_refunded)
        if total > remaining_refundable + Decimal("0.01"):
            raise RefundError("Refund total exceeds remaining invoice balance.")

        payload = stamp_tenant_id(
            {
                "original_invoice": invoice,
                "refund_number": refund_number,
                "branch": invoice.branch,
                "cashier_session": session,
                "reason": reason or "",
                "total_amount": total,
                "processed_by": user,
            },
            user=user,
        )
        refund = SaleRefund.objects.create(**payload, created_by=user)
        for line in parsed_lines:
            SaleRefundItem.objects.create(
                refund=refund,
                product_id=line["product_id"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                created_by=user,
            )

        warehouse = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)
        if warehouse:
            restore = {line["product_id"]: line["quantity"] for line in parsed_lines}
            InventoryService.apply_invoice_quantity_deltas(
                warehouse=warehouse,
                quantity_by_product=restore,
                reference_id=refund.id,
                user=user,
                notes=f"Refund {refund.refund_number} for {invoice.invoice_number}",
            )

        invoice.amount_refunded = _money(invoice.amount_refunded + total)
        invoice.updated_by = user
        invoice.save(update_fields=["amount_refunded", "updated_by", "updated_at"])

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_refund(
            refund=refund,
            invoice=invoice,
            user=user,
            restore_inventory=warehouse is not None,
        )

        return RefundService.serialize(
            SaleRefund.active_objects().prefetch_related("items__product").get(pk=refund.id),
            include_items=True,
        )

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.sales.models import DocumentSequence, Invoice, InvoiceItem, Quotation, QuotationItem
from apps.sales.services.sequence_service import DocumentSequenceService
from apps.settings_app.models import Branch
from apps.inventory.services.inventory_service import InventoryService


def _aggregate_item_quantities(items) -> dict:
    """Return {product_id: Decimal qty} from invoice line dicts or InvoiceItem qs."""
    totals: dict = {}
    for item in items or []:
        if isinstance(item, dict):
            pid = item.get("product_id")
            qty = Decimal(str(item.get("quantity") or 0))
        else:
            pid = item.product_id
            qty = Decimal(str(item.quantity or 0))
        if not pid:
            continue
        totals[pid] = totals.get(pid, Decimal("0")) + qty
    return totals


def _stock_deltas(*, old_qty: dict, new_qty: dict) -> dict:
    """Inventory deltas: sold more → negative stock; sold less → positive stock."""
    keys = set(old_qty) | set(new_qty)
    return {
        pid: -(new_qty.get(pid, Decimal("0")) - old_qty.get(pid, Decimal("0")))
        for pid in keys
        if (new_qty.get(pid, Decimal("0")) - old_qty.get(pid, Decimal("0"))) != 0
    }


class QuotationService:
    @staticmethod
    def list(*, search=None, status=None, customer_id=None, branch_id=None):
        qs = Quotation.active_objects().select_related("customer", "branch", "created_by_user").prefetch_related("items__product")
        if search:
            qs = qs.filter(
                Q(quotation_number__icontains=search) | Q(customer__full_name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("-created_at")

    @staticmethod
    def _next_number(*, branch: Branch) -> str:
        return DocumentSequenceService.allocate(
            branch=branch,
            kind=DocumentSequence.KIND_QUOTATION,
            width=5,
        )["number"]

    @staticmethod
    def _recalculate(*, quotation: Quotation):
        agg = quotation.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or Decimal("0")
        quotation.subtotal = subtotal
        quotation.tax_amount = Decimal("0")
        quotation.total_amount = subtotal - quotation.discount_amount + quotation.tax_amount
        quotation.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    @staticmethod
    @transaction.atomic
    def create(*, data, items, user=None):
        branch_id = data.pop("branch_id", None)
        customer_id = data.pop("customer_id")
        branch = _resolve_branch(branch_id)
        quotation = Quotation.objects.create(
            quotation_number=QuotationService._next_number(branch=branch),
            customer_id=customer_id,
            branch=branch,
            created_by_user=user,
            created_by=user,
            **data,
        )
        for item in items or []:
            QuotationItem.objects.create(
                quotation=quotation,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                created_by=user,
            )
        QuotationService._recalculate(quotation=quotation)
        return QuotationService.list().get(pk=quotation.pk)

    @staticmethod
    @transaction.atomic
    def update(*, instance, data, items=None, user=None):
        if instance.status == Quotation.STATUS_CANCELLED:
            raise ValueError("Cancelled quotations cannot be edited.")
        customer_id = data.pop("customer_id", None)
        branch_id = data.pop("branch_id", None)
        if customer_id:
            instance.customer_id = customer_id
        if branch_id:
            instance.branch_id = branch_id
        for key, value in data.items():
            if key not in ("quotation_number",):
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                QuotationItem.objects.create(
                    quotation=instance,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    created_by=user,
                )
            QuotationService._recalculate(quotation=instance)
        return QuotationService.list().get(pk=instance.pk)

    @staticmethod
    @transaction.atomic
    def delete(*, instance, user=None):
        instance.soft_delete(user=user)
        return instance


class InvoiceService:
    @staticmethod
    def list(
        *,
        search=None,
        status=None,
        payment_state=None,
        customer_id=None,
        branch_id=None,
        date_from=None,
        date_to=None,
        waiter=None,
    ):
        qs = Invoice.active_objects().select_related(
            "customer", "branch", "created_by_user", "served_by_user"
        ).prefetch_related("items__product")
        if search:
            qs = qs.filter(
                Q(invoice_number__icontains=search)
                | Q(customer__full_name__icontains=search)
                | Q(notes__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if payment_state == "paid":
            qs = qs.filter(status=Invoice.STATUS_PAID)
        elif payment_state == "unpaid":
            qs = qs.exclude(
                status__in=[
                    Invoice.STATUS_PAID,
                    Invoice.STATUS_CANCELLED,
                    Invoice.STATUS_ON_HOLD,
                ]
            )
        elif payment_state == "on_hold":
            qs = qs.filter(status=Invoice.STATUS_ON_HOLD)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(issue_date__gte=date_from)
        if date_to:
            qs = qs.filter(issue_date__lte=date_to)
        if waiter:
            qs = qs.filter(
                Q(served_by_user__first_name__icontains=waiter)
                | Q(served_by_user__last_name__icontains=waiter)
                | Q(served_by_user__username__icontains=waiter)
                | Q(notes__icontains=f"Waiter: {waiter}")
            )
        return qs.order_by("-issue_date", "-created_at")

    @staticmethod
    def _next_number(*, branch: Branch) -> str:
        return DocumentSequenceService.allocate(
            branch=branch,
            kind=DocumentSequence.KIND_INVOICE,
            width=5,
        )["number"]

    @staticmethod
    def _recalculate(*, invoice: Invoice):
        agg = invoice.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or Decimal("0")
        invoice.subtotal = subtotal
        invoice.tax_amount = Decimal("0")
        invoice.total_amount = subtotal - invoice.discount_amount + invoice.tax_amount
        invoice.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    @staticmethod
    @transaction.atomic
    def create(*, data, items, user=None):
        branch_id = data.pop("branch_id", None)
        customer_id = data.pop("customer_id")
        branch = _resolve_branch(branch_id)
        invoice = Invoice.objects.create(
            invoice_number=InvoiceService._next_number(branch=branch),
            customer_id=customer_id,
            branch=branch,
            created_by_user=user,
            created_by=user,
            **data,
        )
        for item in items or []:
            InvoiceItem.objects.create(
                invoice=invoice,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                created_by=user,
            )
        InvoiceService._recalculate(invoice=invoice)
        InvoiceService._apply_stock_for_create(invoice=invoice, items=items or [], user=user)
        return InvoiceService.list().get(pk=invoice.pk)

    @staticmethod
    def _apply_stock_for_create(*, invoice, items, user=None):
        warehouse = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)
        if not warehouse:
            return
        sold = _aggregate_item_quantities(items)
        deltas = {pid: -qty for pid, qty in sold.items() if qty}
        InventoryService.apply_invoice_quantity_deltas(
            warehouse=warehouse,
            quantity_by_product=deltas,
            reference_id=invoice.id,
            user=user,
            notes=f"Sale {invoice.invoice_number}",
        )

    @staticmethod
    def _apply_stock_for_update(*, invoice, old_branch, old_items_qty, new_items, user=None):
        """
        Diff line quantities and move stock.

        Legacy invoices (never tracked in stock ledger) treat prior qty as 0 so the
        first edit starts tracking without inventing a restock.
        """
        tracked = InventoryService.invoice_stock_tracked(invoice_id=invoice.id)
        effective_old = old_items_qty if tracked else {}
        new_qty = _aggregate_item_quantities(new_items)
        old_wh = InventoryService.resolve_warehouse_for_branch(branch=old_branch)
        new_wh = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)

        if old_wh and new_wh and old_wh.id == new_wh.id:
            deltas = _stock_deltas(old_qty=effective_old, new_qty=new_qty)
            InventoryService.apply_invoice_quantity_deltas(
                warehouse=new_wh,
                quantity_by_product=deltas,
                reference_id=invoice.id,
                user=user,
                notes=f"Sale edit {invoice.invoice_number}",
            )
            return

        # Branch/warehouse changed: restore old sale, then apply new sale.
        if old_wh and effective_old:
            restore = {pid: qty for pid, qty in effective_old.items() if qty}
            InventoryService.apply_invoice_quantity_deltas(
                warehouse=old_wh,
                quantity_by_product=restore,
                reference_id=invoice.id,
                user=user,
                notes=f"Sale move restore {invoice.invoice_number}",
            )
        if new_wh and new_qty:
            deduct = {pid: -qty for pid, qty in new_qty.items() if qty}
            InventoryService.apply_invoice_quantity_deltas(
                warehouse=new_wh,
                quantity_by_product=deduct,
                reference_id=invoice.id,
                user=user,
                notes=f"Sale move apply {invoice.invoice_number}",
            )

    @staticmethod
    def _apply_stock_for_delete(*, invoice, user=None):
        if not InventoryService.invoice_stock_tracked(invoice_id=invoice.id):
            return
        warehouse = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)
        if not warehouse:
            return
        sold = _aggregate_item_quantities(list(invoice.items.all()))
        restore = {pid: qty for pid, qty in sold.items() if qty}
        InventoryService.apply_invoice_quantity_deltas(
            warehouse=warehouse,
            quantity_by_product=restore,
            reference_id=invoice.id,
            user=user,
            notes=f"Sale deleted {invoice.invoice_number}",
        )

    @staticmethod
    @transaction.atomic
    def update(*, instance, data, items=None, user=None):
        if instance.status == Invoice.STATUS_CANCELLED:
            raise ValueError("Cancelled invoices/receipts cannot be edited.")
        old_branch = instance.branch
        old_items_qty = _aggregate_item_quantities(list(instance.items.all()))
        customer_id = data.pop("customer_id", None)
        branch_id = data.pop("branch_id", None)
        if customer_id:
            instance.customer_id = customer_id
        if branch_id:
            instance.branch_id = branch_id
        for key, value in data.items():
            if key not in ("invoice_number",):
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                InvoiceItem.objects.create(
                    invoice=instance,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    created_by=user,
                )
            InvoiceService._recalculate(invoice=instance)
            instance.refresh_from_db()
            InvoiceService._apply_stock_for_update(
                invoice=instance,
                old_branch=old_branch,
                old_items_qty=old_items_qty,
                new_items=items,
                user=user,
            )
        return InvoiceService.list().get(pk=instance.pk)

    @staticmethod
    @transaction.atomic
    def delete(*, instance, user=None):
        if instance.status == Invoice.STATUS_CANCELLED:
            raise ValueError("Invoice/receipt is already cancelled.")
        InvoiceService._apply_stock_for_delete(invoice=instance, user=user)
        instance.status = Invoice.STATUS_CANCELLED
        instance.updated_by = user
        instance.save(update_fields=["status", "updated_by", "updated_at"])
        instance.soft_delete(user=user)
        return instance

    @staticmethod
    def _set_payment_method_in_notes(notes: str, method: str) -> str:
        import re

        text = notes or ""
        if re.search(r"Payment:\s*[a-z_]+", text, re.IGNORECASE):
            return re.sub(
                r"Payment:\s*[a-z_]+",
                f"Payment: {method}",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        return f"{text}\nPayment: {method}".strip() if text else f"Payment: {method}"

    @staticmethod
    @transaction.atomic
    def mark_paid(*, instance, user=None, payment_method: str = "cash"):
        if instance.status == Invoice.STATUS_PAID:
            raise ValueError("Invoice is already paid.")
        if instance.status == Invoice.STATUS_CANCELLED:
            raise ValueError("Cancelled invoices cannot be marked as paid.")
        method = (payment_method or "cash").strip().lower() or "cash"
        instance.status = Invoice.STATUS_PAID
        instance.amount_paid = instance.total_amount
        instance.notes = InvoiceService._set_payment_method_in_notes(instance.notes or "", method)
        instance.updated_by = user
        instance.save(update_fields=["status", "amount_paid", "notes", "updated_by", "updated_at"])
        return InvoiceService.list().get(pk=instance.pk)

    @staticmethod
    @transaction.atomic
    def mark_unpaid(*, instance, user=None):
        if instance.status == Invoice.STATUS_CANCELLED:
            raise ValueError("Cancelled invoices cannot be marked as unpaid.")
        if instance.status == Invoice.STATUS_SENT and instance.amount_paid == 0:
            raise ValueError("Invoice is already unpaid.")
        instance.status = Invoice.STATUS_SENT
        instance.amount_paid = Decimal("0")
        if not instance.due_date:
            from datetime import timedelta

            instance.due_date = timezone.localdate() + timedelta(days=30)
        instance.notes = InvoiceService._set_payment_method_in_notes(
            instance.notes or "", "on_account"
        )
        instance.updated_by = user
        instance.save(
            update_fields=["status", "amount_paid", "due_date", "notes", "updated_by", "updated_at"]
        )
        return InvoiceService.list().get(pk=instance.pk)

    @staticmethod
    def summary():
        qs = Invoice.active_objects()
        by_status = qs.values("status").annotate(count=Count("id"))
        status_map = {row["status"]: row["count"] for row in by_status}
        today = timezone.localdate()
        month_start = today.replace(day=1)
        today_total = float(
            qs.filter(issue_date=today, status=Invoice.STATUS_PAID).aggregate(t=Sum("total_amount"))["t"] or 0
        )
        month_total = float(
            qs.filter(issue_date__gte=month_start, status=Invoice.STATUS_PAID).aggregate(t=Sum("total_amount"))["t"] or 0
        )
        return {
            "today_sales": today_total,
            "month_sales": month_total,
            "open_invoices": status_map.get(Invoice.STATUS_SENT, 0) + status_map.get(Invoice.STATUS_DRAFT, 0),
            "quotations_count": Quotation.active_objects().count(),
        }


def _resolve_branch(branch_id):
    if branch_id:
        return Branch.active_objects().get(pk=branch_id)
    branch = Branch.active_objects().filter(is_default=True).first()
    return branch or Branch.active_objects().first()

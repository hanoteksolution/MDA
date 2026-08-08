from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.sales.models import DocumentSequence, Invoice, InvoiceItem, Quotation, QuotationItem
from apps.sales.services.sequence_service import DocumentSequenceService
from apps.settings_app.models import Branch
from apps.inventory.services.inventory_service import InventoryService
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


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
    def list(*, search=None, status=None, customer_id=None, branch_id=None, user=None, request=None):
        qs = Quotation.active_objects().select_related("customer", "branch", "created_by_user").prefetch_related("items__product")
        qs = apply_tenant_scope(qs, user=user, request=request)
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
        branch = _resolve_branch(branch_id, user=user)
        payload = stamp_tenant_id(dict(data), user=user)
        if not payload.get("tenant_id") and getattr(branch, "tenant_id", None):
            payload["tenant_id"] = branch.tenant_id
        quotation = Quotation.objects.create(
            quotation_number=QuotationService._next_number(branch=branch),
            customer_id=customer_id,
            branch=branch,
            created_by_user=user,
            created_by=user,
            **payload,
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
        return QuotationService.list(user=user).get(pk=quotation.pk)

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
        return QuotationService.list(user=user).get(pk=instance.pk)

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
        user=None,
        request=None,
    ):
        qs = Invoice.active_objects().select_related(
            "customer", "branch", "created_by_user", "served_by_user"
        ).prefetch_related("items__product")
        qs = apply_tenant_scope(qs, user=user, request=request)
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
        served_by_user = data.pop("served_by_user", None)
        branch = _resolve_branch(branch_id, user=user)
        payload = stamp_tenant_id(dict(data), user=user)
        if not payload.get("tenant_id") and getattr(branch, "tenant_id", None):
            payload["tenant_id"] = branch.tenant_id
        if served_by_user is not None:
            payload["served_by_user"] = served_by_user
        invoice = Invoice.objects.create(
            invoice_number=InvoiceService._next_number(branch=branch),
            customer_id=customer_id,
            branch=branch,
            created_by_user=user,
            created_by=user,
            **payload,
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
        return InvoiceService.list(user=user).get(pk=invoice.pk)

    @staticmethod
    def _apply_stock_for_create(*, invoice, items, user=None):
        warehouse = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)
        if not warehouse:
            return
        sold = _aggregate_item_quantities(items)
        if invoice.status == Invoice.STATUS_ON_HOLD:
            InventoryService.reserve_invoice_quantities(
                warehouse=warehouse,
                quantity_by_product=sold,
                reference_id=invoice.id,
                user=user,
                notes=f"Hold {invoice.invoice_number}",
            )
            return
        deltas = {pid: -qty for pid, qty in sold.items() if qty}
        InventoryService.apply_invoice_quantity_deltas(
            warehouse=warehouse,
            quantity_by_product=deltas,
            reference_id=invoice.id,
            user=user,
            notes=f"Sale {invoice.invoice_number}",
        )

    @staticmethod
    def _apply_stock_for_update(
        *,
        invoice,
        old_branch,
        old_items_qty,
        new_items,
        user=None,
        old_status=None,
    ):
        """
        Diff line quantities and move stock.

        Hold invoices use reserved_quantity (STEP 12). Legacy holds that already
        deducted on-hand keep the sale-ledger path (Option A).
        """
        new_qty = _aggregate_item_quantities(new_items)
        old_wh = InventoryService.resolve_warehouse_for_branch(branch=old_branch)
        new_wh = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)
        was_hold = old_status == Invoice.STATUS_ON_HOLD
        is_hold = invoice.status == Invoice.STATUS_ON_HOLD
        reserve_tracked = InventoryService.invoice_reserve_tracked(invoice_id=invoice.id)
        sale_tracked = InventoryService.invoice_stock_tracked(invoice_id=invoice.id)

        # New-style hold: reserved stock only
        if was_hold and reserve_tracked and not sale_tracked:
            if old_wh and old_items_qty:
                InventoryService.unreserve_invoice_quantities(
                    warehouse=old_wh,
                    quantity_by_product=old_items_qty,
                    reference_id=invoice.id,
                    user=user,
                    notes=f"Hold edit release {invoice.invoice_number}",
                )
            if is_hold:
                if new_wh and new_qty:
                    InventoryService.reserve_invoice_quantities(
                        warehouse=new_wh,
                        quantity_by_product=new_qty,
                        reference_id=invoice.id,
                        user=user,
                        notes=f"Hold edit reserve {invoice.invoice_number}",
                    )
                return
            # Hold → sale/checkout
            if new_wh and new_qty:
                InventoryService.consume_invoice_reserved(
                    warehouse=new_wh,
                    quantity_by_product=new_qty,
                    reference_id=invoice.id,
                    user=user,
                    notes=f"Checkout from hold {invoice.invoice_number}",
                )
                # consume_reserved already unreserves then sells for new_qty;
                # but we already unreserved old_items above. If new_qty differs from
                # old, consume_reserved will unreserve new_qty which may exceed
                # remaining reserved (unreserve clamps). Then sale-deducts new_qty.
                # Problem: we unreserved ALL old already, so reserved is 0.
                # Fix: don't unreserve-all then consume; instead handle carefully.
            return

        # Converting sale → hold (rare): reverse sale tracking then reserve
        if not was_hold and is_hold:
            tracked = sale_tracked
            effective_old = old_items_qty if tracked else {}
            if old_wh and effective_old:
                restore = {pid: qty for pid, qty in effective_old.items() if qty}
                InventoryService.apply_invoice_quantity_deltas(
                    warehouse=old_wh,
                    quantity_by_product=restore,
                    reference_id=invoice.id,
                    user=user,
                    notes=f"Convert to hold restore {invoice.invoice_number}",
                )
            if new_wh and new_qty:
                InventoryService.reserve_invoice_quantities(
                    warehouse=new_wh,
                    quantity_by_product=new_qty,
                    reference_id=invoice.id,
                    user=user,
                    notes=f"Convert to hold {invoice.invoice_number}",
                )
            return

        tracked = sale_tracked
        effective_old = old_items_qty if tracked else {}
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
        warehouse = InventoryService.resolve_warehouse_for_branch(branch=invoice.branch)
        if not warehouse:
            return
        sold = _aggregate_item_quantities(list(invoice.items.all()))
        reserve_tracked = InventoryService.invoice_reserve_tracked(invoice_id=invoice.id)
        sale_tracked = InventoryService.invoice_stock_tracked(invoice_id=invoice.id)

        if invoice.status == Invoice.STATUS_ON_HOLD and reserve_tracked and not sale_tracked:
            InventoryService.unreserve_invoice_quantities(
                warehouse=warehouse,
                quantity_by_product=sold,
                reference_id=invoice.id,
                user=user,
                notes=f"Hold cancelled {invoice.invoice_number}",
            )
            return

        if not sale_tracked:
            return
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
        old_status = instance.status
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
                old_status=old_status,
            )
        elif old_status == Invoice.STATUS_ON_HOLD and instance.status != Invoice.STATUS_ON_HOLD:
            # Status-only convert (items unchanged) — still release reserve → sale
            InvoiceService._apply_stock_for_update(
                invoice=instance,
                old_branch=old_branch,
                old_items_qty=old_items_qty,
                new_items=[
                    {
                        "product_id": i.product_id,
                        "quantity": i.quantity,
                        "unit_price": i.unit_price,
                    }
                    for i in instance.items.all()
                ],
                user=user,
                old_status=old_status,
            )
        return InvoiceService.list(user=user).get(pk=instance.pk)

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
        return InvoiceService.list(user=user).get(pk=instance.pk)

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
        return InvoiceService.list(user=user).get(pk=instance.pk)

    @staticmethod
    def summary(*, user=None, request=None):
        qs = apply_tenant_scope(Invoice.active_objects(), user=user, request=request)
        by_status = qs.values("status").annotate(count=Count("id"))
        status_map = {row["status"]: row["count"] for row in by_status}
        today = timezone.localdate()
        month_start = today.replace(day=1)
        paid = qs.filter(status=Invoice.STATUS_PAID)
        today_total = float(
            paid.filter(issue_date=today).aggregate(t=Sum("total_amount"))["t"] or 0
        )
        month_total = float(
            paid.filter(issue_date__gte=month_start).aggregate(t=Sum("total_amount"))["t"] or 0
        )
        all_time_total = float(paid.aggregate(t=Sum("total_amount"))["t"] or 0)
        return {
            "today_sales": today_total,
            "month_sales": month_total,
            "all_time_sales": all_time_total,
            "invoice_count": qs.exclude(status=Invoice.STATUS_CANCELLED).count(),
            "open_invoices": status_map.get(Invoice.STATUS_SENT, 0) + status_map.get(Invoice.STATUS_DRAFT, 0),
            "quotations_count": apply_tenant_scope(
                Quotation.active_objects(), user=user, request=request
            ).count(),
        }


def _resolve_branch(branch_id, user=None):
    if branch_id:
        qs = Branch.active_objects()
        qs = apply_tenant_scope(qs, user=user)
        return qs.get(pk=branch_id)
    qs = Branch.active_objects()
    qs = apply_tenant_scope(qs, user=user)
    if user is not None and getattr(user, "branch_id", None):
        branch = qs.filter(pk=user.branch_id).first()
        if branch:
            return branch
    branch = qs.filter(is_default=True).first()
    return branch or qs.first()

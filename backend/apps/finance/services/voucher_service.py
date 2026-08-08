"""Receipt and payment vouchers — settle AR / AP through the Central Accounting Engine."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.finance.models import SupplierPayment
from apps.finance.services.posting_service import AccountingPostingService, PostingError
from apps.purchases.models import PurchaseOrder
from apps.sales.models import Invoice, Payment
from core.tenancy import apply_tenant_scope, stamp_tenant_id

MONEY = Decimal("0.01")


class VoucherError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _parse_paid_at(paid_at):
    if paid_at is None:
        return timezone.now()
    if isinstance(paid_at, datetime):
        return paid_at
    if isinstance(paid_at, str):
        dt = parse_datetime(paid_at)
        if dt:
            return dt
        d = parse_date(paid_at)
        if d:
            naive = datetime.combine(d, time.min)
            if timezone.is_aware(timezone.now()):
                return timezone.make_aware(naive)
            return naive
    return timezone.now()


class VoucherService:
    @staticmethod
    def serialize_receipt(payment: Payment) -> dict:
        inv = payment.invoice
        return {
            "id": str(payment.id),
            "type": "receipt",
            "invoice_id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer.full_name if inv.customer_id else "",
            "method": payment.method,
            "amount": float(payment.amount),
            "reference": payment.reference or "",
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "branch_id": str(payment.branch_id) if payment.branch_id else None,
        }

    @staticmethod
    def serialize_supplier_payment(payment: SupplierPayment) -> dict:
        po = payment.purchase_order
        return {
            "id": str(payment.id),
            "type": "supplier_payment",
            "purchase_order_id": str(po.id),
            "order_number": po.order_number,
            "supplier_name": po.supplier.company_name if po.supplier_id else "",
            "method": payment.method,
            "amount": float(payment.amount),
            "reference": payment.reference or "",
            "notes": payment.notes or "",
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "branch_id": str(payment.branch_id) if payment.branch_id else None,
        }

    @staticmethod
    def invoice_balance(invoice: Invoice) -> Decimal:
        balance = _money(invoice.total_amount) - _money(invoice.amount_paid)
        if hasattr(invoice, "amount_refunded"):
            balance -= _money(invoice.amount_refunded or 0)
        return max(balance, Decimal("0"))

    @staticmethod
    def purchase_order_ap_balance(purchase_order: PurchaseOrder) -> Decimal:
        received = Decimal("0")
        for item in purchase_order.items.all():
            qty = Decimal(str(item.quantity_received or 0))
            if qty <= 0:
                continue
            received += qty * Decimal(str(item.unit_cost))
        paid = (
            purchase_order.supplier_payments.filter(deleted_at__isnull=True).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )
        return max(_money(received) - _money(paid), Decimal("0"))

    @staticmethod
    @transaction.atomic
    def record_customer_receipt(
        *,
        invoice_id,
        amount,
        method="cash",
        reference="",
        paid_at=None,
        user=None,
        request=None,
    ) -> Payment:
        """Apply a customer payment against an open invoice — Cr AR / Dr cash asset."""
        qs = apply_tenant_scope(
            Invoice.active_objects().select_related("branch", "customer"),
            user=user,
            request=request,
        )
        invoice = qs.filter(pk=invoice_id).first()
        if not invoice:
            raise VoucherError("Invoice not found.")
        if invoice.status in (Invoice.STATUS_DRAFT, Invoice.STATUS_CANCELLED, Invoice.STATUS_ON_HOLD):
            raise VoucherError("Cannot receive payment on this invoice status.")

        amount = _money(amount)
        if amount <= 0:
            raise VoucherError("Payment amount must be positive.")

        balance = VoucherService.invoice_balance(invoice)
        if amount > balance + Decimal("0.005"):
            raise VoucherError(
                f"Payment ({amount}) exceeds outstanding balance ({balance})."
            )

        method = (method or Payment.METHOD_CASH).strip().lower()
        if method == Payment.METHOD_ON_ACCOUNT:
            raise VoucherError("Receipt method cannot be on_account.")
        if method not in dict(Payment.METHOD_CHOICES):
            method = Payment.METHOD_OTHER

        paid_at = _parse_paid_at(paid_at)
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id") or invoice.tenant_id
        if not tenant_id:
            raise VoucherError("Tenant could not be resolved.")

        payment = Payment.objects.create(
            invoice=invoice,
            branch=invoice.branch,
            method=method,
            amount=amount,
            reference=reference or "",
            paid_at=paid_at,
            tenant_id=tenant_id,
            created_by=user,
        )

        new_paid = _money(invoice.amount_paid) + amount
        invoice.amount_paid = new_paid
        update_fields = ["amount_paid", "updated_at"]
        if new_paid + Decimal("0.005") >= _money(invoice.total_amount):
            invoice.status = Invoice.STATUS_PAID
            update_fields.append("status")
        elif invoice.status == Invoice.STATUS_DRAFT:
            invoice.status = Invoice.STATUS_SENT
            update_fields.append("status")
        invoice.save(update_fields=update_fields)

        try:
            AccountingPostingService.post_customer_payment(
                payment=payment, invoice=invoice, user=user
            )
        except PostingError as exc:
            raise VoucherError(str(exc)) from exc

        return payment

    @staticmethod
    @transaction.atomic
    def record_supplier_payment(
        *,
        purchase_order_id,
        amount,
        method="cash",
        reference="",
        notes="",
        paid_at=None,
        branch_id=None,
        user=None,
        request=None,
    ) -> SupplierPayment:
        """Pay a supplier against goods received — Dr AP / Cr cash asset."""
        qs = apply_tenant_scope(
            PurchaseOrder.active_objects()
            .select_related("supplier", "branch")
            .prefetch_related("items", "supplier_payments"),
            user=user,
            request=request,
        )
        po = qs.filter(pk=purchase_order_id).first()
        if not po:
            raise VoucherError("Purchase order not found.")
        if po.status == PurchaseOrder.STATUS_CANCELLED:
            raise VoucherError("Cannot pay a cancelled purchase order.")

        amount = _money(amount)
        if amount <= 0:
            raise VoucherError("Payment amount must be positive.")

        balance = VoucherService.purchase_order_ap_balance(po)
        if amount > balance + Decimal("0.005"):
            raise VoucherError(
                f"Payment ({amount}) exceeds outstanding AP ({balance})."
            )

        method = (method or SupplierPayment.METHOD_CASH).strip().lower()
        if method not in dict(SupplierPayment.METHOD_CHOICES):
            method = SupplierPayment.METHOD_OTHER

        paid_at = _parse_paid_at(paid_at)
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id") or po.tenant_id
        if not tenant_id:
            raise VoucherError("Tenant could not be resolved.")

        branch = po.branch
        if branch_id:
            from apps.settings_app.models import Branch

            branch_qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
            found = branch_qs.filter(pk=branch_id).first()
            if found:
                branch = found

        payment = SupplierPayment.objects.create(
            purchase_order=po,
            branch=branch,
            method=method,
            amount=amount,
            reference=reference or "",
            notes=notes or "",
            paid_at=paid_at,
            paid_by=user,
            tenant_id=tenant_id,
            created_by=user,
        )

        try:
            AccountingPostingService.post_supplier_payment(payment=payment, user=user)
        except PostingError as exc:
            raise VoucherError(str(exc)) from exc

        return payment

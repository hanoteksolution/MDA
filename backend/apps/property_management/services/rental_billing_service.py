"""Shared rental lease-charge → Invoice / Payment / CAE (housing + office).

No parallel PropertyAccounting — posts through apps.sales + apps.finance.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice, Payment
from apps.sales.services.sales_service import InvoiceService
from apps.settings_app.models import Branch


MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY)


class RentalBillingError(ValueError):
    pass


class RentalBillingService:
    @staticmethod
    def _normalize_method(method: str) -> str:
        method = (method or "cash").strip().lower()
        if method in ("cash", "mobile", "card"):
            return method
        if method in ("bank",):
            return "card"
        if method in ("on_account", "invoice", ""):
            return "on_account"
        return "cash"

    @staticmethod
    @transaction.atomic
    def ensure_service_product(
        *,
        tenant_id,
        sku: str,
        name: str,
        category_name: str = "Rental",
        user=None,
    ) -> Product:
        existing = Product.active_objects().filter(tenant_id=tenant_id, sku=sku).first()
        if existing:
            return existing
        category = Category.active_objects().filter(
            tenant_id=tenant_id, name__iexact=category_name
        ).first()
        if category is None:
            category = Category.objects.create(
                name=category_name,
                description="Rental and property service lines",
                tenant_id=tenant_id,
                created_by=user,
            )
        unit = Unit.active_objects().filter(
            tenant_id=tenant_id, abbreviation__iexact="mo"
        ).first()
        if unit is None:
            unit = Unit.objects.create(
                name="Month",
                abbreviation="mo",
                tenant_id=tenant_id,
                created_by=user,
            )
        return Product.objects.create(
            sku=sku[:100],
            name=name,
            category=category,
            unit=unit,
            cost_price=Decimal("0"),
            selling_price=Decimal("0"),
            minimum_stock=0,
            description=name,
            tenant_id=tenant_id,
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def ensure_customer(
        *,
        tenant_id,
        branch: Branch,
        full_name: str,
        phone: str = "",
        email: str = "",
        code_prefix: str = "RNT",
        existing_customer=None,
        user=None,
    ) -> Customer:
        if existing_customer is not None:
            return existing_customer
        code_base = (full_name or "Tenant").replace(" ", "-")[:40]
        code = f"{code_prefix}-{code_base}"[:80]
        existing = Customer.active_objects().filter(
            tenant_id=tenant_id, customer_code=code
        ).first()
        if existing:
            return existing
        n = 0
        while Customer.active_objects().filter(
            tenant_id=tenant_id, customer_code=code
        ).exists():
            n += 1
            code = f"{code_prefix}-{code_base}-{n}"[:80]
        return Customer.objects.create(
            customer_code=code,
            full_name=full_name,
            phone=phone or "",
            email=email or "",
            customer_type="retail",
            branch=branch,
            tenant_id=tenant_id,
            created_by=user,
        )

    @staticmethod
    def revenue_mapping_key(*, charge_type: str, vertical: str) -> str:
        if charge_type == "deposit":
            return "SECURITY_DEPOSIT_LIABILITY"
        if vertical == "office":
            return "OFFICE_RENT_REVENUE"
        return "HOUSING_RENT_REVENUE"

    @staticmethod
    @transaction.atomic
    def create_invoice_for_charge(
        *,
        charge,
        customer: Customer,
        branch: Branch,
        product: Product,
        vertical: str,
        payment_method: str = "on_account",
        payment_reference: str = "",
        lease_label: str = "",
        user=None,
    ) -> Invoice:
        if charge.invoice_id:
            raise RentalBillingError("Charge already has an invoice.")
        if charge.status in ("paid", "cancelled"):
            raise RentalBillingError(f"Cannot invoice a {charge.status} charge.")

        amount = _money(charge.amount)
        if amount <= 0:
            raise RentalBillingError("Charge amount must be positive.")

        method = RentalBillingService._normalize_method(payment_method)
        is_on_account = method == "on_account"
        invoice_status = Invoice.STATUS_SENT if is_on_account else Invoice.STATUS_PAID
        amount_paid = Decimal("0") if is_on_account else amount
        mapping_key = RentalBillingService.revenue_mapping_key(
            charge_type=charge.charge_type, vertical=vertical
        )

        notes = (
            f"Rental charge · {vertical} · {lease_label or charge.lease_id}\n"
            f"Charge: {charge.id}\n"
            f"Type: {charge.charge_type}\n"
            f"Payment: {method}"
        )
        if payment_reference:
            notes += f" | Ref: {payment_reference}"

        invoice = InvoiceService.create(
            data={
                "customer_id": str(customer.id),
                "branch_id": str(branch.id),
                "status": invoice_status,
                "issue_date": timezone.localdate(),
                "due_date": charge.due_date or timezone.localdate(),
                "discount_amount": Decimal("0"),
                "amount_paid": amount_paid,
                "notes": notes,
            },
            items=[
                {
                    "product_id": str(product.id),
                    "quantity": Decimal("1"),
                    "unit_price": amount,
                }
            ],
            user=user,
        )
        invoice.tax_amount = Decimal("0")
        invoice.total_amount = amount
        invoice.subtotal = amount
        invoice.save(
            update_fields=["tax_amount", "total_amount", "subtotal", "updated_at"]
        )

        if not is_on_account:
            pay_method = (
                method if method in dict(Payment.METHOD_CHOICES) else Payment.METHOD_OTHER
            )
            Payment.objects.create(
                invoice=invoice,
                branch=branch,
                method=pay_method,
                amount=amount,
                reference=payment_reference or f"charge:{charge.id}",
                tenant_id=charge.tenant_id,
                created_by=user,
            )

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_sale(
            invoice=invoice,
            user=user,
            payment_method=method,
            revenue_mapping_key=mapping_key,
        )

        charge.invoice = invoice
        charge.status = (
            charge.__class__.STATUS_PAID
            if not is_on_account
            else charge.__class__.STATUS_INVOICED
        )
        charge.updated_by = user
        charge.save(update_fields=["invoice", "status", "updated_by", "updated_at"])
        return invoice

    @staticmethod
    @transaction.atomic
    def collect_invoice_for_charge(
        *,
        charge,
        payment_method: str = "cash",
        payment_reference: str = "",
        user=None,
    ) -> Invoice:
        if charge.status == "cancelled":
            raise RentalBillingError("Charge is cancelled.")
        if not charge.invoice_id:
            raise RentalBillingError("Invoice the charge before collecting payment.")

        invoice = charge.invoice
        if invoice.status == Invoice.STATUS_PAID:
            charge.status = charge.__class__.STATUS_PAID
            charge.updated_by = user
            charge.save(update_fields=["status", "updated_by", "updated_at"])
            return invoice

        method = RentalBillingService._normalize_method(payment_method)
        if method == "on_account":
            raise RentalBillingError("Select cash, mobile, or card to collect payment.")

        due = _money(invoice.total_amount - invoice.amount_paid)
        if due <= 0:
            InvoiceService.mark_paid(instance=invoice, user=user, payment_method=method)
            charge.status = charge.__class__.STATUS_PAID
            charge.updated_by = user
            charge.save(update_fields=["status", "updated_by", "updated_at"])
            return invoice

        pay_method = (
            method if method in dict(Payment.METHOD_CHOICES) else Payment.METHOD_OTHER
        )
        payment = Payment.objects.create(
            invoice=invoice,
            branch=invoice.branch,
            method=pay_method,
            amount=due,
            reference=payment_reference or f"charge:{charge.id}",
            tenant_id=invoice.tenant_id,
            created_by=user,
        )
        InvoiceService.mark_paid(instance=invoice, user=user, payment_method=method)
        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_customer_payment(
            payment=payment, invoice=invoice, user=user
        )

        charge.status = charge.__class__.STATUS_PAID
        charge.updated_by = user
        charge.save(update_fields=["status", "updated_by", "updated_at"])
        return invoice

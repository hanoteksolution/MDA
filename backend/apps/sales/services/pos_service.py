import re
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.sales.models import Invoice
from apps.sales.serializers.sales_serializers import serialize_invoice
from apps.sales.services.sales_service import InvoiceService, _resolve_branch
from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import SettingsService
from core.utils.media import resolve_product_image_url

DEFAULT_RETURN_POLICY = (
    "Items can be returned within 7 days with the original receipt. Terms and conditions apply."
)

PAYMENT_LABELS = {
    "cash": "Cash",
    "card": "Card",
    "mobile": "Mobile Money",
    "bank": "Bank Transfer",
    "split": "Split Payment",
    "invoice": "Invoice",
}


def _parse_payment_from_notes(notes: str) -> tuple[str, str]:
    """Return (payment_method, payment_reference) parsed from invoice notes."""
    payment_method = "cash"
    payment_reference = ""
    if not notes:
        return payment_method, payment_reference

    method_match = re.search(r"Payment:\s*([a-z_]+)", notes, re.IGNORECASE)
    if method_match:
        payment_method = method_match.group(1).lower()

    ref_match = re.search(r"Ref:\s*([^|]+)", notes, re.IGNORECASE)
    if ref_match:
        payment_reference = ref_match.group(1).strip()

    return payment_method, payment_reference


def _pos_profile_key(user_id) -> str:
    return f"pos_profile_{user_id}"


def get_pos_profile(*, user):
    setting = SettingsService.get_by_key(key=_pos_profile_key(user.id))
    if setting:
        return setting.value
    return {
        "merchants": [],
        "default_payment_method": "cash",
        "receipt_footer": "Thank you for shopping with us! We appreciate your business.",
        "return_policy": DEFAULT_RETURN_POLICY,
    }


def save_pos_profile(*, user, data):
    return SettingsService.upsert(
        key=_pos_profile_key(user.id),
        value=data,
        category="pos",
        user=user,
    )


def _resolve_walkin_customer(*, branch: Branch) -> Customer:
    customer = Customer.active_objects().filter(full_name__iexact="Walk-in Customer").first()
    if customer:
        return customer
    return Customer.objects.create(
        customer_code=f"WALKIN-{branch.code}",
        full_name="Walk-in Customer",
        email="",
        phone="",
        customer_type="retail",
        branch=branch,
        is_active=True,
    )


class PosService:
    @staticmethod
    @transaction.atomic
    def checkout(*, data, user):
        branch_id = data.get("branch_id")
        branch = _resolve_branch(branch_id)
        customer_id = data.get("customer_id")
        if customer_id and customer_id != "walkin":
            customer = Customer.active_objects().get(pk=customer_id)
        else:
            customer = _resolve_walkin_customer(branch=branch)

        items = data.get("items") or []
        if not items:
            raise ValueError("Cart is empty.")

        discount_pct = Decimal(str(data.get("discount_pct") or 0))
        discount_amount_raw = data.get("discount_amount")
        tax_rate = Decimal(str(data.get("tax_rate") or 0))
        payment_method = data.get("payment_method") or "cash"
        merchant_id = data.get("merchant_id")
        order_notes = data.get("notes") or ""
        amount_tendered = data.get("amount_tendered")
        payment_reference = (data.get("payment_reference") or "").strip()

        profile = get_pos_profile(user=user)
        merchant = None
        for m in profile.get("merchants") or []:
            if m.get("id") == merchant_id:
                merchant = m
                break
        if not merchant and profile.get("merchants"):
            merchant = next((m for m in profile["merchants"] if m.get("is_default")), profile["merchants"][0])

        parsed_items = [
            {
                "product_id": item["product_id"],
                "quantity": Decimal(str(item["quantity"])),
                "unit_price": Decimal(str(item["unit_price"])),
            }
            for item in items
        ]

        subtotal = sum(i["quantity"] * i["unit_price"] for i in parsed_items)
        if discount_amount_raw is not None and str(discount_amount_raw).strip() != "":
            discount_amount = min(subtotal, Decimal(str(discount_amount_raw)))
        else:
            discount_amount = subtotal * (discount_pct / Decimal("100"))
        after_discount = subtotal - discount_amount
        tax_amount = after_discount * tax_rate
        total_amount = after_discount + tax_amount

        payment_note = f"Payment: {payment_method}"
        if merchant:
            payment_note += f" | Merchant: {merchant.get('merchant_number', '')} ({merchant.get('company_name', '')})"
        notes = f"{order_notes}\n{payment_note}".strip() if order_notes else payment_note

        invoice = InvoiceService.create(
            data={
                "customer_id": str(customer.id),
                "branch_id": str(branch.id),
                "status": Invoice.STATUS_PAID,
                "issue_date": timezone.localdate(),
                "discount_amount": discount_amount,
                "amount_paid": total_amount,
                "notes": notes,
            },
            items=parsed_items,
            user=user,
        )
        invoice.tax_amount = tax_amount
        invoice.total_amount = total_amount
        invoice.save(update_fields=["tax_amount", "total_amount", "updated_at"])
        invoice = InvoiceService.list().get(pk=invoice.pk)

        company = Company.active_objects().first()
        change = None
        if amount_tendered is not None and payment_method == "cash":
            change = float(Decimal(str(amount_tendered)) - total_amount)

        receipt = PosService.build_receipt(
            invoice=invoice,
            company=company,
            branch=branch,
            user=user,
            payment_method=payment_method,
            merchant=merchant,
            profile=profile,
            amount_tendered=amount_tendered,
            change=change,
            payment_reference=payment_reference,
            tax_rate=tax_rate,
        )
        return {"invoice": serialize_invoice(invoice, include_items=True), "receipt": receipt}

    @staticmethod
    def build_receipt(
        *,
        invoice,
        company,
        branch,
        user,
        payment_method,
        merchant,
        profile,
        amount_tendered=None,
        change=None,
        payment_reference="",
        tax_rate=Decimal("0"),
    ):
        now = timezone.localtime()
        after_discount = invoice.subtotal - invoice.discount_amount
        computed_tax_rate = float(tax_rate)
        if computed_tax_rate <= 0 and after_discount > 0 and invoice.tax_amount > 0:
            computed_tax_rate = float(invoice.tax_amount / after_discount)

        loyalty_earned = int(invoice.total_amount // 10)
        loyalty_total = loyalty_earned + 1160

        return {
            "invoice_number": invoice.invoice_number,
            "invoice_id": str(invoice.id),
            "date": invoice.issue_date.isoformat(),
            "time": now.strftime("%H:%M"),
            "datetime_display": now.strftime("%b %d, %Y · %I:%M %p"),
            "cashier": user.get_full_name() or user.username,
            "terminal": "POS-001",
            "customer_name": invoice.customer.full_name,
            "customer_address": invoice.customer.address or "",
            "customer_phone": invoice.customer.phone or "",
            "customer_email": invoice.customer.email or "",
            "company": {
                "name": company.name if company else branch.name,
                "legal_name": company.legal_name if company else "",
                "tax_id": company.tax_id if company else "",
                "email": company.email if company else "",
                "phone": company.phone if company else branch.phone,
                "address": company.address if company else branch.address,
                "logo": company.logo if company else "",
            },
            "branch": {
                "name": branch.name,
                "code": branch.code,
                "phone": branch.phone,
                "address": branch.address,
            },
            "merchant": merchant,
            "merchant_reference": merchant.get("merchant_number", "") if merchant else "",
            "payment_reference": payment_reference,
            "items": [
                {
                    "name": i.product.name,
                    "sku": i.product.sku,
                    "quantity": float(i.quantity),
                    "unit_price": float(i.unit_price),
                    "line_total": float(i.line_total),
                    "image": resolve_product_image_url(i.product.image),
                }
                for i in invoice.items.select_related("product")
            ],
            "subtotal": float(invoice.subtotal),
            "discount_amount": float(invoice.discount_amount),
            "tax_amount": float(invoice.tax_amount),
            "tax_rate": computed_tax_rate,
            "total_amount": float(invoice.total_amount),
            "payment_method": payment_method,
            "payment_method_label": PAYMENT_LABELS.get(payment_method, payment_method.title()),
            "amount_tendered": float(amount_tendered) if amount_tendered is not None else None,
            "change": change,
            "footer": profile.get("receipt_footer")
            or "Thank you for shopping with us! We appreciate your business.",
            "return_policy": profile.get("return_policy") or DEFAULT_RETURN_POLICY,
            "verification_path": f"/receipt/verify/{invoice.id}",
            "loyalty_points_earned": loyalty_earned,
            "loyalty_points_total": loyalty_total,
        }

    @staticmethod
    def receipt_from_invoice(*, invoice, user):
        """Build a printable receipt payload for an existing sales invoice."""
        branch = invoice.branch
        company = Company.active_objects().first()
        profile = get_pos_profile(user=user)
        payment_method, payment_reference = _parse_payment_from_notes(invoice.notes or "")
        if invoice.status != "paid" and payment_method == "cash":
            payment_method = "invoice"

        cashier = user
        if getattr(invoice, "created_by_user", None):
            cashier = invoice.created_by_user

        after_discount = invoice.subtotal - invoice.discount_amount
        tax_rate = Decimal("0")
        if after_discount > 0 and invoice.tax_amount > 0:
            tax_rate = invoice.tax_amount / after_discount

        receipt = PosService.build_receipt(
            invoice=invoice,
            company=company,
            branch=branch,
            user=cashier,
            payment_method=payment_method,
            merchant=None,
            profile=profile,
            payment_reference=payment_reference,
            tax_rate=tax_rate,
        )

        created = timezone.localtime(invoice.created_at)
        receipt["date"] = invoice.issue_date.isoformat()
        receipt["time"] = created.strftime("%H:%M")
        receipt["datetime_display"] = created.strftime("%b %d, %Y · %I:%M %p")
        receipt["terminal"] = "SALES"
        return receipt

    @staticmethod
    def delivery_note_from_invoice(*, invoice, user):
        """Build a printable delivery note payload for a sales invoice."""
        branch = invoice.branch
        company = Company.active_objects().first()
        cashier = user
        if getattr(invoice, "created_by_user", None):
            cashier = invoice.created_by_user

        suffix = invoice.invoice_number.split("-")[-1]
        date_part = invoice.issue_date.strftime("%d%m%Y")
        vehicle_no = ""
        for part in (invoice.notes or "").split("|"):
            part = part.strip()
            if part.lower().startswith("vehicle:"):
                vehicle_no = part.split(":", 1)[-1].strip()
                break

        return {
            "delivery_number": f"DN-{date_part}-{suffix}",
            "order_number": f"ORD-{date_part}-{suffix}",
            "invoice_number": invoice.invoice_number,
            "invoice_id": str(invoice.id),
            "delivery_date": invoice.issue_date.isoformat(),
            "sales_person": cashier.get_full_name() or cashier.username,
            "vehicle_no": vehicle_no or "—",
            "customer_name": invoice.customer.full_name,
            "customer_address": invoice.customer.address or "",
            "customer_phone": invoice.customer.phone or "",
            "company": {
                "name": company.name if company else branch.name,
                "phone": company.phone if company else branch.phone,
                "email": company.email if company else "",
                "website": "www.mdaretail.com",
                "address": company.address if company else branch.address,
            },
            "branch": {
                "name": branch.name,
                "code": branch.code,
                "address": branch.address,
            },
            "items": [
                {
                    "name": i.product.name,
                    "sku": i.product.sku,
                    "quantity_ordered": float(i.quantity),
                    "quantity_delivered": float(i.quantity),
                    "unit": i.product.unit.name if getattr(i.product, "unit", None) else "Pcs",
                }
                for i in invoice.items.select_related("product", "product__unit")
            ],
        }

"""Hotel folio settlement via central Invoice + Payment (no HotelAccounting)."""

from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.hotel.models import Folio, FolioLine, Guest
from apps.hotel.services.hotel_service import HotelError
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice, Payment
from apps.sales.services.sales_service import InvoiceService
from apps.settings_app.models import Branch

_INVOICE_NOTE_RE = re.compile(r"invoice:([A-Za-z0-9\-_]+)", re.IGNORECASE)
MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY)


class HotelSettlementService:
    """Settle guest folio at check-out through sales invoices + CAE."""

    @staticmethod
    @transaction.atomic
    def ensure_room_product(*, tenant_id, user=None) -> Product:
        sku = "hotel-room-night"
        existing = Product.active_objects().filter(tenant_id=tenant_id, sku=sku).first()
        if existing:
            return existing
        category = Category.active_objects().filter(
            tenant_id=tenant_id, name__iexact="Hotel"
        ).first()
        if category is None:
            category = Category.objects.create(
                name="Hotel",
                description="Room and hotel service lines",
                tenant_id=tenant_id,
                created_by=user,
            )
        unit = Unit.active_objects().filter(
            tenant_id=tenant_id, abbreviation__iexact="nt"
        ).first()
        if unit is None:
            unit = Unit.objects.create(
                name="Night",
                abbreviation="nt",
                tenant_id=tenant_id,
                created_by=user,
            )
        return Product.objects.create(
            sku=sku,
            name="Hotel Room Night",
            category=category,
            unit=unit,
            cost_price=Decimal("0"),
            selling_price=Decimal("0"),
            minimum_stock=0,
            description="Hotel room / folio settlement",
            tenant_id=tenant_id,
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def ensure_guest_customer(*, guest: Guest, branch: Branch, user=None) -> Customer:
        code_base = (guest.full_name or "Guest").replace(" ", "-")[:40]
        code = f"HTL-{code_base}"[:80]
        existing = Customer.active_objects().filter(
            tenant_id=guest.tenant_id, customer_code=code
        ).first()
        if existing:
            return existing
        n = 0
        while Customer.active_objects().filter(
            tenant_id=guest.tenant_id, customer_code=code
        ).exists():
            n += 1
            code = f"HTL-{code_base}-{n}"[:80]
        return Customer.objects.create(
            customer_code=code,
            full_name=guest.full_name,
            email=guest.email or "",
            phone=guest.phone or "",
            customer_type="retail",
            branch=branch,
            tenant_id=guest.tenant_id,
            created_by=user,
        )

    @staticmethod
    def _normalize_method(method: str) -> str:
        method = (method or "cash").strip().lower()
        if method in ("cash", "mobile", "card", "bank"):
            return "card" if method == "bank" else method
        if method == "charge_to_room":
            raise HotelError("Cannot settle folio with charge-to-room.")
        return "cash"

    @staticmethod
    @transaction.atomic
    def settle_folio(
        *,
        folio: Folio,
        payment_method: str = "cash",
        payment_reference: str = "",
        user=None,
    ) -> dict:
        if folio.status != Folio.STATUS_OPEN:
            raise HotelError("Folio is already closed.")

        outstanding = _money(folio.outstanding)
        method = HotelSettlementService._normalize_method(payment_method)
        reference = (payment_reference or "").strip()

        if outstanding <= 0:
            folio.amount_paid = folio.balance
            folio.payment_method = method if folio.balance else ""
            folio.settled_at = timezone.now()
            folio.updated_by = user
            folio.save(
                update_fields=[
                    "amount_paid",
                    "payment_method",
                    "settled_at",
                    "updated_by",
                    "updated_at",
                ]
            )
            return {
                "amount_settled": 0.0,
                "payment_method": folio.payment_method,
                "pos_invoices_paid": [],
                "room_invoice_id": None,
                "room_invoice_number": None,
            }

        lines = list(folio.lines.filter(deleted_at__isnull=True))
        paid_pos: list[dict] = []
        linked_amount = Decimal("0")
        seen_invoice_ids: set = set()

        for line in lines:
            match = _INVOICE_NOTE_RE.search(line.notes or "")
            if not match:
                continue
            inv_number = match.group(1)
            invoice = (
                Invoice.active_objects()
                .filter(tenant_id=folio.tenant_id, invoice_number=inv_number)
                .first()
            )
            if invoice is None:
                continue
            linked_amount += _money(line.amount)
            if invoice.id in seen_invoice_ids:
                continue
            seen_invoice_ids.add(invoice.id)
            if invoice.status == Invoice.STATUS_PAID:
                paid_pos.append(
                    {
                        "id": str(invoice.id),
                        "invoice_number": invoice.invoice_number,
                        "already_paid": True,
                    }
                )
                continue
            due = _money(invoice.total_amount - invoice.amount_paid)
            if due <= 0:
                invoice.status = Invoice.STATUS_PAID
                invoice.amount_paid = invoice.total_amount
                invoice.save(update_fields=["status", "amount_paid", "updated_at"])
                continue

            pay_method = method if method in dict(Payment.METHOD_CHOICES) else Payment.METHOD_OTHER
            payment = Payment.objects.create(
                invoice=invoice,
                branch=invoice.branch,
                method=pay_method,
                amount=due,
                reference=reference or f"folio:{folio.id}",
                tenant_id=invoice.tenant_id,
                created_by=user,
            )
            InvoiceService.mark_paid(instance=invoice, user=user, payment_method=method)
            from apps.finance.services.posting_service import AccountingPostingService

            AccountingPostingService.post_customer_payment(
                payment=payment, invoice=invoice, user=user
            )
            paid_pos.append(
                {
                    "id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "amount": float(due),
                    "already_paid": False,
                }
            )

        unlinked_amount = Decimal("0")
        for line in lines:
            if _INVOICE_NOTE_RE.search(line.notes or ""):
                continue
            unlinked_amount += _money(line.amount)

        room_invoice = None
        if unlinked_amount > 0:
            reservation = folio.reservation
            branch = folio.branch
            guest = reservation.guest
            customer = HotelSettlementService.ensure_guest_customer(
                guest=guest, branch=branch, user=user
            )
            product = HotelSettlementService.ensure_room_product(
                tenant_id=folio.tenant_id, user=user
            )
            room_code = reservation.room.code if reservation.room_id else "—"
            notes = (
                f"Hotel folio settlement · {reservation.reservation_number} · Room {room_code}\n"
                f"Payment: {method}"
            )
            if reference:
                notes += f" | Ref: {reference}"

            pay_method = method if method in dict(Payment.METHOD_CHOICES) else Payment.METHOD_OTHER
            room_invoice = InvoiceService.create(
                data={
                    "customer_id": str(customer.id),
                    "branch_id": str(branch.id),
                    "status": Invoice.STATUS_PAID,
                    "issue_date": timezone.localdate(),
                    "discount_amount": Decimal("0"),
                    "amount_paid": unlinked_amount,
                    "notes": notes,
                },
                items=[
                    {
                        "product_id": str(product.id),
                        "quantity": Decimal("1"),
                        "unit_price": unlinked_amount,
                    }
                ],
                user=user,
            )
            room_invoice.tax_amount = Decimal("0")
            room_invoice.total_amount = unlinked_amount
            room_invoice.save(update_fields=["tax_amount", "total_amount", "updated_at"])
            Payment.objects.create(
                invoice=room_invoice,
                branch=branch,
                method=pay_method,
                amount=unlinked_amount,
                reference=reference or f"folio:{folio.id}",
                tenant_id=folio.tenant_id,
                created_by=user,
            )
            from apps.finance.services.posting_service import AccountingPostingService

            AccountingPostingService.post_sale(
                invoice=room_invoice,
                user=user,
                payment_method=method,
                revenue_mapping_key="HOTEL_ROOM_REVENUE",
            )

        folio.amount_paid = folio.balance
        folio.payment_method = method
        folio.settled_at = timezone.now()
        if reference:
            folio.notes = (
                f"{folio.notes}\nSettled ref: {reference}".strip()
                if folio.notes
                else f"Settled ref: {reference}"
            )
        folio.updated_by = user
        folio.save(
            update_fields=[
                "amount_paid",
                "payment_method",
                "settled_at",
                "notes",
                "updated_by",
                "updated_at",
            ]
        )

        return {
            "amount_settled": float(outstanding),
            "payment_method": method,
            "pos_invoices_paid": paid_pos,
            "room_invoice_id": str(room_invoice.id) if room_invoice else None,
            "room_invoice_number": room_invoice.invoice_number if room_invoice else None,
            "unlinked_amount": float(unlinked_amount),
            "linked_amount": float(linked_amount),
        }

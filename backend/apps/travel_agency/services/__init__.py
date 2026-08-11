from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.audit.services import write_audit
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id
from ..models import (
    Destination, FlightSegment, HotelStay, TravelActivity, TravelBooking, TravelCommission,
    TravelDocument, TravelDriver, TravelInsurance, TravelItinerary, TravelPackage,
    TravelPayment, TravelQuotation, TravelQuotationLine, TravelRefund, TravelTransfer, TravelVehicle,
    TravelExpense, Traveler, VisaApplication,
)


class TravelError(ValueError):
    pass


class TravelService:
    RESOURCE_MODELS = {
        "destinations": Destination, "packages": TravelPackage, "travelers": Traveler,
        "bookings": TravelBooking, "flights": FlightSegment, "hotel_stays": HotelStay,
        "visas": VisaApplication, "commissions": TravelCommission, "insurance": TravelInsurance,
        "vehicles": TravelVehicle, "drivers": TravelDriver, "transfers": TravelTransfer,
        "itineraries": TravelItinerary, "activities": TravelActivity, "quotations": TravelQuotation,
        "quotation_lines": TravelQuotationLine, "documents": TravelDocument, "payments": TravelPayment,
        "refunds": TravelRefund, "expenses": TravelExpense,
    }
    PERMISSION_PREFIX = {
        "destinations": "travel.destinations", "packages": "travel.packages",
        "travelers": "travel.travelers", "bookings": "travel.bookings", "flights": "travel.flights",
        "hotel_stays": "travel.hotels", "visas": "travel.visa", "commissions": "travel.commission",
        "insurance": "travel.insurance", "vehicles": "travel.vehicles", "drivers": "travel.drivers",
        "transfers": "travel.transfers", "itineraries": "travel.itineraries",
        "activities": "travel.activities", "quotations": "travel.quotations",
        "quotation_lines": "travel.quotations", "documents": "travel.documents",
        "payments": "travel.payments", "refunds": "travel.refunds", "expenses": "travel.expenses",
    }
    BOOKING_TRANSITIONS = {TravelBooking.STATUS_DRAFT: {TravelBooking.STATUS_CONFIRMED, TravelBooking.STATUS_CANCELLED}, TravelBooking.STATUS_CONFIRMED: {TravelBooking.STATUS_COMPLETED, TravelBooking.STATUS_CANCELLED}, TravelBooking.STATUS_COMPLETED: set(), TravelBooking.STATUS_CANCELLED: set()}
    COMMISSION_TRANSITIONS = {TravelCommission.STATUS_PENDING: {TravelCommission.STATUS_APPROVED}, TravelCommission.STATUS_APPROVED: {TravelCommission.STATUS_PAID}, TravelCommission.STATUS_PAID: set()}
    QUOTATION_TRANSITIONS = {
        TravelQuotation.STATUS_DRAFT: {TravelQuotation.STATUS_SENT},
        TravelQuotation.STATUS_SENT: {TravelQuotation.STATUS_ACCEPTED, TravelQuotation.STATUS_REJECTED, TravelQuotation.STATUS_EXPIRED},
        TravelQuotation.STATUS_ACCEPTED: set(), TravelQuotation.STATUS_REJECTED: set(), TravelQuotation.STATUS_EXPIRED: set(),
    }

    @staticmethod
    def resource_model(resource):
        if resource not in TravelService.RESOURCE_MODELS:
            raise TravelError("Unknown travel resource.")
        return TravelService.RESOURCE_MODELS[resource]

    @staticmethod
    def _audit_values(values):
        return {
            key: str(value) if isinstance(value, (UUID, Decimal, date)) else value
            for key, value in dict(values or {}).items()
        }

    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id and any(f.name == "branch" for f in qs.model._meta.fields):
            qs = qs.filter(branch_id=branch_id)
        return qs.filter(deleted_at__isnull=True)

    @staticmethod
    def _branch(branch_id, *, user=None, request=None):
        if not branch_id:
            raise TravelError("branch_id is required.")
        branch = apply_tenant_scope(Branch.active_objects(), user=user, request=request).filter(pk=branch_id).first()
        if not branch:
            raise TravelError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _next_booking_code(*, tenant_id, branch_id):
        prefix = f"TRV-{timezone.localdate():%Y%m%d}-"
        count = TravelBooking.objects.filter(tenant_id=tenant_id, booking_code__startswith=prefix).count() + 1
        return f"{prefix}{count:04d}"

    @staticmethod
    def _next_quote_number(*, tenant_id):
        prefix = f"QT-{timezone.localdate():%Y%m%d}-"
        count = TravelQuotation.objects.filter(tenant_id=tenant_id, quote_number__startswith=prefix).count() + 1
        return f"{prefix}{count:04d}"

    @staticmethod
    def list(resource, *, user=None, request=None, branch_id=None, status=None, search=None):
        model = TravelService.resource_model(resource)
        qs = TravelService._scope(model.objects.all(), user=user, request=request, branch_id=branch_id)
        select = [f.name for f in model._meta.fields if f.is_relation and f.many_to_one]
        if select:
            qs = qs.select_related(*select)
        if status and any(f.name == "status" for f in model._meta.fields):
            qs = qs.filter(status=status)
        if search:
            search_fields = {"name", "code", "full_name", "booking_code", "passport_number", "agent_name", "hotel_name", "airline", "country", "city", "provider", "policy_number", "plate_number", "license_number", "quote_number", "doc_number", "title", "description"}
            query = Q()
            for field in model._meta.fields:
                if field.name in search_fields:
                    query |= Q(**{f"{field.name}__icontains": search.strip()})
            if query:
                qs = qs.filter(query)
        return qs.order_by("-created_at")

    @staticmethod
    def get(resource, pk, *, user=None, request=None):
        return TravelService._scope(TravelService.resource_model(resource).objects.all(), user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create(resource, data, *, user=None, request=None):
        model = TravelService.resource_model(resource)
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        payload.pop("id", None)
        if resource == "bookings":
            branch = TravelService._branch(payload.get("branch_id"), user=user, request=request)
            payload["branch_id"] = branch.id
            payload.setdefault("booking_code", TravelService._next_booking_code(tenant_id=payload["tenant_id"], branch_id=branch.id))
        if resource == "quotations":
            branch = TravelService._branch(payload.get("branch_id"), user=user, request=request)
            payload["branch_id"] = branch.id
            payload.setdefault("quote_number", TravelService._next_quote_number(tenant_id=payload["tenant_id"]))
            if not payload.get("total_amount"):
                payload["total_amount"] = Decimal(str(payload.get("subtotal") or 0)) + Decimal(str(payload.get("tax_amount") or 0))
        if resource in {"flights", "hotel_stays", "commissions", "insurance", "transfers"} and not payload.get("booking_id"):
            raise TravelError("booking_id is required.")
        if resource == "visas" and not payload.get("traveler_id"):
            raise TravelError("traveler_id is required.")
        if resource == "documents" and not payload.get("traveler_id"):
            raise TravelError("traveler_id is required.")
        if resource == "activities" and not payload.get("itinerary_id"):
            raise TravelError("itinerary_id is required.")
        if resource == "quotation_lines" and not payload.get("quotation_id"):
            raise TravelError("quotation_id is required.")
        if resource in {"payments", "refunds"} and not payload.get("booking_id"):
            raise TravelError("booking_id is required.")
        if resource == "expenses" and not payload.get("branch_id") and not payload.get("booking_id"):
            payload["branch_id"] = getattr(user, "branch_id", None)
        if resource == "expenses" and not payload.get("branch_id") and not payload.get("booking_id"):
            raise TravelError("branch_id or booking_id is required.")
        if resource == "hotel_stays" and not payload.get("nights") and payload.get("check_in") and payload.get("check_out"):
            check_in = payload["check_in"] if isinstance(payload["check_in"], date) else date.fromisoformat(str(payload["check_in"])[:10])
            check_out = payload["check_out"] if isinstance(payload["check_out"], date) else date.fromisoformat(str(payload["check_out"])[:10])
            payload["nights"] = max((check_out - check_in).days, 1)
        if resource == "commissions" and payload.get("amount") is None and payload.get("rate_percent") is not None:
            booking = TravelService.get("bookings", payload["booking_id"], user=user, request=request)
            payload["amount"] = Decimal(str(booking.total_amount)) * Decimal(str(payload["rate_percent"])) / 100
        if resource == "payments":
            amount = Decimal(str(payload.get("amount") or 0))
            if amount <= 0:
                raise TravelError("Payment amount must be positive.")
        if resource == "refunds":
            amount = Decimal(str(payload.get("amount") or 0))
            if amount <= 0:
                raise TravelError("Refund amount must be positive.")
            if payload.get("payment_id"):
                payment = TravelService.get("payments", payload["payment_id"], user=user, request=request)
                if str(payment.booking_id) != str(payload["booking_id"]):
                    raise TravelError("Refund payment must belong to the selected booking.")
        row = model.objects.create(**payload)
        if resource == "payments" and row.status == TravelPayment.STATUS_RECORDED:
            TravelBooking.objects.filter(pk=row.booking_id).update(paid_amount=F("paid_amount") + row.amount)
        if resource == "refunds" and row.status == TravelRefund.STATUS_RECORDED:
            booking = row.booking
            booking.paid_amount = max(Decimal("0"), booking.paid_amount - Decimal(str(row.amount)))
            booking.save(update_fields=["paid_amount", "updated_at"])
        write_audit(action="create", module="travel_agency", entity=row, user=user, request=request, new_values=TravelService._audit_values(payload))
        return row

    @staticmethod
    @transaction.atomic
    def transition_quotation(row, target, *, user=None, request=None):
        if target not in TravelService.QUOTATION_TRANSITIONS.get(row.status, set()):
            raise TravelError(f"Cannot transition quotation from {row.status} to {target}.")
        previous = row.status
        row.status, row.updated_by = target, user
        row.save(update_fields=["status", "updated_by", "updated_at"])
        write_audit(action="status", module="travel_agency", entity=row, user=user, request=request, new_values={"from": previous, "to": target})
        return row

    @staticmethod
    @transaction.atomic
    def convert_quotation_to_booking(quotation, *, user=None, request=None):
        if quotation.status != TravelQuotation.STATUS_ACCEPTED:
            raise TravelError("Only accepted quotations can be converted to bookings.")
        booking = TravelBooking.objects.filter(
            tenant_id=quotation.tenant_id, notes__contains=f"quotation:{quotation.id}", deleted_at__isnull=True
        ).first()
        if booking:
            return booking
        booking = TravelService.create("bookings", {
            "branch_id": quotation.branch_id, "customer_id": quotation.customer_id,
            "package_id": quotation.package_id, "travel_date": quotation.travel_date,
            "adults": quotation.adults, "children": quotation.children,
            "total_amount": quotation.total_amount, "notes": f"Converted from quotation:{quotation.id}. {quotation.notes}".strip(),
        }, user=user, request=request)
        write_audit(action="convert", module="travel_agency", entity=quotation, user=user, request=request, new_values={"booking_id": str(booking.id)})
        return booking

    @staticmethod
    @transaction.atomic
    def update(resource, row, data, *, user=None, request=None):
        fields = {f.name for f in row._meta.fields}
        changed = {}
        for key, value in dict(data or {}).items():
            if key in fields and key not in {"id", "tenant", "tenant_id", "created_at", "updated_at", "deleted_at"}:
                setattr(row, key, value)
                changed[key] = value
        row.updated_by = user
        row.save()
        write_audit(action="update", module="travel_agency", entity=row, user=user, request=request, new_values=TravelService._audit_values(changed))
        return row

    @staticmethod
    @transaction.atomic
    def delete(resource, row, *, user=None, request=None):
        row.soft_delete(user=user)
        write_audit(action="delete", module="travel_agency", entity=row, user=user, request=request)

    @staticmethod
    @transaction.atomic
    def transition_booking(row, target, *, user=None, request=None):
        if target not in TravelService.BOOKING_TRANSITIONS.get(row.status, set()):
            raise TravelError(f"Cannot transition booking from {row.status} to {target}.")
        previous = row.status
        row.status, row.updated_by = target, user
        row.save(update_fields=["status", "updated_by", "updated_at"])
        write_audit(action="status", module="travel_agency", entity=row, user=user, request=request, new_values={"from": previous, "to": target})
        if target == TravelBooking.STATUS_CONFIRMED and not row.journal_entry_id:
            try:
                TravelAccountingService.post_booking(booking=row, user=user, request=request)
            except TravelError:
                pass
        return row

    @staticmethod
    @transaction.atomic
    def transition_commission(row, target, *, user=None, request=None):
        if target not in TravelService.COMMISSION_TRANSITIONS.get(row.status, set()):
            raise TravelError(f"Cannot transition commission from {row.status} to {target}.")
        row.status, row.updated_by = target, user
        row.save(update_fields=["status", "updated_by", "updated_at"])
        write_audit(action="status", module="travel_agency", entity=row, user=user, request=request, new_values={"status": target})
        return row

    @staticmethod
    def summary(*, user=None, request=None, branch_id=None):
        bookings = TravelService.list("bookings", user=user, request=request, branch_id=branch_id)
        money = bookings.aggregate(total=Sum("total_amount"), paid=Sum("paid_amount"))
        return {"total_bookings": bookings.count(), "draft_bookings": bookings.filter(status="draft").count(), "confirmed_bookings": bookings.filter(status="confirmed").count(), "completed_bookings": bookings.filter(status="completed").count(), "total_revenue": float(money["total"] or 0), "paid_amount": float(money["paid"] or 0), "outstanding_amount": float((money["total"] or 0) - (money["paid"] or 0)), "travelers": TravelService.list("travelers", user=user, request=request).count(), "pending_visas": TravelService.list("visas", user=user, request=request).filter(status__in=["draft", "submitted"]).count()}


class TravelAccountingService:
    @staticmethod
    def suggest_posting(booking, *, user=None):
        from apps.finance.services.chart_service import ChartService
        from apps.finance.services.mapping_service import MappingService
        tenant_id = booking.tenant_id or booking.branch.tenant_id
        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)
        ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
        revenue = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant_id, user=user)
        amount = float(booking.total_amount or 0)
        return {"source": "travel_booking", "booking_id": str(booking.id), "currency": booking.currency, "already_posted": bool(booking.journal_entry_id), "journal_entry_id": str(booking.journal_entry_id) if booking.journal_entry_id else None, "lines": [
            {"account_id": str(ar.id), "account_code": ar.code, "account_name": ar.name, "debit": amount, "credit": 0.0, "description": f"Accounts receivable for {booking.booking_code}"},
            {"account_id": str(revenue.id), "account_code": revenue.code, "account_name": revenue.name, "debit": 0.0, "credit": amount, "description": f"Travel revenue for {booking.booking_code}"},
        ], "note": "Preview of central ledger posting (Dr AR / Cr Travel revenue)."}

    @staticmethod
    @transaction.atomic
    def post_booking(*, booking, user=None, request=None):
        from apps.finance.services.posting_service import AccountingPostingService, PostingError
        if booking.journal_entry_id:
            return booking
        try:
            entry = AccountingPostingService.post_travel_booking(booking=booking, user=user)
        except PostingError as exc:
            raise TravelError(str(exc)) from exc
        if entry is None:
            raise TravelError("Accounting engine did not create a journal entry.")
        booking.journal_entry, booking.posted_at, booking.updated_by = entry, timezone.now(), user
        booking.save(update_fields=["journal_entry", "posted_at", "updated_by", "updated_at"])
        write_audit(action="post_accounting", module="travel_agency", entity=booking, user=user, request=request, new_values={"journal_entry_id": str(entry.id), "entry_number": entry.entry_number})
        return booking

    @staticmethod
    @transaction.atomic
    def post_payment(*, payment, user=None, request=None):
        from apps.finance.services.posting_service import AccountingPostingService, PostingError
        if payment.journal_entry_id:
            return payment
        try:
            entry = AccountingPostingService.post_travel_payment(payment=payment, user=user)
        except PostingError as exc:
            raise TravelError(str(exc)) from exc
        payment.journal_entry, payment.posted_at, payment.updated_by = entry, timezone.now(), user
        payment.save(update_fields=["journal_entry", "posted_at", "updated_by", "updated_at"])
        write_audit(action="post_accounting", module="travel_agency", entity=payment, user=user, request=request, new_values={"journal_entry_id": str(entry.id)})
        return payment

    @staticmethod
    @transaction.atomic
    def post_refund(*, refund, user=None, request=None):
        from apps.finance.services.posting_service import AccountingPostingService, PostingError
        if refund.journal_entry_id:
            return refund
        try:
            entry = AccountingPostingService.post_travel_refund(refund=refund, user=user)
        except PostingError as exc:
            raise TravelError(str(exc)) from exc
        refund.journal_entry, refund.posted_at, refund.updated_by = entry, timezone.now(), user
        refund.save(update_fields=["journal_entry", "posted_at", "updated_by", "updated_at"])
        write_audit(action="post_accounting", module="travel_agency", entity=refund, user=user, request=request, new_values={"journal_entry_id": str(entry.id)})
        return refund

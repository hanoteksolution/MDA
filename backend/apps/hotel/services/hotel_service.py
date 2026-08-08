"""Hotel front-desk services (PHASE 17 skeleton)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.hotel.models import Folio, FolioLine, Guest, Reservation, Room, RoomType
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class HotelError(ValueError):
    pass


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    parsed = parse_date(str(value)[:10])
    return parsed


class HotelService:
    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise HotelError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            branch = Branch.active_objects().filter(pk=branch_id).first()
        if not branch:
            raise HotelError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _next_reservation_number(*, tenant_id) -> str:
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"HR-{today}-"
        count = (
            Reservation.objects.filter(
                tenant_id=tenant_id, reservation_number__startswith=prefix
            ).count()
            + 1
        )
        return f"{prefix}{count:04d}"

    # --- Summary ---
    @staticmethod
    def summary(*, branch_id=None, user=None, request=None) -> dict:
        rooms = HotelService.list_rooms(branch_id=branch_id, user=user, request=request)
        reservations = HotelService.list_reservations(
            branch_id=branch_id, user=user, request=request
        )
        today = timezone.localdate()
        return {
            "room_types": HotelService.list_room_types(
                branch_id=branch_id, user=user, request=request
            ).count(),
            "rooms": rooms.filter(is_active=True).count(),
            "rooms_vacant": rooms.filter(
                is_active=True, status=Room.STATUS_VACANT
            ).count(),
            "rooms_occupied": rooms.filter(
                is_active=True, status=Room.STATUS_OCCUPIED
            ).count(),
            "rooms_dirty": rooms.filter(
                is_active=True, status=Room.STATUS_DIRTY
            ).count(),
            "reservations_booked": reservations.filter(
                status=Reservation.STATUS_BOOKED
            ).count(),
            "in_house": reservations.filter(
                status=Reservation.STATUS_CHECKED_IN
            ).count(),
            "arrivals_today": reservations.filter(
                check_in_date=today,
                status__in=[Reservation.STATUS_BOOKED, Reservation.STATUS_CHECKED_IN],
            ).count(),
            "departures_today": reservations.filter(
                check_out_date=today,
                status=Reservation.STATUS_CHECKED_IN,
            ).count(),
            "guests": HotelService.list_guests(
                branch_id=branch_id, user=user, request=request
            ).count(),
        }

    # --- Room types ---
    @staticmethod
    def list_room_types(*, branch_id=None, user=None, request=None):
        qs = RoomType.active_objects().select_related("branch")
        return HotelService._scope(
            qs, user=user, request=request, branch_id=branch_id
        ).order_by("sort_order", "name")

    @staticmethod
    def get_room_type(*, pk, user=None, request=None):
        return HotelService.list_room_types(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_room_type(*, data, user=None, request=None) -> RoomType:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = HotelService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        if not name:
            raise HotelError("Room type name is required.")
        return RoomType.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name=name,
            code=(payload.get("code") or "").strip(),
            base_rate=Decimal(str(payload.get("base_rate") or 0)),
            capacity=int(payload.get("capacity") or 2),
            description=(payload.get("description") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            sort_order=int(payload.get("sort_order") or 100),
            created_by=user,
        )

    # --- Rooms ---
    @staticmethod
    def list_rooms(*, branch_id=None, status=None, user=None, request=None):
        qs = Room.active_objects().select_related("branch", "room_type")
        qs = HotelService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("code")

    @staticmethod
    def get_room(*, pk, user=None, request=None):
        return HotelService.list_rooms(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_room(*, data, user=None, request=None) -> Room:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = HotelService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        room_type = HotelService.get_room_type(
            pk=payload.get("room_type_id"), user=user, request=request
        )
        code = (payload.get("code") or "").strip()
        if not code:
            raise HotelError("Room code is required.")
        return Room.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            room_type=room_type,
            code=code,
            floor=(payload.get("floor") or "").strip(),
            status=payload.get("status") or Room.STATUS_VACANT,
            is_active=bool(payload.get("is_active", True)),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )

    @staticmethod
    def set_room_status(*, room: Room, status: str, user=None) -> Room:
        if status not in dict(Room.STATUS_CHOICES):
            raise HotelError(f"Invalid room status: {status}")
        room.status = status
        room.updated_by = user
        room.save(update_fields=["status", "updated_by", "updated_at"])
        return room

    # --- Guests ---
    @staticmethod
    def list_guests(*, branch_id=None, user=None, request=None):
        qs = Guest.active_objects().select_related("branch")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch_id__isnull=True))
        return qs.order_by("full_name")

    @staticmethod
    def get_guest(*, pk, user=None, request=None):
        return HotelService.list_guests(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_guest(*, data, user=None, request=None) -> Guest:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = None
        if payload.get("branch_id"):
            branch = HotelService._require_branch(
                branch_id=payload.get("branch_id"), user=user, request=request
            )
        name = (payload.get("full_name") or "").strip()
        if not name:
            raise HotelError("Guest full_name is required.")
        return Guest.objects.create(
            tenant_id=payload.get("tenant_id")
            or (branch.tenant_id if branch else None),
            branch=branch,
            full_name=name,
            phone=(payload.get("phone") or "").strip(),
            email=(payload.get("email") or "").strip(),
            id_number=(payload.get("id_number") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    # --- Reservations ---
    @staticmethod
    def list_reservations(*, branch_id=None, status=None, user=None, request=None):
        qs = Reservation.active_objects().select_related(
            "branch", "guest", "room_type", "room"
        )
        qs = HotelService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-check_in_date", "-created_at")

    @staticmethod
    def get_reservation(*, pk, user=None, request=None):
        return HotelService.list_reservations(user=user, request=request).get(pk=pk)

    @staticmethod
    def _assert_room_available(*, room: Room, check_in: date, check_out: date, exclude_id=None):
        if room.status == Room.STATUS_OOO:
            raise HotelError(f"Room {room.code} is out of order.")
        overlap = Reservation.active_objects().filter(
            room_id=room.id,
            status__in=[Reservation.STATUS_BOOKED, Reservation.STATUS_CHECKED_IN],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        )
        if exclude_id:
            overlap = overlap.exclude(pk=exclude_id)
        if overlap.exists():
            raise HotelError(f"Room {room.code} is already booked for those dates.")

    @staticmethod
    @transaction.atomic
    def create_reservation(*, data, user=None, request=None) -> Reservation:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = HotelService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        tenant_id = payload.get("tenant_id") or branch.tenant_id

        if payload.get("guest_id"):
            guest = HotelService.get_guest(
                pk=payload["guest_id"], user=user, request=request
            )
        else:
            guest = HotelService.create_guest(
                data={
                    "branch_id": branch.id,
                    "full_name": payload.get("guest_name") or payload.get("full_name"),
                    "phone": payload.get("phone") or "",
                    "email": payload.get("email") or "",
                    "id_number": payload.get("id_number") or "",
                    "tenant_id": tenant_id,
                },
                user=user,
                request=request,
            )

        room_type = HotelService.get_room_type(
            pk=payload.get("room_type_id"), user=user, request=request
        )
        check_in = _as_date(payload.get("check_in_date"))
        check_out = _as_date(payload.get("check_out_date"))
        if not check_in or not check_out:
            raise HotelError("check_in_date and check_out_date are required.")
        if check_out <= check_in:
            raise HotelError("check_out_date must be after check_in_date.")

        room = None
        if payload.get("room_id"):
            room = HotelService.get_room(
                pk=payload["room_id"], user=user, request=request
            )
            HotelService._assert_room_available(
                room=room, check_in=check_in, check_out=check_out
            )

        rate = payload.get("rate_amount")
        if rate is None or str(rate).strip() == "":
            rate = room_type.base_rate
        else:
            rate = Decimal(str(rate))

        reservation = Reservation.objects.create(
            tenant_id=tenant_id,
            branch=branch,
            guest=guest,
            room_type=room_type,
            room=room,
            reservation_number=HotelService._next_reservation_number(tenant_id=tenant_id),
            status=Reservation.STATUS_BOOKED,
            check_in_date=check_in,
            check_out_date=check_out,
            adults=int(payload.get("adults") or 1),
            children=int(payload.get("children") or 0),
            rate_amount=rate,
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        if room is not None and room.status == Room.STATUS_VACANT:
            HotelService.set_room_status(
                room=room, status=Room.STATUS_RESERVED, user=user
            )
        return reservation

    @staticmethod
    @transaction.atomic
    def check_in(*, reservation: Reservation, room_id=None, user=None, request=None) -> Reservation:
        if reservation.status != Reservation.STATUS_BOOKED:
            raise HotelError("Only booked reservations can be checked in.")

        room = reservation.room
        if room_id:
            room = HotelService.get_room(pk=room_id, user=user, request=request)
        if room is None:
            # Auto-pick a vacant room of the reserved type
            room = (
                HotelService.list_rooms(
                    branch_id=reservation.branch_id, user=user, request=request
                )
                .filter(
                    room_type_id=reservation.room_type_id,
                    status=Room.STATUS_VACANT,
                    is_active=True,
                )
                .first()
            )
        if room is None:
            raise HotelError("Assign a vacant room before check-in.")

        HotelService._assert_room_available(
            room=room,
            check_in=reservation.check_in_date,
            check_out=reservation.check_out_date,
            exclude_id=reservation.id,
        )

        reservation.room = room
        reservation.status = Reservation.STATUS_CHECKED_IN
        reservation.checked_in_at = timezone.now()
        reservation.updated_by = user
        reservation.save(
            update_fields=[
                "room",
                "status",
                "checked_in_at",
                "updated_by",
                "updated_at",
            ]
        )
        HotelService.set_room_status(room=room, status=Room.STATUS_OCCUPIED, user=user)

        folio, _created = Folio.objects.get_or_create(
            reservation=reservation,
            defaults={
                "tenant_id": reservation.tenant_id,
                "branch_id": reservation.branch_id,
                "status": Folio.STATUS_OPEN,
                "created_by": user,
            },
        )
        nights = reservation.nights
        room_charge = Decimal(str(reservation.rate_amount or 0)) * Decimal(nights)
        if room_charge > 0 and not folio.lines.filter(
            deleted_at__isnull=True, line_type=FolioLine.TYPE_ROOM
        ).exists():
            HotelService.add_folio_line(
                folio=folio,
                data={
                    "line_type": FolioLine.TYPE_ROOM,
                    "description": f"Room {room.code} × {nights} night(s)",
                    "amount": room_charge,
                    "quantity": nights,
                },
                user=user,
            )
        return reservation

    @staticmethod
    @transaction.atomic
    def check_out(*, reservation: Reservation, data=None, user=None) -> Reservation:
        if reservation.status != Reservation.STATUS_CHECKED_IN:
            raise HotelError("Only in-house guests can be checked out.")
        data = data or {}
        folio = getattr(reservation, "folio", None)
        if folio is None:
            try:
                folio = reservation.folio
            except Exception:
                folio = None

        settlement = None
        if folio and folio.status == Folio.STATUS_OPEN:
            outstanding = Decimal(str(folio.balance or 0)) - Decimal(
                str(folio.amount_paid or 0)
            )
            if outstanding > 0:
                payment_method = (data.get("payment_method") or "").strip()
                if not payment_method:
                    raise HotelError(
                        "Folio has an outstanding balance — provide payment_method to settle."
                    )
                from apps.hotel.services.hotel_settlement_service import (
                    HotelSettlementService,
                )

                settlement = HotelSettlementService.settle_folio(
                    folio=folio,
                    payment_method=payment_method,
                    payment_reference=(data.get("payment_reference") or "").strip(),
                    user=user,
                )
            else:
                if not folio.settled_at:
                    folio.amount_paid = folio.balance
                    folio.settled_at = timezone.now()
                    folio.updated_by = user
                    folio.save(
                        update_fields=[
                            "amount_paid",
                            "settled_at",
                            "updated_by",
                            "updated_at",
                        ]
                    )

            folio.refresh_from_db()
            folio.status = Folio.STATUS_CLOSED
            folio.closed_at = timezone.now()
            folio.updated_by = user
            folio.save(update_fields=["status", "closed_at", "updated_by", "updated_at"])

        reservation.status = Reservation.STATUS_CHECKED_OUT
        reservation.checked_out_at = timezone.now()
        reservation.updated_by = user
        reservation.save(
            update_fields=["status", "checked_out_at", "updated_by", "updated_at"]
        )
        if reservation.room_id:
            HotelService.set_room_status(
                room=reservation.room, status=Room.STATUS_DIRTY, user=user
            )
        # Attach last settlement for API serialization callers
        reservation._last_settlement = settlement  # type: ignore[attr-defined]
        return reservation

    @staticmethod
    @transaction.atomic
    def cancel_reservation(*, reservation: Reservation, user=None) -> Reservation:
        if reservation.status in (
            Reservation.STATUS_CHECKED_OUT,
            Reservation.STATUS_CANCELLED,
        ):
            raise HotelError("Reservation cannot be cancelled.")
        was_in_house = reservation.status == Reservation.STATUS_CHECKED_IN
        reservation.status = Reservation.STATUS_CANCELLED
        reservation.updated_by = user
        reservation.save(update_fields=["status", "updated_by", "updated_at"])
        if reservation.room_id:
            new_status = Room.STATUS_DIRTY if was_in_house else Room.STATUS_VACANT
            HotelService.set_room_status(
                room=reservation.room, status=new_status, user=user
            )
        return reservation

    # --- Folios ---
    @staticmethod
    def get_folio_for_reservation(*, reservation: Reservation) -> Folio | None:
        return Folio.active_objects().filter(reservation=reservation).first()

    @staticmethod
    def list_open_folios(*, branch_id=None, user=None, request=None) -> list[Folio]:
        """In-house open folios for POS charge-to-room."""
        qs = Folio.active_objects().filter(status=Folio.STATUS_OPEN).select_related(
            "branch",
            "reservation",
            "reservation__guest",
            "reservation__room",
            "reservation__room_type",
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        qs = qs.filter(reservation__status=Reservation.STATUS_CHECKED_IN)
        return list(qs.order_by("reservation__room__code", "-opened_at"))

    @staticmethod
    def get_folio(*, pk, user=None, request=None) -> Folio:
        qs = Folio.active_objects().select_related(
            "branch", "reservation", "reservation__guest", "reservation__room"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        return qs.get(pk=pk)

    @staticmethod
    @transaction.atomic
    def charge_pos_sale_to_folio(
        *,
        folio: Folio,
        amount,
        invoice_number: str = "",
        description: str = "",
        user=None,
    ) -> FolioLine:
        """Post F&B / POS sale onto an open guest folio."""
        amt = Decimal(str(amount or 0))
        if amt <= 0:
            raise HotelError("Charge amount must be positive.")
        room = folio.reservation.room.code if folio.reservation.room_id else "—"
        desc = (description or "").strip() or (
            f"POS charge · Room {room}"
            + (f" · {invoice_number}" if invoice_number else "")
        )
        return HotelService.add_folio_line(
            folio=folio,
            data={
                "line_type": FolioLine.TYPE_FNB,
                "description": desc,
                "amount": amt,
                "quantity": 1,
                "notes": f"invoice:{invoice_number}" if invoice_number else "",
            },
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def add_folio_line(*, folio: Folio, data, user=None) -> FolioLine:
        if folio.status != Folio.STATUS_OPEN:
            raise HotelError("Cannot post to a closed folio.")
        description = (data.get("description") or "").strip()
        if not description:
            raise HotelError("Folio line description is required.")
        amount = Decimal(str(data.get("amount") or 0))
        line_type = data.get("line_type") or FolioLine.TYPE_OTHER
        if line_type not in dict(FolioLine.TYPE_CHOICES):
            raise HotelError(f"Invalid folio line type: {line_type}")
        line = FolioLine.objects.create(
            tenant_id=folio.tenant_id,
            folio=folio,
            line_type=line_type,
            description=description,
            amount=amount,
            quantity=Decimal(str(data.get("quantity") or 1)),
            notes=(data.get("notes") or "").strip(),
            created_by=user,
        )
        folio.recalc_balance()
        return line

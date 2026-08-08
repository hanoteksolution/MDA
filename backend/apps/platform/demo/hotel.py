"""Hotel demo seeder — room types, rooms, guest, booked + in-house stay."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.hotel.models import Reservation, Room
from apps.hotel.services import HotelService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


def seed(*, tenant, user=None) -> dict:
    with tenant_context(tenant, enforce=True):
        branch = (
            Branch.active_objects()
            .filter(tenant=tenant, is_default=True)
            .first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        if branch is None:
            return {"hotel": {"seeded": False, "reason": "no branch"}}

        existing = Room.active_objects().filter(tenant=tenant).count()
        if existing:
            return {
                "hotel": {
                    "seeded": True,
                    "idempotent": True,
                    "rooms": existing,
                    "reservations": Reservation.active_objects()
                    .filter(tenant=tenant)
                    .count(),
                }
            }

        standard = HotelService.create_room_type(
            data={
                "name": "Standard",
                "code": "STD",
                "base_rate": "45.00",
                "capacity": 2,
                "branch_id": branch.id,
                "sort_order": 10,
            },
            user=user,
        )
        deluxe = HotelService.create_room_type(
            data={
                "name": "Deluxe",
                "code": "DLX",
                "base_rate": "75.00",
                "capacity": 3,
                "branch_id": branch.id,
                "sort_order": 20,
            },
            user=user,
        )

        rooms = []
        for code, rtype, floor in (
            ("101", standard, "1"),
            ("102", standard, "1"),
            ("201", deluxe, "2"),
            ("202", deluxe, "2"),
        ):
            rooms.append(
                HotelService.create_room(
                    data={
                        "branch_id": branch.id,
                        "room_type_id": rtype.id,
                        "code": code,
                        "floor": floor,
                    },
                    user=user,
                )
            )

        today = timezone.localdate()
        guest = HotelService.create_guest(
            data={
                "branch_id": branch.id,
                "full_name": "Demo Guest",
                "phone": "+255700000001",
                "email": "demo.guest@example.com",
            },
            user=user,
        )

        booked = HotelService.create_reservation(
            data={
                "branch_id": branch.id,
                "guest_id": guest.id,
                "room_type_id": standard.id,
                "room_id": rooms[1].id,
                "check_in_date": (today + timedelta(days=1)).isoformat(),
                "check_out_date": (today + timedelta(days=3)).isoformat(),
                "adults": 2,
                "rate_amount": "45.00",
                "notes": "Demo arrival tomorrow",
            },
            user=user,
        )

        in_house = HotelService.create_reservation(
            data={
                "branch_id": branch.id,
                "guest_name": "In-House Guest",
                "phone": "+255700000002",
                "room_type_id": deluxe.id,
                "room_id": rooms[2].id,
                "check_in_date": today.isoformat(),
                "check_out_date": (today + timedelta(days=2)).isoformat(),
                "adults": 1,
                "rate_amount": Decimal("75.00"),
            },
            user=user,
        )
        HotelService.check_in(reservation=in_house, user=user)

        return {
            "hotel": {
                "seeded": True,
                "room_types": 2,
                "rooms": len(rooms),
                "guests": 2,
                "reservations": 2,
                "booked": booked.reservation_number,
                "in_house": in_house.reservation_number,
            }
        }

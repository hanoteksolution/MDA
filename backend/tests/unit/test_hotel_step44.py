"""PHASE 17 — hotel app skeleton."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.hotel.models import Folio, Reservation, Room
from apps.hotel.services import HotelError, HotelService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def hotel_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, report = DemoTenantService.create(
        data={
            "name": "Hotel Demo",
            "business_type_code": "hotel",
            "preset_code": "hotel",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    return {"tenant": tenant, "branch": branch, "report": report}


@pytest.mark.django_db
def test_hotel_demo_seeder(hotel_env):
    tenant = hotel_env["tenant"]
    report = hotel_env["report"]["results"]["hotel"]
    assert report.get("seeded") is True
    assert Room.active_objects().filter(tenant=tenant).count() >= 4
    assert Reservation.active_objects().filter(tenant=tenant).count() >= 2
    assert Reservation.active_objects().filter(
        tenant=tenant, status=Reservation.STATUS_CHECKED_IN
    ).exists()


@pytest.mark.django_db
def test_check_in_opens_folio_and_occupies_room(hotel_env):
    tenant = hotel_env["tenant"]
    branch = hotel_env["branch"]
    today = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        room_type = HotelService.list_room_types(branch_id=branch.id).first()
        room = (
            HotelService.list_rooms(branch_id=branch.id)
            .filter(status=Room.STATUS_VACANT)
            .first()
        )
        assert room_type and room
        reservation = HotelService.create_reservation(
            data={
                "branch_id": branch.id,
                "guest_name": "Walk-in Guest",
                "room_type_id": room_type.id,
                "room_id": room.id,
                "check_in_date": today.isoformat(),
                "check_out_date": (today + timedelta(days=2)).isoformat(),
                "rate_amount": "50.00",
            }
        )
        HotelService.check_in(reservation=reservation)
        reservation.refresh_from_db()
        room.refresh_from_db()
        assert reservation.status == Reservation.STATUS_CHECKED_IN
        assert room.status == Room.STATUS_OCCUPIED
        folio = Folio.active_objects().get(reservation=reservation)
        assert folio.status == Folio.STATUS_OPEN
        assert folio.balance == Decimal("100.00")  # 50 × 2 nights

        HotelService.check_out(reservation=reservation, data={"payment_method": "cash"})
        reservation.refresh_from_db()
        room.refresh_from_db()
        folio.refresh_from_db()
        assert reservation.status == Reservation.STATUS_CHECKED_OUT
        assert room.status == Room.STATUS_DIRTY
        assert folio.status == Folio.STATUS_CLOSED
        assert folio.amount_paid == folio.balance
        assert folio.payment_method == "cash"
        assert folio.settled_at is not None


@pytest.mark.django_db
def test_double_book_blocked(hotel_env):
    tenant = hotel_env["tenant"]
    branch = hotel_env["branch"]
    today = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        room = HotelService.list_rooms(branch_id=branch.id).filter(
            status__in=[Room.STATUS_VACANT, Room.STATUS_RESERVED]
        ).first()
        room_type = room.room_type
        HotelService.create_reservation(
            data={
                "branch_id": branch.id,
                "guest_name": "First",
                "room_type_id": room_type.id,
                "room_id": room.id,
                "check_in_date": (today + timedelta(days=10)).isoformat(),
                "check_out_date": (today + timedelta(days=12)).isoformat(),
            }
        )
        with pytest.raises(HotelError, match="already booked"):
            HotelService.create_reservation(
                data={
                    "branch_id": branch.id,
                    "guest_name": "Second",
                    "room_type_id": room_type.id,
                    "room_id": room.id,
                    "check_in_date": (today + timedelta(days=11)).isoformat(),
                    "check_out_date": (today + timedelta(days=13)).isoformat(),
                }
            )

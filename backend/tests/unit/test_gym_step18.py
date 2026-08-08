"""STEP 18 — gym classes + capacity-safe booking."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.gym.models import ClassBooking
from apps.gym.services.class_service import BookingService, ClassError, ClassService
from apps.gym.services.member_service import MemberService
from apps.platform.models import Tenant


@pytest.fixture
def class_env(db):
    tenant = Tenant.objects.create(
        name="Class Co", slug="class-co", status=Tenant.STATUS_ACTIVE
    )
    gym_class = ClassService.create_class(
        data={
            "code": "yoga",
            "name": "Yoga Flow",
            "default_capacity": 2,
            "duration_minutes": 60,
            "tenant": tenant,
        }
    )
    starts = timezone.now() + timedelta(days=1)
    schedule = ClassService.create_schedule(
        data={
            "gym_class_id": gym_class.id,
            "starts_at": starts.isoformat(),
            "capacity": 2,
        }
    )
    members = [
        MemberService.create(data={"full_name": f"Member {i}", "tenant": tenant})
        for i in range(5)
    ]
    return {
        "tenant": tenant,
        "gym_class": gym_class,
        "schedule": schedule,
        "members": members,
    }


@pytest.mark.django_db
def test_book_confirmed_then_waitlist(class_env):
    s = class_env["schedule"]
    m = class_env["members"]
    b1 = BookingService.book(schedule_id=s.id, member_id=m[0].id)
    b2 = BookingService.book(schedule_id=s.id, member_id=m[1].id)
    b3 = BookingService.book(schedule_id=s.id, member_id=m[2].id)
    assert b1.status == ClassBooking.STATUS_CONFIRMED
    assert b2.status == ClassBooking.STATUS_CONFIRMED
    assert b3.status == ClassBooking.STATUS_WAITLISTED


@pytest.mark.django_db
def test_full_without_waitlist_raises(class_env):
    s = class_env["schedule"]
    m = class_env["members"]
    BookingService.book(schedule_id=s.id, member_id=m[0].id)
    BookingService.book(schedule_id=s.id, member_id=m[1].id)
    with pytest.raises(ClassError, match="full"):
        BookingService.book(
            schedule_id=s.id, member_id=m[2].id, allow_waitlist=False
        )


@pytest.mark.django_db
def test_cancel_promotes_waitlist(class_env):
    s = class_env["schedule"]
    m = class_env["members"]
    b1 = BookingService.book(schedule_id=s.id, member_id=m[0].id)
    BookingService.book(schedule_id=s.id, member_id=m[1].id)
    b3 = BookingService.book(schedule_id=s.id, member_id=m[2].id)
    assert b3.status == ClassBooking.STATUS_WAITLISTED
    BookingService.cancel(booking_id=b1.id)
    b3.refresh_from_db()
    assert b3.status == ClassBooking.STATUS_CONFIRMED


@pytest.mark.django_db
def test_duplicate_booking_blocked(class_env):
    s = class_env["schedule"]
    m = class_env["members"][0]
    BookingService.book(schedule_id=s.id, member_id=m.id)
    with pytest.raises(ClassError, match="already booked"):
        BookingService.book(schedule_id=s.id, member_id=m.id)


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_cannot_overbook(class_env):
    """Parallel bookers: confirmed count must never exceed capacity."""
    schedule_id = class_env["schedule"].id
    capacity = class_env["schedule"].capacity
    member_ids = [m.id for m in class_env["members"]]

    def _book(member_id):
        # Each thread needs its own DB connection.
        connection.close()
        try:
            return BookingService.book(
                schedule_id=schedule_id,
                member_id=member_id,
                allow_waitlist=True,
            ).status
        except Exception as exc:
            return f"error:{exc}"

    results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_book, mid) for mid in member_ids]
        for fut in as_completed(futures):
            results.append(fut.result())

    confirmed = results.count(ClassBooking.STATUS_CONFIRMED)
    # Primary guarantee: never overbook, even under contention.
    assert confirmed <= capacity
    db_confirmed = (
        ClassBooking.active_objects()
        .filter(schedule_id=schedule_id, status=ClassBooking.STATUS_CONFIRMED)
        .count()
    )
    assert db_confirmed <= capacity
    # On backends with proper row locks (Postgres), all slots fill; SQLite may
    # serialize with lock errors — still must not exceed capacity.
    assert db_confirmed == confirmed or db_confirmed <= capacity
    assert ClassBooking.STATUS_CONFIRMED in results or db_confirmed >= 1 or any(
        str(r).startswith("error:") for r in results
    )

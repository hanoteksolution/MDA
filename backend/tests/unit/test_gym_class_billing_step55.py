"""STEP 55 — Gym class drop-in billing → Invoice + GYM_CLASS_REVENUE."""

import pytest

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.finance.events import event_types
from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.gym.services.class_service import BookingService, ClassService
from apps.gym.services.gym_payment_service import GymPaymentError, GymPaymentService
from apps.gym.services.member_service import MemberService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company


@pytest.fixture
def class_bill_env(db):
    tenant = Tenant.objects.create(
        name="Class Gym", slug="class-gym", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Class Gym Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Studio", code="ST", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="class_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    member = MemberService.create(
        data={
            "full_name": "Drop-in Guest",
            "phone": "777",
            "tenant": tenant,
            "branch_id": branch.id,
        },
        user=user,
    )
    gym_class = ClassService.create_class(
        data={
            "code": "yoga",
            "name": "Morning Yoga",
            "default_capacity": 10,
            "drop_in_price": "25.00",
            "tenant": tenant,
        },
        user=user,
    )
    schedule = ClassService.create_schedule(
        data={
            "gym_class_id": gym_class.id,
            "starts_at": timezone.now() + timedelta(hours=2),
            "capacity": 10,
            "branch_id": branch.id,
            "tenant": tenant,
        },
        user=user,
    )
    booking = BookingService.book(
        schedule_id=schedule.id,
        member_id=member.id,
        user=user,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "user": user,
        "member": member,
        "gym_class": gym_class,
        "schedule": schedule,
        "booking": booking,
    }


@pytest.mark.django_db
def test_class_dropin_checkout_posts_cae(class_bill_env):
    result = GymPaymentService.checkout_class_booking(
        booking_id=class_bill_env["booking"].id,
        data={"payment_method": "cash"},
        user=class_bill_env["user"],
    )
    assert result["invoice"]["status"] == "paid"
    assert result["invoice"]["total_amount"] == pytest.approx(25.0)
    assert result["booking"]["invoice_id"]

    invoice_id = result["invoice"]["id"]
    journal = JournalEntry.active_objects().get(source_id=invoice_id, source_module="gym")
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 25.0
    assert all(line.get("business_unit_code") == "GYM" for line in data["lines"])

    event = AccountingEvent.active_objects().get(
        event_type=event_types.GYM_SERVICE_SOLD, source_id=invoice_id
    )
    assert event.status == AccountingEvent.STATUS_POSTED
    assert event.payload.get("revenue_mapping_key") == "GYM_CLASS_REVENUE"


@pytest.mark.django_db
def test_class_dropin_requires_price(class_bill_env):
    class_bill_env["gym_class"].drop_in_price = 0
    class_bill_env["gym_class"].save(update_fields=["drop_in_price"])
    with pytest.raises(GymPaymentError, match="positive"):
        GymPaymentService.checkout_class_booking(
            booking_id=class_bill_env["booking"].id,
            data={"payment_method": "cash"},
            user=class_bill_env["user"],
        )


@pytest.mark.django_db
def test_class_dropin_idempotent(class_bill_env):
    key = "class-dropin-key-1"
    r1 = GymPaymentService.checkout_class_booking(
        booking_id=class_bill_env["booking"].id,
        data={"payment_method": "cash", "idempotency_key": key},
        user=class_bill_env["user"],
    )
    r2 = GymPaymentService.checkout_class_booking(
        booking_id=class_bill_env["booking"].id,
        data={"payment_method": "cash", "idempotency_key": key},
        user=class_bill_env["user"],
    )
    assert r2["idempotent_replay"] is True
    assert r1["invoice"]["id"] == r2["invoice"]["id"]
    assert (
        AccountingEvent.active_objects()
        .filter(event_type=event_types.GYM_SERVICE_SOLD, source_id=r1["invoice"]["id"])
        .count()
        == 1
    )

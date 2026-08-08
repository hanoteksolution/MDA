"""STEP 53 — Gym PT session checkout → Invoice + GYM_SERVICE_SOLD."""

from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.finance.events import event_types
from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.gym.models import PersonalTrainingSession
from apps.gym.services.gym_payment_service import GymPaymentError, GymPaymentService
from apps.gym.services.member_service import MemberService
from apps.gym.services.trainer_service import PTSessionService, TrainerService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pt_env(db):
    tenant = Tenant.objects.create(name="PT Gym", slug="pt-gym", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="PT Gym Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Floor", code="FL", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="pt_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    member = MemberService.create(
        data={
            "full_name": "Client One",
            "phone": "555",
            "tenant": tenant,
            "branch_id": branch.id,
        },
        user=user,
    )
    trainer = TrainerService.create(
        data={
            "full_name": "Coach Kay",
            "hourly_rate": "80.00",
            "tenant": tenant,
            "branch_id": branch.id,
        },
        user=user,
    )
    session = PTSessionService.schedule(
        member_id=member.id,
        trainer_id=trainer.id,
        scheduled_at=timezone.now(),
        duration_minutes=60,
        user=user,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "user": user,
        "member": member,
        "trainer": trainer,
        "session": session,
    }


@pytest.mark.django_db
def test_pt_checkout_cash_invoice_and_cae(pt_env):
    result = GymPaymentService.checkout_pt_session(
        session_id=pt_env["session"].id,
        data={"payment_method": "cash", "tenant": pt_env["tenant"]},
        user=pt_env["user"],
    )
    assert result["invoice"]["status"] == "paid"
    assert result["invoice"]["total_amount"] == pytest.approx(80.0)
    assert result["session"]["status"] == PersonalTrainingSession.STATUS_COMPLETED
    assert result["session"]["invoice_id"]

    invoice_id = result["invoice"]["id"]
    journal = JournalEntry.active_objects().get(source_id=invoice_id, source_module="gym")
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 80.0
    assert all(line.get("business_unit_code") == "GYM" for line in data["lines"])

    event = AccountingEvent.active_objects().get(
        event_type=event_types.GYM_SERVICE_SOLD, source_id=invoice_id
    )
    assert event.status == AccountingEvent.STATUS_POSTED


@pytest.mark.django_db
def test_pt_checkout_amount_override(pt_env):
    result = GymPaymentService.checkout_pt_session(
        session_id=pt_env["session"].id,
        data={"payment_method": "cash", "amount": "45.50"},
        user=pt_env["user"],
    )
    assert result["invoice"]["total_amount"] == pytest.approx(45.5)


@pytest.mark.django_db
def test_pt_checkout_requires_positive_amount(pt_env):
    pt_env["trainer"].hourly_rate = Decimal("0")
    pt_env["trainer"].save(update_fields=["hourly_rate"])
    with pytest.raises(GymPaymentError, match="positive"):
        GymPaymentService.checkout_pt_session(
            session_id=pt_env["session"].id,
            data={"payment_method": "cash"},
            user=pt_env["user"],
        )


@pytest.mark.django_db
def test_pt_checkout_idempotent(pt_env):
    key = "pt-checkout-key-1"
    r1 = GymPaymentService.checkout_pt_session(
        session_id=pt_env["session"].id,
        data={"payment_method": "cash", "idempotency_key": key},
        user=pt_env["user"],
    )
    r2 = GymPaymentService.checkout_pt_session(
        session_id=pt_env["session"].id,
        data={"payment_method": "cash", "idempotency_key": key},
        user=pt_env["user"],
    )
    assert r2["idempotent_replay"] is True
    assert r1["invoice"]["id"] == r2["invoice"]["id"]
    assert (
        AccountingEvent.active_objects()
        .filter(event_type=event_types.GYM_SERVICE_SOLD, source_id=r1["invoice"]["id"])
        .count()
        == 1
    )

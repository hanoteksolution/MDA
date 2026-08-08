"""STEP 35 Phase N — Futsal ledger posts through Central Accounting Engine."""

from decimal import Decimal

import pytest

from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.futsal.models import Court, FutsalLedgerEntry
from apps.futsal.services.futsal_service import FutsalService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.utils import timezone


@pytest.fixture
def futsal_env(db):
    tenant = Tenant.objects.create(name="Futsal Co", slug="futsal-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Futsal Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Pitch", code="P1", is_default=True
    )
    court = Court.objects.create(
        name="Court A",
        code="A1",
        branch=branch,
        tenant=tenant,
        hourly_rate=Decimal("20"),
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="futsal_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {
        "tenant": tenant,
        "branch": branch,
        "court": court,
        "user": user,
    }


@pytest.mark.django_db
def test_futsal_accounts_seeded(futsal_env):
    tenant = futsal_env["tenant"]
    rev = MappingService.resolve(key="FUTSAL_REVENUE", tenant_id=tenant.id)
    exp = MappingService.resolve(key="FUTSAL_EXPENSE", tenant_id=tenant.id)
    assert rev.code == "4100"
    assert exp.code == "6080"


@pytest.mark.django_db
def test_futsal_income_ledger_posts_journal(futsal_env):
    user = futsal_env["user"]
    branch = futsal_env["branch"]

    entry = FutsalService.create_ledger_entry(
        data={
            "branch_id": branch.id,
            "entry_type": FutsalLedgerEntry.TYPE_INCOME,
            "category": "tournament",
            "amount": Decimal("100"),
            "entry_date": timezone.localdate(),
            "description": "Tournament fee",
            "payment_method": "cash",
        },
        user=user,
    )
    event = AccountingEvent.active_objects().get(
        idempotency_key=f"FUTSAL_INCOME_RECORDED:futsal:ledger:{entry.id}"
    )
    assert event.status == AccountingEvent.STATUS_POSTED
    journal = JournalEntry.active_objects().get(pk=event.journal_entry_id)
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["source_type"] == JournalEntry.SOURCE_FUTSAL
    assert data["total_debit"] == 100.0
    memos = {line["memo"] for line in data["lines"]}
    assert "tournament" in memos or "Futsal income" in memos


@pytest.mark.django_db
def test_futsal_expense_ledger_posts_journal(futsal_env):
    user = futsal_env["user"]
    branch = futsal_env["branch"]

    entry = FutsalService.create_ledger_entry(
        data={
            "branch_id": branch.id,
            "entry_type": FutsalLedgerEntry.TYPE_EXPENSE,
            "category": "maintenance",
            "amount": Decimal("40"),
            "description": "Balls",
        },
        user=user,
    )
    event = AccountingEvent.active_objects().get(
        idempotency_key=f"FUTSAL_EXPENSE_RECORDED:futsal:ledger:{entry.id}"
    )
    assert event.status == AccountingEvent.STATUS_POSTED
    data = JournalService.serialize(event.journal_entry)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 40.0


@pytest.mark.django_db
def test_futsal_booking_payment_posts_income(futsal_env):
    user = futsal_env["user"]
    court = futsal_env["court"]
    branch = futsal_env["branch"]

    start = timezone.now()
    end = start + timezone.timedelta(hours=2)
    booking = FutsalService.create_booking(
        data={
            "court_id": court.id,
            "branch_id": branch.id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "hours": "2",
            "hourly_rate": "20",
            "amount_paid": "40",
            "title": "Evening match",
        },
        user=user,
    )
    ledger = FutsalLedgerEntry.active_objects().filter(booking=booking).first()
    assert ledger is not None
    event = AccountingEvent.active_objects().filter(
        source_module="futsal", source_id=ledger.id, status=AccountingEvent.STATUS_POSTED
    ).first()
    assert event is not None
    assert event.event_type == "FUTSAL_INCOME_RECORDED"

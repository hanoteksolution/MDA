"""STEP 37 — Posted journal immutability."""

from decimal import Decimal

import pytest

from apps.finance.models import ImmutableJournalError, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.reversal_service import AccountingReversalService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def imm_env(db):
    tenant = Tenant.objects.create(name="Imm Co", slug="imm-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Imm Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="imm_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    rev = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user, "cash": cash, "rev": rev}


def _post_simple(imm_env):
    return JournalService.create_entry(
        data={
            "tenant_id": imm_env["tenant"].id,
            "entry_date": timezone.localdate(),
            "description": "Cash sale",
            "branch_id": imm_env["branch"].id,
            "lines": [
                {
                    "account_id": str(imm_env["cash"].id),
                    "debit": "50",
                    "credit": "0",
                    "memo": "cash",
                },
                {
                    "account_id": str(imm_env["rev"].id),
                    "debit": "0",
                    "credit": "50",
                    "memo": "revenue",
                },
            ],
        },
        user=imm_env["user"],
    )


@pytest.mark.django_db
def test_posted_journal_header_immutable(imm_env):
    entry = _post_simple(imm_env)
    assert entry.status == JournalEntry.STATUS_POSTED
    entry.description = "tampered"
    with pytest.raises(ImmutableJournalError):
        entry.save()
    with pytest.raises(JournalError) as exc:
        JournalService.assert_mutable(entry)
    assert exc.value.code == "JOURNAL_POSTED_IMMUTABLE"


@pytest.mark.django_db
def test_posted_journal_line_immutable(imm_env):
    entry = _post_simple(imm_env)
    line = entry.lines.first()
    line.debit = Decimal("99")
    with pytest.raises(ImmutableJournalError):
        line.save()
    with pytest.raises(ImmutableJournalError):
        JournalLine.objects.create(
            entry=entry,
            account=imm_env["cash"],
            debit=Decimal("1"),
            credit=Decimal("0"),
        )


@pytest.mark.django_db
def test_posted_journal_soft_delete_forbidden(imm_env):
    entry = _post_simple(imm_env)
    with pytest.raises(ImmutableJournalError):
        entry.soft_delete(user=imm_env["user"])
    line = entry.lines.first()
    with pytest.raises(ImmutableJournalError):
        line.soft_delete(user=imm_env["user"])


@pytest.mark.django_db
def test_reversal_does_not_mutate_original(imm_env):
    entry = _post_simple(imm_env)
    original_desc = entry.description
    reversal = AccountingReversalService.reverse_entry(
        entry=entry, user=imm_env["user"], reason="fix"
    )
    entry.refresh_from_db()
    assert entry.description == original_desc
    assert entry.status == JournalEntry.STATUS_POSTED
    assert reversal.reverses_entry_id == entry.id
    assert reversal.status == JournalEntry.STATUS_POSTED

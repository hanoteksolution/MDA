"""STEP 37 — Maker-checker draft journal approval."""

from decimal import Decimal

import pytest

from apps.finance.models import JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.mapping_service import MappingService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def mc_env(db):
    tenant = Tenant.objects.create(name="MC Co", slug="mc-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="MC Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    User = get_user_model()
    maker = User.objects.create_user(
        username="maker", password="pass12345", tenant=tenant, branch=branch
    )
    checker = User.objects.create_user(
        username="checker", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    rev = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant.id)
    return {
        "tenant": tenant,
        "branch": branch,
        "maker": maker,
        "checker": checker,
        "cash": cash,
        "rev": rev,
    }


def _draft(mc_env, user):
    return JournalService.create_entry(
        data={
            "tenant_id": mc_env["tenant"].id,
            "entry_date": timezone.localdate(),
            "description": "Manual adjust",
            "status": JournalEntry.STATUS_DRAFT,
            "source_type": JournalEntry.SOURCE_MANUAL,
            "branch_id": mc_env["branch"].id,
            "lines": [
                {
                    "account_id": str(mc_env["cash"].id),
                    "debit": "30",
                    "credit": "0",
                },
                {
                    "account_id": str(mc_env["rev"].id),
                    "debit": "0",
                    "credit": "30",
                },
            ],
        },
        user=user,
    )


@pytest.mark.django_db
def test_maker_cannot_approve_own_draft(mc_env):
    entry = _draft(mc_env, mc_env["maker"])
    assert entry.status == JournalEntry.STATUS_DRAFT
    with pytest.raises(JournalError) as exc:
        JournalService.post_draft(entry=entry, user=mc_env["maker"])
    assert exc.value.code == "JOURNAL_MAKER_CHECKER"


@pytest.mark.django_db
def test_checker_posts_draft(mc_env):
    entry = _draft(mc_env, mc_env["maker"])
    posted = JournalService.post_draft(entry=entry, user=mc_env["checker"])
    assert posted.status == JournalEntry.STATUS_POSTED
    assert posted.approved_by_id == mc_env["checker"].id
    assert posted.approved_at is not None


@pytest.mark.django_db
def test_self_approve_override(mc_env):
    entry = _draft(mc_env, mc_env["maker"])
    posted = JournalService.post_draft(
        entry=entry, user=mc_env["maker"], allow_self_approve=True
    )
    assert posted.status == JournalEntry.STATUS_POSTED
    assert posted.approved_by_id == mc_env["maker"].id


@pytest.mark.django_db
def test_discard_draft(mc_env):
    entry = _draft(mc_env, mc_env["maker"])
    JournalService.discard_draft(entry=entry, user=mc_env["maker"])
    entry.refresh_from_db()
    assert entry.deleted_at is not None


@pytest.mark.django_db
def test_cannot_discard_posted(mc_env):
    entry = _draft(mc_env, mc_env["maker"])
    JournalService.post_draft(entry=entry, user=mc_env["checker"])
    with pytest.raises(JournalError) as exc:
        JournalService.discard_draft(entry=entry, user=mc_env["maker"])
    assert exc.value.code == "JOURNAL_NOT_DRAFT"

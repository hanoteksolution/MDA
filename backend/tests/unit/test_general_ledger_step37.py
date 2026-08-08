"""STEP 37 — General ledger account statement selector."""

from decimal import Decimal

import pytest

from apps.finance.selectors.ledger import GeneralLedgerSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def gl_env(db):
    tenant = Tenant.objects.create(name="GL Co", slug="gl-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="GL Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="gl_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    rev = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user, "cash": cash, "rev": rev}


@pytest.mark.django_db
def test_general_ledger_running_balance(gl_env):
    user = gl_env["user"]
    cash = gl_env["cash"]
    rev = gl_env["rev"]
    today = timezone.localdate()

    JournalService.create_entry(
        data={
            "tenant_id": gl_env["tenant"].id,
            "entry_date": today,
            "description": "Sale 1",
            "branch_id": gl_env["branch"].id,
            "lines": [
                {"account_id": str(cash.id), "debit": "100", "credit": "0"},
                {"account_id": str(rev.id), "debit": "0", "credit": "100"},
            ],
        },
        user=user,
    )
    JournalService.create_entry(
        data={
            "tenant_id": gl_env["tenant"].id,
            "entry_date": today,
            "description": "Sale 2",
            "branch_id": gl_env["branch"].id,
            "lines": [
                {"account_id": str(cash.id), "debit": "40", "credit": "0"},
                {"account_id": str(rev.id), "debit": "0", "credit": "40"},
            ],
        },
        user=user,
    )

    data = GeneralLedgerSelector.run(
        account_id=cash.id, date_from=today, date_to=today, user=user
    )
    assert data["account"]["code"] == "1000"
    assert data["period_debit"] == 140.0
    assert data["closing_balance"] == 140.0
    assert len(data["lines"]) == 2
    assert data["lines"][-1]["running_balance"] == 140.0


@pytest.mark.django_db
def test_general_ledger_opening_balance(gl_env):
    user = gl_env["user"]
    cash = gl_env["cash"]
    rev = gl_env["rev"]
    today = timezone.localdate()
    earlier = today.replace(day=1) if today.day > 1 else today

    JournalService.create_entry(
        data={
            "tenant_id": gl_env["tenant"].id,
            "entry_date": earlier,
            "description": "Prior",
            "lines": [
                {"account_id": str(cash.id), "debit": "25", "credit": "0"},
                {"account_id": str(rev.id), "debit": "0", "credit": "25"},
            ],
        },
        user=user,
    )
    # Query from tomorrow → prior is opening
    from datetime import timedelta

    tomorrow = today + timedelta(days=1)
    data = GeneralLedgerSelector.run(
        account_code="1000", date_from=tomorrow, user=user
    )
    assert data["opening_balance"] == 25.0
    assert data["lines"] == []
    assert data["closing_balance"] == 25.0

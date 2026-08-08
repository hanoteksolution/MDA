"""STEP 21 — finance CoA, journal entries, expense posting, KPI fixes."""

from decimal import Decimal

import pytest

from apps.finance.models import Account, JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.summary_service import FinanceSummaryService
from apps.platform.models import Tenant
from apps.sales.models import Expense
from apps.sales.services.daily_ops_service import DailyOpsService
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def fin_env(db):
    tenant = Tenant.objects.create(
        name="Finance Co", slug="finance-co", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Finance Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    return {"tenant": tenant, "branch": branch}


@pytest.mark.django_db
def test_bootstrap_default_chart(fin_env):
    accounts = ChartService.ensure_default_chart(tenant_id=fin_env["tenant"].id)
    assert len(accounts) >= 10
    assert Account.active_objects().filter(tenant_id=fin_env["tenant"].id, code="1000").exists()


@pytest.mark.django_db
def test_balanced_manual_journal(fin_env):
    ChartService.ensure_default_chart(tenant_id=fin_env["tenant"].id)
    entry = JournalService.create_entry(
        data={
            "tenant_id": fin_env["tenant"].id,
            "description": "Test transfer",
            "lines": [
                {"account_code": "6010", "debit": "50", "credit": "0"},
                {"account_code": "1000", "debit": "0", "credit": "50"},
            ],
        }
    )
    data = JournalService.serialize(entry)
    assert data["is_balanced"] is True
    assert JournalLine.active_objects().filter(entry=entry).count() == 2


@pytest.mark.django_db
def test_unbalanced_journal_rejected(fin_env):
    ChartService.ensure_default_chart(tenant_id=fin_env["tenant"].id)
    with pytest.raises(JournalError, match="not balanced"):
        JournalService.create_entry(
            data={
                "tenant_id": fin_env["tenant"].id,
                "lines": [
                    {"account_code": "6010", "debit": "50", "credit": "0"},
                    {"account_code": "1000", "debit": "0", "credit": "40"},
                ],
            }
        )


@pytest.mark.django_db
def test_expense_posts_balanced_journal(fin_env):
    expense = Expense.objects.create(
        branch=fin_env["branch"],
        tenant_id=fin_env["tenant"].id,
        description="Office supplies",
        category="supplies",
        amount=Decimal("25.00"),
        created_by_user=None,
    )
    entry = JournalService.post_expense(expense=expense)
    assert entry is not None
    assert entry.source_type == JournalEntry.SOURCE_EXPENSE
    data = JournalService.serialize(entry)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 25.0

    # Idempotent re-post
    again = JournalService.post_expense(expense=expense)
    assert again.id == entry.id


@pytest.mark.django_db
def test_daily_ops_create_expense_wires_journal(fin_env):
    payload = DailyOpsService.create_expense(
        data={
            "branch_id": str(fin_env["branch"].id),
            "description": "Internet bill",
            "category": "utilities",
            "amount": "120",
        }
    )
    assert payload["amount"] == 120.0
    assert (
        JournalEntry.active_objects()
        .filter(source_type=JournalEntry.SOURCE_EXPENSE, source_id=payload["id"])
        .exists()
    )


@pytest.mark.django_db
def test_summary_includes_operating_expenses(fin_env):
    Expense.objects.create(
        branch=fin_env["branch"],
        tenant_id=fin_env["tenant"].id,
        description="Rent",
        category="rent",
        amount=Decimal("500"),
    )
    with tenant_context(fin_env["tenant"], enforce=True):
        summary = FinanceSummaryService.get_summary(
            branch_id=fin_env["branch"].id, period="month"
        )
    assert summary["kpis"]["operating_expenses"] >= 500
    assert summary["has_ledger"] is True
    assert len(summary["journal"]) >= 0


@pytest.mark.django_db
def test_accounts_tenant_isolated(fin_env):
    other = Tenant.objects.create(name="Other", slug="other-fin", status=Tenant.STATUS_ACTIVE)
    ChartService.ensure_default_chart(tenant_id=fin_env["tenant"].id)
    ChartService.ensure_default_chart(tenant_id=other.id)
    with tenant_context(fin_env["tenant"], enforce=True):
        visible = list(ChartService.list())
    assert all(a.tenant_id == fin_env["tenant"].id for a in visible)

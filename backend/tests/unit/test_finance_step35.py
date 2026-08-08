"""STEP 35 — Central Accounting Engine foundation (Phase A/B)."""

from decimal import Decimal

import pytest

from apps.finance.events import event_types
from apps.finance.models import Account, AccountMapping, AccountingEvent, FinancialPeriod, JournalEntry
from apps.finance.services.chart_service import ChartService, CONTROL_ACCOUNT_CODES
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingError, MappingService
from apps.finance.services.period_service import PeriodService
from apps.finance.services.posting_service import AccountingPostingService, PostingError
from apps.platform.models import Tenant
from apps.sales.models import Expense
from apps.sales.services.daily_ops_service import DailyOpsService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def cae_env(db):
    tenant = Tenant.objects.create(name="CAE Co", slug="cae-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="CAE Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    return {"tenant": tenant, "branch": branch}


@pytest.mark.django_db
def test_mapping_seed_and_resolve(cae_env):
    tenant_id = cae_env["tenant"].id
    ChartService.ensure_default_chart(tenant_id=tenant_id)
    mappings = MappingService.seed_defaults(tenant_id=tenant_id)
    assert len(mappings) >= 10

    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant_id)
    assert cash.code == "1000"


@pytest.mark.django_db
def test_control_accounts_flagged(cae_env):
    ChartService.ensure_default_chart(tenant_id=cae_env["tenant"].id)
    for code in CONTROL_ACCOUNT_CODES:
        acct = Account.active_objects().get(tenant_id=cae_env["tenant"].id, code=code)
        assert acct.is_control_account is True
        assert acct.allow_manual_posting is False


@pytest.mark.django_db
def test_financial_period_bootstrap(cae_env):
    period = PeriodService.ensure_open_period(tenant_id=cae_env["tenant"].id)
    assert period.status == FinancialPeriod.STATUS_OPEN
    again = PeriodService.ensure_open_period(tenant_id=cae_env["tenant"].id)
    assert again.id == period.id


@pytest.mark.django_db
def test_posting_engine_expense_via_event(cae_env):
    expense = Expense.objects.create(
        branch=cae_env["branch"],
        tenant_id=cae_env["tenant"].id,
        description="Utilities",
        category="utilities",
        amount=Decimal("75.00"),
    )
    entry = AccountingPostingService.post_expense(expense=expense)
    assert entry is not None
    assert entry.source_module == "sales"
    assert entry.idempotency_key.startswith("EXPENSE_APPROVED:")

    event = AccountingEvent.active_objects().get(idempotency_key=entry.idempotency_key)
    assert event.status == AccountingEvent.STATUS_POSTED
    assert event.event_type == event_types.EXPENSE_APPROVED
    assert event.journal_entry_id == entry.id

    data = JournalService.serialize(entry)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 75.0


@pytest.mark.django_db
def test_posting_idempotency(cae_env):
    expense = Expense.objects.create(
        branch=cae_env["branch"],
        tenant_id=cae_env["tenant"].id,
        description="Supplies",
        category="supplies",
        amount=Decimal("10.00"),
    )
    first = AccountingPostingService.post_expense(expense=expense)
    second = AccountingPostingService.post_expense(expense=expense)
    assert first.id == second.id
    assert AccountingEvent.active_objects().filter(idempotency_key=first.idempotency_key).count() == 1
    assert JournalEntry.active_objects().filter(idempotency_key=first.idempotency_key).count() == 1


@pytest.mark.django_db
def test_daily_ops_still_posts_through_engine(cae_env):
    payload = DailyOpsService.create_expense(
        data={
            "branch_id": str(cae_env["branch"].id),
            "description": "Rent",
            "category": "rent",
            "amount": "300",
        }
    )
    event = AccountingEvent.active_objects().filter(
        source_type="expense", source_id=payload["id"]
    ).first()
    assert event is not None
    assert event.status == AccountingEvent.STATUS_POSTED


@pytest.mark.django_db
def test_unsupported_event_rejected(cae_env):
    with pytest.raises(PostingError, match="Unsupported"):
        AccountingPostingService.post(
            event_type=event_types.BANK_TRANSFER_COMPLETED,
            tenant_id=cae_env["tenant"].id,
            source_module="finance",
            source_type="voucher",
            source_id=cae_env["tenant"].id,
            payload={"amount": "100"},
            idempotency_key="test:bank:1",
        )


@pytest.mark.django_db
def test_missing_mapping_raises(cae_env):
    ChartService.ensure_default_chart(tenant_id=cae_env["tenant"].id)
    AccountMapping.active_objects().filter(
        tenant_id=cae_env["tenant"].id, mapping_key="DEFAULT_CASH"
    ).delete()
    with pytest.raises(MappingError):
        MappingService.resolve(key="DEFAULT_CASH", tenant_id=cae_env["tenant"].id)

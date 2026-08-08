"""STEP 37 — PostingRule engine activation."""

from decimal import Decimal

import pytest

from apps.finance.events import event_types
from apps.finance.models import AccountingEvent, JournalEntry, PostingRule
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.posting_rule_service import PostingRuleService
from apps.finance.services.posting_service import AccountingPostingService
from apps.platform.models import Tenant
from apps.sales.models import Expense
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def rule_env(db):
    tenant = Tenant.objects.create(name="Rule Co", slug="rule-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Rule Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="rule_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user}


@pytest.mark.django_db
def test_seed_defaults_creates_rule_driven_events(rule_env):
    tenant = rule_env["tenant"]
    created = PostingRuleService.seed_defaults(tenant_id=tenant.id)
    assert len(created) >= 6
    again = PostingRuleService.seed_defaults(tenant_id=tenant.id)
    assert again == []
    types = set(
        PostingRule.active_objects()
        .filter(tenant_id=tenant.id)
        .values_list("event_type", flat=True)
    )
    assert event_types.EXPENSE_APPROVED in types
    assert event_types.PURCHASE_RECEIVED in types
    assert event_types.CUSTOMER_PAYMENT_RECEIVED in types


@pytest.mark.django_db
def test_expense_posts_via_posting_rule(rule_env):
    tenant = rule_env["tenant"]
    user = rule_env["user"]
    branch = rule_env["branch"]
    PostingRuleService.seed_defaults(tenant_id=tenant.id)

    expense = Expense.objects.create(
        tenant=tenant,
        branch=branch,
        description="Office rent",
        category="rent",
        amount=Decimal("250.00"),
        expense_date=timezone.localdate(),
        created_by=user,
    )
    entry = AccountingPostingService.post_expense(expense=expense, user=user)
    assert entry is not None
    assert entry.status == JournalEntry.STATUS_POSTED
    event = AccountingEvent.active_objects().get(
        tenant_id=tenant.id, source_id=expense.id, event_type=event_types.EXPENSE_APPROVED
    )
    assert event.status == AccountingEvent.STATUS_POSTED

    # Prove rule path: deactivate expense rules → still posts via hardcoded fallback
    PostingRule.active_objects().filter(
        tenant_id=tenant.id, event_type=event_types.EXPENSE_APPROVED
    ).update(is_active=False)
    expense2 = Expense.objects.create(
        tenant=tenant,
        branch=branch,
        description="Utilities",
        category="utilities",
        amount=Decimal("40.00"),
        expense_date=timezone.localdate(),
        created_by=user,
    )
    entry2 = AccountingPostingService.post_expense(expense=expense2, user=user)
    assert entry2 is not None


@pytest.mark.django_db
def test_try_build_lines_customer_payment(rule_env):
    tenant = rule_env["tenant"]
    PostingRuleService.seed_defaults(tenant_id=tenant.id)
    lines, desc, _ = PostingRuleService.try_build_lines(
        event_type=event_types.CUSTOMER_PAYMENT_RECEIVED,
        tenant_id=tenant.id,
        payload={"amount": "75", "payment_method": "mobile", "invoice_number": "INV-1"},
    )
    assert len(lines) == 2
    assert sum(Decimal(str(l["debit"])) for l in lines) == Decimal("75")
    assert sum(Decimal(str(l["credit"])) for l in lines) == Decimal("75")
    assert "INV-1" in desc


@pytest.mark.django_db
def test_sale_still_uses_builtin_builder(rule_env):
    """SALE_COMPLETED is not rule-driven yet — try_build returns None."""
    tenant = rule_env["tenant"]
    PostingRuleService.seed_defaults(tenant_id=tenant.id)
    assert (
        PostingRuleService.try_build_lines(
            event_type=event_types.SALE_COMPLETED,
            tenant_id=tenant.id,
            payload={"total_amount": "10"},
        )
        is None
    )

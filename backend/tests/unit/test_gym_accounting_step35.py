"""STEP 35 — gym membership GL + trial balance."""

from decimal import Decimal

import pytest

from django.db.models import Sum

from apps.finance.events import event_types
from apps.finance.models import AccountingEvent, JournalEntry, JournalLine
from apps.finance.selectors.trial_balance import TrialBalanceSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.gym.services.gym_payment_service import GymPaymentService
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def gym_gl_env(db):
    tenant = Tenant.objects.create(name="Gym GL", slug="gym-gl", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Gym GL Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Desk", code="DK", is_default=True
    )
    member = MemberService.create(
        data={"full_name": "Lifter", "phone": "123", "tenant": tenant, "branch_id": branch.id}
    )
    plan = PlanService.create(
        data={
            "code": "silver",
            "name": "Silver Monthly",
            "duration_days": 30,
            "price": "50.00",
            "tenant": tenant,
        }
    )
    return {"tenant": tenant, "branch": branch, "member": member, "plan": plan}


@pytest.mark.django_db
def test_gym_membership_posts_revenue_journal(gym_gl_env):
    result = GymPaymentService.checkout_membership(
        data={
            "member_id": gym_gl_env["member"].id,
            "plan_id": gym_gl_env["plan"].id,
            "payment_method": "cash",
            "tenant": gym_gl_env["tenant"],
        }
    )
    invoice_id = result["invoice"]["id"]
    journal = JournalEntry.active_objects().get(source_id=invoice_id, source_module="gym")
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 50.0

    revenue_line = next(
        line for line in data["lines"] if line["account_code"] == "4000" and line["credit"] > 0
    )
    assert revenue_line["credit"] == 50.0

    event = AccountingEvent.active_objects().get(
        event_type=event_types.GYM_MEMBERSHIP_SOLD, source_id=invoice_id
    )
    assert event.status == AccountingEvent.STATUS_POSTED


@pytest.mark.django_db
def test_trial_balance_is_balanced(gym_gl_env):
    tenant = gym_gl_env["tenant"]
    ChartService.ensure_default_chart(tenant_id=tenant.id)

    GymPaymentService.checkout_membership(
        data={
            "member_id": gym_gl_env["member"].id,
            "plan_id": gym_gl_env["plan"].id,
            "payment_method": "cash",
            "tenant": tenant,
        }
    )

    with tenant_context(tenant, enforce=True):
        report = TrialBalanceSelector.run()

    assert report["is_balanced"] is True
    assert report["totals"]["debit"] == report["totals"]["credit"]
    assert report["totals"]["debit"] >= 50.0
    codes = {row["code"] for row in report["rows"]}
    assert "1000" in codes
    assert "4000" in codes

    total_d = JournalLine.active_objects().filter(
        entry__tenant_id=tenant.id, entry__status="posted"
    ).aggregate(d=Sum("debit"))["d"]
    total_c = JournalLine.active_objects().filter(
        entry__tenant_id=tenant.id, entry__status="posted"
    ).aggregate(c=Sum("credit"))["c"]
    assert total_d == total_c

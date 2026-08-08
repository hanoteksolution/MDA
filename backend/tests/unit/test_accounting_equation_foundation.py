"""Accounting equation + double-entry foundation tests (prompt Phases 1–11, 18)."""

from decimal import Decimal

import pytest

from apps.finance.domain.account_behavior import (
    AccountClass,
    NormalBalance,
    Side,
    is_debit_normal,
    normal_balance_for,
    side_for_decrease,
    side_for_increase,
)
from apps.finance.models import Account
from apps.finance.services.chart_service import ChartService
from apps.finance.services.equation_service import AccountingEquationService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.journal_validation_service import JournalValidationService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def eq_env(db):
    tenant = Tenant.objects.create(name="Eq Co", slug="eq-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Eq Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    User = get_user_model()
    user = User.objects.create_user(
        username="eq_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user}


@pytest.mark.django_db
def test_account_class_normal_balances():
    assert normal_balance_for(AccountClass.ASSET) == NormalBalance.DEBIT
    assert normal_balance_for(AccountClass.EXPENSE) == NormalBalance.DEBIT
    assert normal_balance_for(AccountClass.LIABILITY) == NormalBalance.CREDIT
    assert normal_balance_for(AccountClass.EQUITY) == NormalBalance.CREDIT
    assert normal_balance_for(AccountClass.REVENUE) == NormalBalance.CREDIT
    assert is_debit_normal(AccountClass.ASSET) is True
    assert side_for_increase(AccountClass.ASSET) == Side.DEBIT
    assert side_for_decrease(AccountClass.ASSET) == Side.CREDIT
    assert side_for_increase(AccountClass.REVENUE) == Side.CREDIT


@pytest.mark.django_db
def test_unbalanced_journal_rejected_with_code(eq_env):
    user = eq_env["user"]
    with pytest.raises(JournalError) as exc:
        JournalService.create_entry(
            data={
                "description": "Unbalanced",
                "lines": [
                    {"account_code": "1000", "debit": "100", "credit": "0"},
                    {"account_code": "4000", "debit": "0", "credit": "90"},
                ],
            },
            user=user,
        )
    assert exc.value.code == "UNBALANCED_JOURNAL"
    assert Decimal(exc.value.details["difference"]) == Decimal("10")


@pytest.mark.django_db
def test_manual_post_to_control_ar_rejected(eq_env):
    user = eq_env["user"]
    # 1100 AR is control + allow_manual_posting=False
    with pytest.raises(JournalError) as exc:
        JournalService.create_entry(
            data={
                "description": "Manual AR",
                "source_type": "manual",
                "lines": [
                    {"account_code": "1100", "debit": "50", "credit": "0"},
                    {"account_code": "4000", "debit": "0", "credit": "50"},
                ],
            },
            user=user,
        )
    assert exc.value.code == "JOURNAL_CONTROL_ACCOUNT"


@pytest.mark.django_db
def test_cash_sale_keeps_equation(eq_env):
    user = eq_env["user"]
    tenant = eq_env["tenant"]
    JournalService.create_entry(
        data={
            "description": "Owner capital",
            "source_type": "manual",
            "lines": [
                {"account_code": "1000", "debit": "1000", "credit": "0"},
                {"account_code": "3000", "debit": "0", "credit": "1000"},
            ],
        },
        user=user,
    )
    JournalService.create_entry(
        data={
            "description": "Cash sale",
            "source_type": "invoice",
            "lines": [
                {"account_code": "1000", "debit": "100", "credit": "0"},
                {"account_code": "4000", "debit": "0", "credit": "100"},
            ],
        },
        user=user,
    )
    JournalService.create_entry(
        data={
            "description": "COGS",
            "source_type": "invoice",
            "lines": [
                {"account_code": "5000", "debit": "60", "credit": "0"},
                {"account_code": "1200", "debit": "0", "credit": "60"},
            ],
        },
        user=user,
    )
    result = AccountingEquationService.evaluate(tenant_id=tenant.id, user=user)
    assert result["ok"] is True
    assert result["balance_sheet_ok"] is True
    assert result["expanded_ok"] is True


@pytest.mark.django_db
def test_validation_rejects_both_sides():
    with pytest.raises(Exception) as exc:
        JournalValidationService.validate_lines(
            [
                {"debit": "10", "credit": "10"},
                {"debit": "0", "credit": "0"},
            ]
        )
    assert "both debit and credit" in str(exc.value).lower() or getattr(
        exc.value, "code", ""
    ) == "JOURNAL_LINE_BOTH_SIDES"


@pytest.mark.django_db
def test_account_model_uses_text_choices(eq_env):
    acc = Account.active_objects().filter(tenant_id=eq_env["tenant"].id, code="1000").first()
    assert acc is not None
    assert acc.normal_balance == NormalBalance.DEBIT
    assert acc.account_class == AccountClass.ASSET

"""STEP 35 Phase P — per-tenant accounting cutover."""

from datetime import timedelta

import pytest

from apps.finance.models import AccountingEvent
from apps.finance.services.cutover_service import AccountingCutoverService, CutoverError
from apps.finance.services.posting_service import AccountingPostingService
from apps.platform.models import Tenant, TenantSettings
from apps.sales.models import Expense
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.tenancy import tenant_context


@pytest.fixture
def cutover_env(db):
    tenant = Tenant.objects.create(
        name="Cutover Co", slug="cutover-co", status=Tenant.STATUS_ACTIVE
    )
    TenantSettings.objects.create(tenant=tenant)
    company = Company.objects.create(name="Cutover Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    User = get_user_model()
    user = User.objects.create_user(
        username="cutover_user", password="pass12345", tenant=tenant, branch=branch
    )
    return {"tenant": tenant, "branch": branch, "user": user}


@pytest.mark.django_db
def test_prepare_and_status(cutover_env):
    tenant = cutover_env["tenant"]
    with tenant_context(tenant, enforce=True):
        status = AccountingCutoverService.prepare(tenant_id=tenant.id)
    assert status["prepared"] is True
    assert status["posting_enabled"] is True
    assert status["phase"] == "pre_cutover"
    assert status["global_engine_enabled"] is True


@pytest.mark.django_db
def test_activate_sets_cutover_date(cutover_env):
    tenant = cutover_env["tenant"]
    day = timezone.localdate()
    with tenant_context(tenant, enforce=True):
        result = AccountingCutoverService.activate(
            tenant_id=tenant.id, cutover_date=day.isoformat()
        )
    assert result["activated"] is True
    assert result["cutover_date"] == day.isoformat()
    assert result["phase"] == "live"
    assert AccountingCutoverService.is_strict_after_cutover(tenant_id=tenant.id) is True


@pytest.mark.django_db
def test_disable_posting_skips_journals(cutover_env):
    tenant = cutover_env["tenant"]
    branch = cutover_env["branch"]
    user = cutover_env["user"]

    AccountingCutoverService.disable_posting(tenant_id=tenant.id)
    assert AccountingCutoverService.is_posting_enabled(tenant_id=tenant.id) is False

    exp = Expense.objects.create(
        tenant=tenant,
        branch=branch,
        description="Should not post",
        category="rent",
        amount=25,
        expense_date=timezone.localdate(),
        created_by=user,
    )
    entry = AccountingPostingService.post_expense(expense=exp, user=user)
    assert entry is None
    assert not AccountingEvent.active_objects().filter(source_id=exp.id).exists()


@pytest.mark.django_db
def test_activate_rejects_future_prepare_with_errors(cutover_env, monkeypatch):
    tenant = cutover_env["tenant"]

    def bad_health(**kwargs):
        return {
            "status": "unhealthy",
            "checks": [],
            "summary": {"ok": 0, "warnings": 0, "errors": 2},
        }

    monkeypatch.setattr(
        "apps.finance.services.cutover_service.AccountingHealthService.check",
        staticmethod(bad_health),
    )
    with tenant_context(tenant, enforce=True):
        # prepare still works
        AccountingCutoverService.prepare(tenant_id=tenant.id)
        with pytest.raises(CutoverError, match="critical health"):
            AccountingCutoverService.activate(
                tenant_id=tenant.id, cutover_date=timezone.localdate()
            )

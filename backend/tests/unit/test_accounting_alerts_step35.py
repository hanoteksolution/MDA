"""STEP 35 Phase O — Celery accounting health dual-run alerts."""

from decimal import Decimal

import pytest

from apps.finance.models import JournalEntry, JournalLine
from apps.finance.services.chart_service import ChartService
from apps.finance.tasks.accounting_alerts import scan_accounting_health
from apps.notifications.models import Notification
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def alert_env(db):
    tenant = Tenant.objects.create(
        name="Alert Co", slug="alert-co", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Alert Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    User = get_user_model()
    user = User.objects.create_user(
        username="alert_finance",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user}


@pytest.mark.django_db
def test_scan_accounting_health_healthy_tenant(alert_env):
    result = scan_accounting_health()
    assert result["tenants_scanned"] >= 1
    assert "notifications_created" in result
    assert "tenants_with_issues" in result


@pytest.mark.django_db
def test_scan_notifies_on_unbalanced_journal(alert_env, monkeypatch):
    tenant = alert_env["tenant"]
    user = alert_env["user"]

    from apps.notifications.services import notification_service as ns

    monkeypatch.setattr(
        ns.NotificationService,
        "tenant_users_with_permission",
        staticmethod(lambda tenant, permission_codename: [user]),
    )

    cash = ChartService.get_by_code(code="1000", tenant_id=tenant.id)
    entry = JournalEntry.objects.create(
        tenant_id=tenant.id,
        entry_number="JE-BAD-1",
        entry_date=timezone.localdate(),
        description="Unbalanced test",
        status=JournalEntry.STATUS_POSTED,
        source_type=JournalEntry.SOURCE_MANUAL,
        created_by=user,
    )
    JournalLine.objects.create(
        entry=entry, account=cash, debit=Decimal("10"), credit=Decimal("0")
    )

    result = scan_accounting_health()
    assert result["tenants_with_issues"] >= 1
    assert result["notifications_created"] >= 1
    assert Notification.active_objects().filter(
        tenant_id=tenant.id,
        notification_type=Notification.TYPE_ACCOUNTING_HEALTH,
        user=user,
    ).exists()

    again = scan_accounting_health()
    assert again["notifications_created"] == 0

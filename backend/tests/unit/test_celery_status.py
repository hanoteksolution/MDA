"""Celery beat schedule registration + health probe."""

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from core.health.checks import check_celery


@pytest.mark.django_db
def test_beat_schedule_has_foundation_jobs():
    schedule = settings.CELERY_BEAT_SCHEDULE
    tasks = {entry["task"] for entry in schedule.values()}
    assert "notifications.run_all_scheduled_scans" in tasks
    assert "finance.scan_accounting_health" in tasks


@pytest.mark.django_db
def test_check_celery_reports_schedule(settings):
    result = check_celery(require_workers=False)
    assert result["component"] == "celery"
    assert result["scheduled_jobs"] >= 2
    assert "finance.scan_accounting_health" in result["scheduled_tasks"]
    # Without Redis, broker error → overall error; with Redis, ok/degraded
    assert result["status"] in ("ok", "degraded", "error")


@pytest.mark.django_db
def test_health_celery_endpoint():
    client = APIClient()
    response = client.get("/api/v1/health/celery/")
    assert response.status_code in (200, 503)
    assert response.data["component"] == "celery"
    assert "scheduled_tasks" in response.data
    assert "finance.scan_accounting_health" in response.data["scheduled_tasks"]


@pytest.mark.django_db
def test_celery_status_command(django_db_blocker):
    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    # May raise if broker down and status error — catch that as acceptable in unit env
    try:
        call_command("celery_status", stdout=out)
    except Exception as exc:
        assert "Celery health check failed" in str(exc)
        return
    assert "scheduled_jobs" in out.getvalue()

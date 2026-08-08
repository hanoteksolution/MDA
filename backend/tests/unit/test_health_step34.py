"""STEP 34 — expanded health endpoints (database, cache, readiness)."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_liveness():
    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


@pytest.mark.django_db
def test_health_database_ok():
    client = APIClient()
    response = client.get("/api/v1/health/database/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert response.data["component"] == "database"
    assert "latency_ms" in response.data


@pytest.mark.django_db
def test_health_cache_ok():
    client = APIClient()
    response = client.get("/api/v1/health/cache/")
    # SQLite test env has no Redis — expect 503 unless REDIS_URL reachable
    if response.status_code == 200:
        assert response.data["status"] == "ok"
        assert response.data["component"] == "cache"
    else:
        assert response.status_code == 503
        assert response.data["status"] == "error"


@pytest.mark.django_db
def test_health_ready_reflects_components():
    client = APIClient()
    response = client.get("/api/v1/health/ready/")
    assert response.status_code in (200, 503)
    assert "components" in response.data
    assert response.data["components"]["database"]["status"] == "ok"


@pytest.mark.django_db
def test_check_cache_error_when_redis_unreachable(settings):
    settings.REDIS_URL = "redis://127.0.0.1:6399/0"
    from core.health.checks import check_cache

    result = check_cache()
    assert result["status"] == "error"
    assert result["component"] == "cache"

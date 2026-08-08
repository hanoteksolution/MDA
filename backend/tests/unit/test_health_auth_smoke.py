import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_ok():
    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.data.get("status") == "ok"


@pytest.mark.django_db
def test_login_success(user):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"username": "smoke_user", "password": "smoke-pass-123"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access" in body["data"]
    assert "refresh" in body["data"]


@pytest.mark.django_db
def test_login_invalid_credentials_envelope():
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"username": "nobody", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "message" in body

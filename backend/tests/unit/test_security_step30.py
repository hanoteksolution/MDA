"""STEP 30 — security hardening (lockout, headers, uploads)."""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.fixture
def auth_client(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(username="sec_user", password="correct-pass")
    return user


@pytest.mark.django_db
@override_settings(
    LOGIN_LOCKOUT_MAX_ATTEMPTS=3,
    LOGIN_LOCKOUT_WINDOW_MINUTES=15,
    LOGIN_LOCKOUT_DURATION_MINUTES=30,
)
def test_login_lockout_after_failures(auth_client):
    client = APIClient()
    for _ in range(3):
        response = client.post(
            "/api/v1/auth/login/",
            {"username": "sec_user", "password": "wrong"},
            format="json",
        )
        assert response.status_code == 401

    locked = client.post(
        "/api/v1/auth/login/",
        {"username": "sec_user", "password": "wrong"},
        format="json",
    )
    assert locked.status_code == 403
    body = locked.json()
    assert body["code"] == "ACCOUNT_LOCKED"
    assert body["details"]["retry_after_seconds"] > 0


@pytest.mark.django_db
@override_settings(
    LOGIN_LOCKOUT_MAX_ATTEMPTS=3,
    LOGIN_LOCKOUT_WINDOW_MINUTES=15,
    LOGIN_LOCKOUT_DURATION_MINUTES=30,
)
def test_login_succeeds_before_lockout_threshold(auth_client):
    client = APIClient()
    for _ in range(2):
        client.post(
            "/api/v1/auth/login/",
            {"username": "sec_user", "password": "wrong"},
            format="json",
        )
    ok = client.post(
        "/api/v1/auth/login/",
        {"username": "sec_user", "password": "correct-pass"},
        format="json",
    )
    assert ok.status_code == 200


@pytest.mark.django_db
def test_security_headers_middleware():
    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.get("X-Content-Type-Options") == "nosniff"
    assert response.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.django_db
def test_invalid_upload_rejected():
    from django.core.files.uploadedfile import SimpleUploadedFile

    from core.utils.media import save_product_image

    bad = SimpleUploadedFile("evil.txt", b"not-an-image", content_type="text/plain")
    with pytest.raises(ValueError, match="Invalid image type"):
        save_product_image(uploaded_file=bad)

    corrupt = SimpleUploadedFile("bad.jpg", b"not-really-jpeg", content_type="image/jpeg")
    with pytest.raises(ValueError, match="Invalid or corrupted"):
        save_product_image(uploaded_file=corrupt)

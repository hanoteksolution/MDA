"""STEP 27 — mobile API foundation (OpenAPI, throttling, tenant slug header, contracts)."""

import json

import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.platform.services.platform_service import PlatformService
from apps.platform.services.tenant_resolver import (
    apply_mobile_tenant_slug_header,
    resolve_tenant_from_hostname,
    resolve_tenant_from_slug,
)
from core.throttling import AuthRateThrottle


class _OnePerMinuteAuthThrottle(AuthRateThrottle):
    rate = "1/minute"


@pytest.fixture
def mobile_shop(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Mobile Gym",
            "subdomain": "mobilegym",
            "business_type_code": "gym",
            "owner": {"username": "mobile_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    return tenant


@pytest.mark.django_db
def test_mobile_meta_public(api_client):
    response = api_client.get("/api/v1/mobile/meta/")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["api_version"] == "v1"
    assert data["auth"]["refresh"] == "/api/v1/auth/refresh/"
    assert data["tenant"]["slug_header"] == "X-Tenant-Slug"
    assert data["openapi"]["schema"] == "/api/v1/schema/"
    assert "auth" in data["rate_limits"]


@pytest.mark.django_db
def test_openapi_schema_loads(api_client):
    response = api_client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    schema = json.loads(response.content)
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "MDA ERP API"
    paths = schema.get("paths", {})
    assert "/api/v1/auth/login/" in paths
    assert "/api/v1/mobile/meta/" in paths


@pytest.mark.django_db
def test_resolve_tenant_from_slug(mobile_shop):
    resolution = resolve_tenant_from_slug("mobilegym")
    assert resolution.mode == "tenant"
    assert resolution.tenant_id == mobile_shop.id
    assert resolution.reason == "tenant_slug"


@pytest.mark.django_db
def test_apply_mobile_tenant_slug_header_on_platform_host(mobile_shop):
    platform = resolve_tenant_from_hostname("api.erp.safaritechno.com")
    assert platform.mode == "platform"
    resolved = apply_mobile_tenant_slug_header(
        platform,
        hostname="api.erp.safaritechno.com",
        tenant_slug_header="mobilegym",
    )
    assert resolved.mode == "tenant"
    assert resolved.tenant_id == mobile_shop.id
    assert resolved.reason == "tenant_slug_header"


@pytest.mark.django_db
def test_x_tenant_slug_header_on_api_host(api_client, mobile_shop):
    response = api_client.get(
        "/api/v1/platform/resolve-host/",
        HTTP_HOST="api.erp.safaritechno.com",
        HTTP_X_TENANT_SLUG="mobilegym",
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["mode"] == "tenant"
    assert body["tenant"]["slug"] == "mobilegym"
    assert response.get("X-Tenant-Mode") == "tenant"
    assert response.get("X-Tenant-Slug") == "mobilegym"


@pytest.mark.django_db
def test_refresh_returns_success_envelope(api_client, mobile_shop):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"username": "mobile_owner", "password": "pass12345"},
        format="json",
        HTTP_HOST="mobilegym.erp.safaritechno.com",
    )
    assert login.status_code == 200
    refresh_token = login.json()["data"]["refresh"]
    response = api_client.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
        HTTP_HOST="mobilegym.erp.safaritechno.com",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access" in body["data"]
    assert body["message"] == "Token refreshed."


@pytest.mark.django_db
def test_mobile_bootstrap_authenticated(api_client, mobile_shop):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"username": "mobile_owner", "password": "pass12345"},
        format="json",
        HTTP_HOST="api.erp.safaritechno.com",
        HTTP_X_TENANT_SLUG="mobilegym",
    )
    assert login.status_code == 200
    token = login.json()["data"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(
        "/api/v1/mobile/bootstrap/",
        HTTP_HOST="api.erp.safaritechno.com",
        HTTP_X_TENANT_SLUG="mobilegym",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user"]["username"] == "mobile_owner"
    assert data["tenant_context"]["tenant"]["slug"] == "mobilegym"
    assert data["entitlements"]["plan_code"] == "starter"


@pytest.mark.django_db
def test_auth_throttle_returns_envelope(mobile_shop, monkeypatch):
    from django.core.cache import cache

    from api.v1.auth import views as auth_views

    cache.clear()
    monkeypatch.setattr(auth_views.LoginView, "throttle_classes", [_OnePerMinuteAuthThrottle])

    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"username": "nobody", "password": "wrong"},
        format="json",
        HTTP_HOST="mobilegym.erp.safaritechno.com",
        REMOTE_ADDR="10.0.0.99",
    )
    assert response.status_code == 401
    throttled = client.post(
        "/api/v1/auth/login/",
        {"username": "nobody", "password": "wrong"},
        format="json",
        HTTP_HOST="mobilegym.erp.safaritechno.com",
        REMOTE_ADDR="10.0.0.99",
    )
    assert throttled.status_code == 429
    body = throttled.json()
    assert body["success"] is False
    assert body["code"] == "RATE_LIMITED"

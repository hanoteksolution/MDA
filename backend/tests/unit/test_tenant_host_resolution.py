import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.platform.models import Tenant
from apps.platform.services.platform_service import PlatformService
from apps.platform.services.tenant_resolver import (
    extract_subdomain,
    normalize_hostname,
    resolve_tenant_from_hostname,
    user_matches_host_tenant,
)
from core.tenancy import get_current_tenant, get_current_tenant_id


@pytest.mark.django_db
def test_resolve_platform_apex():
    resolution = resolve_tenant_from_hostname("erp.safaritechno.com")
    assert resolution.mode == "platform"
    assert resolution.tenant is None


@pytest.mark.django_db
def test_resolve_tenant_by_subdomain():
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Power Gym",
            "subdomain": "powergym",
            "business_type_code": "gym",
            "owner": {"username": "gym_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    resolution = resolve_tenant_from_hostname("powergym.erp.safaritechno.com")
    assert resolution.mode == "tenant"
    assert resolution.tenant_id == tenant.id
    assert resolution.subdomain == "powergym"


@pytest.mark.django_db
def test_resolve_unknown_subdomain():
    resolution = resolve_tenant_from_hostname("missing.erp.safaritechno.com")
    assert resolution.mode == "unknown"
    assert resolution.subdomain == "missing"


def test_extract_subdomain_and_normalize():
    assert normalize_hostname("Arabica.ERP.SafariTechno.com:443") == "arabica.erp.safaritechno.com"
    assert extract_subdomain("arabica.erp.safaritechno.com") == "arabica"
    assert extract_subdomain("erp.safaritechno.com") is None


@pytest.mark.django_db
def test_middleware_sets_request_tenant(api_client, db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Fresh Mart",
            "subdomain": "freshmart",
            "owner": {"username": "fm_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    response = api_client.get(
        "/api/v1/platform/resolve-host/",
        HTTP_HOST="freshmart.erp.safaritechno.com",
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["mode"] == "tenant"
    assert body["tenant"]["slug"] == "freshmart"
    assert body["tenant"]["id"] == str(tenant.id)
    assert response.get("X-Tenant-Mode") == "tenant"
    assert response.get("X-Tenant-Slug") == "freshmart"
    # context cleared after response
    assert get_current_tenant() is None


@pytest.mark.django_db
def test_login_rejects_cross_tenant_host():
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    PlatformService.create_shop(
        data={
            "name": "Shop A",
            "subdomain": "shopa",
            "owner": {"username": "owner_a", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    PlatformService.create_shop(
        data={
            "name": "Shop B",
            "subdomain": "shopb",
            "owner": {"username": "owner_b", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"username": "owner_a", "password": "pass12345"},
        format="json",
        HTTP_HOST="shopb.erp.safaritechno.com",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "TENANT_HOST_MISMATCH"


@pytest.mark.django_db
def test_jwt_rejects_cross_tenant_host_on_me():
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    PlatformService.create_shop(
        data={
            "name": "Shop A2",
            "subdomain": "shopa2",
            "owner": {"username": "owner_a2", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    PlatformService.create_shop(
        data={
            "name": "Shop B2",
            "subdomain": "shopb2",
            "owner": {"username": "owner_b2", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "owner_a2", "password": "pass12345"},
        format="json",
        HTTP_HOST="shopa2.erp.safaritechno.com",
    )
    assert login.status_code == 200
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    denied = client.get("/api/v1/auth/me/", HTTP_HOST="shopb2.erp.safaritechno.com")
    assert denied.status_code == 401


@pytest.mark.django_db
def test_platform_admin_can_use_tenant_host():
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    PlatformService.create_shop(
        data={
            "name": "Shop C",
            "subdomain": "shopc",
            "owner": {"username": "owner_c", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        }
    )
    User = get_user_model()
    admin = User.objects.create_user(
        username="global_admin",
        password="pass12345",
        is_platform_admin=True,
    )
    tenant = Tenant.objects.get(slug="shopc")
    assert user_matches_host_tenant(admin, tenant) is True

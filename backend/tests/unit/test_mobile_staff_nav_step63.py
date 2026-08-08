"""STEP 63 — PHASE 24 hotel/restaurant staff mobile workspaces."""

import pytest
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def hospitality_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Hospitality Nav",
            "subdomain": "hospnav",
            "business_type_code": "hotel",
            "owner": {"username": "hosp_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["hotel", "restaurant", "pos", "inventory", "sales"],
        validate_dependencies=False,
    )
    return {"tenant": tenant, "user": owner}


def _bootstrap(username="hosp_owner", host="hospnav.erp.safaritechno.com", audience="staff"):
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": username, "password": "pass12345"},
        format="json",
        HTTP_HOST=host,
    )
    assert login.status_code == 200, login.content
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    url = "/api/v1/mobile/bootstrap/"
    if audience:
        url += f"?audience={audience}"
    response = client.get(url, HTTP_HOST=host)
    assert response.status_code == 200
    return response.json()["data"]


@pytest.mark.django_db
def test_catalog_includes_hotel_and_restaurant_staff():
    ids = {w["id"] for w in MobileNavService.catalog(audience="staff")}
    assert "hotel_staff" in ids
    assert "restaurant_staff" in ids
    assert "gym_member" not in ids


@pytest.mark.django_db
def test_staff_bootstrap_hospitality_workspaces(hospitality_env):
    data = _bootstrap()
    nav = data["mobile_nav"]
    ids = {w["id"] for w in nav["workspaces"]}
    assert "staff_hub" in ids
    assert "hotel_staff" in ids
    assert "restaurant_staff" in ids
    assert "gym_staff" not in ids
    assert "pharmacy_staff" not in ids
    assert "gym_member" not in ids


@pytest.mark.django_db
def test_hospitality_hidden_when_modules_disabled(hospitality_env):
    sync_tenant_modules(
        tenant=hospitality_env["tenant"],
        enabled_codes=["pos", "inventory", "sales"],
        validate_dependencies=False,
        disable_missing=True,
    )
    data = _bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "hotel_staff" not in ids
    assert "restaurant_staff" not in ids

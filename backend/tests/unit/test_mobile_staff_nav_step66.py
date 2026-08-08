"""STEP 66 — PHASE 24 property/housing/office staff mobile workspaces."""

import pytest
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def property_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Property Nav",
            "subdomain": "propnav",
            "business_type_code": "property",
            "owner": {"username": "prop_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=[
            "property_management",
            "housing_rental",
            "office_rental",
            "sales",
        ],
        validate_dependencies=True,
    )
    return {"tenant": tenant, "user": owner}


def _bootstrap(username="prop_owner", host="propnav.erp.safaritechno.com", audience="staff"):
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
def test_catalog_includes_property_housing_office_staff():
    ids = {w["id"] for w in MobileNavService.catalog(audience="staff")}
    assert {"property_staff", "housing_staff", "office_staff"} <= ids
    assert "gym_member" not in ids


@pytest.mark.django_db
def test_staff_bootstrap_property_workspaces(property_env):
    data = _bootstrap()
    nav = data["mobile_nav"]
    ids = {w["id"] for w in nav["workspaces"]}
    assert "staff_hub" in ids
    assert "property_staff" in ids
    assert "housing_staff" in ids
    assert "office_staff" in ids
    assert "gym_staff" not in ids
    assert "hotel_staff" not in ids
    assert "gym_member" not in ids
    routes = {s["route"] for s in nav["screens"]}
    assert {"PropertyWorkspace", "HousingWorkspace", "OfficeWorkspace"} <= routes


@pytest.mark.django_db
def test_housing_hidden_when_property_core_disabled(property_env):
    """Housing/office require property_management (runtime tenant_module_ready)."""
    sync_tenant_modules(
        tenant=property_env["tenant"],
        enabled_codes=["housing_rental", "office_rental"],
        validate_dependencies=False,
        disable_missing=True,
    )
    data = _bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "property_staff" not in ids
    assert "housing_staff" not in ids
    assert "office_staff" not in ids


@pytest.mark.django_db
def test_property_only_hides_housing_and_office(property_env):
    sync_tenant_modules(
        tenant=property_env["tenant"],
        enabled_codes=["property_management"],
        validate_dependencies=False,
        disable_missing=True,
    )
    data = _bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "property_staff" in ids
    assert "housing_staff" not in ids
    assert "office_staff" not in ids

"""STEP 61 — PHASE 24 staff mobile_nav audience + workspaces."""

import pytest
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def staff_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Staff Nav Co",
            "subdomain": "staffnav",
            "business_type_code": "gym",
            "owner": {"username": "staff_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["gym", "pharmacy", "inventory", "pos", "sales"],
        validate_dependencies=False,
    )
    return {"tenant": tenant, "user": owner}


def _bootstrap(username="staff_owner", host="staffnav.erp.safaritechno.com", audience=None):
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
def test_catalog_includes_staff_workspaces():
    ids = {w["id"] for w in MobileNavService.catalog()}
    assert {
        "gym_member",
        "staff_hub",
        "gym_staff",
        "pharmacy_staff",
        "hotel_staff",
        "restaurant_staff",
    } <= ids
    staff_ids = {w["id"] for w in MobileNavService.catalog(audience="staff")}
    assert "gym_member" not in staff_ids
    assert "gym_staff" in staff_ids


@pytest.mark.django_db
def test_staff_bootstrap_returns_module_switcher_workspaces(staff_env):
    data = _bootstrap(audience="staff")
    nav = data["mobile_nav"]
    assert nav["audience"] == "staff"
    ids = {w["id"] for w in nav["workspaces"]}
    assert "staff_hub" in ids
    assert "gym_staff" in ids
    assert "pharmacy_staff" in ids
    assert "gym_member" not in ids
    assert data.get("gym_member") is None


@pytest.mark.django_db
def test_member_audience_excludes_staff_workspaces(staff_env):
    # Create member-like bootstrap with admin still has gym.view — use audience filter
    data = _bootstrap(audience="member")
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    # Admin may lack gym.member_portal → empty member workspaces is OK
    assert "gym_staff" not in ids
    assert "staff_hub" not in ids
    assert "pharmacy_staff" not in ids

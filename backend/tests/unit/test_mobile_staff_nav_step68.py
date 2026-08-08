"""STEP 68 — PHASE 24 futsal staff mobile workspace."""

import pytest
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def futsal_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Futsal Nav",
            "subdomain": "futsalnav",
            "business_type_code": "futsal",
            "owner": {"username": "futsal_nav_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["futsal", "pos", "inventory", "sales"],
        validate_dependencies=False,
    )
    return {"tenant": tenant, "user": owner}


def _bootstrap(
    username="futsal_nav_owner",
    host="futsalnav.erp.safaritechno.com",
    audience="staff",
):
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
def test_catalog_includes_futsal_staff():
    ids = {w["id"] for w in MobileNavService.catalog(audience="staff")}
    assert "futsal_staff" in ids
    assert "gym_member" not in ids


@pytest.mark.django_db
def test_staff_bootstrap_futsal_workspace(futsal_env):
    data = _bootstrap()
    nav = data["mobile_nav"]
    ids = {w["id"] for w in nav["workspaces"]}
    assert "staff_hub" in ids
    assert "futsal_staff" in ids
    assert "gym_staff" not in ids
    assert "pharmacy_staff" not in ids
    assert "gym_member" not in ids
    routes = {s["route"] for s in nav["screens"]}
    assert "FutsalWorkspace" in routes


@pytest.mark.django_db
def test_futsal_hidden_when_module_disabled(futsal_env):
    sync_tenant_modules(
        tenant=futsal_env["tenant"],
        enabled_codes=["pos", "inventory", "sales"],
        validate_dependencies=False,
        disable_missing=True,
    )
    data = _bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "futsal_staff" not in ids

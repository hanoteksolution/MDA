"""STEP 58 — PHASE 24 mobile dynamic module navigation (bootstrap)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.gym.models import Member
from apps.gym.services.member_portal_service import MemberPortalService
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def portal_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Nav Gym",
            "subdomain": "navgym",
            "business_type_code": "gym",
            "owner": {"username": "nav_admin", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    member_role = Role.objects.get(slug="gym_member")
    User = get_user_model()
    member_user = User.objects.create_user(
        username="nav_member",
        password="pass12345",
        tenant=tenant,
        role=member_role,
    )
    member = Member.active_objects().create(
        tenant=tenant,
        membership_number="MEM-NAV-1",
        full_name="Nav Member",
        email="nav@portal.test",
        phone="+15550111",
        created_by=member_user,
    )
    MemberPortalService.link_user(member=member, user=member_user)
    return {"tenant": tenant, "member": member, "user": member_user}


def _bootstrap(user_login="nav_member", host="navgym.erp.safaritechno.com"):
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": user_login, "password": "pass12345"},
        format="json",
        HTTP_HOST=host,
    )
    assert login.status_code == 200
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/mobile/bootstrap/", HTTP_HOST=host)
    assert response.status_code == 200
    return response.json()["data"]


@pytest.mark.django_db
def test_catalog_includes_gym_member_workspace():
    ids = {w["id"] for w in MobileNavService.catalog()}
    assert "gym_member" in ids
    assert "gym_staff" in ids


@pytest.mark.django_db
def test_bootstrap_mobile_nav_when_gym_enabled(portal_env):
    data = _bootstrap()
    assert "gym" in data["enabled_modules"]
    nav = data["mobile_nav"]
    assert any(w["id"] == "gym_member" for w in nav["workspaces"])
    screen_ids = {s["id"] for s in nav["screens"]}
    assert {"gym_home", "gym_qr", "gym_attendance", "gym_workouts", "gym_classes"} <= screen_ids
    assert data["gym_member"]["member"]["membership_number"] == "MEM-NAV-1"


@pytest.mark.django_db
def test_bootstrap_hides_gym_nav_when_module_disabled(portal_env):
    sync_tenant_modules(
        tenant=portal_env["tenant"],
        enabled_codes=["pos", "inventory", "sales"],
        validate_dependencies=False,
        disable_missing=True,
    )
    data = _bootstrap()
    assert "gym" not in data["enabled_modules"]
    assert data["mobile_nav"]["workspaces"] == []
    assert data["mobile_nav"]["screens"] == []
    assert data["gym_member"] is None

"""STEP 68 — Gym module features: members, classes, attendance."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Permission, Role, UserPermission
from apps.gym.models import Member
from apps.gym.services.member_portal_service import MemberPortalService
from apps.platform.models import Tenant, TenantModule
from apps.platform.services.module_feature_service import ModuleFeatureService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def gym_feat_env(db):
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(
        name="Feat Gym", slug="feat-gym", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Feat Gym Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["gym", "sales"],
        validate_dependencies=False,
    )
    user = get_user_model().objects.create_user(
        username="feat_gym_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    for code in ("gym.view", "gym.manage", "gym.attendance.checkin"):
        perm = Permission.objects.filter(codename=code).first()
        if perm:
            UserPermission.objects.get_or_create(user=user, permission=perm)
    return {"tenant": tenant, "user": user, "branch": branch}


def _client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_sync_seeds_gym_features(gym_feat_env):
    link = TenantModule.active_objects().get(
        tenant=gym_feat_env["tenant"], module__code="gym"
    )
    features = (link.configuration or {}).get("features") or {}
    assert features.get("members") is True
    assert features.get("classes") is True
    assert features.get("attendance") is True
    resolved = ModuleFeatureService.resolve_features("gym", user=gym_feat_env["user"])
    assert resolved == {"members": True, "classes": True, "attendance": True}


@pytest.mark.django_db
def test_disable_classes_blocks_class_api(gym_feat_env):
    ModuleFeatureService.set_features(
        tenant=gym_feat_env["tenant"],
        module_code="gym",
        features={"classes": False},
        user=gym_feat_env["user"],
    )
    client = _client(gym_feat_env["user"])
    response = client.get("/api/v1/gym/classes/")
    assert response.status_code == 403
    body = response.json()
    assert body.get("code") == "MODULE_FEATURE_DISABLED"
    assert body.get("details", {}).get("feature") == "classes"
    assert client.get("/api/v1/gym/members/").status_code == 200
    assert client.get("/api/v1/gym/attendance/").status_code == 200


@pytest.mark.django_db
def test_disable_attendance_blocks_checkin(gym_feat_env):
    ModuleFeatureService.set_features(
        tenant=gym_feat_env["tenant"],
        module_code="gym",
        features={"attendance": False},
        user=gym_feat_env["user"],
    )
    client = _client(gym_feat_env["user"])
    assert client.get("/api/v1/gym/attendance/").status_code == 403
    assert client.post("/api/v1/gym/attendance/check-in/", {}, format="json").status_code == 403
    assert client.get("/api/v1/gym/classes/").status_code == 200


@pytest.mark.django_db
def test_disable_members_blocks_membership_apis(gym_feat_env):
    ModuleFeatureService.set_features(
        tenant=gym_feat_env["tenant"],
        module_code="gym",
        features={"members": False},
        user=gym_feat_env["user"],
    )
    client = _client(gym_feat_env["user"])
    assert client.get("/api/v1/gym/members/").status_code == 403
    assert client.get("/api/v1/gym/plans/").status_code == 403
    assert client.get("/api/v1/gym/subscriptions/").status_code == 403
    assert client.get("/api/v1/gym/trainers/").status_code == 200


@pytest.mark.django_db
def test_gym_summary_includes_features(gym_feat_env):
    client = _client(gym_feat_env["user"])
    response = client.get("/api/v1/gym/summary/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["features"]["members"] is True
    assert data["features"]["classes"] is True
    assert data["features"]["attendance"] is True
    ModuleFeatureService.set_features(
        tenant=gym_feat_env["tenant"],
        module_code="gym",
        features={"attendance": False, "classes": False},
        user=gym_feat_env["user"],
    )
    data2 = client.get("/api/v1/gym/summary/").json()["data"]
    assert data2["features"]["attendance"] is False
    assert data2["features"]["classes"] is False
    assert data2["attendance"]["today_checkins"] == 0
    assert data2["classes"]["upcoming_sessions"] == 0


@pytest.fixture
def gym_member_nav_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Feat Nav Gym",
            "subdomain": "featnavgym",
            "business_type_code": "gym",
            "owner": {"username": "featnav_admin", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    member_role = Role.objects.get(slug="gym_member")
    member_user = get_user_model().objects.create_user(
        username="featnav_member",
        password="pass12345",
        tenant=tenant,
        role=member_role,
    )
    member = Member.active_objects().create(
        tenant=tenant,
        membership_number="MEM-FEAT-1",
        full_name="Feat Nav Member",
        created_by=member_user,
    )
    MemberPortalService.link_user(member=member, user=member_user)
    return {"tenant": tenant, "user": member_user}


def _member_bootstrap(host="featnavgym.erp.safaritechno.com"):
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "featnav_member", "password": "pass12345"},
        format="json",
        HTTP_HOST=host,
    )
    assert login.status_code == 200, login.content
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/mobile/bootstrap/?audience=member", HTTP_HOST=host)
    assert response.status_code == 200
    return response.json()["data"]


@pytest.mark.django_db
def test_member_nav_hides_class_and_attendance_screens(gym_member_nav_env):
    ModuleFeatureService.set_features(
        tenant=gym_member_nav_env["tenant"],
        module_code="gym",
        features={"classes": False, "attendance": False},
        user=gym_member_nav_env["user"],
    )
    data = _member_bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "gym_member" in ids
    screen_ids = {s["id"] for s in data["mobile_nav"]["screens"]}
    assert "gym_home" in screen_ids
    assert "gym_workouts" in screen_ids
    assert "gym_attendance" not in screen_ids
    assert "gym_classes" not in screen_ids


@pytest.mark.django_db
def test_member_nav_hides_workspace_when_members_disabled(gym_member_nav_env):
    ModuleFeatureService.set_features(
        tenant=gym_member_nav_env["tenant"],
        module_code="gym",
        features={"members": False},
        user=gym_member_nav_env["user"],
    )
    data = _member_bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "gym_member" not in ids

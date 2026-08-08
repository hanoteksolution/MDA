"""STEP 28 — gym member mobile portal API + member user link."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.gym.models import Member
from apps.gym.services.member_portal_service import MemberPortalService
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def portal_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Portal Gym",
            "subdomain": "portalgym",
            "business_type_code": "gym",
            "owner": {"username": "gym_admin", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    member_role = Role.objects.get(slug="gym_member")
    User = get_user_model()
    member_user = User.objects.create_user(
        username="member_portal",
        password="pass12345",
        tenant=tenant,
        role=member_role,
    )
    member = Member.active_objects().create(
        tenant=tenant,
        membership_number="MEM-90001",
        full_name="Alex Member",
        email="alex@portal.test",
        phone="+15550001",
        created_by=member_user,
    )
    MemberPortalService.link_user(member=member, user=member_user)
    return {"tenant": tenant, "member": member, "user": member_user}


@pytest.mark.django_db
def test_member_portal_qr(portal_env):
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "member_portal", "password": "pass12345"},
        format="json",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    assert login.status_code == 200
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get(
        "/api/v1/mobile/gym/qr/",
        HTTP_HOST="api.erp.safaritechno.com",
        HTTP_X_TENANT_SLUG="portalgym",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["payload"] == "mem:MEM-90001"
    assert data["member_name"] == "Alex Member"


@pytest.mark.django_db
def test_member_portal_home(portal_env):
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "member_portal", "password": "pass12345"},
        format="json",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get(
        "/api/v1/mobile/gym/home/",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["member"]["membership_number"] == "MEM-90001"
    assert data["is_checked_in"] is False
    assert "upcoming_classes" in data


@pytest.mark.django_db
def test_member_portal_requires_link(portal_env):
    User = get_user_model()
    member_role = Role.objects.get(slug="gym_member")
    orphan = User.objects.create_user(
        username="orphan_member",
        password="pass12345",
        tenant=portal_env["tenant"],
        role=member_role,
    )
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "orphan_member", "password": "pass12345"},
        format="json",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get(
        "/api/v1/mobile/gym/home/",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "MEMBER_NOT_LINKED"


@pytest.mark.django_db
def test_bootstrap_includes_gym_member(portal_env):
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "member_portal", "password": "pass12345"},
        format="json",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    token = login.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get(
        "/api/v1/mobile/bootstrap/",
        HTTP_HOST="portalgym.erp.safaritechno.com",
    )
    assert response.status_code == 200
    gym_member = response.json()["data"]["gym_member"]
    assert gym_member["member"]["full_name"] == "Alex Member"


@pytest.mark.django_db
def test_gym_member_role_bootstrapped(db):
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="gym_member")
    perms = set(
        role.role_permissions.filter(deleted_at__isnull=True)
        .values_list("permission__codename", flat=True)
    )
    assert "gym.member_portal" in perms

"""STEP 08 — module catalog, tenant enablement, and API gating."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.models import Module, TenantModule
from apps.platform.services.module_service import (
    ensure_default_modules,
    module_required_for_path,
    sync_tenant_modules,
    tenant_has_module,
)
from apps.platform.services.platform_service import PlatformService


User = get_user_model()


@pytest.mark.django_db
def test_module_catalog_seeded():
    ensure_default_modules()
    codes = set(Module.objects.values_list("code", flat=True))
    assert {"pos", "inventory", "sales", "purchases", "pharmacy", "gym", "futsal"} <= codes


@pytest.mark.django_db
def test_create_shop_provisions_modules_from_business_type():
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    ensure_default_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="mod_actor",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Futsal Hub",
            "subdomain": "futsalhub",
            "business_type_code": "futsal",
            "owner": {"username": "futsal_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        },
        user=actor,
    )
    enabled = set(
        TenantModule.objects.filter(tenant=tenant, enabled=True).values_list("module__code", flat=True)
    )
    assert "futsal" in enabled
    assert "pos" in enabled
    assert "pharmacy" not in enabled


@pytest.mark.django_db
def test_paid_starter_plan_caps_industry_modules():
    from apps.platform.models import TenantSubscription
    from apps.platform.services.entitlement_service import EntitlementService

    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    ensure_default_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="mod_starter",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Futsal Starter",
            "subdomain": "futsalstarter",
            "business_type_code": "futsal",
            "owner": {"username": "futsal_st", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        },
        user=actor,
    )
    sub = tenant.subscription
    sub.status = TenantSubscription.STATUS_ACTIVE
    sub.save(update_fields=["status", "updated_at"])
    EntitlementService.apply_plan_entitlements(tenant=tenant, user=actor)
    enabled = set(
        TenantModule.objects.filter(tenant=tenant, enabled=True).values_list("module__code", flat=True)
    )
    assert "futsal" not in enabled
    assert "pos" in enabled


@pytest.mark.django_db
def test_trial_starter_keeps_industry_modules():
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    ensure_default_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="mod_trial",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Futsal Trial",
            "subdomain": "futsaltrial",
            "business_type_code": "futsal",
            "owner": {"username": "futsal_tr", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        },
        user=actor,
    )
    enabled = set(
        TenantModule.objects.filter(tenant=tenant, enabled=True).values_list("module__code", flat=True)
    )
    assert "futsal" in enabled
    assert "pos" in enabled


@pytest.mark.django_db
def test_tenant_has_module_respects_enabled_flag():
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="mod_actor2",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Retail One",
            "subdomain": "retailone",
            "business_type_code": "retail",
            "owner": {"username": "retail_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        },
        user=actor,
    )
    assert tenant_has_module("pos", user=owner) is True
    assert tenant_has_module("futsal", user=owner) is False
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pos", "inventory", "sales", "purchases", "futsal"],
        disable_missing=True,
    )
    assert tenant_has_module("futsal", user=owner) is True


@pytest.mark.django_db
def test_path_module_mapping():
    assert module_required_for_path("/api/v1/futsal/courts/") == "futsal"
    assert module_required_for_path("/api/v1/products/") == "inventory"
    assert module_required_for_path("/api/v1/health/") is None


@pytest.mark.django_db
def test_disabled_module_blocks_api():
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    role = Role.objects.get(slug="admin")
    actor = User.objects.create_user(
        username="mod_actor3",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "No Futsal Shop",
            "subdomain": "nofutsal",
            "business_type_code": "retail",
            "owner": {"username": "nofutsal_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        },
        user=actor,
    )
    # Grant futsal permission so only module gate should block.
    from apps.authentication.models import Permission, UserPermission

    perm = Permission.objects.filter(codename="futsal.view").first()
    if perm:
        UserPermission.objects.get_or_create(user=owner, permission=perm)

    client = APIClient()
    token = str(RefreshToken.for_user(owner).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/futsal/summary/")
    assert response.status_code == 403
    body = response.json()
    assert body.get("code") == "MODULE_DISABLED"
    assert body.get("details", {}).get("module") == "futsal"

    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pos", "inventory", "sales", "purchases", "futsal"],
        disable_missing=True,
    )
    response2 = client.get("/api/v1/futsal/summary/")
    assert response2.status_code != 403 or response2.json().get("code") != "MODULE_DISABLED"


@pytest.mark.django_db
def test_platform_modules_api(api_client, db):
    ensure_default_modules()
    user = User.objects.create_user(
        username="plat_mod",
        password="pass12345",
        is_platform_admin=True,
    )
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/platform/modules/")
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["data"]["items"]}
    assert "pos" in codes
    assert "gym" in codes

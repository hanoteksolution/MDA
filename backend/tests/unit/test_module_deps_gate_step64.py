"""STEP 64 — runtime module dependency gate (checklist 9–11)."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Permission, Role, UserPermission
from apps.platform.services.dashboard_widget_service import DashboardWidgetService
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import (
    ensure_default_modules,
    missing_module_dependencies,
    sync_tenant_modules,
    tenant_has_module,
    tenant_module_ready,
    usable_module_codes,
)
from apps.platform.services.platform_service import PlatformService


User = get_user_model()


@pytest.fixture
def pharmacy_orphan_env(db):
    """Pharmacy TenantModule on, inventory/pos off (invalid combo; enable-time would expand)."""
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    ensure_default_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="dep_gate_actor",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Orphan Pharmacy",
            "subdomain": "orphpharm",
            "business_type_code": "retail",
            "owner": {"username": "orph_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        },
        user=actor,
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pharmacy"],
        disable_missing=True,
        validate_dependencies=False,
    )
    perm = Permission.objects.filter(codename="pharmacy.view").first()
    if perm:
        UserPermission.objects.get_or_create(user=owner, permission=perm)
    return {"tenant": tenant, "owner": owner}


@pytest.mark.django_db
def test_missing_deps_for_pharmacy_without_inventory(pharmacy_orphan_env):
    tenant = pharmacy_orphan_env["tenant"]
    owner = pharmacy_orphan_env["owner"]
    assert tenant_has_module("pharmacy", user=owner, tenant=tenant) is True
    missing = missing_module_dependencies("pharmacy", user=owner, tenant=tenant)
    assert "inventory" in missing
    assert "pos" in missing
    assert tenant_module_ready("pharmacy", user=owner, tenant=tenant) is False
    usable = usable_module_codes(user=owner, tenant=tenant)
    assert "pharmacy" not in usable


@pytest.mark.django_db
def test_pharmacy_api_blocked_when_deps_disabled(pharmacy_orphan_env):
    owner = pharmacy_orphan_env["owner"]
    client = APIClient()
    token = str(RefreshToken.for_user(owner).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/pharmacy/summary/")
    assert response.status_code == 403
    body = response.json()
    assert body.get("code") == "MODULE_DEPENDENCY"
    assert body.get("details", {}).get("module") == "pharmacy"
    missing = body.get("details", {}).get("missing") or []
    assert "inventory" in missing
    assert "pos" in missing


@pytest.mark.django_db
def test_pharmacy_api_allowed_when_deps_enabled(pharmacy_orphan_env):
    tenant = pharmacy_orphan_env["tenant"]
    owner = pharmacy_orphan_env["owner"]
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pharmacy", "inventory", "pos"],
        disable_missing=True,
        validate_dependencies=True,
    )
    assert tenant_module_ready("pharmacy", user=owner, tenant=tenant) is True
    client = APIClient()
    token = str(RefreshToken.for_user(owner).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/pharmacy/summary/")
    assert response.status_code != 403 or response.json().get("code") not in {
        "MODULE_DISABLED",
        "MODULE_DEPENDENCY",
    }


@pytest.mark.django_db
def test_me_omits_unready_pharmacy(pharmacy_orphan_env):
    owner = pharmacy_orphan_env["owner"]
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/",
        {"username": "orph_owner", "password": "pass12345"},
        format="json",
        HTTP_HOST="orphpharm.erp.safaritechno.com",
    )
    assert login.status_code == 200, login.content
    modules = login.json()["data"]["user"]["enabled_modules"]
    assert "pharmacy" not in modules


@pytest.mark.django_db
def test_dashboard_hides_pharmacy_without_deps(pharmacy_orphan_env):
    widgets = DashboardWidgetService.list_for_actor(
        user=pharmacy_orphan_env["owner"],
        tenant=pharmacy_orphan_env["tenant"],
        is_super_admin=False,
    )
    ids = {w["id"] for w in widgets}
    assert "pharmacy_summary" not in ids


@pytest.mark.django_db
def test_mobile_nav_hides_pharmacy_without_deps(pharmacy_orphan_env):
    nav = MobileNavService.list_for_actor(
        user=pharmacy_orphan_env["owner"],
        tenant=pharmacy_orphan_env["tenant"],
        audience="staff",
    )
    assert "pharmacy" not in nav["enabled_modules"]
    assert "pharmacy_staff" not in {w["id"] for w in nav["workspaces"]}


@pytest.mark.django_db
def test_housing_unready_without_property_core(db):
    ensure_default_modules()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="housing_dep_actor",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Orphan Housing",
            "subdomain": "orphouse",
            "business_type_code": "retail",
            "owner": {"username": "orph_house", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        },
        user=actor,
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["housing_rental"],
        disable_missing=True,
        validate_dependencies=False,
    )
    assert tenant_has_module("housing_rental", user=owner, tenant=tenant) is True
    assert "property_management" in missing_module_dependencies(
        "housing_rental", user=owner, tenant=tenant
    )
    assert tenant_module_ready("housing_rental", user=owner, tenant=tenant) is False

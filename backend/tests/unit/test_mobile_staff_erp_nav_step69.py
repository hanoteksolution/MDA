"""STEP 69 — Staff mobile ERP workspaces (core modules + business units)."""

import pytest
from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


CORE_STAFF_IDS = {
    "dashboard_staff",
    "pos_staff",
    "sales_staff",
    "inventory_staff",
    "purchases_staff",
    "customers_staff",
    "suppliers_staff",
    "finance_staff",
    "business_units_staff",
    "reports_staff",
    "settings_staff",
}

CORE_ROUTES = {
    "DashboardWorkspace",
    "PosWorkspace",
    "SalesWorkspace",
    "InventoryWorkspace",
    "PurchasesWorkspace",
    "CustomersWorkspace",
    "SuppliersWorkspace",
    "FinanceWorkspace",
    "BusinessUnitsWorkspace",
    "ReportsWorkspace",
    "SettingsWorkspace",
}


@pytest.fixture
def erp_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "ERP Nav Co",
            "subdomain": "erpnav",
            "business_type_code": "retail",
            "owner": {"username": "erp_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "business",
        }
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pos", "inventory", "sales", "purchases"],
        validate_dependencies=False,
    )
    return {"tenant": tenant, "user": owner}


def _bootstrap(username="erp_owner", host="erpnav.erp.safaritechno.com", audience="staff"):
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
def test_catalog_includes_core_erp_and_business_units():
    ids = {w["id"] for w in MobileNavService.catalog(audience="staff")}
    assert CORE_STAFF_IDS <= ids
    assert "gym_member" not in ids
    bu = next(w for w in MobileNavService.catalog(audience="staff") if w["id"] == "business_units_staff")
    assert bu["group"] == "finance"
    assert any(s["route"] == "BusinessUnitsWorkspace" for s in bu["screens"])


@pytest.mark.django_db
def test_staff_bootstrap_core_erp_workspaces(erp_env):
    data = _bootstrap()
    nav = data["mobile_nav"]
    ids = {w["id"] for w in nav["workspaces"]}
    assert "staff_hub" in ids
    assert CORE_STAFF_IDS <= ids
    assert "gym_staff" not in ids
    routes = {s["route"] for s in nav["screens"]}
    assert CORE_ROUTES <= routes
    groups = {w["id"]: w.get("group") for w in nav["workspaces"]}
    assert groups["pos_staff"] == "core"
    assert groups["business_units_staff"] == "finance"


@pytest.mark.django_db
def test_pos_hidden_when_module_disabled(erp_env):
    sync_tenant_modules(
        tenant=erp_env["tenant"],
        enabled_codes=["sales"],
        validate_dependencies=False,
        disable_missing=True,
    )
    data = _bootstrap()
    ids = {w["id"] for w in data["mobile_nav"]["workspaces"]}
    assert "sales_staff" in ids
    assert "customers_staff" in ids
    assert "pos_staff" not in ids
    assert "inventory_staff" not in ids
    assert "dashboard_staff" in ids
    assert "finance_staff" in ids
    assert "business_units_staff" in ids

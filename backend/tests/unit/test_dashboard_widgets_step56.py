"""STEP 56 — Dashboard widget registry (PHASE 08) gated by TenantModule."""

import pytest

from django.contrib.auth import get_user_model

from apps.authentication.models import Permission, Role, RolePermission
from apps.platform.models import Tenant
from apps.platform.services.dashboard_widget_service import (
    DASHBOARD_WIDGET_CATALOG,
    DashboardWidgetService,
)
from apps.platform.services.module_service import ensure_default_modules, sync_tenant_modules
from apps.settings_app.models import Branch, Company


@pytest.fixture
def widget_env(db):
    ensure_default_modules()
    tenant = Tenant.objects.create(
        name="Dash Co", slug="dash-co", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Dash Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    role = Role.objects.create(name="Dash Manager", slug="dash-manager")
    for code in (
        "dashboard.view",
        "finance.view",
        "gym.view",
        "pharmacy.view",
        "hotel.view",
    ):
        perm, _ = Permission.objects.get_or_create(
            codename=code,
            defaults={"name": code, "module": code.split(".")[0]},
        )
        RolePermission.objects.get_or_create(role=role, permission=perm)

    user = get_user_model().objects.create_user(
        username="dash_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=role,
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["gym", "pharmacy", "pos", "inventory"],
        validate_dependencies=False,
    )
    return {"tenant": tenant, "user": user, "role": role}


@pytest.mark.django_db
def test_catalog_has_vertical_widgets():
    ids = {w["id"] for w in DashboardWidgetService.catalog()}
    assert "finance_ledger_kpis" in ids
    assert "gym_summary" in ids
    assert "pharmacy_summary" in ids
    assert "hotel_summary" in ids
    assert len(DASHBOARD_WIDGET_CATALOG) >= 8


@pytest.mark.django_db
def test_list_for_actor_filters_by_enabled_modules(widget_env):
    widgets = DashboardWidgetService.list_for_actor(
        user=widget_env["user"],
        tenant=widget_env["tenant"],
        is_super_admin=False,
    )
    ids = {w["id"] for w in widgets}
    # Finance is permission-gated (no TenantModule); gym/pharmacy from modules.
    assert ids == {"finance_ledger_kpis", "gym_summary", "pharmacy_summary"}
    assert "hotel_summary" not in ids
    assert "restaurant_summary" not in ids


@pytest.mark.django_db
def test_list_for_actor_respects_permissions(widget_env):
    gym_perm = Permission.objects.get(codename="gym.view")
    RolePermission.objects.filter(role=widget_env["role"], permission=gym_perm).delete()

    widgets = DashboardWidgetService.list_for_actor(
        user=widget_env["user"],
        tenant=widget_env["tenant"],
        is_super_admin=False,
    )
    ids = {w["id"] for w in widgets}
    assert "gym_summary" not in ids
    assert "pharmacy_summary" in ids
    assert "finance_ledger_kpis" in ids


@pytest.mark.django_db
def test_finance_widget_requires_finance_view(widget_env):
    fin_perm = Permission.objects.get(codename="finance.view")
    RolePermission.objects.filter(role=widget_env["role"], permission=fin_perm).delete()

    widgets = DashboardWidgetService.list_for_actor(
        user=widget_env["user"],
        tenant=widget_env["tenant"],
        is_super_admin=False,
    )
    ids = {w["id"] for w in widgets}
    assert "finance_ledger_kpis" not in ids
    assert "gym_summary" in ids


@pytest.mark.django_db
def test_super_admin_sees_full_catalog(widget_env):
    widgets = DashboardWidgetService.list_for_actor(
        user=widget_env["user"],
        tenant=widget_env["tenant"],
        is_super_admin=True,
    )
    assert len(widgets) == len(DASHBOARD_WIDGET_CATALOG)


@pytest.mark.django_db
def test_business_type_does_not_appear_in_widget_payload(widget_env):
    for w in DashboardWidgetService.list_for_actor(
        user=widget_env["user"],
        tenant=widget_env["tenant"],
    ):
        assert "business_type" not in w
        assert "module" in w
        assert w["route"].startswith("/")
        if w["id"] == "finance_ledger_kpis":
            assert w["module"] == ""
            assert w["permission"] == "finance.view"
        else:
            assert w["module"]

"""Subscription locks apply to shop users, never elevated administrators.

Also verifies that subscription state and Platform Administration authorization
are separate security checks: an active (or expired) tenant subscription must
never grant access to platform-level provider/admin APIs, and a Superadmin must
retain Platform access with no tenant subscription at all.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from api.v1.sync.views import SubscriptionStatusView
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role, User
from apps.platform.models import SubscriptionPlan, Tenant, TenantSubscription
from apps.platform.services.entitlement_service import EntitlementService
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch, Company
from tests.helpers.shop_factory import auth_client_as


@pytest.fixture(params=["super_admin", "platform_admin", "superuser", "admin"])
def actor(request):
    role = Role(slug=request.param)
    return User(username="subscription-test", role=role, is_superuser=request.param == "superuser")


def test_subscription_status_exempts_only_elevated_users(actor):
    request = APIRequestFactory().get("/api/v1/sync/subscription-status/")
    force_authenticate(request, user=actor)
    locked = {"has_subscription": True, "locked": True, "show_alert": True}
    with patch("api.v1.sync.views.ShopSyncService.get_subscription_status", return_value=locked) as status:
        response = SubscriptionStatusView.as_view()(request)
    data = response.data["data"]
    assert data["locked"] is (not actor.is_elevated_admin)
    if actor.is_elevated_admin:
        assert data["has_subscription"] is False
        assert data["show_alert"] is False
        assert data["is_usable"] is True
        status.assert_not_called()
    else:
        status.assert_called_once()


@pytest.mark.parametrize("jwt", [False, True])
def test_write_gate_exempts_elevated_users_after_authentication(actor, jwt):
    request = RequestFactory().post("/api/v1/pos/checkout/")
    request.user = AnonymousUser() if jwt else actor
    with (
        patch.object(EntitlementService, "_authenticate_jwt", return_value=actor),
        patch("apps.platform.services.entitlement_service.resolve_acting_tenant", return_value=object()),
        patch.object(EntitlementService, "evaluate", return_value={"can_write": False}),
    ):
        error = EntitlementService.write_blocked_for_request(request)
    assert (error is None) is actor.is_elevated_admin
    if error:
        assert error.code == "SUBSCRIPTION_EXPIRED"


@pytest.fixture
def platform_env(db):
    """A tenant admin with a real (active or expired) subscription, plus a
    tenant-less Superadmin. Both authenticate through the real JWT flow so the
    checks under test run through the actual middleware/permission stack."""
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_plans()

    tenant = Tenant.objects.create(name="Provider Co", slug="provider-co", status=Tenant.STATUS_ACTIVE)
    from apps.platform.services.module_service import sync_tenant_modules

    sync_tenant_modules(tenant=tenant, enabled_codes=["pos", "inventory", "sales", "purchases"])
    company = Company.objects.create(name="Provider Co", tenant=tenant)
    branch = Branch.objects.create(company=company, tenant=tenant, name="Main", code="MAIN", is_default=True)
    plan = SubscriptionPlan.objects.get(code="starter")
    admin_role = Role.objects.get(slug="admin")
    tenant_admin = User.objects.create_user(
        username="provider_admin", password="pass12345", tenant=tenant, branch=branch, role=admin_role,
    )

    super_role = Role.objects.get(slug="super_admin")
    superadmin = User.objects.create_user(
        username="platform_superadmin", password="pass12345", role=super_role,
        is_platform_admin=False, is_superuser=False,
    )
    assert superadmin.apply_elevated_flags() is True
    superadmin.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])

    return {
        "tenant": tenant, "tenant_admin": tenant_admin, "superadmin": superadmin, "plan": plan,
    }


def _set_subscription(tenant, plan, *, active: bool):
    TenantSubscription.objects.filter(tenant=tenant).delete()
    today = timezone.localdate()
    return TenantSubscription.objects.create(
        reference_code=f"SUB-{tenant.slug}-{'ok' if active else 'exp'}",
        tenant=tenant,
        plan=plan,
        status=TenantSubscription.STATUS_ACTIVE if active else TenantSubscription.STATUS_EXPIRED,
        started_at=today - timedelta(days=60),
        expires_at=(today + timedelta(days=30)) if active else (today - timedelta(days=10)),
        grace_period_days=0,
    )


@pytest.mark.django_db
def test_superadmin_no_subscription_has_platform_access(api_client, platform_env):
    """Superadmin has no tenant, hence no subscription at all, yet the
    platform-admin API — the real check for Platform Administration — succeeds."""
    assert platform_env["superadmin"].tenant_id is None
    assert not TenantSubscription.objects.filter(tenant__isnull=True).exists()
    client = auth_client_as(api_client, platform_env["superadmin"])
    response = client.get("/api/v1/platform/tenants/")
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("active", [True, False])
def test_tenant_admin_never_reaches_platform_api(api_client, platform_env, active):
    """An active subscription must never substitute for platform authorization,
    and an expired one must not produce a different (non-403) failure mode either."""
    _set_subscription(platform_env["tenant"], platform_env["plan"], active=active)
    client = auth_client_as(api_client, platform_env["tenant_admin"])
    response = client.get("/api/v1/platform/tenants/")
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("active", [True, False])
def test_tenant_admin_never_reaches_platform_billing(api_client, platform_env, active):
    """Platform billing/reconciliation (cross-tenant subscription management) is
    gated on subscriptions.manage / is_platform_admin — never on the caller's own
    tenant subscription being active. Regular tenant admins hold neither."""
    sub = _set_subscription(platform_env["tenant"], platform_env["plan"], active=active)
    client = auth_client_as(api_client, platform_env["tenant_admin"])
    response = client.put(
        f"/api/v1/platform/tenants/{platform_env['tenant'].id}/subscription/",
        data={"plan_id": str(sub.plan_id)},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_regular_subscription_enforcement_still_works(api_client, platform_env):
    """Control case: a non-elevated tenant admin with an expired subscription is
    still write-blocked on ordinary tenant-scoped write APIs (unaffected by the
    platform-authorization checks above)."""
    _set_subscription(platform_env["tenant"], platform_env["plan"], active=False)
    client = auth_client_as(api_client, platform_env["tenant_admin"])
    response = client.post("/api/v1/pos/checkout/", data={"items": []}, format="json")
    assert response.status_code == 403
    assert response.json().get("code") == "SUBSCRIPTION_EXPIRED"

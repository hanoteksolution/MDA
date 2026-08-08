"""STEP 24 — subscription entitlements, grace middleware, plan limits."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.models import PlanModule, SubscriptionPlan, Tenant, TenantSubscription
from apps.platform.services.entitlement_service import EntitlementService
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context

User = get_user_model()


@pytest.fixture
def ent_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_plans()
    EntitlementService.ensure_default_plan_modules()
    tenant = Tenant.objects.create(name="Ent Co", slug="ent-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Ent Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    plan = SubscriptionPlan.objects.get(code="starter")
    sub = TenantSubscription.objects.create(
        reference_code="ENT-001",
        tenant=tenant,
        plan=plan,
        status=TenantSubscription.STATUS_ACTIVE,
        started_at=timezone.localdate() - timedelta(days=60),
        expires_at=timezone.localdate() - timedelta(days=10),
        grace_period_days=0,
    )
    from apps.platform.services.module_service import sync_tenant_modules

    sync_tenant_modules(tenant=tenant, enabled_codes=["pos", "inventory", "sales", "purchases"])
    admin_role = Role.objects.get(slug="admin")
    user = User.objects.create_user(
        username="ent_admin",
        password="pass-123",
        tenant=tenant,
        branch=branch,
        role=admin_role,
    )
    return {"tenant": tenant, "user": user, "sub": sub, "plan": plan, "company": company}


def _auth_client(api_client, user):
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.mark.django_db
def test_plan_modules_seeded():
    EntitlementService.ensure_default_plan_modules()
    starter = SubscriptionPlan.objects.get(code="starter")
    codes = EntitlementService.plan_module_codes(plan=starter)
    assert "pos" in codes
    assert "gym" not in codes


@pytest.mark.django_db
def test_evaluate_expired_blocks_write(ent_env):
    ev = EntitlementService.evaluate(tenant=ent_env["tenant"])
    assert ev["can_read"] is True
    assert ev["can_write"] is False
    assert ev["phase"] == "expired"


@pytest.mark.django_db
def test_expired_tenant_blocked_from_pos_write(api_client, ent_env):
    user = ent_env["user"]
    _auth_client(api_client, user)
    resp = api_client.post(
        "/api/v1/pos/checkout/",
        data={"items": []},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "SUBSCRIPTION_EXPIRED"


@pytest.mark.django_db
def test_expired_tenant_can_still_read(api_client, ent_env):
    user = ent_env["user"]
    _auth_client(api_client, user)
    resp = api_client.get("/api/v1/dashboard/kpis/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_data_retained_after_expiry(ent_env):
    tenant = ent_env["tenant"]
    branch_count = Branch.active_objects().filter(tenant=tenant).count()
    EntitlementService.evaluate(tenant=tenant)
    assert Tenant.objects.filter(pk=tenant.pk).exists()
    assert Branch.active_objects().filter(tenant=tenant).count() == branch_count


@pytest.mark.django_db
def test_user_limit_enforced(ent_env):
    tenant = ent_env["tenant"]
    sub = ent_env["sub"]
    sub.expires_at = timezone.localdate() + timedelta(days=30)
    sub.save(update_fields=["expires_at", "updated_at"])
    ent_env["plan"].max_users = 1
    ent_env["plan"].save(update_fields=["max_users", "updated_at"])
    with pytest.raises(ValueError, match="User limit"):
        from apps.authentication.services.auth_service import UserService

        UserService.create_user(
            data={
                "username": "extra_user",
                "password": "pass-123",
                "tenant": tenant,
            },
            created_by=ent_env["user"],
        )


@pytest.mark.django_db
def test_entitlements_api(api_client, ent_env):
    _auth_client(api_client, ent_env["user"])
    resp = api_client.get("/api/v1/platform/entitlements/")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert data["has_subscription"] is True
    assert data["can_write"] is False


@pytest.mark.django_db
def test_apply_plan_entitlements_caps_gym_for_paid_starter(db):
    """Paid (non-trial) starter still caps industry modules."""
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    EntitlementService.ensure_default_plan_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="plan_actor",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Gym Shop",
            "subdomain": "gymshop",
            "business_type_code": "gym",
            "owner": {"username": "gym_owner", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        },
        user=actor,
    )
    sub = tenant.subscription
    sub.status = TenantSubscription.STATUS_ACTIVE
    sub.save(update_fields=["status", "updated_at"])
    EntitlementService.apply_plan_entitlements(tenant=tenant, user=actor)
    with tenant_context(tenant, enforce=True):
        from apps.platform.services.module_service import enabled_module_codes

        codes = enabled_module_codes(tenant=tenant)
    assert "gym" not in codes
    assert "pos" in codes


@pytest.mark.django_db
def test_trial_starter_keeps_gym_modules(db):
    """Trial subscriptions keep business-type / preset modules (PHASE 12)."""
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    EntitlementService.ensure_default_plan_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    actor = User.objects.create_user(
        username="plan_actor_trial",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Gym Trial",
            "subdomain": "gymtrial",
            "business_type_code": "gym",
            "owner": {"username": "gym_trial", "password": "pass12345", "role_slug": "admin"},
            "plan_code": "starter",
        },
        user=actor,
    )
    assert tenant.subscription.status == TenantSubscription.STATUS_TRIAL
    with tenant_context(tenant, enforce=True):
        from apps.platform.services.module_service import enabled_module_codes

        codes = enabled_module_codes(tenant=tenant)
    assert "gym" in codes
    assert "pos" in codes
    assert EntitlementService.plan_includes_module(tenant=tenant, module_code="gym") is True

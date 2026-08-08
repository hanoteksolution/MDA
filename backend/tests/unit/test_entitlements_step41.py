"""PHASE 12 — trial/demo entitlement polish."""

import pytest
from django.contrib.auth import get_user_model

from apps.authentication.models import Role
from apps.platform.models import PlanModule, SubscriptionPlan, TenantSubscription
from apps.platform.services.entitlement_service import EntitlementService
from apps.platform.services.module_service import enabled_module_codes, ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from core.tenancy import tenant_context

User = get_user_model()


@pytest.fixture
def platform_actor(db):
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    ensure_default_modules()
    EntitlementService.ensure_default_plan_modules()
    role, _ = Role.objects.get_or_create(slug="admin", defaults={"name": "Admin", "is_system": True})
    return User.objects.create_user(
        username="ent12_actor",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )


@pytest.mark.django_db
def test_plan_module_seed_restores_included(platform_actor):
    starter = SubscriptionPlan.objects.get(code="starter")
    link = PlanModule.active_objects().filter(plan=starter, module__code="pos").first()
    assert link is not None
    link.included = False
    link.save(update_fields=["included", "updated_at"])
    EntitlementService.ensure_default_plan_modules()
    link.refresh_from_db()
    assert link.included is True


@pytest.mark.django_db
def test_evaluate_includes_enabled_modules(platform_actor):
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Eval Gym",
            "subdomain": "evalgym",
            "business_type_code": "gym",
            "plan_code": "starter",
            "owner": {"username": "eval_gym", "password": "pass12345", "role_slug": "admin"},
        },
        user=platform_actor,
    )
    ev = EntitlementService.evaluate(tenant=tenant)
    assert ev["trial_or_demo"] is True
    assert "gym" in ev["enabled_modules"]
    assert "gym" not in ev["modules"]  # starter catalog still retail-core


@pytest.mark.django_db
def test_demo_flag_keeps_modules_after_paid_cap_would_strip(platform_actor):
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "Demo Flag Gym",
            "subdomain": "demoflaggym",
            "business_type_code": "gym",
            "plan_code": "starter",
            "owner": {"username": "demo_flag", "password": "pass12345", "role_slug": "admin"},
        },
        user=platform_actor,
    )
    tenant.is_demo = True
    tenant.save(update_fields=["is_demo", "updated_at"])
    sub = tenant.subscription
    sub.status = TenantSubscription.STATUS_ACTIVE
    sub.save(update_fields=["status", "updated_at"])
    # Demo bypasses paid starter cap
    EntitlementService.apply_plan_entitlements(tenant=tenant, user=platform_actor)
    with tenant_context(tenant, enforce=True):
        assert "gym" in enabled_module_codes(tenant=tenant)

"""SaaS plan entitlements: modules, limits, subscription grace (STEP 24 / PHASE 12)."""

from __future__ import annotations

from django.utils import timezone

from apps.platform.models import PlanModule, SubscriptionPlan, Tenant, TenantSubscription
from apps.platform.services.module_service import (
    default_module_codes_for_tenant,
    enabled_module_codes,
    ensure_default_modules,
    sync_tenant_modules,
    MODULE_SEEDS,
)
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch
from core.tenancy import is_platform_unscoped_actor, resolve_acting_tenant

# Plan → default module codes (seeded into PlanModule rows).
# Paid starter stays retail-core; industry verticals require business/enterprise
# (trial/demo use business-type / preset defaults — see apply_plan_entitlements).
PLAN_MODULE_DEFAULTS: dict[str, list[str]] = {
    "starter": ["pos", "inventory", "sales", "purchases"],
    "business": [
        "pos",
        "inventory",
        "sales",
        "purchases",
        "pharmacy",
        "gym",
        "futsal",
        "restaurant",
        "hotel",
        "property_management",
        "housing_rental",
        "office_rental",
    ],
    "enterprise": [
        "pos",
        "inventory",
        "sales",
        "purchases",
        "pharmacy",
        "gym",
        "futsal",
        "restaurant",
        "hotel",
        "property_management",
        "housing_rental",
        "office_rental",
    ],
}

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

WRITE_EXEMPT_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/health/",
    "/api/v1/sync/",
    "/api/v1/setup/",
    "/api/v1/onboarding/",
    "/api/v1/platform/subscriptions/",
    "/api/v1/platform/payments/",
    "/api/v1/notifications/",
    "/admin/",
)


class EntitlementError(Exception):
    def __init__(self, message: str, *, code: str = "ENTITLEMENT_DENIED"):
        super().__init__(message)
        self.code = code
        self.message = message


class EntitlementService:
    @staticmethod
    def ensure_default_plan_modules() -> None:
        """Upsert PlanModule rows from PLAN_MODULE_DEFAULTS (idempotent sync)."""
        ensure_default_modules()
        PlatformService.ensure_default_plans()
        all_codes = [code for code, *_ in MODULE_SEEDS]
        # Enterprise always tracks the full module catalog
        PLAN_MODULE_DEFAULTS["enterprise"] = list(all_codes)

        from apps.platform.models import Module

        for plan_code, module_codes in PLAN_MODULE_DEFAULTS.items():
            plan = SubscriptionPlan.objects.filter(code=plan_code, deleted_at__isnull=True).first()
            if not plan:
                continue
            modules = {
                m.code: m
                for m in Module.active_objects().filter(code__in=module_codes)
            }
            for code in module_codes:
                module = modules.get(code)
                if not module:
                    continue
                link, created = PlanModule.objects.get_or_create(
                    plan=plan,
                    module=module,
                    defaults={"included": True},
                )
                if not created and (not link.included or link.deleted_at is not None):
                    link.included = True
                    link.deleted_at = None
                    link.deleted_by = None
                    link.save(
                        update_fields=["included", "deleted_at", "deleted_by", "updated_at"]
                    )

    @staticmethod
    def get_subscription(tenant: Tenant | None) -> TenantSubscription | None:
        if tenant is None:
            return None
        sub = getattr(tenant, "subscription", None)
        if sub is not None:
            return sub
        return (
            TenantSubscription.active_objects()
            .filter(tenant=tenant)
            .select_related("plan")
            .first()
        )

    @staticmethod
    def is_trial_or_demo(
        *, tenant: Tenant | None, sub: TenantSubscription | None = None
    ) -> bool:
        """Trial and SaaS demos use business/preset modules, not paid plan caps."""
        if tenant is not None and getattr(tenant, "is_demo", False):
            return True
        if sub is None:
            sub = EntitlementService.get_subscription(tenant)
        if sub is None:
            return False
        return sub.status == TenantSubscription.STATUS_TRIAL

    @staticmethod
    def plan_module_codes(*, plan: SubscriptionPlan) -> set[str]:
        EntitlementService.ensure_default_plan_modules()
        return set(
            PlanModule.active_objects()
            .filter(plan=plan, included=True, module__is_active=True)
            .values_list("module__code", flat=True)
        )

    @staticmethod
    def plan_includes_module(*, tenant: Tenant | None, module_code: str) -> bool:
        sub = EntitlementService.get_subscription(tenant)
        if sub is None:
            return True
        # Trial/demo: TenantModule is the gate; plan catalog is a paid ceiling only.
        if EntitlementService.is_trial_or_demo(tenant=tenant, sub=sub):
            return True
        return module_code in EntitlementService.plan_module_codes(plan=sub.plan)

    @staticmethod
    def apply_plan_entitlements(*, tenant: Tenant, user=None) -> list[str]:
        """Sync TenantModule from business/preset defaults, capped by paid plan.

        Trial and demo tenants keep full business-type / preset modules so
        onboarding and demos are not stripped by a starter plan catalog.
        Paid (non-trial) subscriptions apply business ∩ plan inclusions.
        """
        EntitlementService.ensure_default_plan_modules()
        sub = EntitlementService.get_subscription(tenant)
        business_codes = default_module_codes_for_tenant(tenant)
        if sub is None or EntitlementService.is_trial_or_demo(tenant=tenant, sub=sub):
            enabled = business_codes
        else:
            plan_codes = EntitlementService.plan_module_codes(plan=sub.plan)
            enabled = [c for c in business_codes if c in plan_codes]
        sync_tenant_modules(
            tenant=tenant,
            enabled_codes=enabled,
            user=user,
            disable_missing=True,
        )
        return enabled

    @staticmethod
    def evaluate(*, tenant: Tenant | None) -> dict:
        sub = EntitlementService.get_subscription(tenant)
        enabled = sorted(enabled_module_codes(tenant=tenant)) if tenant else []
        if sub is None:
            return {
                "has_subscription": False,
                "phase": "none",
                "can_read": True,
                "can_write": True,
                "plan_code": None,
                "plan_name": None,
                "max_users": None,
                "max_branches": None,
                "modules": [],
                "enabled_modules": enabled,
                "trial_or_demo": False,
                "users_used": 0,
                "branches_used": 0,
                "days_until_expiry": None,
                "grace_days_remaining": None,
                "is_usable": True,
            }

        today = timezone.localdate()
        days_left = sub.days_until_expiry
        grace_remaining = None
        in_grace = False
        if sub.expires_at and days_left is not None and days_left < 0:
            grace_remaining = max(sub.grace_period_days - (today - sub.expires_at).days, 0)
            in_grace = grace_remaining > 0

        can_write = sub.is_usable
        if sub.status == TenantSubscription.STATUS_SUSPENDED:
            phase = "suspended"
        elif not can_write:
            phase = "expired"
        elif in_grace:
            phase = "grace"
        elif days_left is not None and 0 <= days_left <= sub.warning_days:
            phase = "warning"
        else:
            phase = "active"

        users_used = EntitlementService.count_users(tenant) if tenant else 0
        branches_used = EntitlementService.count_branches(tenant) if tenant else 0
        plan = sub.plan
        trial_or_demo = EntitlementService.is_trial_or_demo(tenant=tenant, sub=sub)

        return {
            "has_subscription": True,
            "phase": phase,
            "can_read": True,
            "can_write": can_write,
            "plan_code": plan.code,
            "plan_name": plan.name,
            "max_users": plan.max_users,
            "max_branches": plan.max_branches,
            "modules": sorted(EntitlementService.plan_module_codes(plan=plan)),
            "enabled_modules": enabled,
            "trial_or_demo": trial_or_demo,
            "users_used": users_used,
            "branches_used": branches_used,
            "days_until_expiry": days_left,
            "grace_days_remaining": grace_remaining,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "status": sub.status,
            "is_usable": sub.is_usable,
        }

    @staticmethod
    def count_users(tenant: Tenant) -> int:
        return PlatformService.list_tenant_users(tenant).count()

    @staticmethod
    def count_branches(tenant: Tenant) -> int:
        return Branch.active_objects().filter(tenant=tenant).count()

    @staticmethod
    def assert_can_write(*, tenant: Tenant | None, user=None) -> None:
        if user is not None and is_platform_unscoped_actor(user):
            return
        ev = EntitlementService.evaluate(tenant=tenant)
        if not ev["can_write"]:
            raise EntitlementError(
                "Subscription expired. Renew to continue making changes.",
                code="SUBSCRIPTION_EXPIRED",
            )

    @staticmethod
    def assert_can_add_user(*, tenant: Tenant | None, user=None) -> None:
        EntitlementService.assert_can_write(tenant=tenant, user=user)
        if tenant is None:
            return
        sub = EntitlementService.get_subscription(tenant)
        if sub is None:
            return
        used = EntitlementService.count_users(tenant)
        if used >= sub.plan.max_users:
            raise EntitlementError(
                f"User limit reached ({sub.plan.max_users}). Upgrade your plan to add more users.",
                code="PLAN_LIMIT_USERS",
            )

    @staticmethod
    def assert_can_add_branch(*, tenant: Tenant | None, user=None) -> None:
        EntitlementService.assert_can_write(tenant=tenant, user=user)
        if tenant is None:
            return
        sub = EntitlementService.get_subscription(tenant)
        if sub is None:
            return
        used = EntitlementService.count_branches(tenant)
        if used >= sub.plan.max_branches:
            raise EntitlementError(
                f"Branch limit reached ({sub.plan.max_branches}). Upgrade your plan to add more branches.",
                code="PLAN_LIMIT_BRANCHES",
            )

    @staticmethod
    def write_blocked_for_request(request) -> EntitlementError | None:
        method = (request.method or "GET").upper()
        if method in READ_METHODS:
            return None
        path = request.path or ""
        if not path.startswith("/api/v1/"):
            return None
        if any(path.startswith(prefix) for prefix in WRITE_EXEMPT_PREFIXES):
            return None

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            if is_platform_unscoped_actor(user):
                return None
        else:
            user = EntitlementService._authenticate_jwt(request)

        tenant = resolve_acting_tenant(request=request, user=user)
        if tenant is None:
            return None

        ev = EntitlementService.evaluate(tenant=tenant)
        if ev["can_write"]:
            return None
        return EntitlementError(
            "Subscription expired. Renew to continue making changes. Your data is retained.",
            code="SUBSCRIPTION_EXPIRED",
        )

    @staticmethod
    def _authenticate_jwt(request):
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication

            result = JWTAuthentication().authenticate(request)
            if result is None:
                return None
            return result[0]
        except Exception:
            return None

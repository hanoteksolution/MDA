"""Self-serve tenant onboarding (STEP 25).

Wizard: business → type → subdomain → plan → provision (owner + first branch).
"""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.db import transaction

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.platform.models import SubscriptionPlan, Tenant
from apps.platform.services.domain_utils import (
    get_tenant_base_domain,
    validate_tenant_slug,
)
from apps.platform.services.entitlement_service import EntitlementService
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch


class OnboardingError(Exception):
    def __init__(self, message: str, *, code: str = "ONBOARDING_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class OnboardingService:
    @staticmethod
    def catalog() -> dict:
        PlatformService.ensure_default_business_types()
        PlatformService.ensure_default_plans()
        EntitlementService.ensure_default_plan_modules()
        from apps.platform.services.business_preset_service import BusinessPresetService

        types = [
            PlatformService.business_type_payload(bt)
            for bt in PlatformService.list_business_types(active_only=True)
        ]
        presets = [
            BusinessPresetService.serialize(p)
            for p in BusinessPresetService.list_presets()
        ]
        plans = [
            PlatformService.plan_payload(p)
            for p in SubscriptionPlan.objects.filter(is_active=True, deleted_at__isnull=True).order_by(
                "monthly_price"
            )
        ]
        return {
            "business_types": types,
            "business_presets": presets,
            "plans": plans,
            "base_domain": get_tenant_base_domain(),
            "steps": [
                "business",
                "type",
                "preset",
                "subdomain",
                "plan",
                "owner",
                "provision",
            ],
        }

    @staticmethod
    def check_slug(raw: str) -> dict:
        try:
            slug = validate_tenant_slug(raw)
        except ValueError as exc:
            return {
                "slug": (raw or "").strip().lower(),
                "available": False,
                "reason": str(exc),
                "hostname": None,
            }
        taken = Tenant.objects.filter(slug=slug, deleted_at__isnull=True).exists()
        return {
            "slug": slug,
            "available": not taken,
            "reason": "already taken" if taken else "",
            "hostname": f"{slug}.{get_tenant_base_domain()}",
        }

    @staticmethod
    def _validate_payload(data: dict) -> dict:
        name = (data.get("name") or data.get("business_name") or "").strip()
        if not name:
            raise OnboardingError("Business name is required.", code="VALIDATION_ERROR")

        owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
        username = (owner.get("username") or "").strip()
        password = owner.get("password") or ""
        email = (owner.get("email") or data.get("contact_email") or "").strip()
        if not username:
            raise OnboardingError("Owner username is required.", code="VALIDATION_ERROR")
        if len(password) < 8:
            raise OnboardingError(
                "Password must be at least 8 characters.", code="VALIDATION_ERROR"
            )
        if not email:
            raise OnboardingError("Owner email is required.", code="VALIDATION_ERROR")

        slug_raw = (data.get("slug") or data.get("subdomain") or "").strip()
        try:
            slug = validate_tenant_slug(slug_raw)
        except ValueError as exc:
            raise OnboardingError(str(exc), code="SLUG_RESERVED") from exc

        plan_code = (data.get("plan_code") or "starter").strip().lower()
        PlatformService.ensure_default_plans()
        if not SubscriptionPlan.objects.filter(code=plan_code, deleted_at__isnull=True, is_active=True).exists():
            raise OnboardingError(f"Unknown plan '{plan_code}'.", code="VALIDATION_ERROR")

        business_type_code = (data.get("business_type_code") or "retail").strip().lower()
        bt = PlatformService.resolve_business_type(code=business_type_code)
        if bt is None:
            raise OnboardingError(
                f"Unknown business type '{business_type_code}'.",
                code="VALIDATION_ERROR",
            )

        from apps.platform.services.business_preset_service import BusinessPresetService

        preset_code = (data.get("preset_code") or bt.code).strip().lower()
        preset = BusinessPresetService.resolve(code=preset_code)
        if preset is None and preset_code != "custom":
            # Fall back to type-named preset after seed
            BusinessPresetService.ensure_default_presets()
            preset = BusinessPresetService.resolve(code=bt.code)
        if preset is None and preset_code not in ("custom",):
            raise OnboardingError(
                f"Unknown business preset '{preset_code}'.",
                code="VALIDATION_ERROR",
            )

        return {
            "name": name,
            "slug": slug,
            "subdomain": slug,
            "plan_code": plan_code,
            "business_type_code": bt.code,
            "preset_code": preset.code if preset else "custom",
            "contact_email": (data.get("contact_email") or email).strip(),
            "contact_phone": (data.get("contact_phone") or "").strip(),
            "country": (data.get("country") or "").strip(),
            "currency": (data.get("currency") or "USD").strip().upper()[:8],
            "language": (data.get("language") or "en").strip().lower()[:16],
            "timezone": (data.get("timezone") or "UTC").strip() or "UTC",
            "branch_name": (data.get("branch_name") or "Main Branch").strip() or "Main Branch",
            "branch_code": (data.get("branch_code") or "BR01").strip() or "BR01",
            "trial_days": int(data.get("trial_days") or 14),
            "owner": {
                "username": username,
                "password": password,
                "email": email,
                "first_name": (owner.get("first_name") or "").strip(),
                "last_name": (owner.get("last_name") or "").strip(),
                "phone": (owner.get("phone") or data.get("contact_phone") or "").strip(),
                "role_slug": "admin",
            },
        }

    @staticmethod
    def _replay_existing(*, tenant: Tenant, username: str, password: str) -> dict | None:
        """If slug already belongs to this owner credentials, treat as idempotent success."""
        owner = (
            tenant.users.filter(username=username, deleted_at__isnull=True, is_active=True).first()
            if hasattr(tenant, "users")
            else None
        )
        if owner is None:
            from apps.authentication.models import User

            owner = User.objects.filter(
                username=username,
                tenant=tenant,
                deleted_at__isnull=True,
                is_active=True,
            ).first()
        if owner is None:
            return None
        if not owner.check_password(password):
            return None
        return OnboardingService._result_payload(tenant=tenant, owner=owner, idempotent_replay=True)

    @staticmethod
    def _result_payload(*, tenant: Tenant, owner, idempotent_replay: bool = False) -> dict:
        branch = (
            Branch.active_objects()
            .filter(tenant=tenant, is_default=True)
            .first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        primary = tenant.domains.filter(is_primary=True, deleted_at__isnull=True).first()
        overview = PlatformService.tenant_overview(tenant)
        return {
            "tenant": overview["tenant"],
            "subscription": overview.get("subscription"),
            "owner": PlatformService.owner_payload(owner),
            "branch": (
                {
                    "id": str(branch.id),
                    "name": branch.name,
                    "code": branch.code,
                }
                if branch
                else None
            ),
            "hostname": primary.domain if primary else f"{tenant.slug}.{get_tenant_base_domain()}",
            "idempotent_replay": idempotent_replay,
        }

    @staticmethod
    @transaction.atomic
    def provision(*, data: dict) -> dict:
        """Create tenant + first branch + owner. Idempotent on slug + matching owner password."""
        payload = OnboardingService._validate_payload(data)
        existing = Tenant.objects.filter(slug=payload["slug"], deleted_at__isnull=True).first()
        if existing:
            replay = OnboardingService._replay_existing(
                tenant=existing,
                username=payload["owner"]["username"],
                password=payload["owner"]["password"],
            )
            if replay:
                return replay
            raise OnboardingError(
                f"Subdomain '{payload['slug']}' is already taken.",
                code="SLUG_TAKEN",
            )

        bootstrap_roles_and_permissions()
        tenant, owner = PlatformService.create_shop(data=payload, user=None)
        if owner is None:
            raise OnboardingError("Owner account was not created.", code="PROVISION_FAILED")
        return OnboardingService._result_payload(tenant=tenant, owner=owner, idempotent_replay=False)

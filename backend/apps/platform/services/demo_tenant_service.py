"""Demo tenant lifecycle (PHASE 10).

Creates real tenants flagged as demos, with expiration / suspend / convert.
Demo data generation is modular — see apps.platform.demo.
"""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.platform.demo import generate_demo_data
from apps.platform.models import Tenant
from apps.platform.services.module_service import enabled_module_codes, sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


class DemoTenantError(Exception):
    def __init__(self, message: str, *, code: str = "DEMO_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class DemoTenantService:
    DEFAULT_DURATION_DAYS = 14

    @staticmethod
    def _ensure_demo(tenant: Tenant) -> Tenant:
        if not tenant.is_demo:
            raise DemoTenantError("Tenant is not a demo account.", code="NOT_DEMO")
        return tenant

    @staticmethod
    def serialize(tenant: Tenant) -> dict:
        modules = sorted(enabled_module_codes(tenant=tenant))
        bt = tenant.business_type
        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status,
            "is_demo": tenant.is_demo,
            "demo_status": tenant.demo_status or None,
            "demo_expires_at": (
                tenant.demo_expires_at.isoformat() if tenant.demo_expires_at else None
            ),
            "demo_converted_at": (
                tenant.demo_converted_at.isoformat() if tenant.demo_converted_at else None
            ),
            "business_type_code": bt.code if bt else None,
            "business_type_name": bt.name if bt else None,
            "modules": modules,
            "is_active": tenant.is_active,
            "contact_email": tenant.contact_email,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        }

    @staticmethod
    def list_demos(*, status: str | None = None):
        qs = (
            Tenant.objects.filter(is_demo=True, deleted_at__isnull=True)
            .select_related("business_type")
            .order_by("-created_at")
        )
        if status:
            qs = qs.filter(demo_status=status.strip().upper())
        return list(qs)

    @staticmethod
    def _tenant_from_create_result(result) -> Tenant:
        if isinstance(result, Tenant):
            return result
        if isinstance(result, tuple) and result:
            first = result[0]
            if isinstance(first, Tenant):
                return first
        if not isinstance(result, dict):
            raise DemoTenantError("Unexpected create_shop result.", code="PROVISION_ERROR")
        t = result.get("tenant")
        if isinstance(t, Tenant):
            return t
        if isinstance(t, dict) and t.get("id"):
            return Tenant.objects.get(pk=t["id"])
        if result.get("id"):
            return Tenant.objects.get(pk=result["id"])
        raise DemoTenantError("Could not resolve tenant from provision.", code="PROVISION_ERROR")

    @staticmethod
    @transaction.atomic
    def create(*, data: dict, user=None) -> tuple[Tenant, dict]:
        """Provision a demo tenant via the same spine as create_shop."""
        name = (data.get("name") or "").strip()
        if not name:
            raise DemoTenantError("Demo name is required.", code="VALIDATION_ERROR")

        duration = int(data.get("duration_days") or DemoTenantService.DEFAULT_DURATION_DAYS)
        if duration < 1 or duration > 365:
            raise DemoTenantError("duration_days must be 1–365.", code="VALIDATION_ERROR")

        slug_base = (data.get("slug") or f"demo-{slugify(name)}")[:80] or "demo-shop"
        payload = {
            **data,
            "name": name,
            "slug": slug_base,
            "plan_code": data.get("plan_code") or "starter",
            "trial_days": duration,
            "preset_code": (data.get("preset_code") or data.get("business_type_code") or "retail"),
            "business_type_code": data.get("business_type_code") or "retail",
        }
        if Tenant.objects.filter(slug=payload["slug"], deleted_at__isnull=True).exists():
            payload["slug"] = f"{payload['slug']}-{timezone.now().strftime('%H%M%S')}"[:100]

        result = PlatformService.create_shop(data=payload, user=user)
        tenant = DemoTenantService._tenant_from_create_result(result)

        # Mark demo before any further entitlement sync so trial/demo rules apply.
        expires = timezone.now() + timedelta(days=duration)
        tenant.is_demo = True
        tenant.demo_status = Tenant.DEMO_ACTIVE
        tenant.demo_expires_at = expires
        tenant.demo_converted_at = None
        tenant.status = Tenant.STATUS_TRIAL
        tenant.sync_active_flag()
        tenant.save(
            update_fields=[
                "is_demo",
                "demo_status",
                "demo_expires_at",
                "demo_converted_at",
                "status",
                "is_active",
                "updated_at",
            ]
        )

        # Optional explicit module set; otherwise trial entitlements already keep
        # business-type / preset modules (PHASE 12 — no starter ∩ strip on trial).
        module_codes = data.get("modules") or data.get("module_codes")
        if isinstance(module_codes, list) and module_codes:
            sync_tenant_modules(
                tenant=tenant,
                enabled_codes=[str(c).strip().lower() for c in module_codes if c],
                disable_missing=True,
                validate_dependencies=True,
                user=user,
            )
        else:
            # Re-sync after is_demo=True so demo rule is authoritative
            from apps.platform.services.entitlement_service import EntitlementService

            EntitlementService.apply_plan_entitlements(tenant=tenant, user=user)

        seed_report = {}
        if data.get("generate_data", True):
            seed_report = generate_demo_data(
                tenant=tenant,
                user=user,
                modules=list(enabled_module_codes(tenant=tenant)),
            )

        return tenant, seed_report

    @staticmethod
    def extend(*, tenant: Tenant, days: int, user=None) -> Tenant:
        DemoTenantService._ensure_demo(tenant)
        if tenant.demo_status == Tenant.DEMO_CONVERTED:
            raise DemoTenantError("Converted demos cannot be extended.", code="CONVERTED")
        days = int(days)
        if days < 1:
            raise DemoTenantError("days must be >= 1.", code="VALIDATION_ERROR")
        base = tenant.demo_expires_at or timezone.now()
        if base < timezone.now():
            base = timezone.now()
        tenant.demo_expires_at = base + timedelta(days=days)
        tenant.demo_status = Tenant.DEMO_ACTIVE
        if tenant.status == Tenant.STATUS_SUSPENDED:
            tenant.status = Tenant.STATUS_TRIAL
        tenant.sync_active_flag()
        tenant.updated_by = user
        tenant.save(
            update_fields=[
                "demo_expires_at",
                "demo_status",
                "status",
                "is_active",
                "updated_by",
                "updated_at",
            ]
        )
        return tenant

    @staticmethod
    def suspend(*, tenant: Tenant, user=None) -> Tenant:
        DemoTenantService._ensure_demo(tenant)
        if tenant.demo_status == Tenant.DEMO_CONVERTED:
            raise DemoTenantError("Converted demos cannot be suspended.", code="CONVERTED")
        tenant.demo_status = Tenant.DEMO_SUSPENDED
        tenant.status = Tenant.STATUS_SUSPENDED
        tenant.sync_active_flag()
        tenant.updated_by = user
        tenant.save(
            update_fields=["demo_status", "status", "is_active", "updated_by", "updated_at"]
        )
        return tenant

    @staticmethod
    def expire(*, tenant: Tenant, user=None) -> Tenant:
        DemoTenantService._ensure_demo(tenant)
        if tenant.demo_status == Tenant.DEMO_CONVERTED:
            return tenant
        tenant.demo_status = Tenant.DEMO_EXPIRED
        tenant.status = Tenant.STATUS_SUSPENDED
        tenant.sync_active_flag()
        tenant.updated_by = user
        tenant.save(
            update_fields=["demo_status", "status", "is_active", "updated_by", "updated_at"]
        )
        return tenant

    @staticmethod
    @transaction.atomic
    def convert(*, tenant: Tenant, plan_code: str | None = None, user=None) -> Tenant:
        """Mark demo as customer — keeps data; attaches/ensures subscription."""
        DemoTenantService._ensure_demo(tenant)
        if tenant.demo_status == Tenant.DEMO_CONVERTED:
            return tenant

        PlatformService.ensure_default_plans()
        from apps.platform.models import SubscriptionPlan, TenantSubscription
        from apps.platform.services.platform_service import _unique_subscription_ref

        code = (plan_code or "starter").strip().lower()
        plan = SubscriptionPlan.objects.filter(code=code, deleted_at__isnull=True).first()
        if plan is None:
            raise DemoTenantError(f"Unknown plan '{code}'.", code="VALIDATION_ERROR")

        sub = getattr(tenant, "subscription", None)
        if sub is None:
            TenantSubscription.objects.create(
                reference_code=_unique_subscription_ref(),
                tenant=tenant,
                plan=plan,
                status=TenantSubscription.STATUS_ACTIVE,
                started_at=timezone.localdate(),
                expires_at=timezone.localdate() + timedelta(days=30),
                created_by=user,
            )
        else:
            sub.plan = plan
            sub.status = TenantSubscription.STATUS_ACTIVE
            if not sub.expires_at or sub.expires_at < timezone.localdate():
                sub.expires_at = timezone.localdate() + timedelta(days=30)
            sub.save()

        tenant.demo_status = Tenant.DEMO_CONVERTED
        tenant.demo_converted_at = timezone.now()
        tenant.status = Tenant.STATUS_ACTIVE
        tenant.sync_active_flag()
        tenant.updated_by = user
        tenant.save(
            update_fields=[
                "demo_status",
                "demo_converted_at",
                "status",
                "is_active",
                "updated_by",
                "updated_at",
            ]
        )
        return tenant

    @staticmethod
    def expire_due(*, user=None) -> list[Tenant]:
        """Mark ACTIVE demos past demo_expires_at as EXPIRED."""
        now = timezone.now()
        due = list(
            Tenant.objects.filter(
                is_demo=True,
                demo_status=Tenant.DEMO_ACTIVE,
                demo_expires_at__isnull=False,
                demo_expires_at__lt=now,
                deleted_at__isnull=True,
            )
        )
        for t in due:
            DemoTenantService.expire(tenant=t, user=user)
        return due

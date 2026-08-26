"""Demo tenant lifecycle (PHASE 10).

Creates real tenants flagged as demos, with expiration / suspend / convert.
Demo data generation is modular — see apps.platform.demo.
Supports attaching an existing shop as a demo, optional shop groups, and
async (Celery) seed with status stored on TenantSettings.extras.
"""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.platform.demo import generate_demo_data
from apps.platform.models import Tenant, TenantSettings
from apps.platform.services.module_service import enabled_module_codes, sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


class DemoTenantError(Exception):
    def __init__(self, message: str, *, code: str = "DEMO_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


SEED_NONE = "none"
SEED_PENDING = "pending"
SEED_RUNNING = "running"
SEED_DONE = "done"
SEED_FAILED = "failed"


class DemoTenantService:
    DEFAULT_DURATION_DAYS = 14

    @staticmethod
    def _ensure_demo(tenant: Tenant) -> Tenant:
        if not tenant.is_demo:
            raise DemoTenantError("Tenant is not a demo account.", code="NOT_DEMO")
        return tenant

    @staticmethod
    def _settings_row(tenant: Tenant, *, user=None) -> TenantSettings:
        row, _ = TenantSettings.objects.get_or_create(
            tenant=tenant,
            defaults={"created_by": user},
        )
        return row

    @staticmethod
    def _get_extras(tenant: Tenant) -> dict:
        row = TenantSettings.objects.filter(tenant=tenant, deleted_at__isnull=True).first()
        if not row or not isinstance(row.extras, dict):
            return {}
        return dict(row.extras)

    @staticmethod
    def _patch_extras(tenant: Tenant, patch: dict, *, user=None) -> dict:
        row = DemoTenantService._settings_row(tenant, user=user)
        extras = dict(row.extras or {})
        extras.update(patch)
        row.extras = extras
        row.updated_by = user
        row.save(update_fields=["extras", "updated_by", "updated_at"])
        return extras

    @staticmethod
    def serialize(tenant: Tenant) -> dict:
        modules = sorted(enabled_module_codes(tenant=tenant))
        bt = tenant.business_type
        group = getattr(tenant, "shop_group", None)
        extras = DemoTenantService._get_extras(tenant)
        seed_status = extras.get("demo_seed_status") or SEED_NONE
        seed_report = extras.get("demo_seed_report")
        from apps.platform.models import TenantDomain

        primary = (
            TenantDomain.active_objects()
            .filter(tenant=tenant, is_primary=True)
            .order_by("-updated_at")
            .first()
        )
        if primary is None:
            primary = TenantDomain.active_objects().filter(tenant=tenant).first()
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
            "shop_group_id": str(group.id) if group else None,
            "shop_group_name": group.name if group else None,
            "seed_status": seed_status,
            "seed_report": seed_report if isinstance(seed_report, dict) else None,
            "seed_error": extras.get("demo_seed_error") or None,
            "primary_domain": PlatformService.domain_payload(primary) if primary else None,
        }

    @staticmethod
    def list_demos(*, status: str | None = None):
        qs = (
            Tenant.objects.filter(is_demo=True, deleted_at__isnull=True)
            .select_related("business_type", "shop_group")
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
    def _parse_duration(data: dict) -> int:
        duration = int(data.get("duration_days") or DemoTenantService.DEFAULT_DURATION_DAYS)
        if duration < 1 or duration > 365:
            raise DemoTenantError("duration_days must be 1–365.", code="VALIDATION_ERROR")
        return duration

    @staticmethod
    def _apply_demo_flags(tenant: Tenant, *, duration: int, user=None) -> Tenant:
        expires = timezone.now() + timedelta(days=duration)
        tenant.is_demo = True
        tenant.demo_status = Tenant.DEMO_ACTIVE
        tenant.demo_expires_at = expires
        tenant.demo_converted_at = None
        tenant.status = Tenant.STATUS_TRIAL
        tenant.sync_active_flag()
        tenant.updated_by = user
        tenant.save(
            update_fields=[
                "is_demo",
                "demo_status",
                "demo_expires_at",
                "demo_converted_at",
                "status",
                "is_active",
                "updated_by",
                "updated_at",
            ]
        )
        return tenant

    @staticmethod
    def _sync_modules(tenant: Tenant, data: dict, *, user=None) -> None:
        module_codes = data.get("modules") or data.get("module_codes") or data.get("enabled_modules")
        if isinstance(module_codes, list) and module_codes:
            sync_tenant_modules(
                tenant=tenant,
                enabled_codes=[str(c).strip().lower() for c in module_codes if c],
                disable_missing=True,
                validate_dependencies=True,
                user=user,
                persist_snapshot=True,
            )
        else:
            from apps.platform.services.entitlement_service import EntitlementService

            EntitlementService.apply_plan_entitlements(tenant=tenant, user=user)

    @staticmethod
    def update_modules(
        *,
        tenant: Tenant,
        modules: list[str],
        user=None,
        merge: bool = True,
        seed_new: bool = False,
    ) -> Tenant:
        """Add or replace modules on an existing demo (or any tenant used as demo)."""
        DemoTenantService._ensure_demo(tenant)
        wanted = {str(c).strip().lower() for c in (modules or []) if c}
        if not wanted:
            raise DemoTenantError("modules must be a non-empty list.", code="VALIDATION_ERROR")
        if merge:
            wanted |= enabled_module_codes(tenant=tenant)
        sync_tenant_modules(
            tenant=tenant,
            enabled_codes=sorted(wanted),
            disable_missing=not merge,
            validate_dependencies=True,
            user=user,
            persist_snapshot=True,
        )
        if seed_new:
            DemoTenantService.enqueue_seed(tenant=tenant, user=user)
        tenant.refresh_from_db()
        return tenant

    @staticmethod
    def run_seed(*, tenant: Tenant, user=None) -> dict:
        """Synchronous seed; updates TenantSettings.extras status."""
        DemoTenantService._patch_extras(
            tenant,
            {
                "demo_seed_status": SEED_RUNNING,
                "demo_seed_error": None,
            },
            user=user,
        )
        try:
            report = generate_demo_data(
                tenant=tenant,
                user=user,
                modules=list(enabled_module_codes(tenant=tenant)),
            )
            DemoTenantService._patch_extras(
                tenant,
                {
                    "demo_seed_status": SEED_DONE,
                    "demo_seed_report": report,
                    "demo_seed_error": None,
                },
                user=user,
            )
            return report
        except Exception as exc:  # noqa: BLE001 — persist failure for UI poll
            DemoTenantService._patch_extras(
                tenant,
                {
                    "demo_seed_status": SEED_FAILED,
                    "demo_seed_error": str(exc)[:500],
                },
                user=user,
            )
            raise

    @staticmethod
    def enqueue_seed(*, tenant: Tenant, user=None) -> dict:
        """Enqueue Celery seed; fall back to sync if broker/worker unavailable."""
        DemoTenantService._patch_extras(
            tenant,
            {
                "demo_seed_status": SEED_PENDING,
                "demo_seed_report": None,
                "demo_seed_error": None,
            },
            user=user,
        )
        tenant_id = str(tenant.id)
        user_id = str(user.id) if user is not None and getattr(user, "id", None) else None

        def _dispatch():
            try:
                from apps.platform.tasks import seed_demo_tenant

                seed_demo_tenant.delay(tenant_id, user_id)
            except Exception:  # noqa: BLE001 — no worker / broker
                DemoTenantService.run_seed(tenant=tenant, user=user)

        try:
            from apps.platform.tasks import seed_demo_tenant  # noqa: F401 — probe import

            transaction.on_commit(_dispatch)
            return {"async": True, "seed_status": SEED_PENDING}
        except Exception:  # noqa: BLE001
            report = DemoTenantService.run_seed(tenant=tenant, user=user)
            return {"async": False, "seed_status": SEED_DONE, "results": report.get("results")}

    @staticmethod
    def _maybe_seed(tenant: Tenant, data: dict, *, user=None) -> dict:
        generate = data.get("generate_data", True)
        if isinstance(generate, str):
            generate = generate.strip().lower() in {"1", "true", "yes", "on"}
        if not generate:
            DemoTenantService._patch_extras(
                tenant,
                {
                    "demo_seed_status": SEED_NONE,
                    "demo_seed_report": None,
                    "demo_seed_error": None,
                },
                user=user,
            )
            return {}

        seed_async = data.get("seed_async", False)
        if isinstance(seed_async, str):
            seed_async = seed_async.strip().lower() in {"1", "true", "yes", "on"}
        if seed_async:
            return DemoTenantService.enqueue_seed(tenant=tenant, user=user)
        return DemoTenantService.run_seed(tenant=tenant, user=user)

    @staticmethod
    def create_from_existing(*, data: dict, user=None) -> tuple[Tenant, dict]:
        """Flag an existing shop tenant as a demo and sync modules."""
        source_id = data.get("source_tenant_id") or data.get("shop_id")
        if not source_id:
            raise DemoTenantError("source_tenant_id is required.", code="VALIDATION_ERROR")

        tenant = (
            Tenant.objects.filter(pk=source_id, deleted_at__isnull=True)
            .select_related("business_type", "shop_group")
            .first()
        )
        if not tenant:
            raise DemoTenantError("Shop tenant not found.", code="NOT_FOUND")
        if tenant.is_demo and tenant.demo_status == Tenant.DEMO_ACTIVE:
            raise DemoTenantError("Shop is already an active demo.", code="ALREADY_DEMO")

        duration = DemoTenantService._parse_duration(data)
        name = (data.get("name") or "").strip()
        if name:
            tenant.name = name
        contact = (data.get("contact_email") or "").strip()
        if contact:
            tenant.contact_email = contact

        bt_code = (data.get("business_type_code") or "").strip().lower()
        if bt_code:
            PlatformService.ensure_default_business_types()
            from apps.platform.models import BusinessType

            bt = BusinessType.objects.filter(code=bt_code, deleted_at__isnull=True).first()
            if bt:
                tenant.business_type = bt

        update_fields = ["name", "contact_email", "business_type", "updated_at"]
        tenant.updated_by = user
        tenant.save(update_fields=update_fields + ["updated_by"])

        DemoTenantService._apply_demo_flags(tenant, duration=duration, user=user)
        DemoTenantService._sync_modules(tenant, data, user=user)
        DemoTenantService.ensure_friendly_domains(tenant=tenant, user=user)
        seed_report = DemoTenantService._maybe_seed(tenant, data, user=user)
        tenant.refresh_from_db()
        return tenant, seed_report

    @staticmethod
    def ensure_friendly_domains(*, tenant: Tenant, user=None) -> list:
        """Register short aliases so demo-kisima is also reachable as kisima.erp…"""
        from apps.platform.models import TenantDomain
        from apps.platform.services.domain_utils import (
            build_tenant_hostname,
            is_reserved_tenant_slug,
            normalize_tenant_slug,
            validate_tenant_slug,
        )

        aliases: list[str] = []
        slug = normalize_tenant_slug(tenant.slug or "")
        if slug.startswith("demo-") and len(slug) > 5:
            aliases.append(slug[5:])
        name_slug = normalize_tenant_slug(tenant.name or "")
        if name_slug and name_slug != slug:
            aliases.append(name_slug)

        created = []
        for raw in aliases:
            try:
                sub = validate_tenant_slug(raw)
            except ValueError:
                continue
            if is_reserved_tenant_slug(sub) or sub == slug:
                continue
            host = build_tenant_hostname(sub)
            exists = TenantDomain.objects.filter(domain=host, deleted_at__isnull=True).first()
            if exists:
                continue
            created.append(
                TenantDomain.objects.create(
                    tenant=tenant,
                    domain=host,
                    subdomain=sub,
                    is_primary=False,
                    is_custom=False,
                    is_verified=True,
                    verified_at=timezone.now(),
                    is_active=True,
                    created_by=user,
                )
            )
        return created

    @staticmethod
    def create(*, data: dict, user=None) -> tuple[Tenant, dict]:
        """Provision a demo tenant via create_shop, or attach an existing shop.

        Provision is atomic; seeding runs after commit so one seeder cannot
        roll back the tenant or other modules.
        """
        source_id = data.get("source_tenant_id") or data.get("shop_id")
        if source_id:
            return DemoTenantService.create_from_existing(data=data, user=user)

        name = (data.get("name") or "").strip()
        if not name:
            raise DemoTenantError("Demo name is required.", code="VALIDATION_ERROR")

        duration = DemoTenantService._parse_duration(data)

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

        with transaction.atomic():
            if Tenant.objects.filter(slug=payload["slug"], deleted_at__isnull=True).exists():
                payload["slug"] = f"{payload['slug']}-{timezone.now().strftime('%H%M%S')}"[:100]

            result = PlatformService.create_shop(data=payload, user=user)
            tenant = DemoTenantService._tenant_from_create_result(result)

            DemoTenantService._apply_demo_flags(tenant, duration=duration, user=user)
            DemoTenantService._sync_modules(tenant, data, user=user)
            DemoTenantService.ensure_friendly_domains(tenant=tenant, user=user)
            tenant_id = tenant.id

        tenant = Tenant.objects.select_related("business_type", "shop_group").get(pk=tenant_id)
        seed_report = DemoTenantService._maybe_seed(tenant, data, user=user)
        tenant.refresh_from_db()
        return tenant, seed_report

    @staticmethod
    def request_seed(*, tenant: Tenant, user=None, async_mode: bool = True) -> dict:
        DemoTenantService._ensure_demo(tenant)
        if async_mode:
            return DemoTenantService.enqueue_seed(tenant=tenant, user=user)
        return DemoTenantService.run_seed(tenant=tenant, user=user)

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

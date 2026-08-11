import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.platform.models import (
    BusinessType,
    SubscriptionPayment,
    SubscriptionPlan,
    ShopGroup,
    Tenant,
    TenantDomain,
    TenantSettings,
    TenantSubscription,
)
from apps.platform.services.domain_utils import (
    build_tenant_hostname,
    get_tenant_base_domain,
    is_reserved_tenant_slug,
    validate_tenant_slug,
)
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.sync_service import CloudShopSyncService
from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import SettingsService
from apps.authentication.models import Role, User
from apps.inventory.models import Warehouse
from core.services.analytics_service import AnalyticsService

SUBSCRIPTION_PAYMENT_KEY = "platform.subscription_payment"

DEFAULT_SUBSCRIPTION_PAYMENT = {
    "company_name": "SAFARI TECHNOLOGY SOLUTIONS",
    "merchant_number": "608833",
    "ussd_template": "*789*{merchant}*{amount}#",
    "qr_image_url": "",
    "qr_payload_template": "tel:*789*{merchant}*{amount}%23",
    "provider_label": "Waafi / EVC Plus",
    "instructions_title": "Pay with Waafi or EVC Plus",
    "instructions": [
        "Scan the QR code — your phone dials *789*merchant*amount# automatically",
        "Confirm the USSD payment in Waafi / EVC Plus",
        "Or dial the USSD code shown below manually",
    ],
    "contact_phone": "Call 141 | 101",
    "dialog_title_override": "",
    "dialog_message_override": "",
    "auto_renew_enabled": True,
}


def _unique_slug(base: str) -> str:
    raw = slugify(base) or "shop"
    if is_reserved_tenant_slug(raw):
        raw = f"shop-{raw}"
    raw = raw[:90]
    candidate = raw
    n = 1
    while Tenant.objects.filter(slug=candidate).exists() or is_reserved_tenant_slug(candidate):
        candidate = f"{raw}-{n}"[:100]
        n += 1
    return candidate


def _resolve_requested_slug(data: dict, *, name: str) -> str:
    raw = (data.get("slug") or data.get("subdomain") or "").strip()
    if raw:
        slug = validate_tenant_slug(raw)
        if Tenant.objects.filter(slug=slug, deleted_at__isnull=True).exists():
            raise ValueError(f"Subdomain '{slug}' is already taken.")
        return slug
    return _unique_slug(name)


def _unique_subscription_ref() -> str:
    while True:
        code = f"SUB-{secrets.token_hex(3).upper()}"
        if not TenantSubscription.objects.filter(reference_code=code).exists():
            return code


def _unique_group_slug(base: str) -> str:
    slug = slugify(base) or "group"
    slug = slug[:90]
    candidate = slug
    n = 1
    while ShopGroup.objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


class PlatformService:
    @staticmethod
    def ensure_default_plans():
        defaults = [
            ("starter", "Starter", 29, 5, 1),
            ("business", "Business", 79, 20, 3),
            ("enterprise", "Enterprise", 149, 100, 10),
        ]
        for code, name, price, users, branches in defaults:
            SubscriptionPlan.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "monthly_price": price,
                    "max_users": users,
                    "max_branches": branches,
                    "is_active": True,
                },
            )

    @staticmethod
    def ensure_default_business_types():
        seeds = [
            ("retail", "General Retail", ["pos", "inventory", "sales", "purchases"], 10),
            ("supermarket", "Supermarket", ["pos", "inventory", "sales", "purchases"], 20),
            ("pharmacy", "Pharmacy", ["pos", "inventory", "sales", "purchases", "pharmacy"], 30),
            ("cafeteria", "Cafeteria", ["pos", "inventory", "sales", "restaurant"], 40),
            ("restaurant", "Restaurant", ["pos", "inventory", "sales", "restaurant"], 50),
            ("electronics", "Electronics", ["pos", "inventory", "sales", "purchases"], 60),
            ("fashion", "Fashion", ["pos", "inventory", "sales", "purchases"], 70),
            ("hardware", "Hardware", ["pos", "inventory", "sales", "purchases"], 80),
            ("wholesale", "Wholesale", ["pos", "inventory", "sales", "purchases"], 90),
            ("gym", "Gym / Fitness Center", ["pos", "inventory", "sales", "gym"], 100),
            ("hotel", "Hotel", ["pos", "inventory", "sales", "hotel"], 105),
            (
                "property",
                "Property Management",
                ["property_management"],
                108,
            ),
            ("salon", "Salon / Spa", ["pos", "inventory", "sales"], 110),
            ("futsal", "Futsal", ["pos", "inventory", "sales", "futsal"], 120),
            (
                "project_management",
                "Project Management",
                ["inventory", "sales", "purchases", "project_management"],
                130,
            ),
            (
                "travel_agency",
                "Travel Agency",
                ["sales", "purchases", "travel_agency"],
                140,
            ),
            ("other", "Other", ["pos", "inventory", "sales"], 200),
        ]
        for code, name, modules, sort_order in seeds:
            BusinessType.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "default_modules": modules,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )

    @staticmethod
    def list_business_types(*, active_only=True):
        PlatformService.ensure_default_business_types()
        qs = BusinessType.active_objects()
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("sort_order", "name")

    @staticmethod
    def business_type_payload(bt: BusinessType) -> dict:
        return {
            "id": str(bt.id),
            "code": bt.code,
            "name": bt.name,
            "description": bt.description,
            "default_modules": bt.default_modules or [],
            "is_active": bt.is_active,
            "sort_order": bt.sort_order,
        }

    @staticmethod
    def resolve_business_type(*, code: str | None = None, business_type_id=None) -> BusinessType | None:
        PlatformService.ensure_default_business_types()
        if business_type_id:
            return BusinessType.active_objects().filter(pk=business_type_id).first()
        if code:
            return BusinessType.active_objects().filter(code=str(code).strip().lower()).first()
        return BusinessType.active_objects().filter(code="retail").first()

    @staticmethod
    def provision_tenant_defaults(*, tenant: Tenant, user=None) -> tuple[TenantSettings, TenantDomain]:
        settings_row, _ = TenantSettings.objects.get_or_create(
            tenant=tenant,
            defaults={"created_by": user},
        )
        primary = (
            TenantDomain.active_objects()
            .filter(tenant=tenant, is_primary=True)
            .first()
        )
        if not primary:
            hostname = build_tenant_hostname(tenant.slug)
            # Soft-collide: if domain exists for another tenant, suffix.
            if TenantDomain.objects.filter(domain=hostname, deleted_at__isnull=True).exclude(tenant=tenant).exists():
                hostname = build_tenant_hostname(f"{tenant.slug}-{str(tenant.id)[:8]}")
            primary = TenantDomain.objects.create(
                tenant=tenant,
                domain=hostname,
                subdomain=tenant.slug,
                is_primary=True,
                is_custom=False,
                is_verified=True,
                verified_at=timezone.now(),
                is_active=True,
                created_by=user,
            )
        sync_tenant_modules(tenant=tenant, user=user)
        # Apply business preset snapshot when provided (or default = business type code)
        from apps.platform.services.business_preset_service import BusinessPresetService

        preset_code = None
        # Caller may pass via tenant.settings.extras later; check attribute stash
        preset_code = getattr(tenant, "_onboarding_preset_code", None)
        if not preset_code and tenant.business_type_id:
            preset_code = tenant.business_type.code
        if preset_code:
            preset = BusinessPresetService.resolve(code=preset_code)
            if preset:
                BusinessPresetService.apply_to_tenant(
                    tenant=tenant, preset=preset, user=user
                )
        return settings_row, primary

    @staticmethod
    def settings_payload(row: TenantSettings) -> dict:
        return {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "date_format": row.date_format,
            "time_format": row.time_format,
            "fiscal_year_start_month": row.fiscal_year_start_month,
            "default_tax_rate": float(row.default_tax_rate or 0),
            "invoice_prefix": row.invoice_prefix,
            "receipt_footer": row.receipt_footer,
            "low_stock_alert_enabled": row.low_stock_alert_enabled,
            "expiry_alert_days": row.expiry_alert_days,
            "branding": row.branding or {},
            "pos_defaults": row.pos_defaults or {},
            "extras": row.extras or {},
            "accounting_cutover_date": (
                row.accounting_cutover_date.isoformat() if row.accounting_cutover_date else None
            ),
            "accounting_posting_enabled": bool(row.accounting_posting_enabled),
        }

    @staticmethod
    def domain_payload(domain: TenantDomain) -> dict:
        return {
            "id": str(domain.id),
            "tenant_id": str(domain.tenant_id),
            "domain": domain.domain,
            "subdomain": domain.subdomain,
            "is_primary": domain.is_primary,
            "is_custom": domain.is_custom,
            "is_verified": domain.is_verified,
            "verified_at": domain.verified_at.isoformat() if domain.verified_at else None,
            "is_active": domain.is_active,
            "url": f"https://{domain.domain}",
        }

    @staticmethod
    def tenant_foundation_payload(tenant: Tenant) -> dict:
        bt = tenant.business_type
        settings_row = getattr(tenant, "settings", None)
        if settings_row is None:
            settings_row = TenantSettings.objects.filter(tenant=tenant, deleted_at__isnull=True).first()
        domains = list(
            TenantDomain.active_objects().filter(tenant=tenant).order_by("-is_primary", "domain")
        )
        primary = next((d for d in domains if d.is_primary), domains[0] if domains else None)
        from apps.platform.services.module_service import enabled_module_codes, sync_tenant_modules

        sync_tenant_modules(tenant=tenant)
        return {
            "status": tenant.status,
            "currency": tenant.currency,
            "language": tenant.language,
            "timezone": tenant.timezone,
            "business_type": PlatformService.business_type_payload(bt) if bt else None,
            "business_type_code": bt.code if bt else None,
            "primary_domain": PlatformService.domain_payload(primary) if primary else None,
            "domains": [PlatformService.domain_payload(d) for d in domains],
            "settings": PlatformService.settings_payload(settings_row) if settings_row else None,
            "base_domain": get_tenant_base_domain(),
            "enabled_modules": sorted(enabled_module_codes(tenant=tenant)),
        }

    @staticmethod
    @transaction.atomic
    def update_tenant_settings(*, tenant: Tenant, data: dict, user=None) -> TenantSettings:
        row, _ = TenantSettings.objects.get_or_create(tenant=tenant, defaults={"created_by": user})
        scalar_fields = (
            "date_format",
            "time_format",
            "invoice_prefix",
            "receipt_footer",
        )
        for key in scalar_fields:
            if key in data:
                setattr(row, key, data.get(key) or "")
        if "fiscal_year_start_month" in data:
            month = int(data["fiscal_year_start_month"] or 1)
            if month < 1 or month > 12:
                raise ValueError("fiscal_year_start_month must be 1–12.")
            row.fiscal_year_start_month = month
        if "default_tax_rate" in data:
            row.default_tax_rate = data["default_tax_rate"] or 0
        if "accounting_cutover_date" in data:
            raw = data.get("accounting_cutover_date")
            if raw in (None, ""):
                row.accounting_cutover_date = None
            else:
                from django.utils.dateparse import parse_date

                parsed = parse_date(str(raw)) if not hasattr(raw, "isoformat") else raw
                if parsed is None:
                    raise ValueError("accounting_cutover_date must be YYYY-MM-DD.")
                row.accounting_cutover_date = parsed
        if "accounting_posting_enabled" in data:
            row.accounting_posting_enabled = bool(data["accounting_posting_enabled"])
        if "low_stock_alert_enabled" in data:
            row.low_stock_alert_enabled = bool(data["low_stock_alert_enabled"])
        if "expiry_alert_days" in data:
            row.expiry_alert_days = int(data["expiry_alert_days"] or 30)
        for key in ("branding", "pos_defaults", "extras"):
            if key in data and isinstance(data[key], dict):
                setattr(row, key, data[key])
        row.updated_by = user
        row.save()
        return row

    @staticmethod
    @transaction.atomic
    def add_tenant_domain(*, tenant: Tenant, data: dict, user=None) -> TenantDomain:
        raw_domain = (data.get("domain") or "").strip().lower()
        subdomain = (data.get("subdomain") or "").strip().lower()
        is_custom = bool(data.get("is_custom", True))
        if not raw_domain:
            if not subdomain:
                raise ValueError("domain or subdomain is required.")
            raw_domain = build_tenant_hostname(subdomain)
            is_custom = False
        if TenantDomain.objects.filter(domain=raw_domain, deleted_at__isnull=True).exists():
            raise ValueError(f"Domain '{raw_domain}' is already in use.")
        make_primary = bool(data.get("is_primary"))
        if make_primary:
            TenantDomain.objects.filter(tenant=tenant, is_primary=True).update(is_primary=False)
        return TenantDomain.objects.create(
            tenant=tenant,
            domain=raw_domain,
            subdomain=subdomain or (raw_domain.split(".")[0] if not is_custom else ""),
            is_primary=make_primary or not TenantDomain.active_objects().filter(tenant=tenant).exists(),
            is_custom=is_custom,
            is_verified=not is_custom,
            verified_at=timezone.now() if not is_custom else None,
            is_active=True,
            created_by=user,
        )

    @staticmethod
    def resolve_user_tenant(user):
        if user.tenant_id:
            return user.tenant
        if user.branch_id:
            company = getattr(user.branch, "company", None)
            if company and company.tenant_id:
                return company.tenant
        company = Company.objects.filter(deleted_at__isnull=True, tenant__isnull=False).first()
        return company.tenant if company else None

    @staticmethod
    def is_global_platform_admin(user) -> bool:
        """True platform owners — see every shop. Not multi-shop group managers."""
        if user is None:
            return False
        elevated = getattr(user, "is_elevated_admin", None)
        if isinstance(elevated, bool):
            return elevated
        return bool(
            user.is_platform_admin
            or user.is_superuser
            or (user.role and user.role.slug in ("super_admin", "platform_admin"))
        )

    @staticmethod
    def is_platform_superuser(user) -> bool:
        """Global platform admin OR unrestricted platform.manage (no managed group)."""
        if PlatformService.is_global_platform_admin(user):
            return True
        if user.managed_shop_group_id:
            return False
        return bool(user.has_permission("platform.manage"))

    @staticmethod
    def can_manage_shops(user) -> bool:
        """Create/edit/delete shops — global admin, platform.manage, or group manager."""
        if PlatformService.is_global_platform_admin(user):
            return True
        if user.managed_shop_group_id:
            return True
        return bool(user.has_permission("platform.manage"))

    @staticmethod
    def accessible_tenant_ids(user) -> list:
        # Multi-shop managers are ALWAYS limited to their group (even if they also
        # have platform.manage — that permission must not escalate them to all shops).
        if user.managed_shop_group_id and not PlatformService.is_global_platform_admin(user):
            return list(
                Tenant.objects.filter(
                    shop_group_id=user.managed_shop_group_id,
                    deleted_at__isnull=True,
                ).values_list("id", flat=True)
            )
        if PlatformService.is_platform_superuser(user):
            return list(
                Tenant.objects.filter(deleted_at__isnull=True).values_list("id", flat=True)
            )
        if user.tenant_id:
            return [user.tenant_id]
        tenant = PlatformService.resolve_user_tenant(user)
        return [tenant.id] if tenant else []

    @staticmethod
    def user_can_access_tenant(user, tenant: Tenant) -> bool:
        return tenant.id in PlatformService.accessible_tenant_ids(user)

    @staticmethod
    def list_tenants_for_user(user, *, active_only=False):
        ids = PlatformService.accessible_tenant_ids(user)
        qs = Tenant.objects.filter(id__in=ids, deleted_at__isnull=True).select_related(
            "subscription__plan", "shop_group", "business_type", "settings"
        ).prefetch_related("companies", "domains")
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    @staticmethod
    def shop_group_payload(group: ShopGroup) -> dict:
        tenant_count = group.tenants.filter(deleted_at__isnull=True).count()
        managers = list(
            User.objects.filter(
                managed_shop_group=group,
                deleted_at__isnull=True,
                is_active=True,
            )
            .select_related("role")
            .order_by("username")[:20]
        )
        return {
            "id": str(group.id),
            "name": group.name,
            "slug": group.slug,
            "contact_email": group.contact_email,
            "contact_phone": group.contact_phone,
            "is_active": group.is_active,
            "tenant_count": tenant_count,
            "shop_count": tenant_count,
            "managers": [
                {
                    "id": str(m.id),
                    "username": m.username,
                    "full_name": m.get_full_name() or m.username,
                    "email": m.email,
                    "role": m.role.name if m.role_id else "Multi-Shop Manager",
                }
                for m in managers
            ],
        }

    @staticmethod
    def user_can_access_shop_group(user, group: ShopGroup) -> bool:
        if PlatformService.is_global_platform_admin(user):
            return True
        if user.managed_shop_group_id and str(user.managed_shop_group_id) == str(group.id):
            return True
        if PlatformService.is_platform_superuser(user):
            return True
        return False

    @staticmethod
    def shop_group_overview(group: ShopGroup, *, period: str = "month") -> dict:
        """Tenant-org profile: group meta + member shops with KPIs."""
        shops = list(
            Tenant.objects.filter(shop_group=group, deleted_at__isnull=True)
            .select_related("subscription__plan")
            .order_by("name")
        )
        shop_rows = []
        totals = {
            "shops": len(shops),
            "active_shops": 0,
            "total_sales": 0,
            "revenue": 0.0,
            "users": 0,
        }
        for tenant in shops:
            overview = PlatformService.tenant_overview(tenant, period=period)
            kpis = overview.get("kpis") or {}
            users_count = len(overview.get("users") or [])
            if tenant.is_active:
                totals["active_shops"] += 1
            totals["total_sales"] += int(kpis.get("total_sales") or 0)
            totals["revenue"] += float(kpis.get("revenue") or 0)
            totals["users"] += users_count
            shop_rows.append(
                {
                    **overview["tenant"],
                    "subscription": overview.get("subscription"),
                    "kpis": {
                        "total_sales": kpis.get("total_sales") or 0,
                        "revenue": kpis.get("revenue") or 0,
                        "cash_collected": kpis.get("cash_collected") or 0,
                        "profit": kpis.get("profit") or 0,
                    },
                    "users_count": users_count,
                    "catalog": {
                        "products_count": (overview.get("catalog") or {}).get("products_count") or 0,
                        "low_stock": (overview.get("catalog") or {}).get("low_stock") or 0,
                    },
                }
            )

        payload = PlatformService.shop_group_payload(group)
        payload["period"] = period
        payload["totals"] = totals
        payload["shops"] = shop_rows
        return payload

    @staticmethod
    def list_shop_groups(*, active_only=False):
        qs = ShopGroup.objects.filter(deleted_at__isnull=True)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    @staticmethod
    @transaction.atomic
    def create_shop_group(*, data: dict, user=None) -> ShopGroup:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Group name is required.")
        code = (data.get("slug") or slugify(name) or "group")[:90]
        if ShopGroup.objects.filter(slug=code, deleted_at__isnull=True).exists():
            code = _unique_group_slug(name)
        return ShopGroup.objects.create(
            name=name,
            slug=code,
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            is_active=bool(data.get("is_active", True)),
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def assign_group_manager(*, group: ShopGroup, manager_user: User):
        role = Role.objects.filter(slug="shop_group_manager", deleted_at__isnull=True).first()
        if not role:
            raise ValueError("Multi-shop manager role is not available. Run bootstrap.")
        manager_user.managed_shop_group = group
        manager_user.tenant = None
        manager_user.branch = None
        manager_user.role = role
        manager_user.is_platform_admin = False
        manager_user.save()

    @staticmethod
    @transaction.atomic
    def create_tenant_for_company(*, company: Company, contact_email: str = "", plan_code: str = "starter"):
        PlatformService.ensure_default_plans()
        PlatformService.ensure_default_business_types()
        plan = SubscriptionPlan.objects.get(code=plan_code)
        business_type = PlatformService.resolve_business_type(code="retail")
        tenant = Tenant.objects.create(
            name=company.name,
            slug=_unique_slug(company.name),
            contact_email=contact_email or company.email,
            contact_phone=company.phone,
            sync_secret=secrets.token_urlsafe(24),
            status=Tenant.STATUS_TRIAL,
            is_active=True,
            business_type=business_type,
            currency="USD",
            language="en",
        )
        PlatformService.provision_tenant_defaults(tenant=tenant)
        company.tenant = tenant
        company.save(update_fields=["tenant", "updated_at"])
        expires = timezone.localdate() + timedelta(days=30)
        TenantSubscription.objects.create(
            reference_code=_unique_subscription_ref(),
            tenant=tenant,
            plan=plan,
            status=TenantSubscription.STATUS_TRIAL,
            started_at=timezone.localdate(),
            expires_at=expires,
        )
        return tenant

    @staticmethod
    def list_tenants(*, active_only=False):
        qs = Tenant.objects.select_related(
            "subscription__plan", "business_type", "settings"
        ).prefetch_related("companies", "domains")
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    @staticmethod
    def list_subscriptions(*, unassigned_only=False, user=None):
        qs = TenantSubscription.objects.select_related("plan", "tenant", "contact_user").filter(
            deleted_at__isnull=True
        )
        if user is not None and not PlatformService.is_global_platform_admin(user):
            if user.managed_shop_group_id or not PlatformService.is_platform_superuser(user):
                ids = PlatformService.accessible_tenant_ids(user)
                qs = qs.filter(tenant_id__in=ids)
                # Group managers never see unassigned licenses meant for platform owners
                if user.managed_shop_group_id:
                    unassigned_only = False
        if unassigned_only:
            qs = qs.filter(tenant__isnull=True)
        return qs.order_by("-created_at")

    @staticmethod
    def list_tenant_users(tenant: Tenant):
        from django.db.models import Q

        return (
            User.objects.filter(
                Q(tenant=tenant) | Q(branch__company__tenant=tenant),
                deleted_at__isnull=True,
                is_active=True,
            )
            .select_related("role", "branch")
            .distinct()
            .order_by("username")
        )

    @staticmethod
    def subscription_payload(sub: TenantSubscription) -> dict:
        contact = None
        if sub.contact_user_id:
            contact = {
                "id": str(sub.contact_user_id),
                "username": sub.contact_user.username,
                "full_name": sub.contact_user.get_full_name() or sub.contact_user.username,
            }
        return {
            "id": str(sub.id),
            "reference_code": sub.reference_code,
            "tenant_id": str(sub.tenant_id) if sub.tenant_id else None,
            "tenant_name": sub.tenant.name if sub.tenant_id else None,
            "contact_user": contact,
            "plan": sub.plan.name,
            "plan_code": sub.plan.code,
            "status": sub.status,
            "monthly_price": float(sub.plan.monthly_price),
            "monthly_fee": float(sub.effective_monthly_fee),
            "custom_monthly_fee": float(sub.monthly_fee) if sub.monthly_fee is not None else None,
            "started_at": sub.started_at.isoformat(),
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "last_paid_at": sub.last_paid_at.isoformat() if sub.last_paid_at else None,
            "billing_period_days": sub.billing_period_days,
            "warning_days": sub.warning_days,
            "grace_period_days": sub.grace_period_days,
            "alert_title": sub.alert_title,
            "alert_message_template": sub.alert_message_template,
            "days_until_expiry": sub.days_until_expiry,
            "is_usable": sub.is_usable,
            "is_payment_current": sub.is_payment_current,
            "needs_payment_alert": sub.needs_payment_alert,
            "notes": sub.notes,
        }

    @staticmethod
    def tenant_overview(tenant: Tenant, *, period: str = "month"):
        PlatformService.provision_tenant_defaults(tenant=tenant)
        tenant = (
            Tenant.objects.select_related("business_type", "settings", "shop_group", "subscription__plan")
            .prefetch_related("domains", "companies")
            .get(pk=tenant.pk)
        )
        company = tenant.companies.filter(deleted_at__isnull=True).first()
        branch = None
        warehouse = None
        if company:
            branch = Branch.active_objects().filter(company=company, is_default=True).first()
            if not branch:
                branch = Branch.active_objects().filter(company=company).first()
            if branch:
                from apps.inventory.models import Warehouse, Inventory
                from django.db.models import Sum, F

                warehouse = (
                    Warehouse.active_objects().filter(branch=branch, is_default=True).first()
                    or Warehouse.active_objects().filter(branch=branch).first()
                )
        branch_id = str(branch.id) if branch else None
        kpis = AnalyticsService.get_kpis(branch_id=branch_id, period=period)
        snapshot_kpis = CloudShopSyncService.latest_kpis(tenant)
        if snapshot_kpis:
            kpis = {**kpis, **snapshot_kpis, "source": "cloud_sync"}
        snap = tenant.sync_snapshots.order_by("-synced_at").first()
        staff = AnalyticsService.get_staff_performance(
            branch_id=branch_id, tenant_id=str(tenant.id), period=period
        )
        group = tenant.shop_group

        users = list(PlatformService.list_tenant_users(tenant)[:50])
        catalog = {
            "products_count": 0,
            "stock_units": 0,
            "stock_value": 0.0,
            "low_stock": 0,
            "products": [],
        }
        if warehouse:
            from apps.inventory.services.inventory_service import InventoryService

            InventoryService.backfill_missing_inventory(warehouse=warehouse)
            inv_qs = Inventory.active_objects().filter(warehouse=warehouse)
            agg = inv_qs.aggregate(
                units=Sum("quantity"),
                value=Sum(F("quantity") * F("product__cost_price")),
            )
            catalog["products_count"] = inv_qs.values("product_id").distinct().count()
            catalog["stock_units"] = float(agg["units"] or 0)
            catalog["stock_value"] = float(agg["value"] or 0)
            catalog["low_stock"] = (
                inv_qs.filter(quantity__lte=F("product__minimum_stock")).count()
            )
            catalog["products"] = [
                {
                    "id": str(row.product_id),
                    "name": row.product.name if row.product_id else "",
                    "sku": getattr(row.product, "sku", "") or "",
                    "quantity": float(row.quantity or 0),
                    "unit_price": float(getattr(row.product, "selling_price", 0) or 0),
                }
                for row in inv_qs.select_related("product").order_by("product__name")[:100]
            ]
        else:
            catalog["products"] = []

        recent_sales = []
        if branch:
            from apps.sales.models import Invoice

            for inv in (
                Invoice.objects.filter(branch=branch, deleted_at__isnull=True)
                .select_related("customer", "created_by_user")
                .order_by("-issue_date", "-created_at")[:40]
            ):
                recent_sales.append(
                    {
                        "id": str(inv.id),
                        "invoice_number": inv.invoice_number,
                        "customer_name": inv.customer.full_name if inv.customer_id else "Walk-in",
                        "status": inv.status,
                        "total_amount": float(inv.total_amount or 0),
                        "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                        "cashier": (
                            inv.created_by_user.get_full_name() or inv.created_by_user.username
                            if inv.created_by_user_id
                            else ""
                        ),
                    }
                )

        waiters = []
        from apps.settings_app.services.settings_service import SettingsService
        import json

        for key in (f"pos.waiters.{tenant.slug}", "pos.waiters"):
            row = SettingsService.get_by_key(key=key)
            if not row or row.value in (None, "", {}, []):
                continue
            raw = row.value
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    raw = []
            if isinstance(raw, list) and raw:
                waiters = raw
                break

        return {
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "sync_secret": tenant.sync_secret,
                "is_active": tenant.is_active,
                "status": tenant.status,
                "contact_email": tenant.contact_email,
                "contact_phone": tenant.contact_phone,
                "country": tenant.country,
                "timezone": tenant.timezone,
                "currency": tenant.currency,
                "language": tenant.language,
                "business_type_code": tenant.business_type.code if tenant.business_type_id else None,
                "business_type": (
                    PlatformService.business_type_payload(tenant.business_type)
                    if tenant.business_type_id
                    else None
                ),
                "last_synced_at": snap.synced_at.isoformat() if snap else None,
                "shop_group_id": str(group.id) if group else None,
                "shop_group_name": group.name if group else None,
                "is_demo": bool(tenant.is_demo),
                "demo_status": tenant.demo_status or None,
                "demo_expires_at": (
                    tenant.demo_expires_at.isoformat() if tenant.demo_expires_at else None
                ),
                **{
                    k: v
                    for k, v in PlatformService.tenant_foundation_payload(tenant).items()
                    if k
                    in (
                        "primary_domain",
                        "domains",
                        "settings",
                        "base_domain",
                    )
                },
            },
            "subscription": PlatformService._subscription_payload(tenant),
            "company": {"id": str(company.id), "name": company.name} if company else None,
            "branch": {"id": str(branch.id), "name": branch.name, "code": branch.code} if branch else None,
            "kpis": kpis,
            "staff_performance": staff[:20],
            "catalog": catalog,
            "recent_sales": recent_sales,
            "users": [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "full_name": u.get_full_name() or u.username,
                    "email": u.email,
                    "role": u.role.name if u.role_id else "",
                    "is_active": u.is_active,
                }
                for u in users
            ],
            "waiters": [
                {
                    "id": str(w.get("id") or ""),
                    "name": w.get("name") or "",
                    "user_id": w.get("user_id") or None,
                    "is_active": w.get("is_active", True),
                }
                for w in waiters
                if (w.get("name") or "").strip()
            ],
        }

    @staticmethod
    def _subscription_payload(tenant: Tenant) -> dict | None:
        sub = getattr(tenant, "subscription", None)
        if not sub:
            return None
        payload = PlatformService.subscription_payload(sub)
        return {
            "id": payload["id"],
            "reference_code": payload["reference_code"],
            "plan": payload["plan"],
            "plan_code": payload["plan_code"],
            "status": payload["status"],
            "monthly_price": payload["monthly_price"],
            "monthly_fee": payload["monthly_fee"],
            "started_at": payload["started_at"],
            "expires_at": payload["expires_at"],
            "last_paid_at": payload["last_paid_at"],
            "billing_period_days": payload["billing_period_days"],
            "warning_days": payload["warning_days"],
            "grace_period_days": payload["grace_period_days"],
            "days_until_expiry": payload["days_until_expiry"],
            "is_usable": payload["is_usable"],
            "is_payment_current": payload["is_payment_current"],
            "needs_payment_alert": payload["needs_payment_alert"],
        }

    @staticmethod
    @transaction.atomic
    def create_subscription(*, data: dict, user=None) -> TenantSubscription:
        PlatformService.ensure_default_plans()
        plan = SubscriptionPlan.objects.get(code=data["plan_code"])
        duration = int(data.get("duration_days", data.get("billing_period_days", 30)))
        started = data.get("started_at")
        if started:
            from datetime import date

            if isinstance(started, str):
                started = date.fromisoformat(started)
        else:
            started = timezone.localdate()
        expires = started + timedelta(days=duration)
        sub = TenantSubscription.objects.create(
            reference_code=_unique_subscription_ref(),
            tenant=None,
            plan=plan,
            status=data.get("status", TenantSubscription.STATUS_TRIAL),
            started_at=started,
            expires_at=expires,
            billing_period_days=int(data.get("billing_period_days", 30)),
            warning_days=int(data.get("warning_days", 5)),
            grace_period_days=int(data.get("grace_period_days", 5)),
            monthly_fee=data.get("monthly_fee") if data.get("monthly_fee") not in (None, "") else None,
            alert_title=data.get("alert_title", ""),
            alert_message_template=data.get("alert_message_template", ""),
            notes=data.get("notes", ""),
            created_by=user,
        )
        return sub

    @staticmethod
    @transaction.atomic
    def assign_subscription(*, subscription: TenantSubscription, tenant: Tenant, user=None):
        if subscription.tenant_id and subscription.tenant_id != tenant.id:
            raise ValueError("Subscription is already assigned to another shop.")
        existing = TenantSubscription.objects.filter(tenant=tenant).exclude(pk=subscription.pk).first()
        if existing:
            raise ValueError("This shop already has a different subscription.")
        subscription.tenant = tenant
        subscription.updated_by = user
        subscription.save(update_fields=["tenant", "updated_by", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def renew_subscription(*, subscription: TenantSubscription, user=None, notes: str = ""):
        today = timezone.localdate()
        period = subscription.billing_period_days or 30
        base = subscription.expires_at if subscription.expires_at and subscription.expires_at >= today else today
        subscription.expires_at = base + timedelta(days=period)
        subscription.last_paid_at = today
        subscription.status = TenantSubscription.STATUS_ACTIVE
        if notes:
            subscription.notes = notes
        subscription.updated_by = user
        subscription.save()
        return subscription

    @staticmethod
    @transaction.atomic
    def update_subscription_record(*, subscription: TenantSubscription, data: dict, user=None):
        from datetime import date

        sub = subscription
        if "plan_code" in data:
            sub.plan = SubscriptionPlan.objects.get(code=data["plan_code"])
        if "status" in data:
            sub.status = data["status"]
        if "started_at" in data and data["started_at"]:
            started = data["started_at"]
            sub.started_at = date.fromisoformat(started) if isinstance(started, str) else started
        if "expires_at" in data:
            expires = data["expires_at"]
            sub.expires_at = date.fromisoformat(expires) if expires and isinstance(expires, str) else expires
        if "last_paid_at" in data:
            paid = data["last_paid_at"]
            sub.last_paid_at = date.fromisoformat(paid) if paid and isinstance(paid, str) else paid
        if "billing_period_days" in data:
            sub.billing_period_days = int(data["billing_period_days"])
        if "warning_days" in data:
            sub.warning_days = int(data["warning_days"])
        if "grace_period_days" in data:
            sub.grace_period_days = int(data["grace_period_days"])
        if "monthly_fee" in data:
            fee = data["monthly_fee"]
            sub.monthly_fee = None if fee in (None, "") else fee
        if "alert_title" in data:
            sub.alert_title = data["alert_title"] or ""
        if "alert_message_template" in data:
            sub.alert_message_template = data["alert_message_template"] or ""
        if "notes" in data:
            sub.notes = data["notes"]
        if "contact_user_id" in data:
            uid = data["contact_user_id"]
            sub.contact_user = User.objects.get(pk=uid) if uid else None
        if "tenant_id" in data:
            tenant_id = data["tenant_id"]
            if not tenant_id:
                sub.tenant = None
            else:
                tenant = Tenant.objects.get(pk=tenant_id)
                if sub.tenant_id != tenant.id:
                    PlatformService.assign_subscription(subscription=sub, tenant=tenant, user=user)
        sub.updated_by = user
        sub.save()
        if sub.tenant_id and ("plan_code" in data or "tenant_id" in data):
            from apps.platform.services.entitlement_service import EntitlementService

            EntitlementService.apply_plan_entitlements(tenant=sub.tenant, user=user)
        return sub

    @staticmethod
    @transaction.atomic
    def update_shop(*, tenant: Tenant, data: dict, user=None):
        if "name" in data:
            tenant.name = data["name"]
        if "contact_email" in data:
            tenant.contact_email = data["contact_email"]
        if "contact_phone" in data:
            tenant.contact_phone = data["contact_phone"]
        if "country" in data:
            tenant.country = data["country"]
        if "timezone" in data and data["timezone"]:
            tenant.timezone = data["timezone"]
        if "currency" in data and data["currency"]:
            tenant.currency = str(data["currency"]).upper()[:8]
        if "language" in data and data["language"]:
            tenant.language = str(data["language"]).lower()[:16]
        if "business_type_code" in data or "business_type_id" in data:
            bt = PlatformService.resolve_business_type(
                code=data.get("business_type_code"),
                business_type_id=data.get("business_type_id"),
            )
            if not bt and (data.get("business_type_code") or data.get("business_type_id")):
                raise ValueError("Unknown business type.")
            tenant.business_type = bt
        if "tenant_status" in data and data["tenant_status"]:
            status_value = str(data["tenant_status"]).lower()
            allowed = {c[0] for c in Tenant.STATUS_CHOICES}
            if status_value not in allowed:
                raise ValueError(f"Invalid tenant status '{status_value}'.")
            tenant.status = status_value
            tenant.sync_active_flag()
        elif "is_active" in data:
            tenant.is_active = bool(data["is_active"])
            if tenant.is_active and tenant.status in (Tenant.STATUS_SUSPENDED, Tenant.STATUS_CANCELLED):
                tenant.status = Tenant.STATUS_ACTIVE
            elif not tenant.is_active:
                tenant.status = Tenant.STATUS_SUSPENDED
        if "shop_group_id" in data:
            # Group managers cannot move shops out of (or into) another group.
            if user and user.managed_shop_group_id and not PlatformService.is_global_platform_admin(user):
                tenant.shop_group_id = user.managed_shop_group_id
            else:
                gid = data.get("shop_group_id")
                tenant.shop_group = ShopGroup.objects.get(pk=gid) if gid else None
        tenant.updated_by = user
        tenant.save()
        PlatformService.provision_tenant_defaults(tenant=tenant, user=user)

        company = tenant.companies.filter(deleted_at__isnull=True).first()
        if company:
            if "name" in data:
                company.name = data["name"]
            if "contact_email" in data:
                company.email = data["contact_email"]
            if "contact_phone" in data:
                company.phone = data["contact_phone"]
            if "address" in data:
                company.address = data["address"]
            company.updated_by = user
            company.save()

        if "settings" in data and isinstance(data["settings"], dict):
            PlatformService.update_tenant_settings(
                tenant=tenant, data=data["settings"], user=user
            )

        subscription_id = data.get("subscription_id")
        plan_code = data.get("plan_code")
        existing_sub = getattr(tenant, "subscription", None)

        if subscription_id:
            sub = TenantSubscription.objects.get(pk=subscription_id)
            PlatformService.assign_subscription(subscription=sub, tenant=tenant, user=user)
        elif plan_code and not existing_sub:
            PlatformService.ensure_default_plans()
            plan = SubscriptionPlan.objects.get(code=plan_code)
            expires = timezone.localdate() + timedelta(days=int(data.get("trial_days", 30)))
            TenantSubscription.objects.create(
                reference_code=_unique_subscription_ref(),
                tenant=tenant,
                plan=plan,
                status=data.get("status", TenantSubscription.STATUS_TRIAL),
                started_at=timezone.localdate(),
                expires_at=expires,
                billing_period_days=int(data.get("billing_period_days", 30)),
                warning_days=int(data.get("warning_days", 5)),
                grace_period_days=int(data.get("grace_period_days", 5)),
                created_by=user,
            )
        elif existing_sub and (plan_code or "status" in data):
            if plan_code:
                PlatformService.ensure_default_plans()
                existing_sub.plan = SubscriptionPlan.objects.get(code=plan_code)
            if "status" in data:
                existing_sub.status = data["status"]
            existing_sub.updated_by = user
            existing_sub.save()

        return tenant

    @staticmethod
    @transaction.atomic
    def delete_shop(*, tenant: Tenant, user=None):
        tenant.is_active = False
        tenant.updated_by = user
        tenant.save(update_fields=["is_active", "updated_by", "updated_at"])
        tenant.soft_delete(user=user)
        for company in tenant.companies.filter(deleted_at__isnull=True):
            company.soft_delete(user=user)
        return tenant

    @staticmethod
    @transaction.atomic
    def delete_subscription(*, subscription: TenantSubscription, user=None):
        subscription.soft_delete(user=user)
        return subscription

    @staticmethod
    @transaction.atomic
    def update_subscription(*, tenant: Tenant, data: dict, user=None):
        sub = tenant.subscription
        if "monthly_fee" in data:
            fee = data["monthly_fee"]
            sub.monthly_fee = None if fee in (None, "") else fee
        if "alert_title" in data:
            sub.alert_title = data["alert_title"] or ""
        if "alert_message_template" in data:
            sub.alert_message_template = data["alert_message_template"] or ""
        if "contact_user_id" in data:
            uid = data["contact_user_id"]
            sub.contact_user = User.objects.get(pk=uid) if uid else None
        if "status" in data:
            sub.status = data["status"]
        if "expires_at" in data:
            sub.expires_at = data["expires_at"]
        if "last_paid_at" in data:
            sub.last_paid_at = data["last_paid_at"]
        if "plan_code" in data:
            sub.plan = SubscriptionPlan.objects.get(code=data["plan_code"])
        if "billing_period_days" in data:
            sub.billing_period_days = int(data["billing_period_days"])
        if "warning_days" in data:
            sub.warning_days = int(data["warning_days"])
        if "grace_period_days" in data:
            sub.grace_period_days = int(data["grace_period_days"])
        if "notes" in data:
            sub.notes = data["notes"]
        sub.updated_by = user
        sub.save()
        return sub

    @staticmethod
    def list_payment_alerts(*, user=None):
        qs = TenantSubscription.objects.select_related("plan", "tenant").filter(
            tenant__isnull=False,
            deleted_at__isnull=True,
        )
        if user is not None:
            ids = PlatformService.accessible_tenant_ids(user)
            qs = qs.filter(tenant_id__in=ids)
        alerts = []
        for sub in qs:
            if sub.needs_payment_alert:
                alerts.append(PlatformService.enrich_alert_payload(sub, user=user))
        return alerts

    @staticmethod
    def user_subscription_alert(user):
        tenant = PlatformService.resolve_user_tenant(user)
        if not tenant:
            return None
        sub = getattr(tenant, "subscription", None)
        if not sub or not sub.needs_payment_alert:
            return None
        if sub.contact_user_id and sub.contact_user_id != user.id:
            if not (user.is_platform_admin or user.has_permission("platform.view")):
                return None
        return PlatformService.enrich_alert_payload(sub, user=user)

    @staticmethod
    def _shop_owner_role_slugs():
        return {
            "admin",
            "cashier",
            "branch_manager",
            "accountant",
            "inventory_manager",
            "futsal_manager",
        }

    @staticmethod
    def default_branch_for_tenant(tenant: Tenant) -> Branch | None:
        company = tenant.companies.filter(deleted_at__isnull=True).first()
        if not company:
            return None
        return (
            Branch.active_objects().filter(company=company, is_default=True).first()
            or Branch.active_objects().filter(company=company).first()
        )

    @staticmethod
    def create_tenant_user(*, tenant: Tenant, data: dict, created_by=None):
        """Create a shop desktop/cloud user bound to this tenant."""
        branch = PlatformService.default_branch_for_tenant(tenant)
        if not branch:
            raise ValueError("Shop has no branch. Recreate the shop or contact support.")
        return PlatformService.create_shop_owner(
            tenant=tenant,
            branch=branch,
            owner=data,
            shop_group=None,
            as_group_manager=False,
            created_by=created_by,
        )

    @staticmethod
    def create_shop_owner(
        *,
        tenant: Tenant,
        branch: Branch,
        owner: dict,
        shop_group: ShopGroup | None = None,
        as_group_manager: bool = False,
        created_by=None,
    ):
        username = (owner.get("username") or "").strip()
        password = owner.get("password") or ""
        if not username:
            raise ValueError("Shop owner username is required.")
        if len(password) < 8:
            raise ValueError("Shop owner password must be at least 8 characters.")

        existing = User.objects.filter(username__iexact=username, deleted_at__isnull=True).first()
        if existing:
            if as_group_manager and shop_group:
                existing.set_password(password)
                PlatformService.assign_group_manager(group=shop_group, manager_user=existing)
                if created_by and not existing.created_by_id:
                    existing.created_by = created_by
                existing.save()
                return existing
            raise ValueError(f"Username '{username}' is already taken.")

        if as_group_manager and shop_group:
            role = Role.objects.filter(slug="shop_group_manager", deleted_at__isnull=True).first()
            if not role:
                raise ValueError("Multi-shop manager role is not available.")
            user = User.objects.create_user(
                username=username,
                email=(owner.get("email") or tenant.contact_email or "").strip(),
                password=password,
                first_name=(owner.get("first_name") or "").strip(),
                last_name=(owner.get("last_name") or "").strip(),
                phone=(owner.get("phone") or tenant.contact_phone or "").strip(),
                role=role,
                managed_shop_group=shop_group,
                created_by=created_by,
                is_active=True,
            )
            return user

        role_slug = (owner.get("role_slug") or "admin").strip()
        allowed = PlatformService._shop_owner_role_slugs()
        if role_slug not in allowed:
            raise ValueError("Invalid shop owner role.")
        role = Role.objects.filter(slug=role_slug, deleted_at__isnull=True).first()
        if not role:
            raise ValueError(f"Role '{role_slug}' is not available.")

        return User.objects.create_user(
            username=username,
            email=(owner.get("email") or tenant.contact_email or "").strip(),
            password=password,
            first_name=(owner.get("first_name") or "").strip(),
            last_name=(owner.get("last_name") or "").strip(),
            phone=(owner.get("phone") or tenant.contact_phone or "").strip(),
            role=role,
            branch=branch,
            tenant=tenant,
            created_by=created_by,
            is_active=True,
        )

    @staticmethod
    def owner_payload(user: User) -> dict:
        return {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.get_full_name() or user.username,
            "email": user.email,
            "role": user.role.name if user.role_id else None,
            "role_slug": user.role.slug if user.role_id else None,
        }

    @staticmethod
    @transaction.atomic
    def create_shop(*, data: dict, user=None):
        shop_group = None
        # Multi-shop managers can only create shops inside their own group.
        if user and user.managed_shop_group_id and not PlatformService.is_global_platform_admin(user):
            shop_group = user.managed_shop_group
        elif data.get("shop_group_id"):
            shop_group = ShopGroup.objects.get(pk=data["shop_group_id"])
        elif (data.get("shop_group_name") or "").strip():
            shop_group = PlatformService.create_shop_group(
                data={
                    "name": data["shop_group_name"].strip(),
                    "contact_email": data.get("contact_email", ""),
                    "contact_phone": data.get("contact_phone", ""),
                },
                user=user,
            )

        as_group_manager = bool(data.get("assign_owner_as_group_manager")) or bool(
            shop_group and (data.get("owner") or {}).get("role_slug") == "shop_group_manager"
        )

        PlatformService.ensure_default_business_types()
        business_type = PlatformService.resolve_business_type(
            code=data.get("business_type_code"),
            business_type_id=data.get("business_type_id"),
        )
        slug = _resolve_requested_slug(data, name=data["name"])
        currency = str(data.get("currency") or "USD").upper()[:8]
        language = str(data.get("language") or "en").lower()[:16]
        tz = (data.get("timezone") or "UTC").strip() or "UTC"

        tenant = Tenant.objects.create(
            name=data["name"],
            slug=slug,
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            country=data.get("country", ""),
            timezone=tz,
            currency=currency,
            language=language,
            status=Tenant.STATUS_TRIAL,
            business_type=business_type,
            sync_secret=secrets.token_urlsafe(24),
            is_active=True,
            shop_group=shop_group,
            created_by=user,
        )
        preset_code = (data.get("preset_code") or "").strip().lower() or (
            business_type.code if business_type else None
        )
        if preset_code:
            tenant._onboarding_preset_code = preset_code  # noqa: SLF001 — ephemeral provision hint
        PlatformService.provision_tenant_defaults(tenant=tenant, user=user)
        if isinstance(data.get("settings"), dict):
            PlatformService.update_tenant_settings(
                tenant=tenant, data=data["settings"], user=user
            )
        company = Company.objects.create(
            name=data["name"],
            legal_name=data.get("legal_name", ""),
            email=data.get("contact_email", ""),
            phone=data.get("contact_phone", ""),
            address=data.get("address", ""),
            tenant=tenant,
            created_by=user,
        )
        branch = Branch.objects.create(
            company=company,
            name=data.get("branch_name", "Main Branch"),
            code=data.get("branch_code", "BR01"),
            is_default=True,
            is_active=True,
            tenant=tenant,
            created_by=user,
        )
        Warehouse.objects.create(
            branch=branch,
            code="WH01",
            name="Main Warehouse",
            is_default=True,
            is_active=True,
            tenant=tenant,
            created_by=user,
        )

        owner_user = None
        owner = data.get("owner")
        if isinstance(owner, dict) and owner.get("username"):
            owner_user = PlatformService.create_shop_owner(
                tenant=tenant,
                branch=branch,
                owner=owner,
                shop_group=shop_group,
                as_group_manager=as_group_manager,
                created_by=user,
            )

        subscription_id = data.get("subscription_id")
        created_sub = None
        if subscription_id:
            sub = TenantSubscription.objects.get(pk=subscription_id)
            PlatformService.assign_subscription(subscription=sub, tenant=tenant, user=user)
            created_sub = sub
        elif data.get("plan_code"):
            PlatformService.ensure_default_plans()
            plan = SubscriptionPlan.objects.get(code=data["plan_code"])
            expires = timezone.localdate() + timedelta(days=int(data.get("trial_days", 30)))
            created_sub = TenantSubscription.objects.create(
                reference_code=_unique_subscription_ref(),
                tenant=tenant,
                plan=plan,
                status=data.get("status", TenantSubscription.STATUS_TRIAL),
                started_at=timezone.localdate(),
                expires_at=expires,
                billing_period_days=int(data.get("billing_period_days", 30)),
                warning_days=int(data.get("warning_days", 5)),
                grace_period_days=int(data.get("grace_period_days", 5)),
                created_by=user,
            )

        if owner_user and created_sub and not created_sub.contact_user_id:
            created_sub.contact_user = owner_user
            created_sub.save(update_fields=["contact_user", "updated_at"])

        from apps.platform.services.entitlement_service import EntitlementService

        EntitlementService.apply_plan_entitlements(tenant=tenant, user=user)

        return tenant, owner_user

    @staticmethod
    def plan_payload(plan: SubscriptionPlan) -> dict:
        from apps.platform.services.entitlement_service import EntitlementService

        EntitlementService.ensure_default_plan_modules()
        return {
            "code": plan.code,
            "name": plan.name,
            "monthly_price": float(plan.monthly_price),
            "max_users": plan.max_users,
            "max_branches": plan.max_branches,
            "description": plan.description,
            "is_active": plan.is_active,
            "modules": sorted(EntitlementService.plan_module_codes(plan=plan)),
        }

    @staticmethod
    def create_plan(*, data: dict, user=None) -> SubscriptionPlan:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Plan name is required.")
        code = (data.get("code") or slugify(name) or "plan")[:50]
        if SubscriptionPlan.objects.filter(code=code, deleted_at__isnull=True).exists():
            raise ValueError(f"Plan code '{code}' already exists.")
        return SubscriptionPlan.objects.create(
            code=code,
            name=name,
            monthly_price=data.get("monthly_price", 0),
            max_users=int(data.get("max_users", 10)),
            max_branches=int(data.get("max_branches", 3)),
            description=data.get("description", ""),
            is_active=True,
            created_by=user,
        )

    # ── Subscription payment (Waafi / EVC) ──────────────────────────────

    @staticmethod
    def get_subscription_payment_config() -> dict:
        row = SettingsService.get_by_key(key=SUBSCRIPTION_PAYMENT_KEY)
        raw = row.value if row else None
        cfg = dict(DEFAULT_SUBSCRIPTION_PAYMENT)
        if isinstance(raw, dict):
            cfg.update({k: v for k, v in raw.items() if v is not None})
        elif isinstance(raw, str) and raw.strip():
            import json

            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    cfg.update({k: v for k, v in parsed.items() if v is not None})
            except (json.JSONDecodeError, TypeError):
                pass
        if not isinstance(cfg.get("instructions"), list):
            cfg["instructions"] = list(DEFAULT_SUBSCRIPTION_PAYMENT["instructions"])
        return cfg

    @staticmethod
    def ensure_subscription_payment_assets() -> dict:
        """Copy bundled merchant QR/placard into MEDIA and seed payment settings."""
        from pathlib import Path
        from shutil import copy2

        from django.conf import settings

        assets = Path(__file__).resolve().parents[1] / "assets"
        media_root = Path(settings.MEDIA_ROOT)
        dest_dir = media_root / "subscription_qr"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for name in ("merchant-608833.png", "merchant-payment-placard.png"):
            src = assets / name
            if src.is_file():
                copy2(src, dest_dir / name)

        cfg = PlatformService.get_subscription_payment_config()
        changed = False
        if not (cfg.get("qr_image_url") or "").strip():
            cfg["qr_image_url"] = "/media/subscription_qr/merchant-payment-placard.png"
            changed = True
        # Prefer dialable USSD QR with plan amount
        if (cfg.get("qr_payload_template") or "").strip() in ("", "{merchant}"):
            cfg["qr_payload_template"] = DEFAULT_SUBSCRIPTION_PAYMENT["qr_payload_template"]
            changed = True
        if not (cfg.get("ussd_template") or "").strip():
            cfg["ussd_template"] = DEFAULT_SUBSCRIPTION_PAYMENT["ussd_template"]
            changed = True
        if not (cfg.get("merchant_number") or "").strip():
            cfg["merchant_number"] = DEFAULT_SUBSCRIPTION_PAYMENT["merchant_number"]
            changed = True
        if not (cfg.get("instructions") or []):
            cfg["instructions"] = list(DEFAULT_SUBSCRIPTION_PAYMENT["instructions"])
            changed = True
        # Migrate old "scan then enter amount" copy to dial instructions
        old_steps = [
            "Start WAAFI app / Fur Waafi App",
            "Tap on Scan QR icon / Ku Sawir QR-ka",
            "Enter amount to Pay / Gali lacagta kadibna dir",
        ]
        if cfg.get("instructions") == old_steps:
            cfg["instructions"] = list(DEFAULT_SUBSCRIPTION_PAYMENT["instructions"])
            changed = True
        if changed:
            SettingsService.upsert(
                key=SUBSCRIPTION_PAYMENT_KEY,
                value=cfg,
                category="platform",
            )
        return cfg

    @staticmethod
    @transaction.atomic
    def save_subscription_payment_config(*, data: dict, user=None) -> dict:
        cfg = PlatformService.get_subscription_payment_config()
        for key in DEFAULT_SUBSCRIPTION_PAYMENT:
            if key in data:
                cfg[key] = data[key]
        if "instructions" in data:
            instructions = data["instructions"]
            if isinstance(instructions, str):
                instructions = [line.strip() for line in instructions.splitlines() if line.strip()]
            cfg["instructions"] = instructions or list(DEFAULT_SUBSCRIPTION_PAYMENT["instructions"])
        cfg["merchant_number"] = str(cfg.get("merchant_number") or "").strip()
        cfg["company_name"] = str(cfg.get("company_name") or "").strip()
        cfg["auto_renew_enabled"] = bool(cfg.get("auto_renew_enabled", True))
        SettingsService.upsert(
            key=SUBSCRIPTION_PAYMENT_KEY,
            value=cfg,
            category="platform",
            user=user,
        )
        return cfg

    @staticmethod
    def _format_payment_template(template: str, *, merchant: str, amount, reference: str) -> str:
        amount_str = f"{float(amount):.0f}" if float(amount) == int(float(amount)) else f"{float(amount):.2f}"
        try:
            return template.format(merchant=merchant, amount=amount_str, reference=reference)
        except (KeyError, ValueError):
            return (
                template.replace("{merchant}", merchant)
                .replace("{amount}", amount_str)
                .replace("{reference}", reference)
            )

    @staticmethod
    def ussd_to_dial_qr_payload(ussd: str) -> str:
        """Encode USSD so scanning the QR opens the phone dialer (auto-dials on most phones)."""
        code = (ussd or "").strip()
        if not code:
            return ""
        if code.lower().startswith("tel:"):
            return code
        if code.endswith("#"):
            return f"tel:{code[:-1]}%23"
        return f"tel:{code}"

    @staticmethod
    def ensure_pending_payment(*, subscription: TenantSubscription, user=None) -> SubscriptionPayment:
        cfg = PlatformService.get_subscription_payment_config()
        period_key = subscription.payment_period_key()
        amount = subscription.effective_monthly_fee
        merchant = cfg.get("merchant_number") or ""
        existing = (
            SubscriptionPayment.active_objects()
            .filter(
                subscription=subscription,
                period_key=period_key,
                status=SubscriptionPayment.STATUS_PENDING,
            )
            .order_by("-created_at")
            .first()
        )
        if existing:
            # Keep pending row in sync with current plan fee / merchant
            updates = []
            if existing.amount != amount:
                existing.amount = amount
                updates.append("amount")
            if merchant and existing.merchant_number != merchant:
                existing.merchant_number = merchant
                updates.append("merchant_number")
            if updates:
                existing.updated_by = user
                updates.extend(["updated_at", "updated_by"])
                existing.save(update_fields=updates)
            return existing

        reference = f"{subscription.reference_code}-{period_key.replace('-', '')}"
        # Keep reference unique if recreated after expiry of old pending
        base_ref = reference[:60]
        reference = base_ref
        n = 1
        while SubscriptionPayment.objects.filter(payment_reference=reference).exists():
            reference = f"{base_ref}-{n}"[:64]
            n += 1

        return SubscriptionPayment.objects.create(
            subscription=subscription,
            payment_reference=reference,
            amount=amount,
            merchant_number=merchant,
            period_key=period_key,
            status=SubscriptionPayment.STATUS_PENDING,
            created_by=user,
        )

    @staticmethod
    def payment_instructions_for_subscription(subscription: TenantSubscription, *, user=None) -> dict:
        cfg = PlatformService.get_subscription_payment_config()
        payment = PlatformService.ensure_pending_payment(subscription=subscription, user=user)
        merchant = payment.merchant_number or cfg.get("merchant_number") or ""
        amount = payment.amount
        reference = payment.payment_reference
        ussd = PlatformService._format_payment_template(
            cfg.get("ussd_template") or DEFAULT_SUBSCRIPTION_PAYMENT["ussd_template"],
            merchant=merchant,
            amount=amount,
            reference=reference,
        )
        # Prefer dialable USSD QR (plan amount) so scan → phone dialer opens *789*merchant*amount#
        qr_template = (cfg.get("qr_payload_template") or "").strip()
        if qr_template and "{amount}" in qr_template:
            qr_payload = PlatformService._format_payment_template(
                qr_template,
                merchant=merchant,
                amount=amount,
                reference=reference,
            )
            if not qr_payload.lower().startswith("tel:"):
                qr_payload = PlatformService.ussd_to_dial_qr_payload(qr_payload)
        else:
            qr_payload = PlatformService.ussd_to_dial_qr_payload(ussd)
        title_override = (cfg.get("dialog_title_override") or "").strip()
        message_override = (cfg.get("dialog_message_override") or "").strip()
        return {
            "payment_id": str(payment.id),
            "payment_reference": reference,
            "payment_status": payment.status,
            "amount": float(amount),
            "merchant_number": merchant,
            "company_name": cfg.get("company_name") or "",
            "provider_label": cfg.get("provider_label") or "Waafi / EVC Plus",
            "ussd_code": ussd,
            "qr_payload": qr_payload,
            # Dynamic dial QR is authoritative; static placard image is optional branding only
            "qr_image_url": "",
            "qr_branding_image_url": cfg.get("qr_image_url") or "",
            "instructions_title": cfg.get("instructions_title") or "",
            "instructions": cfg.get("instructions") or [],
            "contact_phone": cfg.get("contact_phone") or "",
            "auto_renew_enabled": bool(cfg.get("auto_renew_enabled", True)),
            "dialog_title_override": title_override,
            "dialog_message_override": message_override,
        }

    @staticmethod
    def enrich_alert_payload(subscription: TenantSubscription, *, user=None) -> dict:
        payload = subscription.alert_payload()
        payment = PlatformService.payment_instructions_for_subscription(subscription, user=user)
        if payment.get("dialog_title_override"):
            payload["title"] = payment["dialog_title_override"]
        if payment.get("dialog_message_override"):
            try:
                payload["message"] = payment["dialog_message_override"].format(**subscription.alert_context())
            except (KeyError, ValueError):
                payload["message"] = payment["dialog_message_override"]
        payload["payment"] = payment
        return payload

    @staticmethod
    def serialize_payment(payment: SubscriptionPayment) -> dict:
        return {
            "id": str(payment.id),
            "subscription_id": str(payment.subscription_id),
            "payment_reference": payment.payment_reference,
            "amount": float(payment.amount),
            "merchant_number": payment.merchant_number,
            "payer_phone": payment.payer_phone,
            "external_transaction_id": payment.external_transaction_id,
            "status": payment.status,
            "period_key": payment.period_key,
            "confirmed_at": payment.confirmed_at.isoformat() if payment.confirmed_at else None,
            "auto_renewed": payment.auto_renewed,
            "notes": payment.notes,
            "tenant_name": payment.subscription.tenant.name if payment.subscription.tenant_id else None,
            "reference_code": payment.subscription.reference_code,
        }

    @staticmethod
    @transaction.atomic
    def report_subscription_payment(
        *,
        subscription: TenantSubscription,
        payer_phone: str = "",
        notes: str = "",
        user=None,
    ) -> SubscriptionPayment:
        payment = PlatformService.ensure_pending_payment(subscription=subscription, user=user)
        if payment.status == SubscriptionPayment.STATUS_CONFIRMED:
            return payment
        payment.payer_phone = (payer_phone or "").strip()
        if notes:
            payment.notes = notes
        payment.reported_by = user
        payment.updated_by = user
        payment.save()
        return payment

    @staticmethod
    @transaction.atomic
    def confirm_subscription_payment(
        *,
        payment: SubscriptionPayment,
        external_transaction_id: str = "",
        payer_phone: str = "",
        notes: str = "",
        user=None,
        auto: bool = False,
    ) -> SubscriptionPayment:
        if payment.status == SubscriptionPayment.STATUS_CONFIRMED:
            return payment

        cfg = PlatformService.get_subscription_payment_config()
        payment.status = SubscriptionPayment.STATUS_CONFIRMED
        payment.confirmed_at = timezone.now()
        if external_transaction_id:
            payment.external_transaction_id = external_transaction_id.strip()
        if payer_phone:
            payment.payer_phone = payer_phone.strip()
        if notes:
            payment.notes = ((payment.notes + "\n") if payment.notes else "") + notes
        payment.updated_by = user
        payment.save()

        if cfg.get("auto_renew_enabled", True) and not payment.auto_renewed:
            PlatformService.renew_subscription(
                subscription=payment.subscription,
                user=user,
                notes=f"Auto-renewed via payment {payment.payment_reference}",
            )
            payment.auto_renewed = True
            payment.save(update_fields=["auto_renewed", "updated_at"])

        return payment

    @staticmethod
    @transaction.atomic
    def process_waafi_callback(*, data: dict) -> SubscriptionPayment:
        """Match an incoming Waafi/EVC payment notification and auto-renew."""
        reference = (
            str(data.get("reference") or data.get("payment_reference") or data.get("desc") or "")
            .strip()
        )
        transaction_id = str(
            data.get("transaction_id") or data.get("trx_id") or data.get("id") or ""
        ).strip()
        payer_phone = str(data.get("payer_phone") or data.get("phone") or data.get("msisdn") or "").strip()
        amount_raw = data.get("amount") or data.get("paid_amount")
        merchant = str(data.get("merchant_number") or data.get("merchant") or "").strip()

        payment = None
        if reference:
            payment = SubscriptionPayment.active_objects().filter(payment_reference__iexact=reference).first()
            if not payment:
                payment = (
                    SubscriptionPayment.active_objects()
                    .filter(payment_reference__icontains=reference, status=SubscriptionPayment.STATUS_PENDING)
                    .order_by("-created_at")
                    .first()
                )
        if not payment and transaction_id:
            payment = SubscriptionPayment.active_objects().filter(
                external_transaction_id=transaction_id
            ).first()

        if not payment and amount_raw is not None and merchant:
            from decimal import Decimal

            amount = Decimal(str(amount_raw))
            payment = (
                SubscriptionPayment.active_objects()
                .filter(
                    status=SubscriptionPayment.STATUS_PENDING,
                    merchant_number=merchant,
                    amount=amount,
                )
                .order_by("-created_at")
                .first()
            )

        if not payment:
            raise ValueError("No matching pending subscription payment found.")

        return PlatformService.confirm_subscription_payment(
            payment=payment,
            external_transaction_id=transaction_id,
            payer_phone=payer_phone,
            notes="Confirmed via Waafi/EVC callback",
            auto=True,
        )

    @staticmethod
    def list_pending_payments(*, user=None, limit=50):
        qs = (
            SubscriptionPayment.active_objects()
            .select_related("subscription", "subscription__tenant", "subscription__plan")
            .filter(status=SubscriptionPayment.STATUS_PENDING)
            .order_by("-created_at")
        )
        if user is not None:
            ids = PlatformService.accessible_tenant_ids(user)
            qs = qs.filter(subscription__tenant_id__in=ids)
        return [PlatformService.serialize_payment(p) for p in qs[:limit]]


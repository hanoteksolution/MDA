import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.platform.models import SubscriptionPlan, ShopGroup, Tenant, TenantSubscription
from apps.platform.services.sync_service import CloudShopSyncService
from apps.settings_app.models import Branch, Company
from apps.authentication.models import Role, User
from apps.inventory.models import Warehouse
from core.services.analytics_service import AnalyticsService


def _unique_slug(base: str) -> str:
    slug = slugify(base) or "shop"
    slug = slug[:90]
    candidate = slug
    n = 1
    while Tenant.objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


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
    def is_platform_superuser(user) -> bool:
        return bool(
            user.is_platform_admin
            or user.is_superuser
            or (user.role and user.role.slug in ("super_admin", "platform_admin"))
            or user.has_permission("platform.manage")
        )

    @staticmethod
    def accessible_tenant_ids(user) -> list:
        if PlatformService.is_platform_superuser(user):
            return list(
                Tenant.objects.filter(deleted_at__isnull=True).values_list("id", flat=True)
            )
        if user.managed_shop_group_id:
            return list(
                Tenant.objects.filter(
                    shop_group_id=user.managed_shop_group_id,
                    deleted_at__isnull=True,
                ).values_list("id", flat=True)
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
        qs = Tenant.objects.filter(id__in=ids).select_related(
            "subscription__plan", "shop_group"
        ).prefetch_related("companies")
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    @staticmethod
    def shop_group_payload(group: ShopGroup) -> dict:
        tenant_count = group.tenants.filter(deleted_at__isnull=True).count()
        return {
            "id": str(group.id),
            "name": group.name,
            "slug": group.slug,
            "contact_email": group.contact_email,
            "contact_phone": group.contact_phone,
            "is_active": group.is_active,
            "tenant_count": tenant_count,
        }

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
        plan = SubscriptionPlan.objects.get(code=plan_code)
        tenant = Tenant.objects.create(
            name=company.name,
            slug=_unique_slug(company.name),
            contact_email=contact_email or company.email,
            contact_phone=company.phone,
            sync_secret=secrets.token_urlsafe(24),
            is_active=True,
        )
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
        qs = Tenant.objects.select_related("subscription__plan").prefetch_related("companies")
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    @staticmethod
    def list_subscriptions(*, unassigned_only=False):
        qs = TenantSubscription.objects.select_related("plan", "tenant", "contact_user")
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
        company = tenant.companies.filter(deleted_at__isnull=True).first()
        branch = None
        if company:
            branch = Branch.active_objects().filter(company=company, is_default=True).first()
            if not branch:
                branch = Branch.active_objects().filter(company=company).first()
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
        return {
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "sync_secret": tenant.sync_secret,
                "is_active": tenant.is_active,
                "contact_email": tenant.contact_email,
                "contact_phone": tenant.contact_phone,
                "country": tenant.country,
                "last_synced_at": snap.synced_at.isoformat() if snap else None,
                "shop_group_id": str(group.id) if group else None,
                "shop_group_name": group.name if group else None,
            },
            "subscription": PlatformService._subscription_payload(tenant),
            "company": {"id": str(company.id), "name": company.name} if company else None,
            "kpis": kpis,
            "staff_performance": staff[:5],
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
        if "is_active" in data:
            tenant.is_active = bool(data["is_active"])
        if "shop_group_id" in data:
            gid = data.get("shop_group_id")
            tenant.shop_group = ShopGroup.objects.get(pk=gid) if gid else None
        tenant.updated_by = user
        tenant.save()

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
    def list_payment_alerts():
        alerts = []
        for sub in TenantSubscription.objects.select_related("plan", "tenant").filter(tenant__isnull=False):
            if sub.needs_payment_alert:
                alerts.append(sub.alert_payload())
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
        return sub.alert_payload()

    @staticmethod
    def _shop_owner_role_slugs():
        return {"admin", "branch_manager", "accountant", "inventory_manager", "futsal_manager"}

    @staticmethod
    def create_shop_owner(
        *,
        tenant: Tenant,
        branch: Branch,
        owner: dict,
        shop_group: ShopGroup | None = None,
        as_group_manager: bool = False,
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
        if data.get("shop_group_id"):
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

        tenant = Tenant.objects.create(
            name=data["name"],
            slug=_unique_slug(data["name"]),
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            country=data.get("country", ""),
            sync_secret=secrets.token_urlsafe(24),
            is_active=True,
            shop_group=shop_group,
            created_by=user,
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
            created_by=user,
        )
        Warehouse.objects.create(
            branch=branch,
            code="WH01",
            name="Main Warehouse",
            is_default=True,
            is_active=True,
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

        return tenant, owner_user

    @staticmethod
    def plan_payload(plan: SubscriptionPlan) -> dict:
        return {
            "code": plan.code,
            "name": plan.name,
            "monthly_price": float(plan.monthly_price),
            "max_users": plan.max_users,
            "max_branches": plan.max_branches,
            "description": plan.description,
            "is_active": plan.is_active,
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

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.platform.models import (
    Module,
    SubscriptionPayment,
    SubscriptionPlan,
    Tenant,
    TenantDomain,
    TenantModule,
    TenantSubscription,
)
from apps.platform.services.domain_utils import (
    RESERVED_TENANT_SLUGS,
    get_tenant_base_domain,
    validate_tenant_slug,
)
from apps.platform.services.platform_service import PlatformService
from apps.platform.services.module_feature_service import (
    ModuleFeatureError,
    ModuleFeatureService,
)
from apps.platform.services.module_service import (
    ModuleDependencyError,
    ensure_default_modules,
    module_payload,
    sync_tenant_modules,
    tenant_module_payload,
)
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantError, DemoTenantService
from apps.platform.services.tenant_resolver import (
    normalize_hostname,
    resolution_public_payload,
    resolve_tenant_from_hostname,
)
from core.responses.api_response import error_response, success_response
from core.utils.media import save_subscription_qr
from permissions.base import HasPermission


def _platform_user(user):
    return user.is_platform_admin or user.has_permission("platform.view")


def _platform_manage(user):
    return PlatformService.can_manage_shops(user)


def _platform_global(user):
    return PlatformService.is_global_platform_admin(user)


def _subscriptions_user(user):
    return user.is_platform_admin or user.has_permission("subscriptions.manage")


class PlatformTenantListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenants = PlatformService.list_tenants_for_user(request.user)
        data = []
        for tenant in tenants:
            overview = PlatformService.tenant_overview(tenant, period=request.query_params.get("period", "month"))
            data.append({
                **overview["tenant"],
                "subscription": overview["subscription"],
                "kpis": overview["kpis"],
            })
        return success_response(data=data)

    def post(self, request):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        required = ["name"]
        if not all(request.data.get(k) for k in required):
            return error_response(message="Shop name is required.", status=status.HTTP_400_BAD_REQUEST)
        owner = request.data.get("owner")
        if not isinstance(owner, dict) or not str(owner.get("username") or "").strip():
            return error_response(
                message="Shop owner account is required (username and password).",
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tenant, owner_user = PlatformService.create_shop(data=request.data, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        overview = PlatformService.tenant_overview(tenant)
        if owner_user:
            overview["owner"] = PlatformService.owner_payload(owner_user)
        return success_response(data=overview, message="Shop created.", status=status.HTTP_201_CREATED)


class PlatformTenantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.get(pk=pk)
        if not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        period = request.query_params.get("period", "month")
        return success_response(data=PlatformService.tenant_overview(tenant, period=period))

    def put(self, request, pk):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.get(pk=pk)
        if not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            PlatformService.update_shop(tenant=tenant, data=request.data, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        period = request.query_params.get("period", "month")
        return success_response(
            data=PlatformService.tenant_overview(tenant, period=period),
            message="Shop updated.",
        )

    def delete(self, request, pk):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant:
            return error_response(message="Shop not found.", status=status.HTTP_404_NOT_FOUND)
        if not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        PlatformService.delete_shop(tenant=tenant, user=request.user)
        return success_response(data=None, message="Shop deleted.")


class PlatformTenantUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.get(pk=pk)
        if not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        users = PlatformService.list_tenant_users(tenant)
        data = [
            {
                "id": str(u.id),
                "username": u.username,
                "full_name": u.get_full_name() or u.username,
                "email": u.email,
                "role": u.role.name if u.role_id else None,
            }
            for u in users
        ]
        return success_response(data=data)

    def post(self, request, pk):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            tenant = Tenant.objects.get(pk=pk, deleted_at__isnull=True)
        except Tenant.DoesNotExist:
            return error_response(message="Shop not found.", status=status.HTTP_404_NOT_FOUND)
        if not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            user = PlatformService.create_tenant_user(
                tenant=tenant,
                data=request.data,
                created_by=request.user,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PlatformService.owner_payload(user),
            message="User created. They can sign in on the desktop app with this username and password.",
            status=status.HTTP_201_CREATED,
        )


class PlatformBusinessTypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        rows = PlatformService.list_business_types()
        return success_response(
            data={
                "items": [PlatformService.business_type_payload(bt) for bt in rows],
                "base_domain": get_tenant_base_domain(),
                "reserved_slugs": sorted(RESERVED_TENANT_SLUGS),
            }
        )


class PlatformModulesCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        ensure_default_modules()
        rows = Module.active_objects().filter(is_active=True).order_by("sort_order", "name")
        return success_response(data={"items": [module_payload(m) for m in rows]})


class PlatformTenantModulesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant or not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        sync_tenant_modules(tenant=tenant, user=request.user)
        links = (
            TenantModule.active_objects()
            .filter(tenant=tenant)
            .select_related("module")
            .order_by("module__sort_order", "module__code")
        )
        return success_response(
            data={
                "items": [tenant_module_payload(link) for link in links],
                "enabled": [link.module.code for link in links if link.enabled],
            }
        )

    def put(self, request, pk):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant or not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        enabled = request.data.get("enabled_modules")
        if enabled is None:
            enabled = request.data.get("enabled")
        if not isinstance(enabled, list):
            return error_response(
                message="enabled_modules must be a list of module codes.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sync_tenant_modules(
                tenant=tenant,
                enabled_codes=enabled,
                user=request.user,
                disable_missing=True,
                validate_dependencies=True,
            )
            module_features = request.data.get("module_features") or request.data.get(
                "features"
            )
            if isinstance(module_features, dict):
                for code, fmap in module_features.items():
                    if not isinstance(fmap, dict):
                        continue
                    ModuleFeatureService.set_features(
                        tenant=tenant,
                        module_code=str(code),
                        features=fmap,
                        user=request.user,
                    )
        except ModuleDependencyError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_400_BAD_REQUEST,
                errors={"code": exc.code, "missing": exc.missing},
            )
        except ModuleFeatureError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_400_BAD_REQUEST,
                code=exc.code,
            )
        links = (
            TenantModule.active_objects()
            .filter(tenant=tenant)
            .select_related("module")
            .order_by("module__sort_order", "module__code")
        )
        return success_response(
            data={
                "items": [tenant_module_payload(link) for link in links],
                "enabled": [link.module.code for link in links if link.enabled],
            },
            message="Modules updated.",
        )


class PlatformBusinessPresetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        bt = request.query_params.get("business_type") or None
        rows = BusinessPresetService.list_presets(business_type_code=bt)
        return success_response(
            data={"items": [BusinessPresetService.serialize(p) for p in rows]}
        )


class PlatformDemoTenantListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        status_filter = request.query_params.get("status") or None
        DemoTenantService.expire_due()
        rows = DemoTenantService.list_demos(status=status_filter)
        return success_response(data={"items": [DemoTenantService.serialize(t) for t in rows]})

    def post(self, request):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            tenant, seed_report = DemoTenantService.create(data=request.data or {}, user=request.user)
        except DemoTenantError as exc:
            return error_response(message=exc.message, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data={**DemoTenantService.serialize(tenant), "seed_report": seed_report},
            message="Demo tenant created.",
            status=status.HTTP_201_CREATED,
        )


class PlatformDemoTenantActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True, is_demo=True).first()
        if not tenant:
            return error_response(message="Demo tenant not found.", status=status.HTTP_404_NOT_FOUND)
        try:
            if action == "extend":
                days = int((request.data or {}).get("days") or 14)
                tenant = DemoTenantService.extend(tenant=tenant, days=days, user=request.user)
            elif action == "suspend":
                tenant = DemoTenantService.suspend(tenant=tenant, user=request.user)
            elif action == "expire":
                tenant = DemoTenantService.expire(tenant=tenant, user=request.user)
            elif action == "convert":
                plan_code = (request.data or {}).get("plan_code")
                tenant = DemoTenantService.convert(
                    tenant=tenant, plan_code=plan_code, user=request.user
                )
            else:
                return error_response(message="Unknown action.", status=status.HTTP_404_NOT_FOUND)
        except DemoTenantError as exc:
            return error_response(message=exc.message, status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=DemoTenantService.serialize(tenant),
            message=f"Demo {action} complete.",
        )


class PlatformTenantSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant or not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        settings_row, _ = PlatformService.provision_tenant_defaults(tenant=tenant)
        return success_response(data=PlatformService.settings_payload(settings_row))

    def put(self, request, pk):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant or not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = PlatformService.update_tenant_settings(
                tenant=tenant, data=request.data, user=request.user
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=PlatformService.settings_payload(row), message="Settings updated.")


class PlatformTenantDomainsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant or not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        PlatformService.provision_tenant_defaults(tenant=tenant)
        domains = TenantDomain.active_objects().filter(tenant=tenant).order_by("-is_primary", "domain")
        return success_response(
            data={
                "base_domain": get_tenant_base_domain(),
                "items": [PlatformService.domain_payload(d) for d in domains],
            }
        )

    def post(self, request, pk):
        if not _platform_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not tenant or not PlatformService.user_can_access_tenant(request.user, tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            domain = PlatformService.add_tenant_domain(
                tenant=tenant, data=request.data, user=request.user
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PlatformService.domain_payload(domain),
            message="Domain added.",
            status=status.HTTP_201_CREATED,
        )


class PlatformSlugCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        raw = (request.query_params.get("slug") or request.query_params.get("subdomain") or "").strip()
        try:
            slug = validate_tenant_slug(raw)
        except ValueError as exc:
            return success_response(
                data={
                    "slug": raw,
                    "available": False,
                    "reason": str(exc),
                    "hostname": None,
                }
            )
        taken = Tenant.objects.filter(slug=slug, deleted_at__isnull=True).exists()
        return success_response(
            data={
                "slug": slug,
                "available": not taken,
                "reason": "already taken" if taken else "",
                "hostname": f"{slug}.{get_tenant_base_domain()}",
            }
        )


class PlatformResolveHostView(APIView):
    """Public host → tenant branding resolution (no secrets)."""

    permission_classes = [AllowAny]

    def get(self, request):
        explicit = (request.query_params.get("host") or "").strip()
        hostname = normalize_hostname(
            explicit
            or request.META.get("HTTP_X_FORWARDED_HOST")
            or request.META.get("HTTP_HOST")
        )
        # Prefer middleware resolution when host matches request host
        resolution = getattr(request, "tenant_resolution", None)
        if explicit or resolution is None or normalize_hostname(resolution.hostname) != hostname:
            resolution = resolve_tenant_from_hostname(hostname)
        return success_response(data=resolution_public_payload(resolution))


class PlatformSubscriptionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        unassigned_only = request.query_params.get("unassigned") == "1"
        # Only global platform admins may list unassigned licenses.
        if unassigned_only and not _platform_global(request.user):
            unassigned_only = False
        subs = PlatformService.list_subscriptions(
            unassigned_only=unassigned_only,
            user=request.user,
        )
        return success_response(
            data=[PlatformService.subscription_payload(s) for s in subs]
        )

    def post(self, request):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        if not request.data.get("plan_code"):
            return error_response(message="Plan is required.", status=status.HTTP_400_BAD_REQUEST)
        sub = PlatformService.create_subscription(data=request.data, user=request.user)
        return success_response(
            data=PlatformService.subscription_payload(sub),
            message="Subscription created.",
            status=status.HTTP_201_CREATED,
        )


class PlatformSubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        sub = TenantSubscription.objects.select_related("plan", "tenant", "contact_user").get(pk=pk)
        return success_response(data=PlatformService.subscription_payload(sub))

    def put(self, request, pk):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        sub = TenantSubscription.objects.select_related("plan", "tenant", "contact_user").get(pk=pk)
        try:
            PlatformService.update_subscription_record(
                subscription=sub, data=request.data, user=request.user
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        sub.refresh_from_db()
        return success_response(
            data=PlatformService.subscription_payload(sub),
            message="Subscription updated.",
        )

    def delete(self, request, pk):
        if not (_subscriptions_user(request.user) or _platform_global(request.user) or _platform_manage(request.user)):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        sub = TenantSubscription.objects.filter(pk=pk, deleted_at__isnull=True).select_related("tenant").first()
        if not sub:
            return error_response(message="Subscription not found.", status=status.HTTP_404_NOT_FOUND)
        if sub.tenant_id and not PlatformService.user_can_access_tenant(request.user, sub.tenant):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        if not sub.tenant_id and not _platform_global(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        PlatformService.delete_subscription(subscription=sub, user=request.user)
        return success_response(data=None, message="Subscription deleted.")


class PlatformSubscriptionUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant = Tenant.objects.get(pk=pk)
        if not hasattr(tenant, "subscription") or not tenant.subscription:
            return error_response(message="Shop has no subscription.", status=status.HTTP_404_NOT_FOUND)
        PlatformService.update_subscription(tenant=tenant, data=request.data, user=request.user)
        return success_response(
            data=PlatformService.tenant_overview(tenant),
            message="Subscription updated.",
        )


class PlatformSubscriptionAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        tenant_id = request.data.get("tenant_id")
        if not tenant_id:
            return error_response(message="Shop is required.", status=status.HTTP_400_BAD_REQUEST)
        sub = TenantSubscription.objects.get(pk=pk)
        tenant = Tenant.objects.get(pk=tenant_id)
        try:
            PlatformService.assign_subscription(subscription=sub, tenant=tenant, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PlatformService.subscription_payload(sub),
            message="Subscription assigned to shop.",
        )


class PlatformSubscriptionRenewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        sub = TenantSubscription.objects.get(pk=pk)
        PlatformService.renew_subscription(
            subscription=sub,
            user=request.user,
            notes=request.data.get("notes", ""),
        )
        return success_response(
            data=PlatformService.subscription_payload(sub),
            message="Subscription renewed.",
        )


class PlatformSubscriptionAlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        return success_response(data=PlatformService.list_payment_alerts(user=request.user))


class PlatformMySubscriptionAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        alert = PlatformService.user_subscription_alert(request.user)
        return success_response(data=alert)


class PlatformEntitlementsView(APIView):
    """Current tenant plan limits, modules, and subscription phase."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.platform.services.entitlement_service import EntitlementService

        tenant = PlatformService.resolve_user_tenant(request.user)
        payload = EntitlementService.evaluate(tenant=tenant)
        if tenant and payload.get("has_subscription"):
            sub = EntitlementService.get_subscription(tenant)
            if sub and (sub.needs_payment_alert or not sub.is_usable):
                payload["alert"] = PlatformService.enrich_alert_payload(sub, user=request.user)
        return success_response(data=payload)


class PlatformPlansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        plans = SubscriptionPlan.objects.filter(is_active=True, deleted_at__isnull=True)
        return success_response(data=[PlatformService.plan_payload(p) for p in plans])

    def post(self, request):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            plan = PlatformService.create_plan(data=request.data, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PlatformService.plan_payload(plan),
            message="Plan created.",
            status=status.HTTP_201_CREATED,
        )


class PlatformShopGroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        if _platform_global(request.user):
            groups = PlatformService.list_shop_groups()
        elif request.user.managed_shop_group_id:
            groups = PlatformService.list_shop_groups().filter(pk=request.user.managed_shop_group_id)
        elif _platform_manage(request.user):
            groups = PlatformService.list_shop_groups()
        else:
            groups = PlatformService.list_shop_groups().none()
        period = request.query_params.get("period", "month")
        enrich = request.query_params.get("enrich") in ("1", "true", "yes")
        data = []
        for g in groups:
            if enrich:
                data.append(PlatformService.shop_group_overview(g, period=period))
            else:
                data.append(PlatformService.shop_group_payload(g))
        return success_response(data=data)

    def post(self, request):
        if not _platform_global(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            group = PlatformService.create_shop_group(data=request.data, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PlatformService.shop_group_payload(group),
            message="Shop group created.",
            status=status.HTTP_201_CREATED,
        )


class PlatformShopGroupDetailView(APIView):
    """Tenant (org) profile — shops, managers, aggregate KPIs."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        from apps.platform.models import ShopGroup

        group = ShopGroup.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not group:
            return error_response(message="Tenant not found.", status=status.HTTP_404_NOT_FOUND)
        if not PlatformService.user_can_access_shop_group(request.user, group):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        period = request.query_params.get("period", "month")
        return success_response(data=PlatformService.shop_group_overview(group, period=period))


class PlatformSubscriptionPaymentConfigView(APIView):
    """Get/update Waafi merchant QR + payment instructions shown on expiry alerts."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        return success_response(data=PlatformService.get_subscription_payment_config())

    def put(self, request):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        cfg = PlatformService.save_subscription_payment_config(data=request.data, user=request.user)
        return success_response(data=cfg, message="Subscription payment settings saved.")


class PlatformSubscriptionQrUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        uploaded = request.FILES.get("image")
        if not uploaded:
            return error_response(message="No image file provided.", status=status.HTTP_400_BAD_REQUEST)
        try:
            url = save_subscription_qr(uploaded_file=uploaded)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        cfg = PlatformService.save_subscription_payment_config(
            data={"qr_image_url": url},
            user=request.user,
        )
        return success_response(
            data={"url": url, "config": cfg},
            message="QR image uploaded.",
            status=status.HTTP_201_CREATED,
        )


class PlatformSubscriptionReportPaymentView(APIView):
    """Shop owner reports that they paid via Waafi/EVC — starts online tracking."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sub = TenantSubscription.objects.filter(pk=pk, deleted_at__isnull=True).select_related(
            "tenant", "plan"
        ).first()
        if not sub:
            return error_response(message="Subscription not found.", status=status.HTTP_404_NOT_FOUND)
        # Shop contact / tenant user / platform admin may report
        tenant = PlatformService.resolve_user_tenant(request.user)
        allowed = (
            _subscriptions_user(request.user)
            or (tenant and sub.tenant_id == tenant.id)
            or (sub.contact_user_id and sub.contact_user_id == request.user.id)
        )
        if not allowed:
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        payment = PlatformService.report_subscription_payment(
            subscription=sub,
            payer_phone=request.data.get("payer_phone", ""),
            notes=request.data.get("notes", "Reported by shop"),
            user=request.user,
        )
        return success_response(
            data={
                "payment": PlatformService.serialize_payment(payment),
                "alert": PlatformService.enrich_alert_payload(sub, user=request.user),
            },
            message="Payment reported. Waiting for confirmation.",
        )


class PlatformSubscriptionPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sub = TenantSubscription.objects.filter(pk=pk, deleted_at__isnull=True).select_related(
            "tenant", "plan"
        ).first()
        if not sub:
            return error_response(message="Subscription not found.", status=status.HTTP_404_NOT_FOUND)
        tenant = PlatformService.resolve_user_tenant(request.user)
        allowed = (
            _subscriptions_user(request.user)
            or (tenant and sub.tenant_id == tenant.id)
            or (sub.contact_user_id and sub.contact_user_id == request.user.id)
        )
        if not allowed:
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        payment = (
            SubscriptionPayment.active_objects()
            .filter(subscription=sub)
            .order_by("-created_at")
            .first()
        )
        return success_response(
            data={
                "payment": PlatformService.serialize_payment(payment) if payment else None,
                "subscription": PlatformService.subscription_payload(sub),
                "alert": PlatformService.enrich_alert_payload(sub, user=request.user)
                if sub.needs_payment_alert
                else None,
            }
        )


class PlatformSubscriptionConfirmPaymentView(APIView):
    """Admin manually confirms a pending Waafi/EVC payment → auto-renews."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        payment = SubscriptionPayment.active_objects().filter(pk=pk).select_related(
            "subscription", "subscription__plan", "subscription__tenant"
        ).first()
        if not payment:
            return error_response(message="Payment not found.", status=status.HTTP_404_NOT_FOUND)
        payment = PlatformService.confirm_subscription_payment(
            payment=payment,
            external_transaction_id=request.data.get("external_transaction_id", ""),
            payer_phone=request.data.get("payer_phone", ""),
            notes=request.data.get("notes", "Manually confirmed by admin"),
            user=request.user,
        )
        return success_response(
            data={
                "payment": PlatformService.serialize_payment(payment),
                "subscription": PlatformService.subscription_payload(payment.subscription),
            },
            message="Payment confirmed and subscription renewed.",
        )


class PlatformPendingPaymentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _subscriptions_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        return success_response(data=PlatformService.list_pending_payments(user=request.user))


class PlatformWaafiPaymentCallbackView(APIView):
    """Public webhook for Waafi/EVC payment notifications → auto-renew subscription."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            payment = PlatformService.process_waafi_callback(data=request.data)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_404_NOT_FOUND)
        return success_response(
            data=PlatformService.serialize_payment(payment),
            message="Payment confirmed.",
        )

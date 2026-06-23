from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.platform.models import SubscriptionPlan, Tenant, TenantSubscription
from apps.platform.services.platform_service import PlatformService
from core.responses.api_response import error_response, success_response


def _platform_user(user):
    return user.is_platform_admin or user.has_permission("platform.view")


def _platform_manage(user):
    return PlatformService.is_platform_superuser(user)


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
        if not (request.user.is_platform_admin or request.user.has_permission("platform.manage")):
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
        try:
            PlatformService.update_shop(tenant=tenant, data=request.data, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        period = request.query_params.get("period", "month")
        return success_response(
            data=PlatformService.tenant_overview(tenant, period=period),
            message="Shop updated.",
        )


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


class PlatformSubscriptionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _platform_user(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        unassigned_only = request.query_params.get("unassigned") == "1"
        subs = PlatformService.list_subscriptions(unassigned_only=unassigned_only)
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
        return success_response(data=PlatformService.list_payment_alerts())


class PlatformMySubscriptionAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        alert = PlatformService.user_subscription_alert(request.user)
        return success_response(data=alert)


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
        if _platform_manage(request.user):
            groups = PlatformService.list_shop_groups()
        elif request.user.managed_shop_group_id:
            groups = PlatformService.list_shop_groups().filter(pk=request.user.managed_shop_group_id)
        else:
            groups = PlatformService.list_shop_groups().none()
        return success_response(
            data=[PlatformService.shop_group_payload(g) for g in groups]
        )

    def post(self, request):
        if not _platform_manage(request.user):
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

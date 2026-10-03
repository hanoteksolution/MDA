"""Platform Admin → Billing API (``/api/v1/platform/billing/*``).

Elevated users only (Super Admin / Platform Admin). Tenant users — including tenant admins and
holders of ``platform.view`` or ``subscriptions.manage`` — get 403, so one tenant can never read
another tenant's billing. Responses carry no provider configuration or credentials.
"""

from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from apps.platform.models import Tenant, TenantSubscription
from apps.platform.services.platform_billing_service import (
    PlatformBillingError,
    PlatformBillingService,
    is_super_admin,
    subscription_row,
)
from apps.platform.services.platform_service import PlatformService
from core.responses.api_response import error_response, success_response


class IsPlatformBillingAdmin(BasePermission):
    message = "Platform billing is available to platform administrators only."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and PlatformService.is_global_platform_admin(user))


class _BillingView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformBillingAdmin]


class PlatformBillingOverviewView(_BillingView):
    def get(self, request):
        data = PlatformBillingService.overview()
        data["can_recover"] = is_super_admin(request.user)
        return success_response(data=data)


class PlatformBillingSubscriptionsView(_BillingView):
    def get(self, request):
        return success_response(data=PlatformBillingService.subscriptions(request.query_params))


class PlatformBillingPaymentsView(_BillingView):
    def get(self, request):
        return success_response(data=PlatformBillingService.payments(request.query_params))


class PlatformBillingInvoicesView(_BillingView):
    def get(self, request):
        return success_response(data=PlatformBillingService.invoices(request.query_params))


class PlatformBillingReconciliationView(_BillingView):
    def get(self, request):
        return success_response(data=PlatformBillingService.reconciliation(request.query_params))


class PlatformBillingPlansView(_BillingView):
    def get(self, request):
        return success_response(data=PlatformBillingService.plans())


class PlatformBillingTenantDetailView(_BillingView):
    def get(self, request, pk):
        tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).select_related("shop_group").first()
        if tenant is None:
            return error_response(message="Tenant not found.", status=status.HTTP_404_NOT_FOUND)
        data = PlatformBillingService.tenant_detail(tenant)
        data["can_recover"] = is_super_admin(request.user)
        return success_response(data=data)


class PlatformBillingRecoverView(_BillingView):
    """Exceptional Super Admin recovery. Never creates or confirms a payment."""

    def post(self, request, pk):
        if not is_super_admin(request.user):
            return error_response(message="Only a Super Admin can perform manual subscription recovery.",
                                  status=status.HTTP_403_FORBIDDEN)
        sub = TenantSubscription.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if sub is None:
            return error_response(message="Subscription not found.", status=status.HTTP_404_NOT_FOUND)
        try:
            sub = PlatformBillingService.recover(
                subscription=sub, reason=request.data.get("reason", ""),
                confirmed=request.data.get("confirm") is True, user=request.user, request=request,
            )
        except PlatformBillingError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=subscription_row(sub), message="Subscription recovered. No payment was recorded.")

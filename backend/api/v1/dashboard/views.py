from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses.api_response import success_response
from core.services.analytics_service import AnalyticsService
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


class DashboardKPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        period = request.query_params.get("period", "today")
        branch_id = getattr(request.user.branch, "id", None)
        return success_response(data=AnalyticsService.get_kpis(branch_id=branch_id, period=period))


class DashboardRecentSalesView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        data = AnalyticsService.get_recent_sales(branch_id=branch_id)
        return success_response(data={"results": data, "count": len(data)})


class DashboardLowStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        data = AnalyticsService.get_low_stock(branch_id=branch_id)
        return success_response(data={"results": data, "count": len(data)})


class DashboardTopProductsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        period = request.query_params.get("period", "month")
        data = AnalyticsService.get_top_products(branch_id=branch_id, period=period)
        return success_response(data=data)


class DashboardChartsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        return success_response(data=AnalyticsService.get_chart_data(branch_id=branch_id))


class DashboardWidgetsView(APIView):
    """PHASE 08 — module-gated widget registry (not BusinessType-driven)."""

    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        from apps.platform.services.dashboard_widget_service import DashboardWidgetService

        user = request.user
        role_slug = getattr(getattr(user, "role", None), "slug", None) or ""
        is_super_admin = bool(
            getattr(user, "is_platform_admin", False)
            or getattr(user, "is_superuser", False)
            or role_slug in ("super_admin", "platform_admin")
        )
        widgets = DashboardWidgetService.list_for_actor(
            user=user,
            request=request,
            tenant=getattr(user, "tenant", None),
            is_super_admin=is_super_admin,
        )
        return success_response(data={"results": widgets, "count": len(widgets)})


class DashboardAlertsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("dashboard.view")]

    def get(self, request):
        from apps.inventory.services.inventory_service import InventoryService

        low = list(InventoryService.get_low_stock(branch_id=getattr(request.user.branch, "id", None))[:10])
        out = list(InventoryService.get_out_of_stock(branch_id=getattr(request.user.branch, "id", None))[:10])
        out_ids = {inv.id for inv in out}
        alerts = []
        for inv in out:
            alerts.append({
                "type": "error",
                "title": "Out of Stock",
                "message": f"{inv.product.name} is out of stock in {inv.warehouse.name}",
                "product_id": str(inv.product_id),
            })
        for inv in low:
            if inv.id not in out_ids:
                alerts.append({
                    "type": "warning",
                    "title": "Low Stock",
                    "message": f"{inv.product.name} has {inv.quantity} units (min: {inv.product.minimum_stock})",
                    "product_id": str(inv.product_id),
                })
        return success_response(data=alerts)

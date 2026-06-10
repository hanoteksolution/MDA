from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses.api_response import success_response
from core.services.analytics_service import AnalyticsService
from permissions.base import HasPermission


class ReportDataView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("reports.view")]

    def get(self, request):
        category = request.query_params.get("category", "")
        report = request.query_params.get("report", "")
        branch_id = getattr(request.user.branch, "id", None)
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        data = AnalyticsService.get_report(
            category=category,
            report=report,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
        )
        return success_response(data=data)


class ReportsChartView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("reports.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        charts = AnalyticsService.get_chart_data(branch_id=branch_id)
        category = request.query_params.get("category", "sales")
        key = "revenue" if category in ("sales", "customers") else "profit"
        return success_response(data=charts.get(key, charts["revenue"]))


urlpatterns = [
    path("data/", ReportDataView.as_view(), name="report-data"),
    path("chart/", ReportsChartView.as_view(), name="report-chart"),
]

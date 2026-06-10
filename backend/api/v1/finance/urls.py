from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses.api_response import success_response
from core.services.analytics_service import AnalyticsService
from permissions.base import HasPermission


class FinanceSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        period = request.query_params.get("period", "month")
        branch_id = getattr(request.user.branch, "id", None)
        return success_response(data=AnalyticsService.get_finance_summary(branch_id=branch_id, period=period))


urlpatterns = [
    path("summary/", FinanceSummaryView.as_view(), name="finance-summary"),
]

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authentication.services.staff_evaluation_service import StaffEvaluationService
from apps.reports.services.report_service import ReportService
from core.responses.api_response import error_response, success_response
from core.services.analytics_service import AnalyticsService
from permissions.base import HasPermission


class ReportCatalogView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("reports.view")]

    def get(self, request):
        return success_response(data=ReportService.catalog(user=request.user, request=request))


class ReportDataView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("reports.view")]

    def get(self, request):
        category = request.query_params.get("category", "")
        report = request.query_params.get("report", "")
        branch_id = request.query_params.get("branch_id") or getattr(
            request.user.branch, "id", None
        )
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        try:
            data = ReportService.run(
                category=category,
                report=report,
                branch_id=branch_id,
                date_from=date_from,
                date_to=date_to,
                user=request.user,
                request=request,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)


class ReportExportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("reports.export")]

    def get(self, request):
        category = request.query_params.get("category", "")
        report = request.query_params.get("report", "")
        if not category or not report:
            return error_response(
                message="category and report are required.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        branch_id = request.query_params.get("branch_id") or getattr(
            request.user.branch, "id", None
        )
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        try:
            csv_body = ReportService.export_csv(
                category=category,
                report=report,
                branch_id=branch_id,
                date_from=date_from,
                date_to=date_to,
                user=request.user,
                request=request,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        filename = f"{category}-{report.replace(' ', '-').lower()}.csv"
        response = HttpResponse(csv_body, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SalesReportPrintView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("reports.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        data = AnalyticsService.get_sales_report_print(
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
        key = "revenue" if category in ("sales", "customers", "gym") else "profit"
        return success_response(data=charts.get(key, charts["revenue"]))


class StaffPerformanceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("staff.performance.view")]

    def get(self, request):
        from apps.platform.services.platform_service import PlatformService

        branch_id = request.query_params.get("branch_id") or getattr(request.user.branch, "id", None)
        period = request.query_params.get("period", "month")
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        accessible = [str(tid) for tid in PlatformService.accessible_tenant_ids(request.user)]
        tenant_id = request.query_params.get("tenant_id")
        all_shops = request.query_params.get("all_shops") == "1"

        if tenant_id:
            if tenant_id not in accessible:
                return error_response("You do not have access to this shop.", status=403)
            data = AnalyticsService.get_staff_performance(
                branch_id=branch_id,
                tenant_id=tenant_id,
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
            from apps.platform.models import Tenant

            shop = Tenant.objects.filter(pk=tenant_id).first()
            for row in data:
                row["tenant_id"] = tenant_id
                row["shop_name"] = shop.name if shop else "—"
        elif all_shops and len(accessible) > 1:
            data = AnalyticsService.get_staff_performance_for_tenants(
                tenant_ids=accessible,
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
        elif accessible:
            data = AnalyticsService.get_staff_performance(
                branch_id=branch_id,
                tenant_id=accessible[0] if not branch_id else None,
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            data = AnalyticsService.get_staff_performance(
                branch_id=branch_id,
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
        evaluations = StaffEvaluationService.map_by_staff(
            branch_id=branch_id,
            period=period,
        )
        for row in data:
            row["evaluation"] = evaluations.get(row["user_id"])
        return success_response(data=data)


class StaffEvaluationView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("staff.performance.evaluate")]

    def put(self, request, user_id):
        period = request.data.get("period", "month")
        rating = request.data.get("rating")
        notes = request.data.get("notes", "")

        if rating is None:
            return error_response("rating is required (1-5).", status=400)
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return error_response("rating must be a number between 1 and 5.", status=400)
        if rating < 1 or rating > 5:
            return error_response("rating must be between 1 and 5.", status=400)

        try:
            row = StaffEvaluationService.upsert(
                staff_id=user_id,
                evaluator=request.user,
                period=period,
                rating=rating,
                notes=notes,
            )
        except PermissionError as exc:
            return error_response(str(exc), status=403)
        except ValueError as exc:
            return error_response(str(exc), status=404)

        return success_response(
            data=StaffEvaluationService.serialize(row),
            message="Staff evaluation saved.",
        )

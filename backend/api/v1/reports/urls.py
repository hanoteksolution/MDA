from django.urls import path

from api.v1.reports.views import (
    BranchReportView,
    BranchOverviewView,
    ReportCatalogView,
    ReportDataView,
    ReportExportView,
    ReportsChartView,
    SalesReportPrintView,
    StaffEvaluationView,
    StaffPerformanceView,
)

urlpatterns = [
    path("catalog/", ReportCatalogView.as_view(), name="report-catalog"),
    path("branch-overview/", BranchOverviewView.as_view(), name="report-branch-overview"),
    path("branch/<str:report>/", BranchReportView.as_view(), name="report-branch"),
    path("data/", ReportDataView.as_view(), name="report-data"),
    path("export/", ReportExportView.as_view(), name="report-export"),
    path("sales-print/", SalesReportPrintView.as_view(), name="sales-report-print"),
    path("chart/", ReportsChartView.as_view(), name="report-chart"),
    path("staff-performance/", StaffPerformanceView.as_view(), name="staff-performance"),
    path(
        "staff-performance/<uuid:user_id>/evaluation/",
        StaffEvaluationView.as_view(),
        name="staff-evaluation",
    ),
]

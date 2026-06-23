from django.urls import path

from api.v1.customers.views import (
    CustomerDetailView,
    CustomerListCreateView,
    CustomerPrintReportView,
    CustomerSummaryView,
)

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="customer-list"),
    path("print-report/", CustomerPrintReportView.as_view(), name="customer-print-report"),
    path("summary/", CustomerSummaryView.as_view(), name="customer-summary"),
    path("<uuid:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
]

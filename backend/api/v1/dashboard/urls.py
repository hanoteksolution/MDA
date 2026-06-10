from django.urls import path

from api.v1.dashboard.views import (
    DashboardAlertsView,
    DashboardChartsView,
    DashboardKPIView,
    DashboardLowStockView,
    DashboardRecentSalesView,
    DashboardTopProductsView,
)

urlpatterns = [
    path("kpis/", DashboardKPIView.as_view(), name="dashboard-kpis"),
    path("recent-sales/", DashboardRecentSalesView.as_view(), name="dashboard-recent-sales"),
    path("low-stock/", DashboardLowStockView.as_view(), name="dashboard-low-stock"),
    path("top-products/", DashboardTopProductsView.as_view(), name="dashboard-top-products"),
    path("charts/", DashboardChartsView.as_view(), name="dashboard-charts"),
    path("alerts/", DashboardAlertsView.as_view(), name="dashboard-alerts"),
]

from django.urls import path

from api.v1.inventory.views import (
    AdjustmentListCreateView,
    InventoryListView,
    InventorySummaryView,
    LowStockView,
    OutOfStockView,
    WarehouseDetailView,
    WarehouseListCreateView,
)

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path("summary/", InventorySummaryView.as_view(), name="inventory-summary"),
    path("low-stock/", LowStockView.as_view(), name="inventory-low-stock"),
    path("out-of-stock/", OutOfStockView.as_view(), name="inventory-out-of-stock"),
    path("adjustments/", AdjustmentListCreateView.as_view(), name="inventory-adjustments"),
]

warehouse_urls = [
    path("", WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("<uuid:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"),
]

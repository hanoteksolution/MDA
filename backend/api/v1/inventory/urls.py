from django.urls import path

from api.v1.inventory.views import (
    AdjustmentListCreateView,
    InventoryListView,
    InventorySummaryView,
    LowStockView,
    OutOfStockView,
    TransferCancelView,
    TransferConfirmView,
    TransferDetailView,
    TransferListCreateView,
    WarehouseDetailView,
    WarehouseListCreateView,
)

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path("summary/", InventorySummaryView.as_view(), name="inventory-summary"),
    path("low-stock/", LowStockView.as_view(), name="inventory-low-stock"),
    path("out-of-stock/", OutOfStockView.as_view(), name="inventory-out-of-stock"),
    path("adjustments/", AdjustmentListCreateView.as_view(), name="inventory-adjustments"),
    path("transfers/", TransferListCreateView.as_view(), name="inventory-transfers"),
    path("transfers/<uuid:pk>/", TransferDetailView.as_view(), name="inventory-transfer-detail"),
    path(
        "transfers/<uuid:pk>/confirm/",
        TransferConfirmView.as_view(),
        name="inventory-transfer-confirm",
    ),
    path(
        "transfers/<uuid:pk>/cancel/",
        TransferCancelView.as_view(),
        name="inventory-transfer-cancel",
    ),
]

warehouse_urls = [
    path("", WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("<uuid:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"),
]

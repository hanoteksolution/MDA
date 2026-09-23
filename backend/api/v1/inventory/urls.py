from django.urls import path

from api.v1.inventory.views import (
    AdjustmentListCreateView,
    BranchStockDashboardView,
    BranchTransferApproveView,
    BranchTransferCancelView,
    BranchTransferCompleteView,
    BranchTransferDetailView,
    BranchTransferDispatchView,
    BranchTransferListCreateView,
    BranchTransferRejectView,
    BranchTransferReceiveView,
    BranchTransferReserveView,
    InventoryListView,
    InventorySummaryView,
    LowStockView,
    OutOfStockView,
    ProductAvailabilityView,
    ProductMovementHistoryView,
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
    path("branch-dashboard/", BranchStockDashboardView.as_view(), name="inventory-branch-dashboard"),
    path(
        "products/<uuid:product_id>/availability/",
        ProductAvailabilityView.as_view(),
        name="inventory-product-availability",
    ),
    path(
        "products/<uuid:product_id>/movements/",
        ProductMovementHistoryView.as_view(),
        name="inventory-product-movements",
    ),
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
    path("branch-transfers/", BranchTransferListCreateView.as_view(), name="branch-transfers"),
    path("branch-transfers/<uuid:pk>/", BranchTransferDetailView.as_view(), name="branch-transfer-detail"),
    path("branch-transfers/<uuid:pk>/approve/", BranchTransferApproveView.as_view(), name="branch-transfer-approve"),
    path("branch-transfers/<uuid:pk>/reject/", BranchTransferRejectView.as_view(), name="branch-transfer-reject"),
    path("branch-transfers/<uuid:pk>/reserve/", BranchTransferReserveView.as_view(), name="branch-transfer-reserve"),
    path("branch-transfers/<uuid:pk>/dispatch/", BranchTransferDispatchView.as_view(), name="branch-transfer-dispatch"),
    path("branch-transfers/<uuid:pk>/receive/", BranchTransferReceiveView.as_view(), name="branch-transfer-receive"),
    path("branch-transfers/<uuid:pk>/complete/", BranchTransferCompleteView.as_view(), name="branch-transfer-complete"),
    path("branch-transfers/<uuid:pk>/cancel/", BranchTransferCancelView.as_view(), name="branch-transfer-cancel"),
]

warehouse_urls = [
    path("", WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("<uuid:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"),
]

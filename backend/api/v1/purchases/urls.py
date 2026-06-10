from django.urls import path

from api.v1.purchases.views import (
    PurchaseOrderDetailView,
    PurchaseOrderListCreateView,
    PurchaseOrderSummaryView,
)

urlpatterns = [
    path("", PurchaseOrderListCreateView.as_view(), name="purchase-order-list"),
    path("summary/", PurchaseOrderSummaryView.as_view(), name="purchase-order-summary"),
    path("<uuid:pk>/", PurchaseOrderDetailView.as_view(), name="purchase-order-detail"),
]

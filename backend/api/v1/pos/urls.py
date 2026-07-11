from django.urls import path

from api.v1.pos.views import (
    PosCheckoutView,
    PosProfileView,
    PosReceiptNumberView,
    PosWaiterPerformanceView,
    PosWaiterSalesView,
)

urlpatterns = [
    path("checkout/", PosCheckoutView.as_view(), name="pos-checkout"),
    path("profile/", PosProfileView.as_view(), name="pos-profile"),
    path("receipt-number/", PosReceiptNumberView.as_view(), name="pos-receipt-number"),
    path("waiter-sales/", PosWaiterSalesView.as_view(), name="pos-waiter-sales"),
    path("waiter-performance/", PosWaiterPerformanceView.as_view(), name="pos-waiter-performance"),
]

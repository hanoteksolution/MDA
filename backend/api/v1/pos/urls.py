from django.urls import path

from api.v1.pos.views import (
    PosCheckoutView,
    PosHoldListCreateView,
    PosProfileView,
    PosReceiptNumberView,
    PosRefundView,
    PosSessionCloseView,
    PosSessionCurrentView,
    PosSessionListView,
    PosSessionOpenView,
    PosWaiterPerformanceView,
    PosWaiterSalesView,
)

urlpatterns = [
    path("checkout/", PosCheckoutView.as_view(), name="pos-checkout"),
    path("holds/", PosHoldListCreateView.as_view(), name="pos-holds"),
    path("profile/", PosProfileView.as_view(), name="pos-profile"),
    path("receipt-number/", PosReceiptNumberView.as_view(), name="pos-receipt-number"),
    path("waiter-sales/", PosWaiterSalesView.as_view(), name="pos-waiter-sales"),
    path("waiter-performance/", PosWaiterPerformanceView.as_view(), name="pos-waiter-performance"),
    path("sessions/", PosSessionListView.as_view(), name="pos-sessions"),
    path("sessions/open/", PosSessionOpenView.as_view(), name="pos-session-open"),
    path("sessions/current/", PosSessionCurrentView.as_view(), name="pos-session-current"),
    path("sessions/close/", PosSessionCloseView.as_view(), name="pos-session-close"),
    path("refunds/", PosRefundView.as_view(), name="pos-refunds"),
]

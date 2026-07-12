from django.urls import path

from api.v1.sync.views import (
    ShopPaymentStatusView,
    ShopPullSyncView,
    ShopPushSyncView,
    ShopReportPaymentView,
    SubscriptionStatusView,
    SyncConfigView,
    SyncPaymentStatusView,
    SyncReportPaymentView,
    SyncRunView,
)

urlpatterns = [
    path("config/", SyncConfigView.as_view(), name="sync-config"),
    path("run/", SyncRunView.as_view(), name="sync-run"),
    path("subscription-status/", SubscriptionStatusView.as_view(), name="sync-subscription-status"),
    path("report-payment/", SyncReportPaymentView.as_view(), name="sync-report-payment"),
    path("payment-status/", SyncPaymentStatusView.as_view(), name="sync-payment-status"),
    path("shop-push/", ShopPushSyncView.as_view(), name="sync-shop-push"),
    path("shop-pull/", ShopPullSyncView.as_view(), name="sync-shop-pull"),
    path("shop-report-payment/", ShopReportPaymentView.as_view(), name="sync-shop-report-payment"),
    path("shop-payment-status/", ShopPaymentStatusView.as_view(), name="sync-shop-payment-status"),
]

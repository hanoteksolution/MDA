from django.urls import path

from api.v1.sync.views import (
    ShopPullSyncView,
    ShopPushSyncView,
    SubscriptionStatusView,
    SyncConfigView,
    SyncRunView,
)

urlpatterns = [
    path("config/", SyncConfigView.as_view(), name="sync-config"),
    path("run/", SyncRunView.as_view(), name="sync-run"),
    path("subscription-status/", SubscriptionStatusView.as_view(), name="sync-subscription-status"),
    path("shop-push/", ShopPushSyncView.as_view(), name="sync-shop-push"),
    path("shop-pull/", ShopPullSyncView.as_view(), name="sync-shop-pull"),
]

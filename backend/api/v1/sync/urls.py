from django.urls import path

from api.v1.sync.views import ShopPullSyncView, ShopPushSyncView, SyncConfigView, SyncRunView

urlpatterns = [
    path("config/", SyncConfigView.as_view(), name="sync-config"),
    path("run/", SyncRunView.as_view(), name="sync-run"),
    path("shop-push/", ShopPushSyncView.as_view(), name="sync-shop-push"),
    path("shop-pull/", ShopPullSyncView.as_view(), name="sync-shop-pull"),
]

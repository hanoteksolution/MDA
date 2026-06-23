from django.urls import path

from api.v1.platform.views import (
    PlatformMySubscriptionAlertView,
    PlatformPlansView,
    PlatformShopGroupListCreateView,
    PlatformSubscriptionAlertsView,
    PlatformSubscriptionAssignView,
    PlatformSubscriptionDetailView,
    PlatformSubscriptionListCreateView,
    PlatformSubscriptionRenewView,
    PlatformSubscriptionUpdateView,
    PlatformTenantDetailView,
    PlatformTenantListCreateView,
    PlatformTenantUsersView,
)

urlpatterns = [
    path("tenants/", PlatformTenantListCreateView.as_view(), name="platform-tenants"),
    path("tenants/<uuid:pk>/", PlatformTenantDetailView.as_view(), name="platform-tenant-detail"),
    path("tenants/<uuid:pk>/users/", PlatformTenantUsersView.as_view(), name="platform-tenant-users"),
    path("tenants/<uuid:pk>/subscription/", PlatformSubscriptionUpdateView.as_view(), name="platform-subscription"),
    path("subscriptions/", PlatformSubscriptionListCreateView.as_view(), name="platform-subscriptions"),
    path("subscriptions/alerts/", PlatformSubscriptionAlertsView.as_view(), name="platform-subscription-alerts"),
    path("subscriptions/my-alert/", PlatformMySubscriptionAlertView.as_view(), name="platform-my-subscription-alert"),
    path("subscriptions/<uuid:pk>/", PlatformSubscriptionDetailView.as_view(), name="platform-subscription-detail"),
    path("subscriptions/<uuid:pk>/assign/", PlatformSubscriptionAssignView.as_view(), name="platform-subscription-assign"),
    path("subscriptions/<uuid:pk>/renew/", PlatformSubscriptionRenewView.as_view(), name="platform-subscription-renew"),
    path("shop-groups/", PlatformShopGroupListCreateView.as_view(), name="platform-shop-groups"),
    path("plans/", PlatformPlansView.as_view(), name="platform-plans"),
]

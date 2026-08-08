from django.urls import path

from api.v1.auth.views import (
    DesktopProvisionView,
    DesktopUserStatusView,
    LoginView,
    LogoutView,
    MeView,
    MobileTokenRefreshView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("refresh/", MobileTokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("desktop-status/", DesktopUserStatusView.as_view(), name="auth-desktop-status"),
    path("desktop-provision/", DesktopProvisionView.as_view(), name="auth-desktop-provision"),
]

from django.urls import path

from api.v1.auth.views import PermissionListView, RoleDetailView, RoleListCreateView

urlpatterns = [
    path("", RoleListCreateView.as_view(), name="role-list"),
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
    path("<uuid:pk>/", RoleDetailView.as_view(), name="role-detail"),
]

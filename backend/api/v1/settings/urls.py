from django.urls import path

from api.v1.settings.views import (
    BranchDetailView,
    BranchListCreateView,
    BranchSetDefaultView,
    CompanyProfileView,
    SettingDetailView,
    SettingsListView,
)

urlpatterns = [
    path("branches/", BranchListCreateView.as_view(), name="branch-list"),
    path("branches/<uuid:pk>/", BranchDetailView.as_view(), name="branch-detail"),
    path("branches/<uuid:pk>/set-default/", BranchSetDefaultView.as_view(), name="branch-set-default"),
    path("", SettingsListView.as_view(), name="settings-list"),
    path("company/", CompanyProfileView.as_view(), name="settings-company"),
    path("<str:key>/", SettingDetailView.as_view(), name="setting-detail"),
]

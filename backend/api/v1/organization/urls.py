from django.urls import path

from api.v1.organization.views import (
    AccessProfileDetailView,
    AccessProfileListCreateView,
    BranchAccessDetailView,
    BranchAccessListCreateView,
    BranchContextView,
    CashRegisterDetailView,
    CashRegisterListCreateView,
    MyBranchesView,
    PosTerminalDetailView,
    PosTerminalListCreateView,
    StockLocationDetailView,
    StockLocationListCreateView,
)

urlpatterns = [
    path("my-branches/", MyBranchesView.as_view(), name="organization-my-branches"),
    path("context/", BranchContextView.as_view(), name="organization-branch-context"),
    path("access-profiles/", AccessProfileListCreateView.as_view(), name="organization-access-profiles"),
    path("access-profiles/<uuid:pk>/", AccessProfileDetailView.as_view(), name="organization-access-profile-detail"),
    path("branch-access/", BranchAccessListCreateView.as_view(), name="organization-branch-access"),
    path("branch-access/<uuid:pk>/", BranchAccessDetailView.as_view(), name="organization-branch-access-detail"),
    path("stock-locations/", StockLocationListCreateView.as_view(), name="organization-stock-locations"),
    path("stock-locations/<uuid:pk>/", StockLocationDetailView.as_view(), name="organization-stock-location-detail"),
    path("cash-registers/", CashRegisterListCreateView.as_view(), name="organization-cash-registers"),
    path("cash-registers/<uuid:pk>/", CashRegisterDetailView.as_view(), name="organization-cash-register-detail"),
    path("pos-terminals/", PosTerminalListCreateView.as_view(), name="organization-pos-terminals"),
    path("pos-terminals/<uuid:pk>/", PosTerminalDetailView.as_view(), name="organization-pos-terminal-detail"),
]

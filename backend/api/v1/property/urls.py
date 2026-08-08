from django.urls import path

from api.v1.property.views import (
    BuildingListCreateView,
    DocumentListCreateView,
    MaintenanceListCreateView,
    MaintenanceStatusView,
    OwnerListCreateView,
    PropertyListCreateView,
    PropertySummaryView,
    UnitListCreateView,
    UnitStatusView,
)

urlpatterns = [
    path("summary/", PropertySummaryView.as_view(), name="property-summary"),
    path("owners/", OwnerListCreateView.as_view(), name="property-owners"),
    path("properties/", PropertyListCreateView.as_view(), name="property-properties"),
    path("buildings/", BuildingListCreateView.as_view(), name="property-buildings"),
    path("units/", UnitListCreateView.as_view(), name="property-units"),
    path("units/<uuid:pk>/status/", UnitStatusView.as_view(), name="property-unit-status"),
    path("maintenance/", MaintenanceListCreateView.as_view(), name="property-maintenance"),
    path(
        "maintenance/<uuid:pk>/status/",
        MaintenanceStatusView.as_view(),
        name="property-maintenance-status",
    ),
    path("documents/", DocumentListCreateView.as_view(), name="property-documents"),
]

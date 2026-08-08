from django.urls import path

from api.v1.property.views import (
    BuildingDetailView,
    BuildingListCreateView,
    DocumentListCreateView,
    MaintenanceListCreateView,
    MaintenanceStatusView,
    OwnerDetailView,
    OwnerListCreateView,
    PropertyDetailView,
    PropertyListCreateView,
    PropertySummaryView,
    UnitDetailView,
    UnitListCreateView,
    UnitStatusView,
)

urlpatterns = [
    path("summary/", PropertySummaryView.as_view(), name="property-summary"),
    path("owners/", OwnerListCreateView.as_view(), name="property-owners"),
    path("owners/<uuid:pk>/", OwnerDetailView.as_view(), name="property-owner-detail"),
    path("properties/", PropertyListCreateView.as_view(), name="property-properties"),
    path("properties/<uuid:pk>/", PropertyDetailView.as_view(), name="property-detail"),
    path("buildings/", BuildingListCreateView.as_view(), name="property-buildings"),
    path("buildings/<uuid:pk>/", BuildingDetailView.as_view(), name="property-building-detail"),
    path("units/", UnitListCreateView.as_view(), name="property-units"),
    path("units/<uuid:pk>/", UnitDetailView.as_view(), name="property-unit-detail"),
    path("units/<uuid:pk>/status/", UnitStatusView.as_view(), name="property-unit-status"),
    path("maintenance/", MaintenanceListCreateView.as_view(), name="property-maintenance"),
    path(
        "maintenance/<uuid:pk>/status/",
        MaintenanceStatusView.as_view(),
        name="property-maintenance-status",
    ),
    path("documents/", DocumentListCreateView.as_view(), name="property-documents"),
]

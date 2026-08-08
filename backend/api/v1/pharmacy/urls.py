from django.urls import path

from api.v1.pharmacy.views import (
    BatchExpiringView,
    BatchFefoPreviewView,
    BatchListCreateView,
    PharmacyCategoryListView,
    PharmacySummaryView,
    PrescriptionDispenseView,
    PrescriptionListCreateView,
)

urlpatterns = [
    path("summary/", PharmacySummaryView.as_view(), name="pharmacy-summary"),
    path("categories/", PharmacyCategoryListView.as_view(), name="pharmacy-categories"),
    path("batches/", BatchListCreateView.as_view(), name="pharmacy-batches"),
    path("batches/expiring/", BatchExpiringView.as_view(), name="pharmacy-batches-expiring"),
    path("batches/fefo-preview/", BatchFefoPreviewView.as_view(), name="pharmacy-fefo-preview"),
    path(
        "prescriptions/",
        PrescriptionListCreateView.as_view(),
        name="pharmacy-prescriptions",
    ),
    path(
        "prescriptions/<uuid:pk>/dispense/",
        PrescriptionDispenseView.as_view(),
        name="pharmacy-prescription-dispense",
    ),
]

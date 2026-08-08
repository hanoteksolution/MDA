from django.urls import path

from api.v1.housing.views import (
    ChargeInvoiceView,
    ChargePaidView,
    HousingSummaryView,
    LeaseActivateView,
    LeaseChargeListCreateView,
    LeaseDetailView,
    LeaseListCreateView,
    LeaseTerminateView,
    TenantListCreateView,
)

urlpatterns = [
    path("summary/", HousingSummaryView.as_view(), name="housing-summary"),
    path("tenants/", TenantListCreateView.as_view(), name="housing-tenants"),
    path("leases/", LeaseListCreateView.as_view(), name="housing-leases"),
    path("leases/<uuid:pk>/", LeaseDetailView.as_view(), name="housing-lease-detail"),
    path(
        "leases/<uuid:pk>/activate/",
        LeaseActivateView.as_view(),
        name="housing-lease-activate",
    ),
    path(
        "leases/<uuid:pk>/terminate/",
        LeaseTerminateView.as_view(),
        name="housing-lease-terminate",
    ),
    path(
        "leases/<uuid:pk>/charges/",
        LeaseChargeListCreateView.as_view(),
        name="housing-lease-charges",
    ),
    path(
        "charges/<uuid:pk>/invoice/",
        ChargeInvoiceView.as_view(),
        name="housing-charge-invoice",
    ),
    path(
        "charges/<uuid:pk>/paid/",
        ChargePaidView.as_view(),
        name="housing-charge-paid",
    ),
]

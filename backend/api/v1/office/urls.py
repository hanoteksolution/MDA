from django.urls import path

from api.v1.office.views import (
    ChargeInvoiceView,
    ChargePaidView,
    LeaseActivateView,
    LeaseChargeListCreateView,
    LeaseDetailView,
    LeaseListCreateView,
    LeaseTerminateView,
    OfficeSummaryView,
    TenantDetailView,
    TenantListCreateView,
)

urlpatterns = [
    path("summary/", OfficeSummaryView.as_view(), name="office-summary"),
    path("tenants/", TenantListCreateView.as_view(), name="office-tenants"),
    path("tenants/<uuid:pk>/", TenantDetailView.as_view(), name="office-tenant-detail"),
    path("leases/", LeaseListCreateView.as_view(), name="office-leases"),
    path("leases/<uuid:pk>/", LeaseDetailView.as_view(), name="office-lease-detail"),
    path(
        "leases/<uuid:pk>/activate/",
        LeaseActivateView.as_view(),
        name="office-lease-activate",
    ),
    path(
        "leases/<uuid:pk>/terminate/",
        LeaseTerminateView.as_view(),
        name="office-lease-terminate",
    ),
    path(
        "leases/<uuid:pk>/charges/",
        LeaseChargeListCreateView.as_view(),
        name="office-lease-charges",
    ),
    path(
        "charges/<uuid:pk>/invoice/",
        ChargeInvoiceView.as_view(),
        name="office-charge-invoice",
    ),
    path(
        "charges/<uuid:pk>/paid/",
        ChargePaidView.as_view(),
        name="office-charge-paid",
    ),
]

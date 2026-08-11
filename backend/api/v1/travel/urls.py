from django.urls import path

from .views import (
    BookingAccountingPreviewView, BookingPostAccountingView, BookingStatusView, CommissionStatusView,
    QuotationConvertView, QuotationStatusView, TravelResourceDetailView,
    TravelMobileBookingsView, TravelMobileSummaryView, TravelResourceListCreateView, TravelSummaryView,
    TravelTransactionPostAccountingView,
)


def resource_paths(path_prefix, resource):
    return [
        path(f"{path_prefix}/", TravelResourceListCreateView.as_view(resource=resource), name=f"travel-{path_prefix}-list"),
        path(f"{path_prefix}/<uuid:pk>/", TravelResourceDetailView.as_view(resource=resource), name=f"travel-{path_prefix}-detail"),
    ]


urlpatterns = [
    path("summary/", TravelSummaryView.as_view(), name="travel-summary"),
    path("mobile/summary/", TravelMobileSummaryView.as_view(), name="travel-mobile-summary"),
    path("mobile/bookings/", TravelMobileBookingsView.as_view(), name="travel-mobile-bookings"),
    *resource_paths("destinations", "destinations"),
    *resource_paths("packages", "packages"),
    *resource_paths("travelers", "travelers"),
    *resource_paths("bookings", "bookings"),
    path("bookings/<uuid:pk>/status/", BookingStatusView.as_view(), name="travel-booking-status"),
    path("bookings/<uuid:pk>/accounting-preview/", BookingAccountingPreviewView.as_view(), name="travel-booking-accounting-preview"),
    path("bookings/<uuid:pk>/post-accounting/", BookingPostAccountingView.as_view(), name="travel-booking-post-accounting"),
    *resource_paths("flights", "flights"),
    *resource_paths("hotel-stays", "hotel_stays"),
    *resource_paths("visas", "visas"),
    *resource_paths("commissions", "commissions"),
    path("commissions/<uuid:pk>/status/", CommissionStatusView.as_view(), name="travel-commission-status"),
    *resource_paths("insurance", "insurance"),
    *resource_paths("vehicles", "vehicles"),
    *resource_paths("drivers", "drivers"),
    *resource_paths("transfers", "transfers"),
    *resource_paths("itineraries", "itineraries"),
    *resource_paths("activities", "activities"),
    *resource_paths("quotations", "quotations"),
    *resource_paths("quotation-lines", "quotation_lines"),
    path("quotations/<uuid:pk>/status/", QuotationStatusView.as_view(), name="travel-quotation-status"),
    path("quotations/<uuid:pk>/convert/", QuotationConvertView.as_view(), name="travel-quotation-convert"),
    *resource_paths("documents", "documents"),
    *resource_paths("payments", "payments"),
    path("payments/<uuid:pk>/post-accounting/", TravelTransactionPostAccountingView.as_view(resource="payments"), name="travel-payment-post-accounting"),
    *resource_paths("refunds", "refunds"),
    path("refunds/<uuid:pk>/post-accounting/", TravelTransactionPostAccountingView.as_view(resource="refunds"), name="travel-refund-post-accounting"),
    *resource_paths("expenses", "expenses"),
]

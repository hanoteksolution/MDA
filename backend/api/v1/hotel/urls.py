from django.urls import path

from api.v1.hotel.views import (
    GuestListCreateView,
    HotelSummaryView,
    OpenFoliosView,
    ReservationCancelView,
    ReservationCheckInView,
    ReservationCheckOutView,
    ReservationDetailView,
    ReservationFolioView,
    ReservationListCreateView,
    RoomListCreateView,
    RoomStatusView,
    RoomTypeListCreateView,
)

urlpatterns = [
    path("summary/", HotelSummaryView.as_view(), name="hotel-summary"),
    path("folios/open/", OpenFoliosView.as_view(), name="hotel-folios-open"),
    path("room-types/", RoomTypeListCreateView.as_view(), name="hotel-room-types"),
    path("rooms/", RoomListCreateView.as_view(), name="hotel-rooms"),
    path("rooms/<uuid:pk>/status/", RoomStatusView.as_view(), name="hotel-room-status"),
    path("guests/", GuestListCreateView.as_view(), name="hotel-guests"),
    path("reservations/", ReservationListCreateView.as_view(), name="hotel-reservations"),
    path(
        "reservations/<uuid:pk>/",
        ReservationDetailView.as_view(),
        name="hotel-reservation-detail",
    ),
    path(
        "reservations/<uuid:pk>/check-in/",
        ReservationCheckInView.as_view(),
        name="hotel-reservation-check-in",
    ),
    path(
        "reservations/<uuid:pk>/check-out/",
        ReservationCheckOutView.as_view(),
        name="hotel-reservation-check-out",
    ),
    path(
        "reservations/<uuid:pk>/cancel/",
        ReservationCancelView.as_view(),
        name="hotel-reservation-cancel",
    ),
    path(
        "reservations/<uuid:pk>/folio/",
        ReservationFolioView.as_view(),
        name="hotel-reservation-folio",
    ),
]

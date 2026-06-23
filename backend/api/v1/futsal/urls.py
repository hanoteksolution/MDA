from django.urls import path

from api.v1.futsal.views import (
    BookingDetailView,
    BookingListCreateView,
    CourtDetailView,
    CourtListCreateView,
    FutsalSummaryView,
    LedgerListCreateView,
    PlayerDetailView,
    PlayerListCreateView,
    TeamDetailView,
    TeamListCreateView,
)

urlpatterns = [
    path("summary/", FutsalSummaryView.as_view(), name="futsal-summary"),
    path("courts/", CourtListCreateView.as_view(), name="futsal-courts"),
    path("courts/<uuid:pk>/", CourtDetailView.as_view(), name="futsal-court-detail"),
    path("teams/", TeamListCreateView.as_view(), name="futsal-teams"),
    path("teams/<uuid:pk>/", TeamDetailView.as_view(), name="futsal-team-detail"),
    path("players/", PlayerListCreateView.as_view(), name="futsal-players"),
    path("players/<uuid:pk>/", PlayerDetailView.as_view(), name="futsal-player-detail"),
    path("bookings/", BookingListCreateView.as_view(), name="futsal-bookings"),
    path("bookings/<uuid:pk>/", BookingDetailView.as_view(), name="futsal-booking-detail"),
    path("ledger/", LedgerListCreateView.as_view(), name="futsal-ledger"),
]

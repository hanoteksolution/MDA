from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.futsal.serializers.futsal_serializers import (
    serialize_booking,
    serialize_court,
    serialize_ledger,
    serialize_player,
    serialize_team,
)
from apps.futsal.services.futsal_service import FutsalService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class FutsalSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def get(self, request):
        data = FutsalService.summary(branch_id=_branch_id(request))
        return success_response(data=data)


class CourtListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def get(self, request):
        qs = FutsalService.list_courts(branch_id=_branch_id(request))
        return paginate_queryset(request, qs, lambda items: [serialize_court(c) for c in items])

    def post(self, request):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        if not data.get("name") or not data.get("code") or not data.get("branch_id"):
            return error_response(message="name, code, and branch_id are required.", status=status.HTTP_400_BAD_REQUEST)
        court = FutsalService.create_court(
            data={
                "name": data["name"],
                "code": data["code"],
                "branch_id": data["branch_id"],
                "hourly_rate": Decimal(str(data.get("hourly_rate", 0))),
                "is_active": data.get("is_active", True),
                "notes": data.get("notes", ""),
            },
            user=request.user,
        )
        return success_response(data=serialize_court(court), message="Court created.", status=status.HTTP_201_CREATED)


class CourtDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def put(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        court = FutsalService.list_courts().get(pk=pk)
        data = {}
        for key in ("name", "code", "branch_id", "is_active", "notes"):
            if key in request.data:
                data[key] = request.data[key]
        if "hourly_rate" in request.data:
            data["hourly_rate"] = Decimal(str(request.data["hourly_rate"]))
        court = FutsalService.update_court(court=court, data=data, user=request.user)
        return success_response(data=serialize_court(court), message="Court updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        court = FutsalService.list_courts().get(pk=pk)
        court.soft_delete(user=request.user)
        return success_response(message="Court deleted.")


class TeamListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def get(self, request):
        qs = FutsalService.list_teams(branch_id=_branch_id(request), search=request.query_params.get("search"))
        return paginate_queryset(request, qs, lambda items: [serialize_team(t) for t in items])

    def post(self, request):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        if not data.get("name") or not data.get("branch_id"):
            return error_response(message="name and branch_id are required.", status=status.HTTP_400_BAD_REQUEST)
        team = FutsalService.create_team(
            data={
                "name": data["name"],
                "branch_id": data["branch_id"],
                "captain_name": data.get("captain_name", ""),
                "contact_phone": data.get("contact_phone", ""),
                "is_active": data.get("is_active", True),
                "notes": data.get("notes", ""),
            },
            user=request.user,
        )
        return success_response(data=serialize_team(team), message="Team created.", status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def put(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        team = FutsalService.list_teams().get(pk=pk)
        data = {k: request.data[k] for k in ("name", "branch_id", "captain_name", "contact_phone", "is_active", "notes") if k in request.data}
        team = FutsalService.update_team(team=team, data=data, user=request.user)
        return success_response(data=serialize_team(team), message="Team updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        team = FutsalService.list_teams().get(pk=pk)
        team.soft_delete(user=request.user)
        return success_response(message="Team deleted.")


class PlayerListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def get(self, request):
        qs = FutsalService.list_players(
            branch_id=_branch_id(request),
            team_id=request.query_params.get("team_id"),
            search=request.query_params.get("search"),
        )
        return paginate_queryset(request, qs, lambda items: [serialize_player(p) for p in items])

    def post(self, request):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        if not data.get("full_name") or not data.get("branch_id"):
            return error_response(message="full_name and branch_id are required.", status=status.HTTP_400_BAD_REQUEST)
        player = FutsalService.create_player(
            data={
                "full_name": data["full_name"],
                "branch_id": data["branch_id"],
                "team_id": data.get("team_id"),
                "phone": data.get("phone", ""),
                "jersey_number": data.get("jersey_number"),
                "is_active": data.get("is_active", True),
                "notes": data.get("notes", ""),
            },
            user=request.user,
        )
        return success_response(data=serialize_player(player), message="Player created.", status=status.HTTP_201_CREATED)


class PlayerDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def put(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        player = FutsalService.list_players().get(pk=pk)
        data = {k: request.data[k] for k in ("full_name", "branch_id", "team_id", "phone", "jersey_number", "is_active", "notes") if k in request.data}
        player = FutsalService.update_player(player=player, data=data, user=request.user)
        return success_response(data=serialize_player(player), message="Player updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        player = FutsalService.list_players().get(pk=pk)
        player.soft_delete(user=request.user)
        return success_response(message="Player deleted.")


class BookingListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def get(self, request):
        qs = FutsalService.list_bookings(
            branch_id=_branch_id(request),
            court_id=request.query_params.get("court_id"),
            status=request.query_params.get("status"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return paginate_queryset(request, qs, lambda items: [serialize_booking(b) for b in items])

    def post(self, request):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        if not data.get("court_id") or not data.get("start_at") or not data.get("end_at"):
            return error_response(message="court_id, start_at, and end_at are required.", status=status.HTTP_400_BAD_REQUEST)
        booking = FutsalService.create_booking(data=data, user=request.user)
        return success_response(data=serialize_booking(booking), message="Booking created.", status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.view")]

    def put(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        booking = FutsalService.list_bookings().get(pk=pk)
        booking = FutsalService.update_booking(booking=booking, data=request.data, user=request.user)
        return success_response(data=serialize_booking(booking), message="Booking updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("futsal.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        booking = FutsalService.list_bookings().get(pk=pk)
        booking.soft_delete(user=request.user)
        return success_response(message="Booking deleted.")


class LedgerListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("futsal.finance")]

    def get(self, request):
        qs = FutsalService.list_ledger(
            branch_id=_branch_id(request),
            entry_type=request.query_params.get("entry_type"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return paginate_queryset(request, qs, lambda items: [serialize_ledger(e) for e in items])

    def post(self, request):
        if not request.user.has_permission("futsal.finance"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        if not data.get("branch_id") or not data.get("entry_type") or not data.get("amount"):
            return error_response(message="branch_id, entry_type, and amount are required.", status=status.HTTP_400_BAD_REQUEST)
        entry = FutsalService.create_ledger_entry(
            data={
                "branch_id": data["branch_id"],
                "entry_type": data["entry_type"],
                "category": data.get("category", "other"),
                "amount": Decimal(str(data["amount"])),
                "entry_date": data.get("entry_date"),
                "description": data.get("description", ""),
                "booking_id": data.get("booking_id"),
            },
            user=request.user,
        )
        return success_response(data=serialize_ledger(entry), message="Entry recorded.", status=status.HTTP_201_CREATED)

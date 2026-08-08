from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.hotel.serializers import (
    serialize_folio,
    serialize_guest,
    serialize_open_folio_for_pos,
    serialize_reservation,
    serialize_room,
    serialize_room_type,
)
from apps.hotel.services import HotelError, HotelService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _not_found(entity="Record"):
    return error_response(message=f"{entity} not found.", status=status.HTTP_404_NOT_FOUND)


def _can_manage(user):
    return user.has_permission("hotel.manage") or user.has_permission("hotel.front_desk")


class HotelSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request):
        data = HotelService.summary(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return success_response(data=data)


class RoomTypeListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request):
        qs = HotelService.list_room_types(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_room_type(r) for r in items]
        )

    def post(self, request):
        if not request.user.has_permission("hotel.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = HotelService.create_room_type(
                data=data, user=request.user, request=request
            )
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_room_type(row),
            message="Room type created.",
            status=status.HTTP_201_CREATED,
        )


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request):
        qs = HotelService.list_rooms(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_room(r) for r in items]
        )

    def post(self, request):
        if not request.user.has_permission("hotel.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = HotelService.create_room(data=data, user=request.user, request=request)
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_room(row),
            message="Room created.",
            status=status.HTTP_201_CREATED,
        )


class RoomStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def post(self, request, pk):
        if not (
            request.user.has_permission("hotel.manage")
            or request.user.has_permission("hotel.housekeeping")
            or request.user.has_permission("hotel.front_desk")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            room = HotelService.get_room(pk=pk, user=request.user, request=request)
            room = HotelService.set_room_status(
                room=room, status=request.data.get("status"), user=request.user
            )
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_room(room), message="Room updated.")


class GuestListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request):
        qs = HotelService.list_guests(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_guest(g) for g in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = HotelService.create_guest(data=data, user=request.user, request=request)
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_guest(row),
            message="Guest created.",
            status=status.HTTP_201_CREATED,
        )


class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request):
        qs = HotelService.list_reservations(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_reservation(r) for r in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = HotelService.create_reservation(
                data=data, user=request.user, request=request
            )
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_reservation(row),
            message="Reservation created.",
            status=status.HTTP_201_CREATED,
        )


class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request, pk):
        try:
            row = HotelService.get_reservation(
                pk=pk, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Reservation")
        return success_response(data=serialize_reservation(row))


class ReservationCheckInView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = HotelService.get_reservation(
                pk=pk, user=request.user, request=request
            )
            row = HotelService.check_in(
                reservation=row,
                room_id=request.data.get("room_id"),
                user=request.user,
                request=request,
            )
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_reservation(row), message="Checked in.")


class ReservationCheckOutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = HotelService.get_reservation(
                pk=pk, user=request.user, request=request
            )
            row = HotelService.check_out(
                reservation=row, data=request.data or {}, user=request.user
            )
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        payload = serialize_reservation(row)
        settlement = getattr(row, "_last_settlement", None)
        if settlement:
            payload["settlement"] = settlement
        return success_response(data=payload, message="Checked out.")


class ReservationCancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = HotelService.get_reservation(
                pk=pk, user=request.user, request=request
            )
            row = HotelService.cancel_reservation(reservation=row, user=request.user)
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_reservation(row), message="Cancelled.")


class ReservationFolioView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("hotel.view")]

    def get(self, request, pk):
        try:
            reservation = HotelService.get_reservation(
                pk=pk, user=request.user, request=request
            )
            folio = HotelService.get_folio_for_reservation(reservation=reservation)
        except ObjectDoesNotExist:
            return _not_found("Reservation")
        if folio is None:
            return _not_found("Folio")
        return success_response(data=serialize_folio(folio))

    def post(self, request, pk):
        """Post a folio line (service / F&B / other)."""
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            reservation = HotelService.get_reservation(
                pk=pk, user=request.user, request=request
            )
            folio = HotelService.get_folio_for_reservation(reservation=reservation)
            if folio is None:
                return error_response(
                    message="No open folio — check in first.",
                    status=status.HTTP_400_BAD_REQUEST,
                )
            HotelService.add_folio_line(
                folio=folio, data=request.data, user=request.user
            )
            folio.refresh_from_db()
        except (HotelError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_folio(folio),
            message="Folio line posted.",
            status=status.HTTP_201_CREATED,
        )


class OpenFoliosView(APIView):
    """In-house open folios for POS charge-to-room (hotel.view or pos.access)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (
            user.has_permission("hotel.view")
            or user.has_permission("hotel.front_desk")
            or user.has_permission("pos.access")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        folios = HotelService.list_open_folios(
            branch_id=_branch_id(request), user=user, request=request
        )
        return success_response(
            data={
                "results": [serialize_open_folio_for_pos(f) for f in folios],
                "count": len(folios),
            }
        )

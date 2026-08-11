from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.travel_agency.serializers import serialize_travel
from apps.travel_agency.services import TravelAccountingService, TravelError, TravelService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class TravelSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.view")]

    def get(self, request):
        return success_response(data=TravelService.summary(user=request.user, request=request, branch_id=_branch_id(request)))


class TravelResourceListCreateView(APIView):
    resource = ""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(f"{TravelService.PERMISSION_PREFIX[self.resource]}.view")()]

    def get(self, request):
        rows = TravelService.list(
            self.resource, user=request.user, request=request, branch_id=_branch_id(request),
            status=request.query_params.get("status"), search=request.query_params.get("search"),
        )
        return paginate_queryset(request, rows, serialize_travel)

    def post(self, request):
        prefix = TravelService.PERMISSION_PREFIX[self.resource]
        if not user_has_any(request.user, f"{prefix}.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            payload = dict(request.data)
            if self.resource == "bookings":
                payload.setdefault("branch_id", _branch_id(request))
            row = TravelService.create(self.resource, payload, user=request.user, request=request)
        except (TravelError, ObjectDoesNotExist, ValueError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_travel(row), message="Record created.", status=status.HTTP_201_CREATED)


class TravelResourceDetailView(APIView):
    resource = ""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(f"{TravelService.PERMISSION_PREFIX[self.resource]}.view")()]

    def _get(self, request, pk):
        return TravelService.get(self.resource, pk, user=request.user, request=request)

    def get(self, request, pk):
        try:
            return success_response(data=serialize_travel(self._get(request, pk)))
        except ObjectDoesNotExist:
            return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        return self._update(request, pk)

    def put(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        prefix = TravelService.PERMISSION_PREFIX[self.resource]
        if not user_has_any(request.user, f"{prefix}.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            return success_response(data=serialize_travel(TravelService.update(self.resource, self._get(request, pk), request.data, user=request.user, request=request)), message="Record updated.")
        except ObjectDoesNotExist:
            return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        except (TravelError, ValueError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        prefix = TravelService.PERMISSION_PREFIX[self.resource]
        if not user_has_any(request.user, f"{prefix}.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            TravelService.delete(self.resource, self._get(request, pk), user=request.user, request=request)
            return success_response(message="Record deleted.")
        except ObjectDoesNotExist:
            return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)


class BookingStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.view")]

    def post(self, request, pk):
        target = request.data.get("status")
        permission = "travel.bookings.cancel" if target == "cancelled" else "travel.bookings.update"
        if not user_has_any(request.user, permission):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = TravelService.transition_booking(TravelService.get("bookings", pk, user=request.user, request=request), target, user=request.user, request=request)
            return success_response(data=serialize_travel(row), message="Booking status updated.")
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class CommissionStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.commissions.view")]

    def post(self, request, pk):
        target = request.data.get("status")
        permission = "travel.commissions.pay" if target == "paid" else "travel.commissions.approve"
        if not user_has_any(request.user, permission):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = TravelService.transition_commission(TravelService.get("commissions", pk, user=request.user, request=request), target, user=request.user, request=request)
            return success_response(data=serialize_travel(row), message="Commission status updated.")
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class QuotationStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.quotations.update")]

    def post(self, request, pk):
        try:
            row = TravelService.transition_quotation(
                TravelService.get("quotations", pk, user=request.user, request=request),
                request.data.get("status"), user=request.user, request=request,
            )
            return success_response(data=serialize_travel(row), message="Quotation status updated.")
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class QuotationConvertView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.create")]

    def post(self, request, pk):
        try:
            booking = TravelService.convert_quotation_to_booking(
                TravelService.get("quotations", pk, user=request.user, request=request),
                user=request.user, request=request,
            )
            return success_response(data=serialize_travel(booking), message="Quotation converted to booking.")
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class BookingAccountingPreviewView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.view")]

    def get(self, request, pk):
        try:
            booking = TravelService.get("bookings", pk, user=request.user, request=request)
            return success_response(data=TravelAccountingService.suggest_posting(booking, user=request.user))
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class BookingPostAccountingView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.post_accounting")]

    def post(self, request, pk):
        try:
            booking = TravelAccountingService.post_booking(
                booking=TravelService.get("bookings", pk, user=request.user, request=request),
                user=request.user, request=request,
            )
            return success_response(data=serialize_travel(booking), message="Booking posted to ledger.")
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class TravelTransactionPostAccountingView(APIView):
    resource = ""

    def post(self, request, pk):
        prefix = TravelService.PERMISSION_PREFIX[self.resource]
        if not user_has_any(request.user, f"{prefix}.post_accounting"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = TravelService.get(self.resource, pk, user=request.user, request=request)
            posted = (
                TravelAccountingService.post_payment(payment=row, user=request.user, request=request)
                if self.resource == "payments"
                else TravelAccountingService.post_refund(refund=row, user=request.user, request=request)
            )
            return success_response(data=serialize_travel(posted), message="Transaction posted to ledger.")
        except (ObjectDoesNotExist, TravelError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)


class TravelMobileSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.view")]

    def get(self, request):
        branch_id = _branch_id(request)
        today = timezone.localdate()
        bookings = TravelService.list("bookings", user=request.user, request=request, branch_id=branch_id)
        visas = TravelService.list("visas", user=request.user, request=request)
        commissions = TravelService.list("commissions", user=request.user, request=request, branch_id=branch_id)
        return success_response(data={
            "todays_bookings": bookings.filter(travel_date=today).count(),
            "open_visas": visas.filter(status__in=["draft", "submitted"]).count(),
            "pending_commissions": commissions.filter(status__in=["pending", "approved"]).count(),
        })


class TravelMobileBookingsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("travel.bookings.view")]

    def get(self, request):
        rows = TravelService.list("bookings", user=request.user, request=request, branch_id=_branch_id(request)).filter(
            status="confirmed"
        ).filter(Q(travel_date__isnull=True) | Q(travel_date__gte=timezone.localdate()))
        return paginate_queryset(request, rows, serialize_travel)

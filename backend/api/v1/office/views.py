from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.office_rental.serializers import (
    serialize_charge,
    serialize_lease,
    serialize_tenant,
)
from apps.office_rental.services import OfficeError, OfficeService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _can_manage(user):
    return user.has_permission("office_rental.manage")


class OfficeSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def get(self, request):
        data = OfficeService.summary(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return success_response(data=data)


class TenantListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def get(self, request):
        qs = OfficeService.list_tenants(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_tenant(t) for t in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = OfficeService.create_tenant(
                data=data, user=request.user, request=request
            )
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_tenant(row),
            message="Tenant created.",
            status=status.HTTP_201_CREATED,
        )


class LeaseListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def get(self, request):
        qs = OfficeService.list_leases(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_lease(r) for r in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = OfficeService.create_lease(
                data=data, user=request.user, request=request
            )
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_lease(row, include_charges=True),
            message="Lease created.",
            status=status.HTTP_201_CREATED,
        )


class LeaseDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def get(self, request, pk):
        try:
            row = OfficeService.get_lease(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(
                message="Lease not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(data=serialize_lease(row, include_charges=True))


class LeaseActivateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = OfficeService.get_lease(pk=pk, user=request.user, request=request)
            row = OfficeService.activate_lease(lease=row, user=request.user)
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_lease(row, include_charges=True), message="Lease activated."
        )


class LeaseTerminateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = OfficeService.get_lease(pk=pk, user=request.user, request=request)
            row = OfficeService.terminate_lease(
                lease=row,
                user=request.user,
                status=request.data.get("status"),
            )
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_lease(row), message="Lease terminated.")


class LeaseChargeListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def get(self, request, pk):
        try:
            OfficeService.get_lease(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(
                message="Lease not found.", status=status.HTTP_404_NOT_FOUND
            )
        qs = OfficeService.list_charges(
            lease_id=pk, branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_charge(c) for c in items]
        )

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            lease = OfficeService.get_lease(pk=pk, user=request.user, request=request)
            if request.data.get("post_rent"):
                charge = OfficeService.post_rent_charge(
                    lease=lease,
                    user=request.user,
                    period_start=request.data.get("period_start"),
                    period_end=request.data.get("period_end"),
                )
            else:
                charge = OfficeService.add_charge(
                    lease=lease, data=request.data, user=request.user
                )
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_charge(charge),
            message="Charge posted.",
            status=status.HTTP_201_CREATED,
        )


class ChargeInvoiceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            charge = (
                OfficeService.list_charges(user=request.user, request=request)
                .select_related("invoice", "lease", "lease__office_tenant", "branch")
                .get(pk=pk)
            )
            charge = OfficeService.invoice_charge(
                charge=charge,
                payment_method=request.data.get("payment_method") or "on_account",
                payment_reference=(request.data.get("payment_reference") or "").strip(),
                user=request.user,
            )
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_charge(charge), message="Charge invoiced.")


class ChargePaidView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("office_rental.view")]

    def post(self, request, pk):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            charge = (
                OfficeService.list_charges(user=request.user, request=request)
                .select_related("invoice", "lease", "lease__office_tenant", "branch")
                .get(pk=pk)
            )
            charge = OfficeService.mark_charge_paid(
                charge=charge, user=request.user, data=request.data or {}
            )
        except (OfficeError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_charge(charge), message="Charge collected.")

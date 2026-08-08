from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.property_management.serializers import (
    serialize_building,
    serialize_document,
    serialize_maintenance,
    serialize_owner,
    serialize_property,
    serialize_unit,
)
from apps.property_management.services import PropertyError, PropertyService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _can_manage(user):
    return user.has_permission("property_management.manage")


def _can_maintenance(user):
    return (
        user.has_permission("property_management.manage")
        or user.has_permission("property_management.maintenance")
    )


class PropertySummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        data = PropertyService.summary(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return success_response(data=data)


class OwnerListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        qs = PropertyService.list_owners(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_owner(o) for o in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = PropertyService.create_owner(
                data=data, user=request.user, request=request
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_owner(row),
            message="Owner created.",
            status=status.HTTP_201_CREATED,
        )


class PropertyListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        qs = PropertyService.list_properties(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_property(p) for p in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = PropertyService.create_property(
                data=data, user=request.user, request=request
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_property(row),
            message="Property created.",
            status=status.HTTP_201_CREATED,
        )


class BuildingListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        qs = PropertyService.list_buildings(
            branch_id=_branch_id(request),
            property_id=request.query_params.get("property_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_building(b) for b in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = PropertyService.create_building(
                data=data, user=request.user, request=request
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_building(row),
            message="Building created.",
            status=status.HTTP_201_CREATED,
        )


class UnitListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        qs = PropertyService.list_units(
            branch_id=_branch_id(request),
            building_id=request.query_params.get("building_id"),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_unit(u) for u in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = PropertyService.create_unit(
                data=data, user=request.user, request=request
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_unit(row),
            message="Unit created.",
            status=status.HTTP_201_CREATED,
        )


class UnitStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def post(self, request, pk):
        if not _can_maintenance(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            unit = PropertyService.get_unit(pk=pk, user=request.user, request=request)
            unit = PropertyService.set_unit_status(
                unit=unit, status=request.data.get("status"), user=request.user
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_unit(unit), message="Unit updated.")


class MaintenanceListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        qs = PropertyService.list_maintenance(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_maintenance(m) for m in items]
        )

    def post(self, request):
        if not _can_maintenance(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = PropertyService.create_maintenance(
                data=data, user=request.user, request=request
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_maintenance(row),
            message="Maintenance request created.",
            status=status.HTTP_201_CREATED,
        )


class MaintenanceStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def post(self, request, pk):
        if not _can_maintenance(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = PropertyService.get_maintenance(
                pk=pk, user=request.user, request=request
            )
            row = PropertyService.update_maintenance_status(
                request_row=row, status=request.data.get("status"), user=request.user
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_maintenance(row), message="Maintenance updated."
        )


class DocumentListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("property_management.view")]

    def get(self, request):
        qs = PropertyService.list_documents(
            branch_id=_branch_id(request),
            property_id=request.query_params.get("property_id"),
            unit_id=request.query_params.get("unit_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_document(d) for d in items]
        )

    def post(self, request):
        if not _can_manage(request.user):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = PropertyService.create_document(
                data=data, user=request.user, request=request
            )
        except (PropertyError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_document(row),
            message="Document created.",
            status=status.HTTP_201_CREATED,
        )

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_boq
from apps.project_management.services import BoqError, BoqService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


class BoqListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.boq.view")]
    def get(self, request):
        qs = BoqService.list(project_id=request.query_params.get("project_id"), branch_id=request.query_params.get("branch_id") or request.user.branch_id, user=request.user, request=request)
        return paginate_queryset(request, qs, lambda rows: [serialize_boq(row, include_lines=True) for row in rows])
    def post(self, request):
        if not user_has_any(request.user, "project.boq.create"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: row = BoqService.create(data=request.data, user=request.user, request=request)
        except (BoqError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_boq(row, include_lines=True), message="BOQ created.", status=status.HTTP_201_CREATED)


class BoqDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.boq.view")]
    def get(self, request, pk):
        try: return success_response(data=serialize_boq(BoqService.get(pk=pk, user=request.user, request=request), include_lines=True))
        except ObjectDoesNotExist: return error_response(message="BOQ not found.", status=status.HTTP_404_NOT_FOUND)
    def patch(self, request, pk):
        if not user_has_any(request.user, "project.boq.update"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: row = BoqService.update(boq=BoqService.get(pk=pk, user=request.user, request=request), data=request.data, user=request.user, request=request)
        except (BoqError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_boq(row, include_lines=True), message="BOQ updated.")
    def delete(self, request, pk):
        if not user_has_any(request.user, "project.boq.update"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: BoqService.soft_delete(boq=BoqService.get(pk=pk, user=request.user, request=request), user=request.user, request=request)
        except (BoqError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(message="BOQ deleted.")


class BoqStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.boq.view")]
    def post(self, request, pk):
        if not user_has_any(request.user, "project.boq.update", "project.boq.approve"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: row = BoqService.update_status(boq=BoqService.get(pk=pk, user=request.user, request=request), status=request.data.get("status"), user=request.user, request=request)
        except (BoqError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_boq(row, include_lines=True), message="BOQ status updated.")

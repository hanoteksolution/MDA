from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_construction
from apps.project_management.services import ConstructionError, ConstructionService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


class ConstructionListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]
    kind = None
    def get(self, request):
        qs = ConstructionService.list(self.kind, project_id=request.query_params.get("project_id"), branch_id=request.query_params.get("branch_id") or request.user.branch_id, user=request.user, request=request)
        return paginate_queryset(request, qs, lambda rows: [serialize_construction(row) for row in rows])
    def post(self, request):
        if not user_has_any(request.user, "projects.update"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: row = ConstructionService.create(self.kind, data=request.data, user=request.user, request=request)
        except (ConstructionError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_construction(row), message=f"{self.kind.title()} created.", status=status.HTTP_201_CREATED)


class ConstructionDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]
    kind = None
    def get(self, request, pk):
        try: return success_response(data=serialize_construction(ConstructionService.get(self.kind, pk=pk, user=request.user, request=request)))
        except ObjectDoesNotExist: return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
    def patch(self, request, pk):
        if not user_has_any(request.user, "projects.update"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: row = ConstructionService.update(self.kind, row=ConstructionService.get(self.kind, pk=pk, user=request.user, request=request), data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist: return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=serialize_construction(row), message="Record updated.")
    def delete(self, request, pk):
        if not user_has_any(request.user, "projects.delete", "projects.update"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: ConstructionService.soft_delete(row=ConstructionService.get(self.kind, pk=pk, user=request.user, request=request), user=request.user, request=request)
        except ObjectDoesNotExist: return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(message="Record deleted.")


for _kind in ("site", "building", "floor", "unit"):
    globals()[f"{_kind.title()}ListCreateView"] = type(f"{_kind.title()}ListCreateView", (ConstructionListCreateView,), {"kind": _kind})
    globals()[f"{_kind.title()}DetailView"] = type(f"{_kind.title()}DetailView", (ConstructionDetailView,), {"kind": _kind})

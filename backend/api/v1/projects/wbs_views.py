from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_wbs_node
from apps.project_management.services import WbsError, WbsService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _not_found(entity="Record"):
    return error_response(message=f"{entity} not found.", status=status.HTTP_404_NOT_FOUND)


class WbsListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.wbs.view")]

    def get(self, request):
        if request.query_params.get("tree") == "1":
            project_id = request.query_params.get("project_id")
            if not project_id:
                return error_response(message="project_id is required.", status=status.HTTP_400_BAD_REQUEST)
            nodes = list(
                WbsService.list_nodes(
                    project_id=project_id,
                    branch_id=_branch_id(request),
                    user=request.user,
                    request=request,
                )
            )
            return success_response(data=WbsService.build_tree(nodes))

        qs = WbsService.list_nodes(
            project_id=request.query_params.get("project_id"),
            search=request.query_params.get("search"),
            branch_id=_branch_id(request),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_wbs_node(n) for n in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "project.wbs.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = WbsService.create_node(data=request.data, user=request.user, request=request)
        except (WbsError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_wbs_node(row),
            message="WBS node created.",
            status=status.HTTP_201_CREATED,
        )


class WbsDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.wbs.view")]

    def get(self, request, pk):
        try:
            row = WbsService.get_node(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("WBS node")
        return success_response(data=serialize_wbs_node(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "project.wbs.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = WbsService.get_node(pk=pk, user=request.user, request=request)
            row = WbsService.update_node(
                node=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("WBS node")
        except WbsError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_wbs_node(row), message="WBS node updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "project.wbs.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = WbsService.get_node(pk=pk, user=request.user, request=request)
            WbsService.soft_delete_node(node=row, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("WBS node")
        except WbsError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(message="WBS node deleted.")


class WbsMoveView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.wbs.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "project.wbs.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = WbsService.get_node(pk=pk, user=request.user, request=request)
            row = WbsService.move_node(
                node=row,
                parent_id=request.data.get("parent_id"),
                user=request.user,
                request=request,
            )
        except (WbsError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_wbs_node(row), message="WBS node moved.")

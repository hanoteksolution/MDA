from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_task
from apps.project_management.services import ProjectTaskError, ProjectTaskService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class ProjectTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.tasks.view")]

    def get(self, request):
        qs = ProjectTaskService.list_tasks(
            project_id=request.query_params.get("project_id"),
            search=request.query_params.get("search"),
            branch_id=_branch_id(request),
            user=request.user,
            request=request,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_task(row) for row in items])

    def post(self, request):
        if not user_has_any(request.user, "project.tasks.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectTaskService.create_task(data=request.data, user=request.user, request=request)
        except (ProjectTaskError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_task(row), message="Task created.", status=status.HTTP_201_CREATED
        )


class ProjectTaskDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.tasks.view")]

    def get(self, request, pk):
        try:
            row = ProjectTaskService.get_task(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Task not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=serialize_task(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "project.tasks.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectTaskService.get_task(pk=pk, user=request.user, request=request)
            row = ProjectTaskService.update_task(
                task=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Task not found.", status=status.HTTP_404_NOT_FOUND)
        except ProjectTaskError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_task(row), message="Task updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "project.tasks.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectTaskService.get_task(pk=pk, user=request.user, request=request)
            ProjectTaskService.soft_delete_task(task=row, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Task not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(message="Task deleted.")


class ProjectTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.tasks.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "project.tasks.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectTaskService.get_task(pk=pk, user=request.user, request=request)
            row = ProjectTaskService.update_status(
                task=row, status=request.data.get("status"), user=request.user, request=request
            )
        except (ProjectTaskError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_task(row), message="Task status updated.")

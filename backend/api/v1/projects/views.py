from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_project
from apps.project_management.services import ProjectError, ProjectService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _not_found(entity="Record"):
    return error_response(message=f"{entity} not found.", status=status.HTTP_404_NOT_FOUND)


class ProjectSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def get(self, request):
        data = ProjectService.summary(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return success_response(data=data)


class ProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def get(self, request):
        qs = ProjectService.list_projects(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            project_type=request.query_params.get("project_type"),
            search=request.query_params.get("search"),
            include_archived=request.query_params.get("archived") == "1",
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_project(p) for p in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "projects.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = ProjectService.create_project(
                data=data, user=request.user, request=request
            )
        except (ProjectError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_project(row),
            message="Project created.",
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def get(self, request, pk):
        try:
            row = ProjectService.get_project(
                pk=pk,
                user=request.user,
                request=request,
                include_archived=request.query_params.get("archived") == "1",
            )
        except ObjectDoesNotExist:
            return _not_found("Project")
        return success_response(data=serialize_project(row))

    def patch(self, request, pk):
        return self._update(request, pk)

    def put(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        if not user_has_any(request.user, "projects.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectService.get_project(pk=pk, user=request.user, request=request)
            row = ProjectService.update_project(
                project=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Project")
        except ProjectError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_project(row), message="Project updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "projects.delete", "projects.archive"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectService.get_project(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Project")
        ProjectService.soft_delete_project(project=row, user=request.user, request=request)
        return success_response(message="Project archived.")


class ProjectStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def post(self, request, pk):
        if not user_has_any(
            request.user, "projects.update", "projects.approve"
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectService.get_project(pk=pk, user=request.user, request=request)
            row = ProjectService.update_status(
                project=row,
                status=request.data.get("status"),
                user=request.user,
                request=request,
            )
        except (ProjectError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_project(row), message="Status updated.")


class ProjectRestoreView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "projects.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectService.get_project(
                pk=pk, user=request.user, request=request, include_archived=True
            )
            row = ProjectService.restore_project(
                project=row, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Project")
        return success_response(data=serialize_project(row), message="Project restored.")


class ProjectDuplicateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "projects.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectService.get_project(pk=pk, user=request.user, request=request)
            copy = ProjectService.duplicate_project(
                project=row, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Project")
        return success_response(
            data=serialize_project(copy),
            message="Project duplicated.",
            status=status.HTTP_201_CREATED,
        )

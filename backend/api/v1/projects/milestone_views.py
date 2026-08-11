from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_milestone
from apps.project_management.services import ProjectMilestoneError, ProjectMilestoneService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class ProjectMilestoneListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.milestones.view")]

    def get(self, request):
        qs = ProjectMilestoneService.list_milestones(
            project_id=request.query_params.get("project_id"),
            search=request.query_params.get("search"),
            branch_id=_branch_id(request),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_milestone(row) for row in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "project.milestones.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectMilestoneService.create_milestone(
                data=request.data, user=request.user, request=request
            )
        except (ProjectMilestoneError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_milestone(row),
            message="Milestone created.",
            status=status.HTTP_201_CREATED,
        )


class ProjectMilestoneDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.milestones.view")]

    def get(self, request, pk):
        try:
            row = ProjectMilestoneService.get_milestone(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Milestone not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=serialize_milestone(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "project.milestones.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectMilestoneService.get_milestone(pk=pk, user=request.user, request=request)
            row = ProjectMilestoneService.update_milestone(
                milestone=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Milestone not found.", status=status.HTTP_404_NOT_FOUND)
        except ProjectMilestoneError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_milestone(row), message="Milestone updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "project.milestones.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectMilestoneService.get_milestone(pk=pk, user=request.user, request=request)
            ProjectMilestoneService.soft_delete_milestone(
                milestone=row, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Milestone not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(message="Milestone deleted.")


class ProjectMilestoneStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.milestones.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "project.milestones.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectMilestoneService.get_milestone(pk=pk, user=request.user, request=request)
            row = ProjectMilestoneService.update_status(
                milestone=row, status=request.data.get("status"), user=request.user, request=request
            )
        except (ProjectMilestoneError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_milestone(row), message="Milestone status updated.")

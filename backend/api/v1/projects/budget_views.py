from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_budget
from apps.project_management.services import BudgetError, ProjectBudgetService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _not_found(entity="Record"):
    return error_response(message=f"{entity} not found.", status=status.HTTP_404_NOT_FOUND)


class ProjectBudgetListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.budget.view")]

    def get(self, request):
        qs = ProjectBudgetService.list_budgets(
            project_id=request.query_params.get("project_id"),
            branch_id=_branch_id(request),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [serialize_budget(b, include_lines=True) for b in items],
        )

    def post(self, request):
        if not user_has_any(request.user, "project.budget.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectBudgetService.create_budget(
                data=request.data, user=request.user, request=request
            )
        except (BudgetError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        row = ProjectBudgetService.get_budget(pk=row.id, user=request.user, request=request)
        return success_response(
            data=serialize_budget(row, include_lines=True),
            message="Budget created.",
            status=status.HTTP_201_CREATED,
        )


class ProjectBudgetDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.budget.view")]

    def get(self, request, pk):
        try:
            row = ProjectBudgetService.get_budget(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Budget")
        return success_response(data=serialize_budget(row, include_lines=True))

    def patch(self, request, pk):
        if not user_has_any(request.user, "project.budget.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectBudgetService.get_budget(pk=pk, user=request.user, request=request)
            row = ProjectBudgetService.update_budget(
                budget=row, data=request.data, user=request.user, request=request
            )
            row = ProjectBudgetService.get_budget(pk=row.id, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Budget")
        except BudgetError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_budget(row, include_lines=True), message="Budget updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "project.budget.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectBudgetService.get_budget(pk=pk, user=request.user, request=request)
            ProjectBudgetService.soft_delete_budget(
                budget=row, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Budget")
        except BudgetError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(message="Budget deleted.")


class ProjectBudgetStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.budget.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "project.budget.update", "project.budget.approve"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = ProjectBudgetService.get_budget(pk=pk, user=request.user, request=request)
            row = ProjectBudgetService.update_status(
                budget=row,
                status=request.data.get("status"),
                user=request.user,
                request=request,
            )
            row = ProjectBudgetService.get_budget(pk=row.id, user=request.user, request=request)
        except (BudgetError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_budget(row, include_lines=True),
            message="Budget status updated.",
        )

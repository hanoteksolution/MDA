from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers.project_operations_serializers import serialize_project_operation
from apps.project_management.services.project_operations_service import (
    ProjectAccountingService, ProjectOperationError,
)
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class ProjectOperationListCreateView(APIView):
    service = None
    permission_prefix = ""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(f"{self.permission_prefix}.view")()]

    def get(self, request):
        qs = self.service.list(project_id=request.query_params.get("project_id"), branch_id=_branch_id(request), user=request.user, request=request)
        return paginate_queryset(request, qs, lambda items: [serialize_project_operation(row) for row in items])

    def post(self, request):
        if not user_has_any(request.user, f"{self.permission_prefix}.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = self.service.create(data=request.data, user=request.user, request=request)
        except (ProjectOperationError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_project_operation(row), message="Created.", status=status.HTTP_201_CREATED)


class ProjectOperationDetailView(APIView):
    service = None
    permission_prefix = ""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(f"{self.permission_prefix}.view")()]

    def get(self, request, pk):
        try:
            return success_response(data=serialize_project_operation(self.service.get(pk=pk, user=request.user, request=request)))
        except ObjectDoesNotExist:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        if not user_has_any(request.user, f"{self.permission_prefix}.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = self.service.update(row=self.service.get(pk=pk, user=request.user, request=request), data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)
        except ProjectOperationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_project_operation(row), message="Updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, f"{self.permission_prefix}.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            self.service.soft_delete(row=self.service.get(pk=pk, user=request.user, request=request), user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(message="Deleted.")


class ProjectOperationStatusView(APIView):
    service = None
    permission_prefix = ""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(f"{self.permission_prefix}.view")()]

    def post(self, request, pk):
        if not user_has_any(request.user, f"{self.permission_prefix}.update", f"{self.permission_prefix}.approve"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = self.service.transition_status(row=self.service.get(pk=pk, user=request.user, request=request), status=request.data.get("status"), user=request.user, request=request)
        except (ProjectOperationError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_project_operation(row), message="Status updated.")


class ProjectInvoiceAccountingPreviewView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.invoices.view")]
    service = None

    def post(self, request, pk):
        try:
            invoice = self.service.get(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Invoice not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(
            data=ProjectAccountingService.suggest_posting(invoice, user=request.user)
        )


class ProjectInvoicePostAccountingView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.invoices.view")]
    service = None

    def post(self, request, pk):
        if not user_has_any(request.user, "project.invoices.update", "project.invoices.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            invoice = self.service.get(pk=pk, user=request.user, request=request)
            invoice = ProjectAccountingService.post_invoice(
                invoice=invoice, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Invoice not found.", status=status.HTTP_404_NOT_FOUND)
        except ProjectOperationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_project_operation(invoice),
            message="Invoice posted to central ledger.",
        )

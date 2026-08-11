from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_attendance, serialize_wage, serialize_worker
from apps.project_management.services import WorkforceError, WorkforceService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


SERIALIZERS = {"worker": serialize_worker, "attendance": serialize_attendance, "wage": serialize_wage}
PERMS = {"worker": ("project.workers.view", "project.workers.create"), "attendance": ("project.workers.view", "project.workers.create"), "wage": ("project.wages.view", "project.wages.create")}


class WorkforceListCreateView(APIView):
    kind = None
    def get_permissions(self): return [IsAuthenticated(), HasPermission(PERMS[self.kind][0])()]
    def get(self, request):
        qs = WorkforceService.list(self.kind, project_id=request.query_params.get("project_id"), branch_id=request.query_params.get("branch_id") or request.user.branch_id, user=request.user, request=request)
        return paginate_queryset(request, qs, lambda rows: [SERIALIZERS[self.kind](row) for row in rows])
    def post(self, request):
        if not user_has_any(request.user, PERMS[self.kind][1]): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            fn = {"worker": WorkforceService.create_worker, "attendance": WorkforceService.create_attendance, "wage": WorkforceService.create_wage}[self.kind]
            row = fn(data=request.data, user=request.user, request=request)
        except (WorkforceError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=SERIALIZERS[self.kind](row), message=f"{self.kind.title()} created.", status=status.HTTP_201_CREATED)


class WorkforceDetailView(APIView):
    kind = None
    def get_permissions(self): return [IsAuthenticated(), HasPermission(PERMS[self.kind][0])()]
    def get(self, request, pk):
        try: return success_response(data=SERIALIZERS[self.kind](WorkforceService.get(self.kind, pk=pk, user=request.user, request=request)))
        except ObjectDoesNotExist: return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
    def patch(self, request, pk):
        if not user_has_any(request.user, PERMS[self.kind][1]): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = WorkforceService.get(self.kind, pk=pk, user=request.user, request=request)
            row = WorkforceService.update_worker(worker=row, data=request.data, user=request.user, request=request) if self.kind == "worker" else WorkforceService.update(self.kind, row=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist: return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=SERIALIZERS[self.kind](row), message="Record updated.")
    def delete(self, request, pk):
        if not user_has_any(request.user, PERMS[self.kind][1]): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: WorkforceService.soft_delete(row=WorkforceService.get(self.kind, pk=pk, user=request.user, request=request), user=request.user, request=request)
        except ObjectDoesNotExist: return error_response(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(message="Record deleted.")


class WorkerRatesView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.workers.view")]
    def get(self, request, pk):
        try: worker = WorkforceService.get("worker", pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist: return error_response(message="Worker not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=[{"id": str(rate.id), "rate": float(rate.rate), "effective_from": rate.effective_from.isoformat(), "effective_to": rate.effective_to.isoformat() if rate.effective_to else None, "notes": rate.notes or ""} for rate in worker.rate_history.all()])


class WageStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.wages.view")]
    def post(self, request, pk):
        if not user_has_any(request.user, "project.wages.approve", "project.wages.pay"): return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try: row = WorkforceService.update_wage_status(wage=WorkforceService.get("wage", pk=pk, user=request.user, request=request), status=request.data.get("status"), user=request.user, request=request)
        except (WorkforceError, ObjectDoesNotExist) as exc: return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_wage(row), message="Wage status updated.")


for _kind in ("worker", "attendance", "wage"):
    globals()[f"{_kind.title()}ListCreateView"] = type(f"{_kind.title()}ListCreateView", (WorkforceListCreateView,), {"kind": _kind})
    globals()[f"{_kind.title()}DetailView"] = type(f"{_kind.title()}DetailView", (WorkforceDetailView,), {"kind": _kind})

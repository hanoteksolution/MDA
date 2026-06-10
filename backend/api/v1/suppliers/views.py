from decimal import Decimal

from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.suppliers.models import Supplier
from apps.suppliers.serializers.supplier_serializers import serialize_supplier
from apps.suppliers.services.supplier_service import SupplierService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _parse_supplier_data(data):
    parsed = {}
    for src in ("company_name", "contact_person", "email", "phone", "address", "payment_terms", "is_active"):
        if src in data:
            parsed[src] = data[src]
    if "payment_terms" in parsed:
        parsed["payment_terms"] = int(parsed["payment_terms"])
    return parsed


class SupplierListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("suppliers.view")]

    def get(self, request):
        is_active = request.query_params.get("is_active")
        qs = SupplierService.list(
            search=request.query_params.get("search"),
            is_active=is_active == "true" if is_active else None,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_supplier(s) for s in items])

    def post(self, request):
        if not request.user.has_permission("suppliers.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = _parse_supplier_data(request.data)
        if not data.get("company_name"):
            return error_response(message="Company name is required.", status=status.HTTP_400_BAD_REQUEST)
        supplier = SupplierService.create(data=data, user=request.user)
        return success_response(
            data=serialize_supplier(supplier),
            message="Supplier created.",
            status=status.HTTP_201_CREATED,
        )


class SupplierDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("suppliers.view")]

    def get(self, request, pk):
        supplier = SupplierService.list().get(pk=pk)
        return success_response(data=serialize_supplier(supplier))

    def put(self, request, pk):
        if not request.user.has_permission("suppliers.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        supplier = SupplierService.list().get(pk=pk)
        supplier = SupplierService.update(instance=supplier, data=_parse_supplier_data(request.data), user=request.user)
        return success_response(data=serialize_supplier(supplier), message="Supplier updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("suppliers.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        supplier = SupplierService.list().get(pk=pk)
        supplier.soft_delete(user=request.user)
        return success_response(message="Supplier deleted.")


class SupplierSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("suppliers.view")]

    def get(self, request):
        qs = Supplier.active_objects()
        return success_response(
            data={
                "total": qs.count(),
                "active": qs.filter(is_active=True).count(),
                "payables": float(qs.aggregate(t=Sum("outstanding_balance"))["t"] or 0),
            }
        )

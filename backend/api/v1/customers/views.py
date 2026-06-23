from decimal import Decimal

from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.customers.models import Customer
from apps.customers.serializers.customer_serializers import serialize_customer
from apps.customers.services.customer_service import CustomerService
from core.services.analytics_service import AnalyticsService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _parse_customer_data(data):
    parsed = {}
    for src in ("full_name", "email", "phone", "address", "customer_type", "is_active", "branch_id"):
        if src in data:
            parsed[src] = data[src]
    if "credit_limit" in data:
        parsed["credit_limit"] = Decimal(str(data["credit_limit"]))
    return parsed


class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("customers.view")]

    def get(self, request):
        is_active = request.query_params.get("is_active")
        qs = CustomerService.list(
            search=request.query_params.get("search"),
            customer_type=request.query_params.get("customer_type"),
            is_active=is_active == "true" if is_active else None,
            branch_id=request.query_params.get("branch_id"),
        )
        return paginate_queryset(request, qs, lambda items: [serialize_customer(c) for c in items])

    def post(self, request):
        if not request.user.has_permission("customers.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = _parse_customer_data(request.data)
        if not data.get("full_name"):
            return error_response(message="Full name is required.", status=status.HTTP_400_BAD_REQUEST)
        customer = CustomerService.create(data=data, user=request.user)
        return success_response(
            data=serialize_customer(customer),
            message="Customer created.",
            status=status.HTTP_201_CREATED,
        )


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("customers.view")]

    def get(self, request, pk):
        customer = CustomerService.list().get(pk=pk)
        return success_response(data=serialize_customer(customer))

    def put(self, request, pk):
        if not request.user.has_permission("customers.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        customer = CustomerService.list().get(pk=pk)
        customer = CustomerService.update(instance=customer, data=_parse_customer_data(request.data), user=request.user)
        return success_response(data=serialize_customer(customer), message="Customer updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("customers.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        customer = CustomerService.list().get(pk=pk)
        customer.soft_delete(user=request.user)
        return success_response(message="Customer deleted.")


class CustomerSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("customers.view")]

    def get(self, request):
        qs = Customer.active_objects()
        return success_response(
            data={
                "total": qs.count(),
                "active": qs.filter(is_active=True).count(),
                "credit_outstanding": float(qs.aggregate(t=Sum("outstanding_balance"))["t"] or 0),
            }
        )


class CustomerPrintReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("customers.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        data = AnalyticsService.get_customers_report_print(
            branch_id=branch_id,
            search=request.query_params.get("search"),
            customer_type=request.query_params.get("customer_type"),
            user=request.user,
        )
        return success_response(data=data)

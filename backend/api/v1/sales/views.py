from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.sales.models import Invoice, Quotation
from apps.sales.serializers.sales_serializers import serialize_invoice, serialize_quotation
from apps.sales.services.pos_service import PosService
from apps.sales.services.sales_service import InvoiceService, QuotationService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _parse_items(raw_items):
    return [
        {
            "product_id": item["product_id"],
            "quantity": Decimal(str(item["quantity"])),
            "unit_price": Decimal(str(item["unit_price"])),
        }
        for item in (raw_items or [])
    ]


class QuotationListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request):
        qs = QuotationService.list(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
            customer_id=request.query_params.get("customer_id"),
            branch_id=request.query_params.get("branch_id"),
        )
        return paginate_queryset(request, qs, lambda items: [serialize_quotation(q) for q in items])

    def post(self, request):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        if not data.get("customer_id"):
            return error_response(message="Customer is required.", status=status.HTTP_400_BAD_REQUEST)
        items = _parse_items(data.pop("items", []))
        if not items:
            return error_response(message="At least one line item is required.", status=status.HTTP_400_BAD_REQUEST)
        customer_id = data.pop("customer_id")
        branch_id = data.pop("branch_id", None)
        q = QuotationService.create(
            data={**data, "customer_id": customer_id, "branch_id": branch_id},
            items=items,
            user=request.user,
        )
        return success_response(
            data=serialize_quotation(q, include_items=True),
            message="Quotation created.",
            status=status.HTTP_201_CREATED,
        )


class QuotationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request, pk):
        q = QuotationService.list().get(pk=pk)
        return success_response(data=serialize_quotation(q, include_items=True))

    def put(self, request, pk):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        q = QuotationService.list().get(pk=pk)
        data = dict(request.data)
        customer_id = data.pop("customer_id", None)
        branch_id = data.pop("branch_id", None)
        items = _parse_items(data.pop("items")) if "items" in request.data else None
        update_data = {**data}
        if customer_id:
            update_data["customer_id"] = customer_id
        if branch_id:
            update_data["branch_id"] = branch_id
        q = QuotationService.update(instance=q, data=update_data, items=items, user=request.user)
        return success_response(data=serialize_quotation(q, include_items=True), message="Quotation updated.")


class InvoiceListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request):
        qs = InvoiceService.list(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
            customer_id=request.query_params.get("customer_id"),
            branch_id=request.query_params.get("branch_id"),
        )
        return paginate_queryset(request, qs, lambda items: [serialize_invoice(inv) for inv in items])

    def post(self, request):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        if not data.get("customer_id"):
            return error_response(message="Customer is required.", status=status.HTTP_400_BAD_REQUEST)
        items = _parse_items(data.pop("items", []))
        if not items:
            return error_response(message="At least one line item is required.", status=status.HTTP_400_BAD_REQUEST)
        customer_id = data.pop("customer_id")
        branch_id = data.pop("branch_id", None)
        inv = InvoiceService.create(
            data={**data, "customer_id": customer_id, "branch_id": branch_id},
            items=items,
            user=request.user,
        )
        return success_response(
            data=serialize_invoice(inv, include_items=True),
            message="Invoice created.",
            status=status.HTTP_201_CREATED,
        )


class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request, pk):
        inv = InvoiceService.list().get(pk=pk)
        return success_response(data=serialize_invoice(inv, include_items=True))

    def put(self, request, pk):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        inv = InvoiceService.list().get(pk=pk)
        data = dict(request.data)
        customer_id = data.pop("customer_id", None)
        branch_id = data.pop("branch_id", None)
        items = _parse_items(data.pop("items")) if "items" in request.data else None
        update_data = {**data}
        if customer_id:
            update_data["customer_id"] = customer_id
        if branch_id:
            update_data["branch_id"] = branch_id
        inv = InvoiceService.update(instance=inv, data=update_data, items=items, user=request.user)
        return success_response(data=serialize_invoice(inv, include_items=True), message="Invoice updated.")


class InvoiceReceiptView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request, pk):
        inv = InvoiceService.list().get(pk=pk)
        receipt = PosService.receipt_from_invoice(invoice=inv, user=request.user)
        return success_response(data=receipt)


class InvoiceDeliveryNoteView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request, pk):
        inv = InvoiceService.list().get(pk=pk)
        note = PosService.delivery_note_from_invoice(invoice=inv, user=request.user)
        return success_response(data=note)


class SalesSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.view")]

    def get(self, request):
        return success_response(data=InvoiceService.summary())

from datetime import datetime
from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.purchases.models import PurchaseOrder
from apps.purchases.serializers.purchase_serializers import serialize_purchase_order
from apps.purchases.services.purchase_service import PurchaseOrderService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _parse_items(raw_items):
    items = []
    for item in raw_items or []:
        items.append({
            "product_id": item["product_id"],
            "quantity_ordered": Decimal(str(item["quantity_ordered"])),
            "unit_cost": Decimal(str(item["unit_cost"])),
        })
    return items


def _parse_po_data(data):
    parsed = {}
    if "supplier_id" in data:
        parsed["supplier_id"] = data["supplier_id"]
    if "branch_id" in data:
        parsed["branch_id"] = data["branch_id"]
    if "status" in data:
        parsed["status"] = data["status"]
    if "expected_date" in data:
        parsed["expected_date"] = data["expected_date"] or None
    if "notes" in data:
        parsed["notes"] = data["notes"]
    if "order_date" in data:
        parsed["order_date"] = data["order_date"]
    return parsed


class PurchaseOrderListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("purchases.view")]

    def get(self, request):
        qs = PurchaseOrderService.list(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
            supplier_id=request.query_params.get("supplier_id"),
            branch_id=request.query_params.get("branch_id"),
            user=request.user,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_purchase_order(po) for po in items])

    def post(self, request):
        if not request.user.has_permission("purchases.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = _parse_po_data(request.data)
        if not data.get("supplier_id"):
            return error_response(message="Supplier is required.", status=status.HTTP_400_BAD_REQUEST)
        items = _parse_items(request.data.get("items", []))
        if not items:
            return error_response(message="At least one line item is required.", status=status.HTTP_400_BAD_REQUEST)
        po = PurchaseOrderService.create(data=data, items=items, user=request.user)
        return success_response(
            data=serialize_purchase_order(po, include_items=True),
            message="Purchase order created.",
            status=status.HTTP_201_CREATED,
        )


class PurchaseOrderDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("purchases.view")]

    def get(self, request, pk):
        po = PurchaseOrderService.list(user=request.user).get(pk=pk)
        return success_response(data=serialize_purchase_order(po, include_items=True))

    def put(self, request, pk):
        if not request.user.has_permission("purchases.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        po = PurchaseOrderService.list(user=request.user).get(pk=pk)
        if po.status == PurchaseOrder.STATUS_RECEIVED:
            return error_response(message="Received orders cannot be edited.", status=status.HTTP_400_BAD_REQUEST)
        data = _parse_po_data(request.data)
        supplier_id = data.pop("supplier_id", None)
        branch_id = data.pop("branch_id", None)
        items = _parse_items(request.data.get("items")) if "items" in request.data else None
        update_data = {**data}
        if supplier_id:
            update_data["supplier_id"] = supplier_id
        if branch_id:
            update_data["branch_id"] = branch_id
        po = PurchaseOrderService.update(instance=po, data=update_data, items=items, user=request.user)
        return success_response(data=serialize_purchase_order(po, include_items=True), message="Purchase order updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("purchases.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        po = PurchaseOrderService.list(user=request.user).get(pk=pk)
        if po.status not in (PurchaseOrder.STATUS_DRAFT, PurchaseOrder.STATUS_CANCELLED):
            return error_response(message="Only draft orders can be deleted.", status=status.HTTP_400_BAD_REQUEST)
        po.soft_delete(user=request.user)
        return success_response(message="Purchase order deleted.")


class PurchaseOrderSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("purchases.view")]

    def get(self, request):
        return success_response(data=PurchaseOrderService.summary(user=request.user))


class PurchaseOrderReceivePreviewView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("purchases.view")]

    def get(self, request, pk):
        from apps.inventory.services.receiving_service import PurchaseReceivingService, ReceivingError

        try:
            data = PurchaseReceivingService.preview(purchase_order_id=pk, user=request.user)
        except PurchaseOrder.DoesNotExist:
            return error_response(message="Purchase order not found.", status=status.HTTP_404_NOT_FOUND)
        except ReceivingError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)


class PurchaseOrderReceiveView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("purchases.create")]

    def post(self, request, pk):
        from datetime import date as date_cls
        from uuid import UUID

        from apps.inventory.services.receiving_service import (
            PurchaseReceivingService,
            ReceiveLineInput,
            ReceivingError,
        )

        warehouse_id = request.data.get("warehouse_id")
        if not warehouse_id:
            return error_response(message="warehouse_id is required.", status=status.HTTP_400_BAD_REQUEST)
        raw_lines = request.data.get("lines") or []
        if not raw_lines:
            return error_response(message="At least one receive line is required.", status=status.HTTP_400_BAD_REQUEST)

        lines = []
        try:
            for item in raw_lines:
                expiry = item.get("expiry_date")
                if expiry and isinstance(expiry, str):
                    expiry = date_cls.fromisoformat(expiry)
                lines.append(
                    ReceiveLineInput(
                        product_id=UUID(str(item["product_id"])),
                        quantity_received=Decimal(str(item["quantity_received"])),
                        unit_cost=Decimal(str(item["unit_cost"])) if item.get("unit_cost") is not None else None,
                        batch_number=item.get("batch_number"),
                        expiry_date=expiry,
                    )
                )
        except (KeyError, ValueError, TypeError) as exc:
            return error_response(message=f"Invalid receive line: {exc}", status=status.HTTP_400_BAD_REQUEST)

        try:
            data = PurchaseReceivingService.receive(
                purchase_order_id=pk,
                warehouse_id=warehouse_id,
                lines=lines,
                user=request.user,
                notes=request.data.get("notes") or "",
            )
        except PurchaseOrder.DoesNotExist:
            return error_response(message="Purchase order not found.", status=status.HTTP_404_NOT_FOUND)
        except ReceivingError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data, message="Goods received.")

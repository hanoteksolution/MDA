from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.inventory.models import Warehouse
from apps.inventory.serializers import (
    serialize_adjustment,
    serialize_inventory,
    serialize_warehouse,
)
from apps.inventory.services.inventory_service import InventoryService, WarehouseService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


class WarehouseListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        branch_id = request.query_params.get("branch") or getattr(request.user.branch, "id", None)
        qs = WarehouseService.list_warehouses(branch_id=branch_id, user=request.user)
        return paginate_queryset(request, qs, lambda items: [serialize_warehouse(w) for w in items])

    def post(self, request):
        if not request.user.has_permission("inventory.adjust"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        wh = WarehouseService.create(data=request.data, user=request.user)
        return success_response(data=serialize_warehouse(wh), message="Warehouse created.", status=status.HTTP_201_CREATED)


class WarehouseDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def put(self, request, pk):
        if not request.user.has_permission("inventory.adjust"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        wh = WarehouseService.list_warehouses(user=request.user).get(pk=pk)
        wh = WarehouseService.update(warehouse=wh, data=request.data, user=request.user)
        return success_response(data=serialize_warehouse(wh), message="Warehouse updated.")


class InventoryListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        qs = InventoryService.list_inventory(
            warehouse_id=request.query_params.get("warehouse"),
            search=request.query_params.get("search"),
            low_stock=request.query_params.get("low_stock") == "true",
            branch_id=branch_id,
            user=request.user,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class InventorySummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        return success_response(data=InventoryService.get_summary(branch_id=branch_id, user=request.user))


class LowStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        qs = InventoryService.get_low_stock(branch_id=branch_id, user=request.user)
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class OutOfStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        qs = InventoryService.get_out_of_stock(branch_id=branch_id, user=request.user)
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class AdjustmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        qs = InventoryService.list_adjustments(user=request.user)
        return paginate_queryset(request, qs, lambda items: [serialize_adjustment(a) for a in items])

    def post(self, request):
        if not request.user.has_permission("inventory.adjust"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        warehouse = Warehouse.active_objects().get(id=request.data["warehouse_id"])
        branch = warehouse.branch
        items = request.data.get("items", [])
        if not items:
            return error_response(message="At least one item is required.", status=status.HTTP_400_BAD_REQUEST)
        adj = InventoryService.create_adjustment(
            warehouse=warehouse,
            branch=branch,
            reason=request.data.get("reason", ""),
            items=items,
            user=request.user,
        )
        return success_response(
            data=serialize_adjustment(adj),
            message="Adjustment confirmed.",
            status=status.HTTP_201_CREATED,
        )


class TransferListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        from apps.inventory.serializers import serialize_transfer
        from apps.inventory.services.transfer_service import StockTransferService

        qs = StockTransferService.list(
            status=request.query_params.get("status"),
            branch_id=request.query_params.get("branch_id")
            or getattr(getattr(request.user, "branch", None), "id", None),
            user=request.user,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_transfer(t) for t in items]
        )

    def post(self, request):
        from apps.inventory.serializers import serialize_transfer
        from apps.inventory.services.transfer_service import (
            StockTransferService,
            TransferError,
            TransferLineInput,
        )

        if not request.user.has_permission("inventory.transfer"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        source_id = request.data.get("source_warehouse_id")
        dest_id = request.data.get("destination_warehouse_id")
        if not source_id or not dest_id:
            return error_response(
                message="source_warehouse_id and destination_warehouse_id are required.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        lines = []
        for item in request.data.get("lines") or []:
            lines.append(
                TransferLineInput(
                    product_id=item["product_id"],
                    quantity=Decimal(str(item["quantity"])),
                )
            )
        try:
            transfer = StockTransferService.create_draft(
                source_warehouse_id=source_id,
                destination_warehouse_id=dest_id,
                branch_id=request.data.get("branch_id"),
                user=request.user,
                notes=request.data.get("notes") or "",
                lines=lines or None,
            )
        except TransferError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_transfer(transfer, include_lines=True),
            message="Transfer draft created.",
            status=status.HTTP_201_CREATED,
        )


class TransferDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request, pk):
        from apps.inventory.serializers import serialize_transfer
        from apps.inventory.services.transfer_service import StockTransferService

        transfer = StockTransferService.list(user=request.user).get(pk=pk)
        return success_response(data=serialize_transfer(transfer, include_lines=True))


class TransferConfirmView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        from apps.inventory.serializers import serialize_transfer
        from apps.inventory.services.transfer_service import StockTransferService, TransferError

        try:
            transfer = StockTransferService.confirm(transfer_id=pk, user=request.user)
        except TransferError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_transfer(transfer, include_lines=True),
            message="Transfer confirmed.",
        )


class TransferCancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        from apps.inventory.serializers import serialize_transfer
        from apps.inventory.services.transfer_service import StockTransferService, TransferError

        try:
            transfer = StockTransferService.cancel(transfer_id=pk, user=request.user)
        except TransferError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_transfer(transfer, include_lines=True),
            message="Transfer cancelled.",
        )

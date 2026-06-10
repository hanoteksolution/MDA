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
        qs = WarehouseService.list_warehouses(branch_id=branch_id)
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
        wh = WarehouseService.list_warehouses().get(pk=pk)
        wh = WarehouseService.update(warehouse=wh, data=request.data, user=request.user)
        return success_response(data=serialize_warehouse(wh), message="Warehouse updated.")


class InventoryListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        qs = InventoryService.list_inventory(
            warehouse_id=request.query_params.get("warehouse"),
            search=request.query_params.get("search"),
            low_stock=request.query_params.get("low_stock") == "true",
        )
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class InventorySummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        branch_id = getattr(request.user.branch, "id", None)
        return success_response(data=InventoryService.get_summary(branch_id=branch_id))


class LowStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        qs = InventoryService.get_low_stock()
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class OutOfStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        qs = InventoryService.get_out_of_stock()
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class AdjustmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        qs = InventoryService.list_adjustments()
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

from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.inventory.models import Warehouse
from apps.inventory.serializers import (
    serialize_adjustment,
    serialize_inventory,
    serialize_movement,
    serialize_warehouse,
)
from apps.inventory.services.branch_stock_service import (
    branch_stock_dashboard,
    product_availability,
)
from apps.inventory.services.inventory_service import InventoryService, WarehouseService
from core.branching import get_branch_scope, has_branch_permission
from core.responses.api_response import error_response, success_response
from core.tenancy import apply_tenant_scope, resolve_acting_tenant
from core.utils.pagination import paginate_queryset
from permissions.base import HasAnyPermission, HasPermission


def _scope(request, permission="inventory.view"):
    return get_branch_scope(request, permission=permission)


class WarehouseListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        scope = _scope(request)
        branch_id = request.query_params.get("branch") or scope.branch_id
        qs = WarehouseService.list_warehouses(branch_id=branch_id, user=request.user)
        if branch_id is None:
            qs = scope.filter(qs, field_name="branch_id")
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
    """Branch scope is resolved via ``core.branching``, not the legacy ``request.user.branch``
    — a user with only ``UserBranchAccess`` grants (no ``User.branch``) now sees the
    inventory their access actually covers, instead of an unfiltered/empty list."""

    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        scope = _scope(request)
        qs = InventoryService.list_inventory(
            warehouse_id=request.query_params.get("warehouse"),
            search=request.query_params.get("search"),
            low_stock=request.query_params.get("low_stock") == "true",
            branch_id=scope.branch_id,
            module_code=request.query_params.get("module_code"),
            user=request.user,
        )
        if scope.branch_id is None:
            qs = scope.filter(qs, field_name="warehouse__branch_id")
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class InventorySummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        scope = _scope(request)
        return success_response(
            data=InventoryService.get_summary(
                branch_id=scope.branch_id,
                module_code=request.query_params.get("module_code"),
                user=request.user,
            )
        )


class LowStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        scope = _scope(request)
        qs = InventoryService.get_low_stock(
            branch_id=scope.branch_id,
            module_code=request.query_params.get("module_code"),
            user=request.user,
        )
        if scope.branch_id is None:
            qs = scope.filter(qs, field_name="warehouse__branch_id")
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class OutOfStockView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        scope = _scope(request)
        qs = InventoryService.get_out_of_stock(
            branch_id=scope.branch_id,
            module_code=request.query_params.get("module_code"),
            user=request.user,
        )
        if scope.branch_id is None:
            qs = scope.filter(qs, field_name="warehouse__branch_id")
        return paginate_queryset(request, qs, lambda items: [serialize_inventory(i) for i in items])


class BranchStockDashboardView(APIView):
    """Branch inventory dashboard figures: SKUs, value, low/out-of-stock, reserved,
    recent movement count. Requires a single resolved branch — ambiguous ("all
    branches") requests are rejected rather than silently summed across branches,
    since the dashboard is framed as "this branch's" numbers."""

    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        from apps.settings_app.models import Branch

        scope = _scope(request)
        branch_id = scope.require_single("the branch inventory dashboard")
        branch = Branch.active_objects().filter(pk=branch_id).first()
        if branch is None:
            return error_response(message="Branch not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(
            data=branch_stock_dashboard(
                branch=branch, module_code=request.query_params.get("module_code")
            )
        )


class ProductAvailabilityView(APIView):
    """Cross-branch stock visibility (BRANCH_INVENTORY.md §7). Read-only: never a
    mutation capability. ``inventory.cross_branch_view`` gates the ``other_branches``
    list independently of ``inventory.view``/``inventory.adjust`` — a cashier who
    cannot open the inventory list can still see "is this available elsewhere"."""

    # inventory.view OR inventory.cross_branch_view — a cashier holds only the
    # latter and must still reach this endpoint (see class docstring).
    permission_classes = [IsAuthenticated, HasAnyPermission("inventory.view", "inventory.cross_branch_view")]

    def get(self, request, product_id):
        from apps.products.models import Product
        from apps.settings_app.models import Branch

        # No permission filter here: resolving "which branch is this user acting in"
        # for an availability check must not require inventory.view specifically —
        # that would defeat the point of granting cross_branch_view to roles (like
        # cashier) that never held inventory.view in the first place.
        scope = get_branch_scope(request, permission=None)
        branch_id = scope.require_single("checking stock availability")
        branch = Branch.active_objects().filter(pk=branch_id).first()
        if branch is None:
            return error_response(message="Branch not found.", status=status.HTTP_404_NOT_FOUND)

        product = apply_tenant_scope(
            Product.active_objects(), request=request, user=request.user
        ).filter(pk=product_id).first()
        if product is None:
            return error_response(message="Product not found.", status=status.HTTP_404_NOT_FOUND)

        tenant = resolve_acting_tenant(request=request, user=request.user)
        # Branch-scoped, not a bare global check: a branch access profile can narrow
        # this permission exactly like any other (core.branching's rule — a profile
        # only ever narrows, never widens), so a user whose profile in *this* branch
        # doesn't include cross_branch_view sees only their own branch's figures,
        # even if their role holds the permission globally.
        include_other = has_branch_permission(request.user, "inventory.cross_branch_view", branch)
        data = product_availability(
            product=product,
            current_branch=branch,
            tenant=tenant,
            include_other_branches=include_other,
        )
        return success_response(data=data)


class ProductMovementHistoryView(APIView):
    """Read-only ledger history for a product's stock-detail screen. Scoped to the
    caller's branch access — a movement in a branch the caller cannot see is not
    listed, matching every other Phase 2/3 endpoint's isolation guarantee."""

    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request, product_id):
        from apps.products.models import Product

        product = apply_tenant_scope(
            Product.active_objects(), request=request, user=request.user
        ).filter(pk=product_id).first()
        if product is None:
            return error_response(message="Product not found.", status=status.HTTP_404_NOT_FOUND)

        scope = _scope(request)
        qs = InventoryService.list_movements(product=product, user=request.user, request=request)
        qs = scope.filter(qs, field_name="branch_id")
        return paginate_queryset(request, qs, lambda items: [serialize_movement(m) for m in items])


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


# --------------------------------------------------------------------------- #
# Phase 4: inter-branch transfer requests
# --------------------------------------------------------------------------- #


class BranchTransferListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def get(self, request):
        from apps.inventory.serializers import serialize_branch_transfer
        from apps.inventory.services.branch_transfer_service import BranchTransferService

        qs = BranchTransferService.list(
            status=request.query_params.get("status"),
            branch_id=request.query_params.get("branch_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_branch_transfer(t, include_lines=False) for t in items])

    def post(self, request):
        from apps.inventory.serializers import serialize_branch_transfer
        from apps.inventory.services.branch_transfer_service import (
            BranchTransferError,
            BranchTransferService,
            TransferLineInput,
        )

        data = request.data
        lines = [
            TransferLineInput(product_id=item["product_id"], quantity=Decimal(str(item["quantity"])))
            for item in data.get("lines") or []
        ]
        try:
            req = BranchTransferService.request_transfer(
                source_branch_id=data.get("source_branch_id"),
                destination_branch_id=data.get("destination_branch_id"),
                source_warehouse_id=data.get("source_warehouse_id"),
                destination_warehouse_id=data.get("destination_warehouse_id"),
                lines=lines,
                user=request.user,
                notes=data.get("notes") or "",
            )
        except BranchTransferError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_branch_transfer(req), message="Transfer requested.", status=status.HTTP_201_CREATED
        )


class BranchTransferDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def get(self, request, pk):
        from apps.inventory.serializers import serialize_branch_transfer
        from apps.inventory.services.branch_transfer_service import BranchTransferService

        req = get_object_or_404(BranchTransferService.list(user=request.user, request=request), pk=pk)
        return success_response(data=serialize_branch_transfer(req))


def _branch_transfer_action(request, pk, action, **kwargs):
    from apps.inventory.serializers import serialize_branch_transfer
    from apps.inventory.services.branch_transfer_service import BranchTransferError, BranchTransferService

    method = getattr(BranchTransferService, action)
    try:
        req = method(request_id=pk, user=request.user, **kwargs)
    except BranchTransferError as exc:
        return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
    return success_response(data=serialize_branch_transfer(req), message=f"Transfer {action}d.")


class BranchTransferApproveView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        return _branch_transfer_action(request, pk, "approve")


class BranchTransferRejectView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        return _branch_transfer_action(request, pk, "reject", reason=request.data.get("reason", ""))


class BranchTransferReserveView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        return _branch_transfer_action(request, pk, "reserve")


class BranchTransferDispatchView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        return _branch_transfer_action(request, pk, "dispatch")


class BranchTransferReceiveView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        from apps.inventory.services.branch_transfer_service import TransferLineInput

        lines = None
        if request.data.get("lines"):
            lines = [
                TransferLineInput(product_id=item["product_id"], quantity=Decimal(str(item["quantity"])))
                for item in request.data["lines"]
            ]
        return _branch_transfer_action(
            request, pk, "receive", lines=lines, idempotency_key=request.data.get("idempotency_key", "")
        )


class BranchTransferCompleteView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        return _branch_transfer_action(request, pk, "complete")


class BranchTransferCancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.transfer")]

    def post(self, request, pk):
        return _branch_transfer_action(request, pk, "cancel")

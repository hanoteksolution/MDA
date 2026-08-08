from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.inventory.models import Warehouse
from apps.pharmacy.services.batch_service import BatchError, BatchService
from apps.pharmacy.services.prescription_service import (
    PrescriptionError,
    PrescriptionService,
)
from apps.platform.services.module_feature_service import ModuleFeatureService
from apps.products.models import Product
from core.responses.api_response import error_response, success_response
from core.tenancy import apply_tenant_scope
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _require_pharmacy_feature(request, feature: str):
    if ModuleFeatureService.tenant_has_feature(
        "pharmacy", feature, user=request.user, request=request
    ):
        return None
    return error_response(
        message=f"Pharmacy feature '{feature}' is not enabled for this business.",
        status=status.HTTP_403_FORBIDDEN,
        code="MODULE_FEATURE_DISABLED",
        details={"module": "pharmacy", "feature": feature},
    )


class PharmacySummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def get(self, request):
        data = BatchService.summary(user=request.user, request=request)
        features = ModuleFeatureService.resolve_features(
            "pharmacy", user=request.user, request=request
        )
        data["features"] = features
        if not features.get("batches"):
            data["batch_count"] = 0
            data["total_quantity"] = 0
            data["categories"] = []
        if not features.get("expiry_alerts"):
            data["expired_count"] = 0
            data["expiring_count"] = 0
        if not features.get("prescriptions"):
            data["prescriptions_active"] = 0
            data["prescriptions_dispensed"] = 0
            data["prescriptions_total"] = 0
        return success_response(data=data)


class PharmacyCategoryListView(APIView):
    """Inventory categories that appear on pharmacy batches (no parallel catalog)."""

    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def get(self, request):
        denied = _require_pharmacy_feature(request, "batches")
        if denied:
            return denied
        return success_response(data=BatchService.list_categories(user=request.user, request=request))


class BatchListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def get(self, request):
        denied = _require_pharmacy_feature(request, "batches")
        if denied:
            return denied
        qs = BatchService.list_batches(
            user=request.user,
            request=request,
            product_id=request.query_params.get("product_id"),
            warehouse_id=request.query_params.get("warehouse_id"),
            category_id=request.query_params.get("category_id"),
            expiring_within_days=request.query_params.get("expiring_within_days"),
            include_zero=request.query_params.get("include_zero") == "true",
            search=request.query_params.get("search"),
        )
        return paginate_queryset(
            request, qs, lambda items: [BatchService.serialize(b) for b in items]
        )

    def post(self, request):
        denied = _require_pharmacy_feature(request, "batches")
        if denied:
            return denied
        if not request.user.has_permission("pharmacy.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        product_id = data.get("product_id")
        warehouse_id = data.get("warehouse_id")
        if not product_id or not warehouse_id:
            return error_response(
                message="product_id and warehouse_id are required.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        product = apply_tenant_scope(Product.active_objects(), user=request.user).get(pk=product_id)
        warehouse = apply_tenant_scope(Warehouse.active_objects(), user=request.user).get(
            pk=warehouse_id
        )
        from datetime import date as date_cls

        expiry = data.get("expiry_date") or None
        if expiry and isinstance(expiry, str):
            expiry = date_cls.fromisoformat(expiry)
        manufacturing = data.get("manufacturing_date") or None
        if manufacturing and isinstance(manufacturing, str):
            manufacturing = date_cls.fromisoformat(manufacturing)
        try:
            batch = BatchService.receive_stock(
                product=product,
                warehouse=warehouse,
                quantity=data.get("quantity") or 0,
                batch_number=data.get("batch_number"),
                expiry_date=expiry,
                manufacturing_date=manufacturing,
                cost_price=data.get("cost_price"),
                user=request.user,
                notes=data.get("notes") or "",
            )
        except BatchError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=BatchService.serialize(batch),
            message="Batch recorded.",
            status=status.HTTP_201_CREATED,
        )


class BatchExpiringView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def get(self, request):
        denied = _require_pharmacy_feature(request, "expiry_alerts")
        if denied:
            return denied
        within = request.query_params.get("within_days")
        qs = BatchService.expiring(
            user=request.user,
            request=request,
            within_days=int(within) if within else None,
            warehouse_id=request.query_params.get("warehouse_id"),
            category_id=request.query_params.get("category_id"),
        )
        return paginate_queryset(
            request, qs, lambda items: [BatchService.serialize(b) for b in items]
        )


class BatchFefoPreviewView(APIView):
    """Preview FEFO allocation for a product quantity (POS hint)."""

    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def get(self, request):
        denied = _require_pharmacy_feature(request, "batches")
        if denied:
            return denied
        product_id = request.query_params.get("product_id")
        warehouse_id = request.query_params.get("warehouse_id")
        quantity = request.query_params.get("quantity") or "1"
        if not product_id or not warehouse_id:
            return error_response(
                message="product_id and warehouse_id are required.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        product = apply_tenant_scope(Product.active_objects(), user=request.user).get(pk=product_id)
        warehouse = apply_tenant_scope(Warehouse.active_objects(), user=request.user).get(
            pk=warehouse_id
        )
        try:
            plan = BatchService.plan_fefo(
                product=product, warehouse=warehouse, quantity=quantity
            )
        except BatchError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=[
                {
                    "batch_id": str(batch.id),
                    "batch_number": batch.batch_number,
                    "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
                    "quantity": float(qty),
                }
                for batch, qty in plan
            ]
        )


class PrescriptionListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def get(self, request):
        denied = _require_pharmacy_feature(request, "prescriptions")
        if denied:
            return denied
        qs = PrescriptionService.list(
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
            category_id=request.query_params.get("category_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [PrescriptionService.serialize(r) for r in items],
        )

    def post(self, request):
        denied = _require_pharmacy_feature(request, "prescriptions")
        if denied:
            return denied
        if not (
            request.user.has_permission("pharmacy.manage")
            or request.user.has_permission("pharmacy.dispense")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            rx = PrescriptionService.create(
                data=request.data, user=request.user, request=request
            )
        except PrescriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PrescriptionService.serialize(rx),
            message="Prescription created.",
            status=status.HTTP_201_CREATED,
        )


class PrescriptionDispenseView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pharmacy.view")]

    def post(self, request, pk):
        denied = _require_pharmacy_feature(request, "prescriptions")
        if denied:
            return denied
        if not (
            request.user.has_permission("pharmacy.dispense")
            or request.user.has_permission("pharmacy.manage")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            fill_lines = None
            raw_lines = request.data.get("lines")
            if isinstance(raw_lines, list):
                fill_lines = {
                    str(row.get("id") or row.get("line_id")): row.get("quantity")
                    for row in raw_lines
                    if row.get("id") or row.get("line_id")
                }
            fill_quantities = request.data.get("fill_quantities")
            if isinstance(fill_quantities, dict):
                fill_quantities = {str(k): v for k, v in fill_quantities.items()}
            else:
                fill_quantities = None

            rx = PrescriptionService.dispense(
                prescription_id=pk,
                user=request.user,
                request=request,
                notes=request.data.get("notes") or "",
                deduct_stock=True,
                warehouse_id=request.data.get("warehouse_id"),
                fill_lines=fill_lines,
                fill_quantities=fill_quantities,
            )
        except PrescriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PrescriptionService.serialize(rx),
            message="Prescription dispensed.",
        )

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum

from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class PurchaseOrderService:
    @staticmethod
    def list(*, search=None, status=None, supplier_id=None, branch_id=None, user=None, request=None):
        qs = PurchaseOrder.active_objects().select_related("supplier", "branch", "ordered_by", "project", "wbs_node").prefetch_related("items__product")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) | Q(supplier__company_name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("-order_date", "-created_at")

    @staticmethod
    def _next_order_number(*, branch: Branch) -> str:
        count = PurchaseOrder.objects.filter(branch=branch).count() + 1
        return f"PO-{branch.code}-{count:05d}"

    @staticmethod
    def _recalculate_totals(*, order: PurchaseOrder):
        agg = order.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or Decimal("0")
        order.subtotal = subtotal
        order.tax_amount = Decimal("0")
        order.total_amount = subtotal + order.tax_amount
        order.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    @staticmethod
    @transaction.atomic
    def create(*, data, items, user=None):
        branch_id = data.pop("branch_id", None)
        supplier_id = data.pop("supplier_id")
        branch_qs = apply_tenant_scope(Branch.active_objects(), user=user)
        branch = branch_qs.get(pk=branch_id) if branch_id else branch_qs.filter(is_default=True).first()
        if not branch:
            branch = branch_qs.first()

        payload = stamp_tenant_id(dict(data), user=user)
        if not payload.get("tenant_id") and getattr(branch, "tenant_id", None):
            payload["tenant_id"] = branch.tenant_id
        if payload.get("project_id"):
            from apps.project_management.services.project_service import ProjectService
            project = ProjectService.get_project(pk=payload["project_id"], user=user)
            if project.tenant_id != payload.get("tenant_id"):
                raise ValueError("Project must belong to the purchase order tenant.")
            if payload.get("wbs_node_id"):
                from apps.project_management.models import WbsNode
                if not WbsNode.active_objects().filter(pk=payload["wbs_node_id"], project=project).exists():
                    raise ValueError("WBS node does not belong to the project.")
        order = PurchaseOrder.objects.create(
            order_number=PurchaseOrderService._next_order_number(branch=branch),
            supplier_id=supplier_id,
            branch=branch,
            ordered_by=user,
            created_by=user,
            **payload,
        )
        for item in items or []:
            PurchaseOrderItem.objects.create(
                purchase_order=order,
                product_id=item["product_id"],
                quantity_ordered=item["quantity_ordered"],
                unit_cost=item["unit_cost"],
                created_by=user,
            )
        PurchaseOrderService._recalculate_totals(order=order)
        return PurchaseOrderService.list(user=user).get(pk=order.pk)

    @staticmethod
    @transaction.atomic
    def update(*, instance, data, items=None, user=None):
        branch_id = data.pop("branch_id", None)
        supplier_id = data.pop("supplier_id", None)
        if supplier_id:
            instance.supplier_id = supplier_id
        if branch_id:
            instance.branch_id = branch_id
        for key, value in data.items():
            if key not in ("order_number",):
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()

        if items is not None:
            instance.items.all().delete()
            for item in items:
                PurchaseOrderItem.objects.create(
                    purchase_order=instance,
                    product_id=item["product_id"],
                    quantity_ordered=item["quantity_ordered"],
                    unit_cost=item["unit_cost"],
                    created_by=user,
                )
            PurchaseOrderService._recalculate_totals(order=instance)

        return PurchaseOrderService.list(user=user).get(pk=instance.pk)

    @staticmethod
    def summary(*, user=None, request=None):
        qs = apply_tenant_scope(PurchaseOrder.active_objects(), user=user, request=request)
        by_status = qs.values("status").annotate(count=Count("id"))
        status_map = {row["status"]: row["count"] for row in by_status}
        return {
            "open_orders": status_map.get(PurchaseOrder.STATUS_ORDERED, 0) + status_map.get(PurchaseOrder.STATUS_DRAFT, 0),
            "pending_receipt": status_map.get(PurchaseOrder.STATUS_ORDERED, 0),
            "total_orders": qs.count(),
            "month_total": float(
                qs.filter(status=PurchaseOrder.STATUS_RECEIVED).aggregate(t=Sum("total_amount"))["t"] or 0
            ),
        }

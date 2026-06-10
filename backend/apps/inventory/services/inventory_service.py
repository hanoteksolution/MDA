from decimal import Decimal

from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.audit.repositories.audit_repository import AuditRepository
from apps.inventory.models import (
    Inventory,
    InventoryAdjustment,
    InventoryAdjustmentItem,
    InventoryTransaction,
    StockMovement,
    Warehouse,
)
from apps.products.models import Product


class WarehouseService:
    @staticmethod
    def list_warehouses(*, branch_id=None, is_active=None):
        qs = Warehouse.active_objects().select_related("branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("name")

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None):
        if data.get("is_default"):
            Warehouse.objects.filter(branch_id=data["branch_id"]).update(is_default=False)
        return Warehouse.objects.create(**data, created_by=user)

    @staticmethod
    @transaction.atomic
    def update(*, warehouse, data, user=None):
        if data.get("is_default"):
            Warehouse.objects.filter(branch=warehouse.branch).update(is_default=False)
        for key, value in data.items():
            setattr(warehouse, key, value)
        warehouse.updated_by = user
        warehouse.save()
        return warehouse


class InventoryService:
    @staticmethod
    def list_inventory(*, warehouse_id=None, search=None, low_stock=False):
        qs = (
            Inventory.active_objects()
            .select_related("product", "product__category", "warehouse")
            .filter(product__deleted_at__isnull=True)
        )
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if search:
            qs = qs.filter(
                Q(product__name__icontains=search)
                | Q(product__sku__icontains=search)
                | Q(product__barcode__icontains=search)
            )
        if low_stock:
            qs = qs.filter(quantity__lte=F("product__minimum_stock"))
        return qs.order_by("product__name")

    @staticmethod
    def get_low_stock():
        return InventoryService.list_inventory(low_stock=True).filter(quantity__gt=0)

    @staticmethod
    def get_out_of_stock():
        return InventoryService.list_inventory().filter(quantity__lte=0)

    @staticmethod
    def get_summary(*, branch_id=None):
        qs = Inventory.active_objects().select_related("product")
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        agg = qs.aggregate(
            total_items=Count("id"),
            total_quantity=Sum("quantity"),
            inventory_value=Sum(F("quantity") * F("product__cost_price")),
        )
        low_stock_count = InventoryService.get_low_stock().count()
        out_of_stock_count = InventoryService.get_out_of_stock().count()
        return {
            "total_items": agg["total_items"] or 0,
            "total_quantity": float(agg["total_quantity"] or 0),
            "inventory_value": float(agg["inventory_value"] or 0),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
        }

    @staticmethod
    @transaction.atomic
    def ensure_inventory_record(*, product, warehouse, user=None):
        inv, created = Inventory.active_objects().get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={"quantity": 0, "created_by": user},
        )
        return inv

    @staticmethod
    @transaction.atomic
    def create_adjustment(*, warehouse, branch, reason, items, user=None):
        count = InventoryAdjustment.objects.count() + 1
        adjustment_number = f"ADJ-{branch.code}-{count:06d}"

        adjustment = InventoryAdjustment.objects.create(
            adjustment_number=adjustment_number,
            warehouse=warehouse,
            branch=branch,
            reason=reason,
            status="confirmed",
            created_by=user,
        )

        for item in items:
            product = Product.active_objects().get(id=item["product_id"])
            inv = InventoryService.ensure_inventory_record(
                product=product, warehouse=warehouse, user=user
            )
            qty_before = inv.quantity
            qty_after = Decimal(str(item["quantity_after"]))
            qty_change = qty_after - qty_before

            inv.quantity = qty_after
            inv.updated_by = user
            inv.save(update_fields=["quantity", "updated_by", "updated_at"])

            InventoryAdjustmentItem.objects.create(
                adjustment=adjustment,
                product=product,
                quantity_before=qty_before,
                quantity_after=qty_after,
                quantity_change=qty_change,
                created_by=user,
            )

            StockMovement.objects.create(
                product=product,
                warehouse=warehouse,
                movement_type="adjustment",
                quantity=qty_change,
                reference_type="adjustment",
                reference_id=adjustment.id,
                notes=reason,
                created_by=user,
            )

            InventoryTransaction.objects.create(
                inventory=inv,
                transaction_type="in" if qty_change >= 0 else "out",
                quantity_before=qty_before,
                quantity_after=qty_after,
                quantity_change=qty_change,
                reference_type="adjustment",
                reference_id=adjustment.id,
                created_by=user,
            )

        AuditRepository.create(
            user=user,
            action="create",
            module="inventory",
            entity_type="InventoryAdjustment",
            entity_id=adjustment.id,
            new_values={"adjustment_number": adjustment_number, "items_count": len(items)},
        )
        return adjustment

    @staticmethod
    def list_adjustments():
        return (
            InventoryAdjustment.active_objects()
            .select_related("warehouse", "branch")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

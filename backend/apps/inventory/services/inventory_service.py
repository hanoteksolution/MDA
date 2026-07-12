from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum

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
    @transaction.atomic
    def backfill_missing_inventory(*, user=None, warehouse=None):
        """Create qty=0 inventory rows for products that have none (so they appear in Stock)."""
        wh = warehouse or (
            Warehouse.active_objects().filter(is_default=True).first()
            or Warehouse.active_objects().first()
        )
        if not wh:
            return 0
        existing_ids = set(
            Inventory.active_objects()
            .filter(warehouse=wh)
            .values_list("product_id", flat=True)
        )
        missing = list(Product.active_objects().exclude(id__in=existing_ids))
        for product in missing:
            InventoryService.ensure_inventory_record(product=product, warehouse=wh, user=user)
        return len(missing)

    @staticmethod
    @transaction.atomic
    def dedupe_inventory(*, user=None, preferred_branch_id=None):
        """Merge duplicate inventory rows so each product×warehouse appears once.

        Also collapses same-named warehouses (e.g. two 'Main Warehouse' rows for
        Cappuccino on different branch records) into one keeper row.
        """
        merged = 0

        # Exact product + warehouse duplicates
        by_exact: dict[tuple, list] = defaultdict(list)
        for inv in (
            Inventory.active_objects()
            .select_related("warehouse")
            .order_by("product_id", "warehouse_id", "-quantity", "created_at")
        ):
            by_exact[(inv.product_id, inv.warehouse_id)].append(inv)

        for group in by_exact.values():
            if len(group) < 2:
                continue
            keeper = group[0]
            keeper.quantity = sum((r.quantity for r in group), Decimal("0"))
            keeper.reserved_quantity = sum((r.reserved_quantity for r in group), Decimal("0"))
            keeper.damaged_quantity = sum((r.damaged_quantity for r in group), Decimal("0"))
            keeper.returned_quantity = sum((r.returned_quantity for r in group), Decimal("0"))
            keeper.updated_by = user
            keeper.save(
                update_fields=[
                    "quantity",
                    "reserved_quantity",
                    "damaged_quantity",
                    "returned_quantity",
                    "updated_by",
                    "updated_at",
                ]
            )
            for extra in group[1:]:
                extra.soft_delete(user=user)
                merged += 1

        # Same product + same warehouse display name (across duplicate branch records)
        by_name: dict[tuple, list] = defaultdict(list)
        for inv in Inventory.active_objects().select_related("warehouse"):
            key = (
                inv.product_id,
                (inv.warehouse.name or "").strip().lower(),
                (inv.warehouse.code or "").strip().lower(),
            )
            by_name[key].append(inv)

        for group in by_name.values():
            if len(group) < 2:
                continue

            def _keeper_score(r):
                prefer = 1 if preferred_branch_id and str(r.warehouse.branch_id) == str(preferred_branch_id) else 0
                return (prefer, r.quantity, r.warehouse.is_default, r.created_at)

            group.sort(key=_keeper_score, reverse=True)
            keeper = group[0]
            for extra in group[1:]:
                keeper.quantity += extra.quantity
                keeper.reserved_quantity += extra.reserved_quantity
                keeper.damaged_quantity += extra.damaged_quantity
                keeper.returned_quantity += extra.returned_quantity
                extra.soft_delete(user=user)
                merged += 1
            keeper.updated_by = user
            keeper.save(
                update_fields=[
                    "quantity",
                    "reserved_quantity",
                    "damaged_quantity",
                    "returned_quantity",
                    "updated_by",
                    "updated_at",
                ]
            )

        return merged

    @staticmethod
    def list_inventory(*, warehouse_id=None, search=None, low_stock=False, ensure_rows=True, branch_id=None):
        if ensure_rows:
            InventoryService.dedupe_inventory(preferred_branch_id=branch_id)
            InventoryService.backfill_missing_inventory(
                warehouse=(
                    Warehouse.active_objects().filter(pk=warehouse_id).first()
                    if warehouse_id
                    else (
                        Warehouse.active_objects().filter(branch_id=branch_id, is_default=True).first()
                        if branch_id
                        else None
                    )
                )
            )
        qs = (
            Inventory.active_objects()
            .select_related("product", "product__category", "warehouse")
            .filter(product__deleted_at__isnull=True)
        )
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        if search:
            qs = qs.filter(
                Q(product__name__icontains=search)
                | Q(product__sku__icontains=search)
                | Q(product__barcode__icontains=search)
            )
        if low_stock:
            # At or below minimum — includes out-of-stock (qty 0) when min >= 0
            qs = qs.filter(quantity__lte=F("product__minimum_stock"))
        return qs.order_by("product__name")

    @staticmethod
    def get_low_stock(*, branch_id=None):
        """Products at or below minimum stock (includes zero / out of stock)."""
        return InventoryService.list_inventory(low_stock=True, branch_id=branch_id)

    @staticmethod
    def get_out_of_stock(*, branch_id=None):
        return InventoryService.list_inventory(branch_id=branch_id).filter(quantity__lte=0)

    @staticmethod
    def get_summary(*, branch_id=None):
        InventoryService.dedupe_inventory(preferred_branch_id=branch_id)
        qs = Inventory.active_objects().select_related("product")
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        agg = qs.aggregate(
            total_items=Count("id"),
            total_quantity=Sum("quantity"),
            # Retail/on-hand value at selling price (what the stock is worth to sell)
            inventory_value=Sum(F("quantity") * F("product__selling_price")),
        )
        # Low stock = at/below min but still some units; out of stock counted separately
        low_stock_count = qs.filter(
            quantity__gt=0,
            quantity__lte=F("product__minimum_stock"),
        ).count()
        out_of_stock_count = qs.filter(quantity__lte=0).count()
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
        inv = (
            Inventory.objects.filter(
                product=product,
                warehouse=warehouse,
                deleted_at__isnull=True,
            )
            .order_by("-quantity", "created_at")
            .first()
        )
        if inv:
            return inv

        soft = (
            Inventory.objects.filter(product=product, warehouse=warehouse)
            .exclude(deleted_at__isnull=True)
            .order_by("-updated_at")
            .first()
        )
        if soft:
            soft.restore()
            soft.updated_by = user
            soft.save(update_fields=["updated_by", "updated_at"])
            return soft

        try:
            return Inventory.objects.create(
                product=product,
                warehouse=warehouse,
                quantity=0,
                created_by=user,
            )
        except IntegrityError:
            return (
                Inventory.objects.filter(product=product, warehouse=warehouse)
                .order_by("deleted_at")
                .first()
            )

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

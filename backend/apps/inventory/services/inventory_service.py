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
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class WarehouseService:
    @staticmethod
    def list_warehouses(*, branch_id=None, is_active=None, user=None, request=None):
        qs = Warehouse.active_objects().select_related("branch")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("name")

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None):
        payload = stamp_tenant_id(dict(data), user=user)
        if data.get("is_default"):
            Warehouse.objects.filter(branch_id=data["branch_id"]).update(is_default=False)
        return Warehouse.objects.create(**payload, created_by=user)

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
    def list_inventory(
        *,
        warehouse_id=None,
        search=None,
        low_stock=False,
        ensure_rows=True,
        branch_id=None,
        user=None,
        request=None,
    ):
        if ensure_rows:
            InventoryService.dedupe_inventory(preferred_branch_id=branch_id, user=user)
            wh_qs = apply_tenant_scope(Warehouse.active_objects(), user=user, request=request)
            InventoryService.backfill_missing_inventory(
                warehouse=(
                    wh_qs.filter(pk=warehouse_id).first()
                    if warehouse_id
                    else (
                        wh_qs.filter(branch_id=branch_id, is_default=True).first()
                        if branch_id
                        else None
                    )
                ),
                user=user,
            )
        qs = (
            Inventory.active_objects()
            .select_related("product", "product__category", "warehouse")
            .filter(product__deleted_at__isnull=True)
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
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
    def get_reorder_candidates(*, branch_id=None, user=None, request=None):
        """Products at/below minimum stock — hook for future Celery reorder alerts."""
        return InventoryService.list_inventory(
            branch_id=branch_id,
            low_stock=True,
            ensure_rows=False,
            user=user,
            request=request,
        )

    @staticmethod
    def get_out_of_stock(*, branch_id=None, user=None, request=None):
        return InventoryService.list_inventory(
            branch_id=branch_id, user=user, request=request
        ).filter(quantity__lte=0)

    @staticmethod
    def get_summary(*, branch_id=None, user=None, request=None):
        InventoryService.dedupe_inventory(preferred_branch_id=branch_id, user=user)
        qs = Inventory.active_objects().select_related("product")
        qs = apply_tenant_scope(qs, user=user, request=request)
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
            tenant_id = (
                getattr(warehouse, "tenant_id", None)
                or getattr(product, "tenant_id", None)
            )
            return Inventory.objects.create(
                product=product,
                warehouse=warehouse,
                quantity=0,
                tenant_id=tenant_id,
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
            tenant_id=getattr(warehouse, "tenant_id", None) or getattr(branch, "tenant_id", None),
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
    def resolve_warehouse_for_branch(*, branch=None, branch_id=None):
        """Default warehouse for a sales branch (falls back to any default warehouse)."""
        bid = branch_id or (getattr(branch, "id", None) if branch is not None else None)
        if bid:
            wh = (
                Warehouse.active_objects().filter(branch_id=bid, is_default=True).first()
                or Warehouse.active_objects().filter(branch_id=bid).first()
            )
            if wh:
                return wh
        return (
            Warehouse.active_objects().filter(is_default=True).first()
            or Warehouse.active_objects().first()
        )

    @staticmethod
    def invoice_stock_tracked(*, invoice_id) -> bool:
        return StockMovement.objects.filter(
            reference_type="invoice",
            reference_id=invoice_id,
            deleted_at__isnull=True,
            movement_type__in=["sale", "return"],
        ).exists()

    @staticmethod
    def invoice_reserve_tracked(*, invoice_id) -> bool:
        return InventoryTransaction.objects.filter(
            reference_type="invoice",
            reference_id=invoice_id,
            transaction_type="reserve",
            deleted_at__isnull=True,
        ).exists()

    @staticmethod
    @transaction.atomic
    def reserve_invoice_quantities(
        *,
        warehouse,
        quantity_by_product: dict,
        reference_id,
        user=None,
        notes="",
    ):
        if not warehouse or not quantity_by_product:
            return
        for product_id, qty in quantity_by_product.items():
            qty = Decimal(str(qty))
            if qty <= 0:
                continue
            product = Product.active_objects().filter(pk=product_id).first() or Product.objects.filter(
                pk=product_id
            ).first()
            if product is None:
                continue
            InventoryService.reserve_quantity(
                product=product,
                warehouse=warehouse,
                quantity=qty,
                reference_type="invoice",
                reference_id=reference_id,
                user=user,
                notes=notes,
            )

    @staticmethod
    @transaction.atomic
    def unreserve_invoice_quantities(
        *,
        warehouse,
        quantity_by_product: dict,
        reference_id,
        user=None,
        notes="",
    ):
        if not warehouse or not quantity_by_product:
            return
        for product_id, qty in quantity_by_product.items():
            qty = Decimal(str(qty))
            if qty <= 0:
                continue
            product = Product.active_objects().filter(pk=product_id).first() or Product.objects.filter(
                pk=product_id
            ).first()
            if product is None:
                continue
            InventoryService.unreserve_quantity(
                product=product,
                warehouse=warehouse,
                quantity=qty,
                reference_type="invoice",
                reference_id=reference_id,
                user=user,
                notes=notes,
            )

    @staticmethod
    @transaction.atomic
    def consume_invoice_reserved(
        *,
        warehouse,
        quantity_by_product: dict,
        reference_id,
        user=None,
        notes="",
    ):
        if not warehouse or not quantity_by_product:
            return
        for product_id, qty in quantity_by_product.items():
            qty = Decimal(str(qty))
            if qty <= 0:
                continue
            product = Product.active_objects().filter(pk=product_id).first() or Product.objects.filter(
                pk=product_id
            ).first()
            if product is None:
                continue
            InventoryService.consume_reserved(
                product=product,
                warehouse=warehouse,
                quantity=qty,
                reference_type="invoice",
                reference_id=reference_id,
                user=user,
                notes=notes,
            )

    @staticmethod
    def _locked_inventory(*, product, warehouse, user=None):
        if warehouse is None:
            raise ValueError("No warehouse available for inventory update.")
        inv = InventoryService.ensure_inventory_record(
            product=product, warehouse=warehouse, user=user
        )
        return Inventory.objects.select_for_update().filter(pk=inv.pk).first()

    @staticmethod
    @transaction.atomic
    def reserve_quantity(
        *,
        product,
        warehouse,
        quantity,
        reference_type="invoice",
        reference_id=None,
        user=None,
        notes="",
        allow_negative_available=False,
    ):
        """Increase reserved_quantity without changing on-hand quantity.

        Used by POS hold (STEP 12 wiring). available = quantity - reserved.
        """
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Reserve quantity must be positive.")

        inv = InventoryService._locked_inventory(
            product=product, warehouse=warehouse, user=user
        )
        available = inv.quantity - inv.reserved_quantity
        if not allow_negative_available and qty > available:
            raise ValueError(
                f"Insufficient available stock to reserve for {product.sku} "
                f"(available={available}, requested={qty})."
            )

        before = inv.reserved_quantity
        inv.reserved_quantity = before + qty
        inv.updated_by = user
        inv.save(update_fields=["reserved_quantity", "updated_by", "updated_at"])

        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="reserve",
            quantity_before=before,
            quantity_after=inv.reserved_quantity,
            quantity_change=qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )
        if notes:
            StockMovement.objects.create(
                product=product,
                warehouse=warehouse,
                movement_type="adjustment",
                quantity=Decimal("0"),
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"RESERVE: {notes}",
                created_by=user,
            )
        return inv

    @staticmethod
    @transaction.atomic
    def unreserve_quantity(
        *,
        product,
        warehouse,
        quantity,
        reference_type="invoice",
        reference_id=None,
        user=None,
        notes="",
    ):
        """Decrease reserved_quantity (release hold or convert hold → sale)."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Unreserve quantity must be positive.")

        inv = InventoryService._locked_inventory(
            product=product, warehouse=warehouse, user=user
        )
        before = inv.reserved_quantity
        if qty > before:
            qty = before
        inv.reserved_quantity = before - qty
        inv.updated_by = user
        inv.save(update_fields=["reserved_quantity", "updated_by", "updated_at"])

        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="unreserve",
            quantity_before=before,
            quantity_after=inv.reserved_quantity,
            quantity_change=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )
        if notes:
            StockMovement.objects.create(
                product=product,
                warehouse=warehouse,
                movement_type="adjustment",
                quantity=Decimal("0"),
                reference_type=reference_type,
                reference_id=reference_id,
                notes=f"UNRESERVE: {notes}",
                created_by=user,
            )
        return inv

    @staticmethod
    @transaction.atomic
    def consume_reserved(
        *,
        product,
        warehouse,
        quantity,
        reference_type="invoice",
        reference_id=None,
        user=None,
        notes="",
    ):
        """Convert a reservation into a sale: unreserve then deduct on-hand."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            return None
        InventoryService.unreserve_quantity(
            product=product,
            warehouse=warehouse,
            quantity=qty,
            reference_type=reference_type,
            reference_id=reference_id,
            user=user,
            notes=notes,
        )
        return InventoryService.apply_sale_delta(
            product=product,
            warehouse=warehouse,
            quantity_delta=-qty,
            reference_id=reference_id,
            user=user,
            notes=notes or "Consume reserved stock",
        )

    @staticmethod
    @transaction.atomic
    def apply_sale_delta(
        *,
        product,
        warehouse,
        quantity_delta,
        reference_id=None,
        reference_type="invoice",
        user=None,
        notes="",
    ):
        """
        Apply a sale-related stock change.

        quantity_delta < 0 → units sold (movement_type=sale)
        quantity_delta > 0 → units returned / sale reversed (movement_type=return)
        quantity_delta == 0 → no-op
        """
        delta = Decimal(str(quantity_delta))
        if delta == 0:
            return None
        if warehouse is None:
            raise ValueError("No warehouse available to update stock for this sale.")

        inv = InventoryService._locked_inventory(
            product=product, warehouse=warehouse, user=user
        )
        qty_before = inv.quantity
        qty_after = qty_before + delta
        inv.quantity = qty_after
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        movement_type = "sale" if delta < 0 else "return"
        txn_type = "out" if delta < 0 else "return"
        ref_type = reference_type or "invoice"

        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=delta,
            reference_type=ref_type,
            reference_id=reference_id,
            notes=notes,
            created_by=user,
        )
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type=txn_type,
            quantity_before=qty_before,
            quantity_after=qty_after,
            quantity_change=delta,
            reference_type=ref_type,
            reference_id=reference_id,
            created_by=user,
        )
        # Pharmacy FEFO when batches exist for this product/warehouse.
        from apps.pharmacy.services.batch_service import BatchService

        if delta < 0:
            BatchService.deduct_fefo(
                product=product,
                warehouse=warehouse,
                quantity=abs(delta),
                reference_type=ref_type,
                reference_id=reference_id,
                user=user,
                notes=notes or "POS/sale FEFO",
            )
        elif delta > 0 and reference_id:
            restored = BatchService.restore_for_reference(
                reference_type=ref_type,
                reference_id=reference_id,
                product=product,
                quantity=delta,
                user=user,
            )
            leftover = delta - restored
            if leftover > 0:
                BatchService.receive_stock(
                    product=product,
                    warehouse=warehouse,
                    quantity=leftover,
                    batch_number=f"RETURN-{reference_id}",
                    user=user,
                    notes=notes or "Sale return",
                )
        return inv

    @staticmethod
    @transaction.atomic
    def apply_invoice_quantity_deltas(
        *,
        warehouse,
        quantity_by_product: dict,
        reference_id,
        user=None,
        notes="",
    ):
        """
        quantity_by_product maps product_id → signed inventory delta
        (negative = sold more / reduce stock, positive = return / increase stock).
        """
        if not warehouse or not quantity_by_product:
            return
        for product_id, delta in quantity_by_product.items():
            delta = Decimal(str(delta))
            if delta == 0:
                continue
            product = Product.active_objects().filter(pk=product_id).first()
            if product is None:
                # Soft-deleted catalog item — still adjust stock if inventory row exists.
                product = Product.objects.filter(pk=product_id).first()
            if product is None:
                continue
            InventoryService.apply_sale_delta(
                product=product,
                warehouse=warehouse,
                quantity_delta=delta,
                reference_id=reference_id,
                user=user,
                notes=notes,
            )

    @staticmethod
    def list_adjustments(*, user=None, request=None):
        qs = (
            InventoryAdjustment.active_objects()
            .select_related("warehouse", "branch")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        return apply_tenant_scope(qs, user=user, request=request)

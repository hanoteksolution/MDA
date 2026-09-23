from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum

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
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


def _normalize_module_code(module_code=None) -> str:
    raw = (module_code or "").strip().lower()
    if not raw:
        return ""
    aliases = {
        "cafeteria": "restaurant",
        "property": "property_management",
        "project": "project_management",
        "travel": "travel_agency",
    }
    return aliases.get(raw, raw)


def _module_scope_inventory(qs, *, module_code=None):
    """Restrict inventory rows to products belonging to one industry module."""
    code = _normalize_module_code(module_code)
    if not code:
        return qs
    if code in {"retail", "shared"}:
        return qs.filter(Q(product__module_code="") | Q(product__module_code="retail"))
    return qs.filter(product__module_code=code)


def _module_scope_products(qs, *, module_code=None):
    code = _normalize_module_code(module_code)
    if not code:
        return qs
    if code in {"retail", "shared"}:
        return qs.filter(Q(module_code="") | Q(module_code="retail"))
    return qs.filter(module_code=code)


def _default_location_id(warehouse):
    """The location a movement uses when the caller doesn't name one explicitly.

    BRANCH_INVENTORY.md §5.1: historical rows stay NULL rather than guessed, but every
    *new* movement gets a real location — defaulting to the warehouse's default
    StockLocation, which every warehouse has had since Phase 2's
    ``ensure_default_locations``.
    """
    if warehouse is None:
        return None
    from apps.organization.models import StockLocation

    return (
        StockLocation.active_objects()
        .filter(warehouse_id=warehouse.pk, is_default=True)
        .values_list("pk", flat=True)
        .first()
    )


def _movement_stamp(*, warehouse, user=None, location_id=None):
    """Common branch/location/actor fields for a new StockMovement or InventoryTransaction.

    Centralised so every mutation path stamps the same way — the brief's warning
    against "different services inventing different formulas" applies to ledger
    metadata too, not only to quantity math.
    """
    return {
        "branch_id": getattr(warehouse, "branch_id", None),
        "location_id": location_id if location_id is not None else _default_location_id(warehouse),
    }


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
        from apps.organization.services.structure_service import (
            StockLocationService,
            validate_warehouse_branch,
        )

        payload = stamp_tenant_id(dict(data), user=user)
        if data.get("is_default"):
            Warehouse.objects.filter(branch_id=data["branch_id"]).update(is_default=False)
        warehouse = Warehouse.objects.create(**payload, created_by=user)
        # The warehouse rule: branch ownership is validated now, never inferred later.
        validate_warehouse_branch(warehouse)
        # Every warehouse has somewhere for a movement to point from day one.
        StockLocationService.ensure_default_locations(warehouse=warehouse, actor=user)
        return warehouse

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
    def backfill_missing_inventory(
        *, user=None, request=None, tenant=None, warehouse=None, module_code=None
    ):
        """Create qty=0 inventory rows for products that have none (so they appear in Stock)."""
        tenant = tenant or resolve_acting_tenant(user=user, request=request)
        wh_qs = apply_tenant_scope(
            Warehouse.active_objects(), user=user, request=request, tenant=tenant
        )
        wh = warehouse or (wh_qs.filter(is_default=True).first() or wh_qs.first())
        if not wh:
            return 0
        if tenant is not None and wh.tenant_id != getattr(tenant, "pk", tenant):
            raise ValueError("Warehouse does not belong to the acting tenant.")
        existing_ids = set(
            Inventory.active_objects()
            .filter(warehouse=wh)
            .values_list("product_id", flat=True)
        )
        products = apply_tenant_scope(
            Product.active_objects(), user=user, request=request, tenant=tenant
        )
        products = _module_scope_products(products, module_code=module_code)
        missing = list(products.exclude(id__in=existing_ids))
        for product in missing:
            InventoryService.ensure_inventory_record(product=product, warehouse=wh, user=user)
        return len(missing)

    @staticmethod
    @transaction.atomic
    def dedupe_inventory(
        *, user=None, request=None, tenant=None, preferred_branch_id=None
    ):
        """Merge duplicate inventory rows so each product×warehouse appears once.

        Warehouse identity is its primary key. Rows from different warehouses,
        branches, or tenants must never be combined merely because their display
        names/codes happen to match.
        """
        merged = 0
        tenant = tenant or resolve_acting_tenant(user=user, request=request)
        inventory_qs = apply_tenant_scope(
            Inventory.active_objects(), user=user, request=request, tenant=tenant
        )

        # Exact product + warehouse duplicates
        by_exact: dict[tuple, list] = defaultdict(list)
        for inv in (
            inventory_qs
            .select_related("warehouse")
            .order_by("product_id", "warehouse_id", "-quantity", "created_at")
        ):
            by_exact[(inv.tenant_id, inv.product_id, inv.warehouse_id)].append(inv)

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

        return merged

    @staticmethod
    def list_inventory(
        *,
        warehouse_id=None,
        search=None,
        low_stock=False,
        ensure_rows=True,
        branch_id=None,
        module_code=None,
        user=None,
        request=None,
        tenant=None,
    ):
        if ensure_rows:
            wh_qs = apply_tenant_scope(
                Warehouse.active_objects(), user=user, request=request, tenant=tenant
            )
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
                request=request,
                module_code=module_code,
            )
        qs = (
            Inventory.active_objects()
            .select_related("product", "product__category", "warehouse")
            .filter(product__deleted_at__isnull=True)
        )
        qs = apply_tenant_scope(qs, user=user, request=request, tenant=tenant)
        qs = _module_scope_inventory(qs, module_code=module_code)
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
    def get_reorder_candidates(
        *, branch_id=None, module_code=None, user=None, request=None, tenant=None
    ):
        """Products at/below minimum stock — hook for future Celery reorder alerts."""
        return InventoryService.list_inventory(
            branch_id=branch_id,
            low_stock=True,
            ensure_rows=False,
            module_code=module_code,
            user=user,
            request=request,
            tenant=tenant,
        )

    @staticmethod
    def get_low_stock(
        *, branch_id=None, module_code=None, user=None, request=None, tenant=None
    ):
        return InventoryService.get_reorder_candidates(
            branch_id=branch_id, module_code=module_code, user=user, request=request,
            tenant=tenant,
        )

    @staticmethod
    def get_out_of_stock(
        *, branch_id=None, module_code=None, user=None, request=None, tenant=None
    ):
        return InventoryService.list_inventory(
            branch_id=branch_id, module_code=module_code, user=user, request=request,
            tenant=tenant,
        ).filter(quantity__lte=0)

    @staticmethod
    def get_summary(
        *, branch_id=None, module_code=None, user=None, request=None, tenant=None
    ):
        qs = Inventory.active_objects().select_related("product")
        qs = apply_tenant_scope(qs, user=user, request=request, tenant=tenant)
        qs = _module_scope_inventory(qs, module_code=module_code)
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        agg = qs.aggregate(
            total_items=Count("id"),
            total_quantity=Sum("quantity"),
            # Retail/on-hand value at selling price (what the stock is worth to sell)
            inventory_value=Sum(
                ExpressionWrapper(
                    F("quantity") * F("product__selling_price"),
                    output_field=DecimalField(max_digits=38, decimal_places=4),
                )
            ),
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
            qty_after = max(Decimal("0"), Decimal(str(item["quantity_after"])))
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

            stamp = _movement_stamp(warehouse=warehouse, user=user)
            StockMovement.objects.create(
                product=product,
                warehouse=warehouse,
                movement_type="adjustment",
                quantity=qty_change,
                reference_type="adjustment",
                reference_id=adjustment.id,
                notes=reason,
                created_by=user,
                performed_by=user,
                **stamp,
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
                **stamp,
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

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="reserve",
            quantity_before=before,
            quantity_after=inv.reserved_quantity,
            quantity_change=qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **stamp,
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
                performed_by=user,
                **stamp,
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

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="unreserve",
            quantity_before=before,
            quantity_after=inv.reserved_quantity,
            quantity_change=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **stamp,
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
                performed_by=user,
                **stamp,
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
        location_id=None,
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
        # Never drive on-hand below zero, and never below what is currently
        # reserved (a transfer reservation, a POS hold, etc.) — a direct sale must
        # not consume stock an active reservation is holding. Oversell clamps to
        # that floor instead of raising, matching the existing sale-side policy.
        qty_after = qty_before + delta
        if delta < 0:
            # Only ever clamp a deduction, and never so far that it adds stock
            # (on-hand already below the floor is left as-is, not raised).
            floor = min(max(inv.reserved_quantity, Decimal("0")), qty_before)
            if qty_after < floor:
                qty_after = floor
                delta = qty_after - qty_before
                if delta == 0:
                    return inv
        inv.quantity = qty_after
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        movement_type = "sale" if delta < 0 else "return"
        txn_type = "out" if delta < 0 else "return"
        ref_type = reference_type or "invoice"
        stamp = _movement_stamp(warehouse=warehouse, user=user, location_id=location_id)

        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=delta,
            reference_type=ref_type,
            reference_id=reference_id,
            notes=notes,
            created_by=user,
            performed_by=user,
            **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type=txn_type,
            quantity_before=qty_before,
            quantity_after=qty_after,
            quantity_change=delta,
            reference_type=ref_type,
            reference_id=reference_id,
            **stamp,
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
        location_id=None,
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
                location_id=location_id,
            )

    # --- Branch Phase 3 additions (BRANCH_INVENTORY.md §6). Same locking discipline as
    # every existing mutation path: select_for_update inside @transaction.atomic, write
    # the ledger in the same transaction as the balance change. ---

    @staticmethod
    @transaction.atomic
    def damage_stock(
        *, product, warehouse, quantity, reason="", reference_type="", reference_id=None, user=None
    ):
        """Move on-hand units into damaged_quantity. Physical count is unchanged;
        sellable on-hand decreases."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Damage quantity must be positive.")

        inv = InventoryService._locked_inventory(product=product, warehouse=warehouse, user=user)
        if qty > inv.quantity:
            raise ValueError(
                f"Cannot damage {qty} of {product.sku}; only {inv.quantity} on hand."
            )
        qty_before = inv.quantity
        inv.quantity = qty_before - qty
        inv.damaged_quantity = inv.damaged_quantity + qty
        inv.updated_by = user
        inv.save(update_fields=["quantity", "damaged_quantity", "updated_by", "updated_at"])

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type="damage",
            quantity=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=reason,
            created_by=user,
            performed_by=user,
            **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="damage",
            quantity_before=qty_before,
            quantity_after=inv.quantity,
            quantity_change=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **stamp,
        )
        return inv

    @staticmethod
    @transaction.atomic
    def write_off_stock(
        *,
        product,
        warehouse,
        quantity,
        source="damaged",
        reason="",
        reference_type="",
        reference_id=None,
        user=None,
    ):
        """Permanently remove stock already known to be bad (damaged) or still on hand.

        Distinct from ``adjustment``: an adjustment corrects a miscounted number, a
        write-off disposes of known-bad stock (BRANCH_INVENTORY.md §5.2).
        """
        if source not in ("damaged", "on_hand"):
            raise ValueError("source must be 'damaged' or 'on_hand'.")
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Write-off quantity must be positive.")

        inv = InventoryService._locked_inventory(product=product, warehouse=warehouse, user=user)
        if source == "damaged":
            if qty > inv.damaged_quantity:
                raise ValueError(
                    f"Cannot write off {qty} of {product.sku}; only {inv.damaged_quantity} "
                    "damaged."
                )
            inv.damaged_quantity = inv.damaged_quantity - qty
            inv.updated_by = user
            inv.save(update_fields=["damaged_quantity", "updated_by", "updated_at"])
            qty_before = qty_after = inv.quantity  # on-hand is unaffected
        else:
            if qty > inv.quantity:
                raise ValueError(
                    f"Cannot write off {qty} of {product.sku}; only {inv.quantity} on hand."
                )
            qty_before = inv.quantity
            inv.quantity = qty_before - qty
            qty_after = inv.quantity
            inv.updated_by = user
            inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type="write_off",
            quantity=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=reason,
            created_by=user,
            performed_by=user,
            metadata={"source": source},
            **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="write_off",
            quantity_before=qty_before,
            quantity_after=qty_after,
            quantity_change=(qty_after - qty_before),
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **stamp,
        )
        return inv

    @staticmethod
    @transaction.atomic
    def receive_purchase_return(
        *, product, warehouse, quantity, reason="", reference_type="", reference_id=None, user=None
    ):
        """Return stock to a supplier: decrements on-hand. Rejected if it would go
        negative — a return can never remove stock that isn't there (unlike a sale,
        which is allowed to clamp; see BRANCH_INVENTORY.md §1)."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Purchase-return quantity must be positive.")

        inv = InventoryService._locked_inventory(product=product, warehouse=warehouse, user=user)
        if qty > inv.quantity:
            raise ValueError(
                f"Cannot return {qty} of {product.sku} to the supplier; only "
                f"{inv.quantity} on hand."
            )
        qty_before = inv.quantity
        inv.quantity = qty_before - qty
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type="purchase_return",
            quantity=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=reason,
            created_by=user,
            performed_by=user,
            **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="out",
            quantity_before=qty_before,
            quantity_after=inv.quantity,
            quantity_change=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **stamp,
        )
        return inv

    @staticmethod
    @transaction.atomic
    def record_opening_balance(*, product, warehouse, quantity, notes="", user=None):
        """A warehouse's very first stock figure for a product. Refuses if a non-zero
        Inventory row already exists — this is a one-time starting figure, not a
        correction tool (use create_adjustment for that)."""
        qty = Decimal(str(quantity))
        if qty < 0:
            raise ValueError("Opening balance cannot be negative.")

        inv = InventoryService._locked_inventory(product=product, warehouse=warehouse, user=user)
        if inv.quantity != 0:
            raise ValueError(
                f"{product.sku} already has an opening balance recorded at "
                f"{warehouse.code} ({inv.quantity} on hand)."
            )
        inv.quantity = qty
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type="opening_balance",
            quantity=qty,
            notes=notes,
            created_by=user,
            performed_by=user,
            **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv,
            transaction_type="in",
            quantity_before=Decimal("0"),
            quantity_after=qty,
            quantity_change=qty,
            created_by=user,
            **stamp,
        )
        return inv

    @staticmethod
    @transaction.atomic
    def move_stock(
        *,
        product,
        source_warehouse,
        destination_warehouse,
        quantity,
        notes="",
        reference_type="",
        reference_id=None,
        user=None,
        allow_negative_available=False,
    ):
        """Same-branch (or any-branch, in Phase 3) warehouse-to-warehouse move.

        The primitive Phase 4's cross-branch service will call for the "credit the
        destination on receipt" half of its workflow (BRANCH_INVENTORY.md §6). Writes
        ``warehouse_move``, never ``transfer_in``/``transfer_out`` — those names are
        reserved for the branch-transfer workflow so the two are never confused in a
        report. Not wired to ``StockTransferService`` in this phase (§2 boundary).

        Source and destination Inventory rows are locked in ascending ``pk`` order
        (not "source then destination") so two concurrent moves between the same
        warehouse pair in opposite directions cannot deadlock — the Phase 2 lesson
        (BRANCH_INVENTORY.md §6.1).
        """
        if source_warehouse.pk == destination_warehouse.pk:
            raise ValueError("Source and destination warehouses must differ.")
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Move quantity must be positive.")

        source_inv = InventoryService.ensure_inventory_record(
            product=product, warehouse=source_warehouse, user=user
        )
        destination_inv = InventoryService.ensure_inventory_record(
            product=product, warehouse=destination_warehouse, user=user
        )
        first_pk, second_pk = sorted([source_inv.pk, destination_inv.pk], key=str)
        locked = {
            row.pk: row
            for row in Inventory.objects.select_for_update().filter(pk__in=[first_pk, second_pk])
        }
        src_inv = locked[source_inv.pk]
        dst_inv = locked[destination_inv.pk]

        available = src_inv.quantity - src_inv.reserved_quantity
        if not allow_negative_available and qty > available:
            raise ValueError(
                f"Insufficient available stock for {product.sku} "
                f"(available={available}, requested={qty})."
            )

        src_before = src_inv.quantity
        src_inv.quantity = src_before - qty
        src_inv.updated_by = user
        src_inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        dst_before = dst_inv.quantity
        dst_inv.quantity = dst_before + qty
        dst_inv.updated_by = user
        dst_inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        source_stamp = _movement_stamp(warehouse=source_warehouse, user=user)
        dest_location_id = _default_location_id(destination_warehouse)
        StockMovement.objects.create(
            product=product,
            warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            destination_location_id=dest_location_id,
            movement_type="warehouse_move",
            quantity=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            created_by=user,
            performed_by=user,
            **source_stamp,
        )
        InventoryTransaction.objects.create(
            inventory=src_inv,
            transaction_type="out",
            quantity_before=src_before,
            quantity_after=src_inv.quantity,
            quantity_change=-qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **source_stamp,
        )
        dest_stamp = _movement_stamp(
            warehouse=destination_warehouse, user=user, location_id=dest_location_id
        )
        InventoryTransaction.objects.create(
            inventory=dst_inv,
            transaction_type="in",
            quantity_before=dst_before,
            quantity_after=dst_inv.quantity,
            quantity_change=qty,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
            **dest_stamp,
        )
        return src_inv, dst_inv

    # --- Phase 4: branch transfer primitives. Dispatch and receive are separate
    # calls (unlike move_stock) so the destination is credited only at receipt,
    # never at dispatch — see BranchTransferService. ---

    @staticmethod
    @transaction.atomic
    def dispatch_reserved(
        *, product, warehouse, quantity, reference_type="branch_transfer", reference_id=None,
        user=None, notes="",
    ):
        """Convert a reservation into an outbound branch transfer: unreserve, then
        decrement on-hand. Writes ``transfer_out`` — never ``sale`` — since this stock
        is leaving via a transfer, not being sold."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            return None
        InventoryService.unreserve_quantity(
            product=product, warehouse=warehouse, quantity=qty,
            reference_type=reference_type, reference_id=reference_id, user=user,
        )
        inv = InventoryService._locked_inventory(product=product, warehouse=warehouse, user=user)
        qty_before = inv.quantity
        qty_after = qty_before - qty
        if qty_after < 0:
            raise ValueError(
                f"Cannot dispatch {qty} of {product.sku}; only {qty_before} on hand."
            )
        inv.quantity = qty_after
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        StockMovement.objects.create(
            product=product, warehouse=warehouse, movement_type="transfer_out", quantity=-qty,
            reference_type=reference_type, reference_id=reference_id, notes=notes,
            created_by=user, performed_by=user, **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv, transaction_type="out", quantity_before=qty_before,
            quantity_after=qty_after, quantity_change=-qty, reference_type=reference_type,
            reference_id=reference_id, created_by=user, **stamp,
        )
        return inv

    @staticmethod
    @transaction.atomic
    def receive_transfer_in(
        *, product, warehouse, quantity, reference_type="branch_transfer", reference_id=None,
        user=None, notes="",
    ):
        """Credit on-hand for an inbound branch transfer. Writes ``transfer_in``."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            return None
        inv = InventoryService._locked_inventory(product=product, warehouse=warehouse, user=user)
        qty_before = inv.quantity
        qty_after = qty_before + qty
        inv.quantity = qty_after
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])

        stamp = _movement_stamp(warehouse=warehouse, user=user)
        StockMovement.objects.create(
            product=product, warehouse=warehouse, movement_type="transfer_in", quantity=qty,
            reference_type=reference_type, reference_id=reference_id, notes=notes,
            created_by=user, performed_by=user, **stamp,
        )
        InventoryTransaction.objects.create(
            inventory=inv, transaction_type="in", quantity_before=qty_before,
            quantity_after=qty_after, quantity_change=qty, reference_type=reference_type,
            reference_id=reference_id, created_by=user, **stamp,
        )
        return inv

    @staticmethod
    def list_adjustments(*, user=None, request=None):
        qs = (
            InventoryAdjustment.active_objects()
            .select_related("warehouse", "branch")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        return apply_tenant_scope(qs, user=user, request=request)

    @staticmethod
    def list_movements(
        *, product=None, warehouse=None, branch_id=None, user=None, request=None, tenant=None
    ):
        """Read-only ledger history for a product stock-detail screen (movement
        traceability, BRANCH_INVENTORY.md §5). Never a mutation path."""
        qs = (
            StockMovement.active_objects()
            .select_related("product", "warehouse", "branch", "location", "performed_by")
            .order_by("-created_at")
        )
        qs = apply_tenant_scope(qs, user=user, request=request, tenant=tenant)
        if product is not None:
            qs = qs.filter(product=product)
        if warehouse is not None:
            qs = qs.filter(warehouse=warehouse)
        if branch_id is not None:
            qs = qs.filter(branch_id=branch_id)
        return qs

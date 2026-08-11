"""Purchase receiving (GRN) — STEP 11.

receive(purchase_order, lines, warehouse, user) — atomic:
  - update PurchaseOrderItem.quantity_received
  - increase Inventory.quantity
  - StockMovement(movement_type=purchase)
  - InventoryTransaction(type=in)
  - set PO status to received when fully received (partial allowed)
  - optional batch creation hook for pharmacy (STEP 13)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from django.db import transaction

from apps.inventory.models import InventoryTransaction, StockMovement, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from core.tenancy import apply_tenant_scope


class ReceivingError(ValueError):
    """Domain validation error for goods receipt."""


# Kept for backward-compatible imports from older stub tests.
ReceivingNotImplemented = ReceivingError


@dataclass(frozen=True)
class ReceiveLineInput:
    product_id: UUID
    quantity_received: Decimal
    unit_cost: Optional[Decimal] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None


class PurchaseReceivingService:
    @staticmethod
    def preview(*, purchase_order_id, user=None):
        po = apply_tenant_scope(PurchaseOrder.active_objects(), user=user).select_related(
            "branch", "supplier"
        ).prefetch_related("items__product").get(pk=purchase_order_id)
        lines = []
        for item in po.items.all():
            remaining = Decimal(str(item.quantity_ordered)) - Decimal(str(item.quantity_received))
            if remaining < 0:
                remaining = Decimal("0")
            lines.append(
                {
                    "product_id": str(item.product_id),
                    "product_name": item.product.name,
                    "product_sku": item.product.sku,
                    "quantity_ordered": float(item.quantity_ordered),
                    "quantity_received": float(item.quantity_received),
                    "quantity_remaining": float(remaining),
                    "unit_cost": float(item.unit_cost),
                }
            )
        return {
            "purchase_order_id": str(po.id),
            "order_number": po.order_number,
            "status": po.status,
            "fully_received": all(
                Decimal(str(i.quantity_received)) >= Decimal(str(i.quantity_ordered))
                for i in po.items.all()
            ),
            "lines": lines,
        }

    @staticmethod
    def _pharmacy_batch_hook(*, product, quantity, batch_number, expiry_date, warehouse, user):
        """Create/increase ProductBatch when pharmacy module is on or batch data given."""
        from apps.pharmacy.services.batch_service import BatchService
        from apps.platform.models import Tenant
        from apps.platform.services.module_service import tenant_has_module

        tenant_id = getattr(warehouse, "tenant_id", None) or getattr(product, "tenant_id", None)
        has_batch_data = bool(batch_number) or bool(expiry_date)
        pharmacy_on = False
        if tenant_id:
            tenant = Tenant.objects.filter(pk=tenant_id).first()
            if tenant is not None:
                pharmacy_on = tenant_has_module("pharmacy", tenant=tenant)
        if not has_batch_data and not pharmacy_on:
            return None
        return BatchService.receive_stock(
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            batch_number=batch_number,
            expiry_date=expiry_date,
            cost_price=getattr(product, "cost_price", None),
            user=user,
            notes="Goods receipt",
        )
    @staticmethod
    @transaction.atomic
    def receive(*, purchase_order_id, warehouse_id, lines: Sequence[ReceiveLineInput], user=None, notes=""):
        if not lines:
            raise ReceivingError("At least one receive line is required.")

        po = apply_tenant_scope(PurchaseOrder.active_objects(), user=user).select_for_update().get(
            pk=purchase_order_id
        )
        if po.status == PurchaseOrder.STATUS_CANCELLED:
            raise ReceivingError("Cancelled purchase orders cannot be received.")
        if po.status == PurchaseOrder.STATUS_DRAFT:
            po.status = PurchaseOrder.STATUS_ORDERED
            po.updated_by = user
            po.save(update_fields=["status", "updated_by", "updated_at"])

        wh_qs = apply_tenant_scope(Warehouse.active_objects(), user=user)
        warehouse = wh_qs.select_for_update().get(pk=warehouse_id)
        if not warehouse.is_active:
            raise ReceivingError("Warehouse is inactive.")

        items_by_product = {
            item.product_id: item
            for item in PurchaseOrderItem.objects.select_for_update()
            .filter(purchase_order=po)
            .select_related("product")
        }

        received_rows = []
        receive_total = Decimal("0")
        for line in lines:
            qty = Decimal(str(line.quantity_received))
            if qty <= 0:
                raise ReceivingError("Receive quantity must be positive.")
            item = items_by_product.get(line.product_id)
            if item is None:
                raise ReceivingError(f"Product {line.product_id} is not on this purchase order.")

            remaining = Decimal(str(item.quantity_ordered)) - Decimal(str(item.quantity_received))
            if qty > remaining:
                raise ReceivingError(
                    f"Cannot receive {qty} of {item.product.sku}; remaining is {remaining}."
                )

            item.quantity_received = Decimal(str(item.quantity_received)) + qty
            item.updated_by = user
            item.save(update_fields=["quantity_received", "updated_by", "updated_at"])

            product = item.product
            inv = InventoryService._locked_inventory(
                product=product, warehouse=warehouse, user=user
            )
            before = inv.quantity
            after = before + qty
            inv.quantity = after
            inv.updated_by = user
            inv.save(update_fields=["quantity", "updated_by", "updated_at"])

            tenant_id = getattr(warehouse, "tenant_id", None) or getattr(po, "tenant_id", None)
            StockMovement.objects.create(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=qty,
                reference_type="purchase_order",
                reference_id=po.id,
                notes=notes or f"GRN for {po.order_number}",
                tenant_id=tenant_id,
                created_by=user,
            )
            InventoryTransaction.objects.create(
                inventory=inv,
                transaction_type="in",
                quantity_before=before,
                quantity_after=after,
                quantity_change=qty,
                reference_type="purchase_order",
                reference_id=po.id,
                tenant_id=tenant_id,
                created_by=user,
            )

            PurchaseReceivingService._pharmacy_batch_hook(
                product=product,
                quantity=qty,
                batch_number=line.batch_number,
                expiry_date=line.expiry_date,
                warehouse=warehouse,
                user=user,
            )
            if line.unit_cost is not None and Decimal(str(line.unit_cost)) >= 0:
                product.cost_price = Decimal(str(line.unit_cost))
                product.updated_by = user
                product.save(update_fields=["cost_price", "updated_by", "updated_at"])

            unit_cost = (
                Decimal(str(line.unit_cost))
                if line.unit_cost is not None
                else Decimal(str(item.unit_cost))
            )
            receive_total += qty * unit_cost

            received_rows.append(
                {
                    "product_id": str(product.id),
                    "sku": product.sku,
                    "quantity_received": float(qty),
                    "quantity_on_hand": float(after),
                }
            )

        fully = all(
            Decimal(str(i.quantity_received)) >= Decimal(str(i.quantity_ordered))
            for i in PurchaseOrderItem.objects.filter(purchase_order=po)
        )
        if fully and po.status != PurchaseOrder.STATUS_RECEIVED:
            po.status = PurchaseOrder.STATUS_RECEIVED
            po.updated_by = user
            po.save(update_fields=["status", "updated_by", "updated_at"])
        elif po.status == PurchaseOrder.STATUS_ORDERED:
            # stay ordered while partial
            po.updated_by = user
            po.save(update_fields=["updated_by", "updated_at"])

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_purchase_received(
            purchase_order=po,
            receive_total=receive_total,
            lines=lines,
            user=user,
            warehouse=warehouse,
        )
        if po.project_id:
            from apps.project_management.services.project_operations_service import ProjectInventoryService

            ProjectInventoryService.allocate_from_grn(
                purchase_order=po, lines=lines, user=user, notes=notes
            )

        return {
            "purchase_order_id": str(po.id),
            "order_number": po.order_number,
            "status": po.status,
            "warehouse_id": str(warehouse.id),
            "fully_received": fully,
            "lines": received_rows,
        }

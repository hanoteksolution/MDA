"""Warehouse transfer service — STEP 11.

create_draft → add_lines → confirm
On confirm (atomic):
  - lock source + destination inventory rows
  - decrease source quantity (transfer_out movement)
  - increase destination quantity (transfer_in movement)
  - write InventoryTransaction rows on both sides
  - never allow source available_quantity to go negative unless override
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    InventoryTransaction,
    StockMovement,
    StockTransfer,
    StockTransferLine,
    Warehouse,
)
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class TransferError(ValueError):
    """Domain validation error for stock transfers."""


# Kept for backward-compatible imports from older stub tests.
TransferNotImplemented = TransferError


@dataclass(frozen=True)
class TransferLineInput:
    product_id: UUID
    quantity: Decimal


class StockTransferService:
    @staticmethod
    def list(*, status=None, branch_id=None, user=None, request=None):
        qs = (
            StockTransfer.active_objects()
            .select_related("source_warehouse", "destination_warehouse", "branch", "confirmed_by")
            .prefetch_related("lines__product")
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if status:
            qs = qs.filter(status=status)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("-created_at")

    @staticmethod
    def _next_number(*, branch: Branch) -> str:
        count = StockTransfer.objects.filter(branch=branch).count() + 1
        return f"TR-{branch.code}-{count:05d}"

    @staticmethod
    @transaction.atomic
    def create_draft(
        *,
        source_warehouse_id,
        destination_warehouse_id,
        branch_id=None,
        user=None,
        notes="",
        lines: Sequence[TransferLineInput] | None = None,
    ):
        if str(source_warehouse_id) == str(destination_warehouse_id):
            raise TransferError("Source and destination warehouses must differ.")

        wh_qs = apply_tenant_scope(Warehouse.active_objects(), user=user)
        source = wh_qs.get(pk=source_warehouse_id)
        destination = wh_qs.get(pk=destination_warehouse_id)
        branch_qs = apply_tenant_scope(Branch.active_objects(), user=user)
        if branch_id:
            branch = branch_qs.get(pk=branch_id)
        else:
            branch = source.branch

        payload = stamp_tenant_id({}, user=user)
        if not payload.get("tenant_id"):
            payload["tenant_id"] = getattr(source, "tenant_id", None) or getattr(branch, "tenant_id", None)

        transfer = StockTransfer.objects.create(
            transfer_number=StockTransferService._next_number(branch=branch),
            source_warehouse=source,
            destination_warehouse=destination,
            branch=branch,
            status=StockTransfer.STATUS_DRAFT,
            notes=notes or "",
            created_by=user,
            **payload,
        )
        if lines:
            StockTransferService.add_lines(transfer_id=transfer.id, lines=lines, user=user)
        return StockTransferService.list(user=user).get(pk=transfer.pk)

    @staticmethod
    @transaction.atomic
    def add_lines(*, transfer_id, lines: Sequence[TransferLineInput], user=None, replace=False):
        transfer = apply_tenant_scope(
            StockTransfer.active_objects(), user=user
        ).select_for_update().get(pk=transfer_id)
        if transfer.status != StockTransfer.STATUS_DRAFT:
            raise TransferError("Only draft transfers can be edited.")
        if not lines and not replace:
            raise TransferError("At least one transfer line is required.")

        if replace:
            transfer.lines.all().delete()

        for line in lines or []:
            qty = Decimal(str(line.quantity))
            if qty <= 0:
                raise TransferError("Transfer quantity must be positive.")
            product = apply_tenant_scope(Product.active_objects(), user=user).get(pk=line.product_id)
            existing = transfer.lines.filter(product=product).first()
            if existing:
                existing.quantity = qty
                existing.updated_by = user
                existing.save(update_fields=["quantity", "updated_by", "updated_at"])
            else:
                StockTransferLine.objects.create(
                    transfer=transfer,
                    product=product,
                    quantity=qty,
                    created_by=user,
                )
        return StockTransferService.list(user=user).get(pk=transfer.pk)

    @staticmethod
    @transaction.atomic
    def confirm(*, transfer_id, user=None, allow_negative_available=False):
        transfer = apply_tenant_scope(
            StockTransfer.active_objects(), user=user
        ).select_for_update().prefetch_related("lines__product").get(pk=transfer_id)
        if transfer.status == StockTransfer.STATUS_CONFIRMED:
            return StockTransferService.list(user=user).get(pk=transfer.pk)
        if transfer.status != StockTransfer.STATUS_DRAFT:
            raise TransferError("Only draft transfers can be confirmed.")
        lines = list(transfer.lines.all())
        if not lines:
            raise TransferError("Transfer has no lines.")

        source = transfer.source_warehouse
        destination = transfer.destination_warehouse
        tenant_id = transfer.tenant_id or getattr(source, "tenant_id", None)

        # Lock both sides in stable order to reduce deadlock risk.
        for line in sorted(lines, key=lambda L: str(L.product_id)):
            qty = Decimal(str(line.quantity))
            product = line.product

            src_inv = InventoryService._locked_inventory(
                product=product, warehouse=source, user=user
            )
            available = src_inv.quantity - src_inv.reserved_quantity
            if not allow_negative_available and qty > available:
                raise TransferError(
                    f"Insufficient available stock for {product.sku} "
                    f"(available={available}, requested={qty})."
                )

            src_before = src_inv.quantity
            src_after = src_before - qty
            src_inv.quantity = src_after
            src_inv.updated_by = user
            src_inv.save(update_fields=["quantity", "updated_by", "updated_at"])

            dst_inv = InventoryService._locked_inventory(
                product=product, warehouse=destination, user=user
            )
            dst_before = dst_inv.quantity
            dst_after = dst_before + qty
            dst_inv.quantity = dst_after
            dst_inv.updated_by = user
            dst_inv.save(update_fields=["quantity", "updated_by", "updated_at"])

            StockMovement.objects.create(
                product=product,
                warehouse=source,
                movement_type="transfer_out",
                quantity=-qty,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                notes=f"Transfer {transfer.transfer_number} → {destination.code}",
                tenant_id=tenant_id,
                created_by=user,
            )
            StockMovement.objects.create(
                product=product,
                warehouse=destination,
                movement_type="transfer_in",
                quantity=qty,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                notes=f"Transfer {transfer.transfer_number} ← {source.code}",
                tenant_id=tenant_id,
                created_by=user,
            )
            InventoryTransaction.objects.create(
                inventory=src_inv,
                transaction_type="out",
                quantity_before=src_before,
                quantity_after=src_after,
                quantity_change=-qty,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                tenant_id=tenant_id,
                created_by=user,
            )
            InventoryTransaction.objects.create(
                inventory=dst_inv,
                transaction_type="in",
                quantity_before=dst_before,
                quantity_after=dst_after,
                quantity_change=qty,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                tenant_id=tenant_id,
                created_by=user,
            )

        transfer.status = StockTransfer.STATUS_CONFIRMED
        transfer.confirmed_at = timezone.now()
        transfer.confirmed_by = user
        transfer.updated_by = user
        transfer.save(
            update_fields=["status", "confirmed_at", "confirmed_by", "updated_by", "updated_at"]
        )
        return StockTransferService.list(user=user).get(pk=transfer.pk)

    @staticmethod
    @transaction.atomic
    def cancel(*, transfer_id, user=None):
        transfer = apply_tenant_scope(
            StockTransfer.active_objects(), user=user
        ).select_for_update().get(pk=transfer_id)
        if transfer.status == StockTransfer.STATUS_CONFIRMED:
            raise TransferError("Confirmed transfers cannot be cancelled.")
        if transfer.status == StockTransfer.STATUS_CANCELLED:
            return StockTransferService.list(user=user).get(pk=transfer.pk)
        transfer.status = StockTransfer.STATUS_CANCELLED
        transfer.updated_by = user
        transfer.save(update_fields=["status", "updated_by", "updated_at"])
        return StockTransferService.list(user=user).get(pk=transfer.pk)

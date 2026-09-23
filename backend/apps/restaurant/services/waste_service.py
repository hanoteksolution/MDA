"""Waste / spoilage overlay → shared inventory adjustments."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import write_audit
from apps.inventory.services.inventory_service import InventoryService
from apps.restaurant.models import Ingredient, WasteRecord
from apps.restaurant.services.restaurant_service import RestaurantError, RestaurantService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class WasteError(RestaurantError):
    pass


class WasteService:
    @staticmethod
    def serialize(row: WasteRecord) -> dict:
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id),
            "waste_date": row.waste_date.isoformat() if row.waste_date else None,
            "ingredient_id": str(row.ingredient_id) if row.ingredient_id else None,
            "ingredient_name": row.ingredient.name if row.ingredient_id else "",
            "product_id": str(row.product_id) if row.product_id else None,
            "menu_item_id": str(row.menu_item_id) if row.menu_item_id else None,
            "quantity": float(row.quantity or 0),
            "unit": row.unit or "",
            "unit_cost": float(row.unit_cost or 0),
            "total_cost": float(row.total_cost or 0),
            "waste_type": row.waste_type,
            "employee_user_id": str(row.employee_user_id) if row.employee_user_id else None,
            "reason": row.reason or "",
            "notes": row.notes or "",
            "approval_status": row.approval_status,
            "inventory_adjustment_id": str(row.inventory_adjustment_id)
            if row.inventory_adjustment_id
            else None,
            "photo_url": row.photo_url or "",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def list(*, branch_id=None, approval_status=None, user=None, request=None):
        qs = WasteRecord.active_objects().select_related(
            "branch", "ingredient", "product", "menu_item", "employee_user"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if approval_status:
            qs = qs.filter(approval_status=approval_status)
        return qs.order_by("-waste_date", "-created_at")

    @staticmethod
    def get(*, pk, user=None, request=None) -> WasteRecord:
        return WasteService.list(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> WasteRecord:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        qty = Decimal(str(payload.get("quantity") or 0))
        if qty <= 0:
            raise WasteError("Quantity must be positive.")
        unit_cost = Decimal(str(payload.get("unit_cost") or 0))
        ingredient = None
        if payload.get("ingredient_id"):
            ingredient = (
                apply_tenant_scope(Ingredient.active_objects(), user=user, request=request)
                .filter(pk=payload["ingredient_id"])
                .first()
            )
            if not ingredient:
                raise WasteError("Ingredient not found.")
            if not unit_cost:
                unit_cost = Decimal(str(ingredient.unit_cost or ingredient.average_cost or 0))

        product_id = payload.get("product_id") or (
            ingredient.product_id if ingredient else None
        )
        row = WasteRecord.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            waste_date=payload.get("waste_date") or timezone.localdate(),
            ingredient=ingredient,
            product_id=product_id,
            menu_item_id=payload.get("menu_item_id") or None,
            quantity=qty,
            unit=(payload.get("unit") or (ingredient.unit if ingredient else "unit")),
            unit_cost=unit_cost,
            total_cost=qty * unit_cost,
            waste_type=payload.get("waste_type") or WasteRecord.TYPE_OTHER,
            employee_user_id=payload.get("employee_user_id") or getattr(user, "id", None),
            reason=(payload.get("reason") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            photo_url=(payload.get("photo_url") or "").strip(),
            approval_status=WasteRecord.APPROVAL_DRAFT,
            created_by=user,
        )
        write_audit(
            action="create",
            module="restaurant",
            entity=row,
            user=user,
            request=request,
            new_values={"waste_type": row.waste_type, "quantity": float(qty)},
        )
        if _as_bool(payload.get("auto_approve")):
            return WasteService.approve(waste=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def approve(*, waste: WasteRecord, user=None, request=None) -> WasteRecord:
        if waste.approval_status == WasteRecord.APPROVAL_APPROVED:
            return waste
        product = waste.product
        if not product and waste.ingredient_id and waste.ingredient.product_id:
            product = waste.ingredient.product
        if not product:
            raise WasteError("Waste record has no product/ingredient stock link.")

        warehouse = InventoryService.resolve_warehouse_for_branch(branch=waste.branch)
        if not warehouse:
            raise WasteError("No warehouse available for waste posting.")

        inv = InventoryService.ensure_inventory_record(
            product=product, warehouse=warehouse, user=user
        )
        qty_after = max(Decimal("0"), Decimal(str(inv.quantity or 0)) - Decimal(str(waste.quantity)))
        adjustment = InventoryService.create_adjustment(
            warehouse=warehouse,
            branch=waste.branch,
            reason=f"Waste: {waste.waste_type} — {waste.reason or waste.notes or waste.id}",
            items=[
                {
                    "product_id": product.id,
                    "quantity_after": qty_after,
                }
            ],
            user=user,
        )
        waste.approval_status = WasteRecord.APPROVAL_APPROVED
        waste.inventory_adjustment_id = adjustment.id
        waste.total_cost = Decimal(str(waste.quantity or 0)) * Decimal(
            str(waste.unit_cost or 0)
        )
        waste.updated_by = user
        waste.save(
            update_fields=[
                "approval_status",
                "inventory_adjustment_id",
                "total_cost",
                "updated_by",
                "updated_at",
            ]
        )
        # Post to Central Accounting when enabled / mappings exist.
        try:
            from apps.finance.services.posting_service import AccountingPostingService

            if waste.total_cost and Decimal(str(waste.total_cost)) > 0:
                AccountingPostingService.post_cafeteria_waste(waste=waste, user=user)
        except Exception:
            # Accounting optional — stock movement already committed.
            pass
        write_audit(
            action="approve",
            module="restaurant",
            entity=waste,
            user=user,
            request=request,
            new_values={"inventory_adjustment_id": str(adjustment.id)},
        )
        return waste


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() not in {"0", "false", "no", ""}

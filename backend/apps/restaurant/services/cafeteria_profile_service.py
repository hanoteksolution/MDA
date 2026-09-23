"""Cafeteria workspace profile services."""

from __future__ import annotations

from django.db import transaction

from apps.audit.services import write_audit
from apps.restaurant.models import CafeteriaProfile
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class ProfileError(ValueError):
    pass


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() not in {"0", "false", "no", ""}


class CafeteriaProfileService:
    @staticmethod
    def _branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise ProfileError("branch_id is required.")
        branch = (
            apply_tenant_scope(Branch.active_objects(), user=user, request=request)
            .filter(pk=branch_id)
            .first()
        )
        if not branch:
            raise ProfileError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def serialize(row: CafeteriaProfile) -> dict:
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id),
            "branch_name": row.branch.name if row.branch_id else "",
            "business_name": row.business_name,
            "trading_name": row.trading_name or "",
            "logo_url": row.logo_url or "",
            "phone": row.phone or "",
            "email": row.email or "",
            "address": row.address or "",
            "currency": row.currency,
            "timezone": row.timezone,
            "language": row.language,
            "receipt_header": row.receipt_header or "",
            "receipt_footer": row.receipt_footer or "",
            "order_prefix": row.order_prefix,
            "invoice_prefix": row.invoice_prefix,
            "kitchen_barista_mode": row.kitchen_barista_mode,
            "table_service_enabled": row.table_service_enabled,
            "takeaway_enabled": row.takeaway_enabled,
            "delivery_enabled": row.delivery_enabled,
            "reservations_enabled": row.reservations_enabled,
            "tips_enabled": row.tips_enabled,
            "service_charge_enabled": row.service_charge_enabled,
            "loyalty_enabled": row.loyalty_enabled,
            "recipe_deduction_enabled": row.recipe_deduction_enabled,
            "negative_stock_allowed": row.negative_stock_allowed,
            "default_warehouse_id": str(row.default_warehouse_id)
            if row.default_warehouse_id
            else None,
            "default_cash_account_id": str(row.default_cash_account_id)
            if row.default_cash_account_id
            else None,
            "default_sales_account_id": str(row.default_sales_account_id)
            if row.default_sales_account_id
            else None,
            "default_inventory_account_id": str(row.default_inventory_account_id)
            if row.default_inventory_account_id
            else None,
            "default_cogs_account_id": str(row.default_cogs_account_id)
            if row.default_cogs_account_id
            else None,
            "settings": row.settings or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def get_for_branch(*, branch_id, user=None, request=None) -> CafeteriaProfile | None:
        branch = CafeteriaProfileService._branch(
            branch_id=branch_id, user=user, request=request
        )
        return (
            apply_tenant_scope(
                CafeteriaProfile.active_objects(), user=user, request=request
            )
            .filter(branch_id=branch.id)
            .select_related("branch", "default_warehouse")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def upsert(*, data: dict, user=None, request=None) -> CafeteriaProfile:
        branch_id = data.get("branch_id")
        branch = CafeteriaProfileService._branch(
            branch_id=branch_id, user=user, request=request
        )
        business_name = str(data.get("business_name") or branch.name or "").strip()
        if not business_name:
            raise ProfileError("Business name is required.")

        row = (
            apply_tenant_scope(
                CafeteriaProfile.active_objects(), user=user, request=request
            )
            .filter(branch_id=branch.id)
            .first()
        )
        is_create = row is None
        if is_create:
            payload = stamp_tenant_id({}, user=user, request=request)
            row = CafeteriaProfile(
                branch=branch, business_name=business_name, **payload
            )
            row.created_by = user
        else:
            row.business_name = business_name

        scalars = (
            "trading_name",
            "logo_url",
            "phone",
            "email",
            "address",
            "currency",
            "timezone",
            "language",
            "receipt_header",
            "receipt_footer",
            "order_prefix",
            "invoice_prefix",
            "kitchen_barista_mode",
        )
        for key in scalars:
            if key in data:
                setattr(row, key, data.get(key) or getattr(row, key) or "")

        bools = (
            "table_service_enabled",
            "takeaway_enabled",
            "delivery_enabled",
            "reservations_enabled",
            "tips_enabled",
            "service_charge_enabled",
            "loyalty_enabled",
            "recipe_deduction_enabled",
            "negative_stock_allowed",
        )
        for key in bools:
            if key in data:
                setattr(row, key, _as_bool(data.get(key), getattr(row, key)))

        uuid_fields = (
            "default_cash_account_id",
            "default_sales_account_id",
            "default_inventory_account_id",
            "default_cogs_account_id",
        )
        for key in uuid_fields:
            if key in data:
                setattr(row, key, data.get(key) or None)

        if "default_warehouse_id" in data:
            wh_id = data.get("default_warehouse_id") or None
            if wh_id:
                from apps.inventory.models import Warehouse

                wh = (
                    apply_tenant_scope(
                        Warehouse.active_objects(), user=user, request=request
                    )
                    .filter(pk=wh_id)
                    .first()
                )
                if not wh:
                    raise ProfileError("Default warehouse not found.")
                row.default_warehouse = wh
            else:
                row.default_warehouse = None

        if "settings" in data and isinstance(data.get("settings"), dict):
            row.settings = data.get("settings") or {}

        row.updated_by = user
        row.save()
        write_audit(
            action="create" if is_create else "update",
            module="restaurant",
            entity=row,
            user=user,
            request=request,
            new_values={"business_name": row.business_name},
        )
        return row

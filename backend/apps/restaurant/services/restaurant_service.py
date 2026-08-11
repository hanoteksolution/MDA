"""Restaurant floor + menu services (PHASE 15 skeleton)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.audit.services import write_audit
from apps.restaurant.models import (
    DiningTable,
    Ingredient,
    KitchenStation,
    MenuCategory,
    MenuItem,
    Modifier,
    ModifierGroup,
    OrderLine,
    Recipe,
    RecipeIngredient,
    RestaurantFloor,
    RestaurantOrder,
)
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


def _as_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() not in {"0", "false", "no", ""}


class RestaurantError(ValueError):
    pass


class RestaurantService:
    ORDER_OPEN_STATES = {
        RestaurantOrder.STATUS_DRAFT,
        RestaurantOrder.STATUS_OPEN,
        RestaurantOrder.STATUS_SUBMITTED,
        RestaurantOrder.STATUS_PREPARING,
        RestaurantOrder.STATUS_SENT,
        RestaurantOrder.STATUS_READY,
        RestaurantOrder.STATUS_SERVED,
        RestaurantOrder.STATUS_COMPLETED,
    }

    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise RestaurantError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            # Fall back when platform actor seeds with tenant context
            branch = Branch.active_objects().filter(pk=branch_id).first()
        if not branch:
            raise RestaurantError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _next_order_number(*, tenant_id) -> str:
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"RO-{today}-"
        count = RestaurantOrder.objects.filter(
            tenant_id=tenant_id, order_number__startswith=prefix
        ).count() + 1
        return f"{prefix}{count:04d}"

    # --- Summary ---
    @staticmethod
    def summary(*, branch_id=None, user=None, request=None) -> dict:
        cats = RestaurantService.list_categories(
            branch_id=branch_id, user=user, request=request
        )
        items = RestaurantService.list_items(
            branch_id=branch_id, user=user, request=request
        )
        tables = RestaurantService.list_tables(
            branch_id=branch_id, user=user, request=request
        )
        orders = RestaurantService.list_orders(
            branch_id=branch_id, user=user, request=request
        )
        open_statuses = [
            RestaurantOrder.STATUS_OPEN,
            RestaurantOrder.STATUS_SENT,
            RestaurantOrder.STATUS_READY,
            RestaurantOrder.STATUS_SERVED,
        ]
        return {
            "categories": cats.count(),
            "menu_items": items.filter(is_available=True).count(),
            "tables": tables.filter(is_active=True).count(),
            "tables_occupied": tables.filter(
                is_active=True, status=DiningTable.STATUS_OCCUPIED
            ).count(),
            "orders_open": orders.filter(status__in=open_statuses).count(),
            "orders_today": orders.filter(opened_at__date=timezone.localdate())
            .exclude(status=RestaurantOrder.STATUS_CANCELLED)
            .count(),
        }

    # --- Categories ---
    @staticmethod
    def list_categories(*, branch_id=None, user=None, request=None):
        qs = MenuCategory.active_objects().select_related("branch")
        return RestaurantService._scope(
            qs, user=user, request=request, branch_id=branch_id
        ).order_by("sort_order", "name")

    @staticmethod
    def get_category(*, pk, user=None, request=None):
        return RestaurantService.list_categories(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_category(*, data, user=None, request=None) -> MenuCategory:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        if not name:
            raise RestaurantError("Category name is required.")
        row = MenuCategory.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name=name,
            sort_order=int(payload.get("sort_order") or 100),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(
            action="create",
            module="restaurant",
            entity=row,
            user=user,
            request=request,
            new_values={"name": row.name},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_category(*, category: MenuCategory, data, user=None, request=None) -> MenuCategory:
        payload = dict(data or {})
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise RestaurantError("Category name is required.")
            category.name = name
        if "sort_order" in payload:
            category.sort_order = int(payload.get("sort_order") or 100)
        if "is_active" in payload:
            category.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            category.notes = (payload.get("notes") or "").strip()
        category.updated_by = user
        category.save()
        write_audit(action="update", module="restaurant", entity=category, user=user, request=request)
        return category

    @staticmethod
    def soft_delete_category(*, category: MenuCategory, user=None, request=None) -> MenuCategory:
        category.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=category, user=user, request=request)
        return category

    # --- Items ---
    @staticmethod
    def list_items(*, branch_id=None, category_id=None, available_only=False, user=None, request=None):
        qs = MenuItem.active_objects().select_related("category", "branch", "product")
        qs = RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if available_only:
            qs = qs.filter(is_available=True)
        return qs.order_by("sort_order", "name")

    @staticmethod
    def get_item(*, pk, user=None, request=None):
        return RestaurantService.list_items(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_item(*, data, user=None, request=None) -> MenuItem:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        category = RestaurantService.get_category(
            pk=payload.get("category_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        if not name:
            raise RestaurantError("Item name is required.")
        row = MenuItem.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id or category.tenant_id,
            branch=branch,
            category=category,
            product_id=payload.get("product_id") or None,
            name=name,
            sku=(payload.get("sku") or "").strip(),
            description=(payload.get("description") or "").strip(),
            unit_price=Decimal(str(payload.get("unit_price") or 0)),
            is_available=_as_bool(payload.get("is_available"), True),
            sort_order=int(payload.get("sort_order") or 100),
            created_by=user,
        )
        write_audit(
            action="create",
            module="restaurant",
            entity=row,
            user=user,
            request=request,
            new_values={"name": row.name},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_item(*, item: MenuItem, data, user=None, request=None) -> MenuItem:
        payload = dict(data or {})
        if payload.get("category_id"):
            item.category = RestaurantService.get_category(
                pk=payload["category_id"], user=user, request=request
            )
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise RestaurantError("Item name is required.")
            item.name = name
        if "sku" in payload:
            item.sku = (payload.get("sku") or "").strip()
        if "description" in payload:
            item.description = (payload.get("description") or "").strip()
        if "unit_price" in payload:
            item.unit_price = Decimal(str(payload.get("unit_price") or 0))
        if "is_available" in payload:
            item.is_available = _as_bool(payload.get("is_available"))
        if "sort_order" in payload:
            item.sort_order = int(payload.get("sort_order") or 100)
        if "product_id" in payload:
            item.product_id = payload.get("product_id") or None
        item.updated_by = user
        item.save()
        write_audit(action="update", module="restaurant", entity=item, user=user, request=request)
        return item

    @staticmethod
    def soft_delete_item(*, item: MenuItem, user=None, request=None) -> MenuItem:
        item.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=item, user=user, request=request)
        return item

    # --- Tables ---
    @staticmethod
    def list_tables(*, branch_id=None, status=None, user=None, request=None):
        qs = DiningTable.active_objects().select_related("branch", "floor")
        qs = RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("code")

    @staticmethod
    def get_table(*, pk, user=None, request=None):
        return RestaurantService.list_tables(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_table(*, data, user=None, request=None) -> DiningTable:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        code = (payload.get("code") or "").strip()
        if not code:
            raise RestaurantError("Table code is required.")
        row = DiningTable.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            code=code,
            label=(payload.get("label") or code).strip(),
            capacity=int(payload.get("capacity") or 4),
            status=payload.get("status") or DiningTable.STATUS_FREE,
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(
            action="create",
            module="restaurant",
            entity=row,
            user=user,
            request=request,
            new_values={"code": row.code},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_table(*, table: DiningTable, data, user=None, request=None) -> DiningTable:
        payload = dict(data or {})
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise RestaurantError("Table code is required.")
            table.code = code
        if "label" in payload:
            table.label = (payload.get("label") or table.code).strip()
        if "capacity" in payload:
            table.capacity = int(payload.get("capacity") or 4)
        if "status" in payload and payload.get("status"):
            if payload["status"] not in dict(DiningTable.STATUS_CHOICES):
                raise RestaurantError(f"Invalid table status: {payload['status']}")
            table.status = payload["status"]
        if "is_active" in payload:
            table.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            table.notes = (payload.get("notes") or "").strip()
        table.updated_by = user
        table.save()
        write_audit(action="update", module="restaurant", entity=table, user=user, request=request)
        return table

    # --- Floors ---
    @staticmethod
    def list_floors(*, branch_id=None, user=None, request=None):
        qs = RestaurantFloor.active_objects().select_related("branch")
        return RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id).order_by(
            "sort_order", "name"
        )

    @staticmethod
    def get_floor(*, pk, user=None, request=None):
        return RestaurantService.list_floors(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_floor(*, data, user=None, request=None) -> RestaurantFloor:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        code = (payload.get("code") or "").strip()
        if not name or not code:
            raise RestaurantError("name and code are required.")
        row = RestaurantFloor.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name=name,
            code=code,
            sort_order=int(payload.get("sort_order") or 100),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_floor(*, floor: RestaurantFloor, data, user=None, request=None) -> RestaurantFloor:
        payload = dict(data or {})
        if "name" in payload:
            floor.name = (payload.get("name") or "").strip()
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise RestaurantError("code is required.")
            floor.code = code
        if "sort_order" in payload:
            floor.sort_order = int(payload.get("sort_order") or 100)
        if "is_active" in payload:
            floor.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            floor.notes = (payload.get("notes") or "").strip()
        floor.updated_by = user
        floor.save()
        write_audit(action="update", module="restaurant", entity=floor, user=user, request=request)
        return floor

    @staticmethod
    def soft_delete_floor(*, floor: RestaurantFloor, user=None, request=None) -> RestaurantFloor:
        floor.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=floor, user=user, request=request)
        return floor

    # --- Kitchen stations ---
    @staticmethod
    def list_stations(*, branch_id=None, user=None, request=None):
        qs = KitchenStation.active_objects().select_related("branch")
        return RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id).order_by(
            "sort_order", "name"
        )

    @staticmethod
    def get_station(*, pk, user=None, request=None):
        return RestaurantService.list_stations(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_station(*, data, user=None, request=None) -> KitchenStation:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        code = (payload.get("code") or "").strip()
        if not name or not code:
            raise RestaurantError("name and code are required.")
        row = KitchenStation.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name=name,
            code=code,
            sort_order=int(payload.get("sort_order") or 100),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_station(*, station: KitchenStation, data, user=None, request=None) -> KitchenStation:
        payload = dict(data or {})
        if "name" in payload:
            station.name = (payload.get("name") or "").strip()
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise RestaurantError("code is required.")
            station.code = code
        if "sort_order" in payload:
            station.sort_order = int(payload.get("sort_order") or 100)
        if "is_active" in payload:
            station.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            station.notes = (payload.get("notes") or "").strip()
        station.updated_by = user
        station.save()
        write_audit(action="update", module="restaurant", entity=station, user=user, request=request)
        return station

    @staticmethod
    def soft_delete_station(*, station: KitchenStation, user=None, request=None) -> KitchenStation:
        station.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=station, user=user, request=request)
        return station

    # --- Modifiers ---
    @staticmethod
    def list_modifier_groups(*, branch_id=None, user=None, request=None):
        qs = ModifierGroup.active_objects().select_related("branch")
        return RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id).order_by(
            "sort_order", "name"
        )

    @staticmethod
    def get_modifier_group(*, pk, user=None, request=None):
        return RestaurantService.list_modifier_groups(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_modifier_group(*, data, user=None, request=None) -> ModifierGroup:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        code = (payload.get("code") or "").strip()
        if not name or not code:
            raise RestaurantError("name and code are required.")
        row = ModifierGroup.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name=name,
            code=code,
            required=_as_bool(payload.get("required"), False),
            min_select=int(payload.get("min_select") or 0),
            max_select=int(payload.get("max_select") or 1),
            sort_order=int(payload.get("sort_order") or 100),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_modifier_group(*, group: ModifierGroup, data, user=None, request=None) -> ModifierGroup:
        payload = dict(data or {})
        if "name" in payload:
            group.name = (payload.get("name") or "").strip()
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise RestaurantError("code is required.")
            group.code = code
        if "required" in payload:
            group.required = _as_bool(payload.get("required"), False)
        if "min_select" in payload:
            group.min_select = int(payload.get("min_select") or 0)
        if "max_select" in payload:
            group.max_select = int(payload.get("max_select") or 1)
        if group.max_select < group.min_select:
            raise RestaurantError("max_select must be >= min_select.")
        if "sort_order" in payload:
            group.sort_order = int(payload.get("sort_order") or 100)
        if "is_active" in payload:
            group.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            group.notes = (payload.get("notes") or "").strip()
        group.updated_by = user
        group.save()
        write_audit(action="update", module="restaurant", entity=group, user=user, request=request)
        return group

    @staticmethod
    def soft_delete_modifier_group(*, group: ModifierGroup, user=None, request=None) -> ModifierGroup:
        group.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=group, user=user, request=request)
        return group

    @staticmethod
    def list_modifiers(*, branch_id=None, group_id=None, user=None, request=None):
        qs = Modifier.active_objects().select_related("group")
        qs = RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id)
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs.order_by("sort_order", "name")

    @staticmethod
    def get_modifier(*, pk, user=None, request=None):
        return RestaurantService.list_modifiers(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_modifier(*, data, user=None, request=None) -> Modifier:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        group = RestaurantService.get_modifier_group(
            pk=payload.get("group_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        code = (payload.get("code") or "").strip()
        if not name or not code:
            raise RestaurantError("name and code are required.")
        row = Modifier.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            group=group,
            name=name,
            code=code,
            price_delta=Decimal(str(payload.get("price_delta") or 0)),
            sort_order=int(payload.get("sort_order") or 100),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_modifier(*, modifier: Modifier, data, user=None, request=None) -> Modifier:
        payload = dict(data or {})
        if payload.get("group_id"):
            modifier.group = RestaurantService.get_modifier_group(
                pk=payload.get("group_id"), user=user, request=request
            )
        if "name" in payload:
            modifier.name = (payload.get("name") or "").strip()
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise RestaurantError("code is required.")
            modifier.code = code
        if "price_delta" in payload:
            modifier.price_delta = Decimal(str(payload.get("price_delta") or 0))
        if "sort_order" in payload:
            modifier.sort_order = int(payload.get("sort_order") or 100)
        if "is_active" in payload:
            modifier.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            modifier.notes = (payload.get("notes") or "").strip()
        modifier.updated_by = user
        modifier.save()
        write_audit(action="update", module="restaurant", entity=modifier, user=user, request=request)
        return modifier

    @staticmethod
    def soft_delete_modifier(*, modifier: Modifier, user=None, request=None) -> Modifier:
        modifier.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=modifier, user=user, request=request)
        return modifier

    # --- Ingredients ---
    @staticmethod
    def list_ingredients(*, branch_id=None, user=None, request=None):
        qs = Ingredient.active_objects().select_related("product")
        return RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id).order_by("name")

    @staticmethod
    def get_ingredient(*, pk, user=None, request=None):
        return RestaurantService.list_ingredients(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_ingredient(*, data, user=None, request=None) -> Ingredient:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        code = (payload.get("code") or "").strip()
        if not name or not code:
            raise RestaurantError("name and code are required.")
        row = Ingredient.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            product_id=payload.get("product_id") or None,
            name=name,
            code=code,
            unit=(payload.get("unit") or "unit").strip() or "unit",
            unit_cost=Decimal(str(payload.get("unit_cost") or 0)),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_ingredient(*, ingredient: Ingredient, data, user=None, request=None) -> Ingredient:
        payload = dict(data or {})
        if "name" in payload:
            ingredient.name = (payload.get("name") or "").strip()
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise RestaurantError("code is required.")
            ingredient.code = code
        if "unit" in payload:
            ingredient.unit = (payload.get("unit") or "unit").strip() or "unit"
        if "unit_cost" in payload:
            ingredient.unit_cost = Decimal(str(payload.get("unit_cost") or 0))
        if "product_id" in payload:
            ingredient.product_id = payload.get("product_id") or None
        if "is_active" in payload:
            ingredient.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            ingredient.notes = (payload.get("notes") or "").strip()
        ingredient.updated_by = user
        ingredient.save()
        write_audit(action="update", module="restaurant", entity=ingredient, user=user, request=request)
        return ingredient

    @staticmethod
    def soft_delete_ingredient(*, ingredient: Ingredient, user=None, request=None) -> Ingredient:
        ingredient.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=ingredient, user=user, request=request)
        return ingredient

    # --- Recipes ---
    @staticmethod
    def list_recipes(*, branch_id=None, menu_item_id=None, user=None, request=None):
        qs = Recipe.active_objects().select_related("menu_item")
        qs = RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id)
        if menu_item_id:
            qs = qs.filter(menu_item_id=menu_item_id)
        return qs.order_by("-created_at")

    @staticmethod
    def get_recipe(*, pk, user=None, request=None):
        return RestaurantService.list_recipes(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_recipe(*, data, user=None, request=None) -> Recipe:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        item = RestaurantService.get_item(pk=payload.get("menu_item_id"), user=user, request=request)
        name = (payload.get("name") or item.name).strip()
        row = Recipe.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            menu_item=item,
            name=name,
            version=(payload.get("version") or "v1").strip() or "v1",
            yield_qty=Decimal(str(payload.get("yield_qty") or 1)),
            waste_percent=Decimal(str(payload.get("waste_percent") or 0)),
            is_active=_as_bool(payload.get("is_active"), True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        ingredients = payload.get("ingredients") or []
        for line in ingredients:
            RestaurantService.add_recipe_ingredient(recipe=row, data=line, user=user, request=request)
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_recipe(*, recipe: Recipe, data, user=None, request=None) -> Recipe:
        payload = dict(data or {})
        if payload.get("menu_item_id"):
            recipe.menu_item = RestaurantService.get_item(pk=payload.get("menu_item_id"), user=user, request=request)
        if "name" in payload:
            recipe.name = (payload.get("name") or "").strip()
        if "version" in payload:
            recipe.version = (payload.get("version") or "v1").strip() or "v1"
        if "yield_qty" in payload:
            recipe.yield_qty = Decimal(str(payload.get("yield_qty") or 1))
        if "waste_percent" in payload:
            recipe.waste_percent = Decimal(str(payload.get("waste_percent") or 0))
        if "is_active" in payload:
            recipe.is_active = _as_bool(payload.get("is_active"))
        if "notes" in payload:
            recipe.notes = (payload.get("notes") or "").strip()
        recipe.updated_by = user
        recipe.save()
        write_audit(action="update", module="restaurant", entity=recipe, user=user, request=request)
        return recipe

    @staticmethod
    def soft_delete_recipe(*, recipe: Recipe, user=None, request=None) -> Recipe:
        recipe.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=recipe, user=user, request=request)
        return recipe

    @staticmethod
    @transaction.atomic
    def add_recipe_ingredient(*, recipe: Recipe, data, user=None, request=None) -> RecipeIngredient:
        ingredient = RestaurantService.get_ingredient(
            pk=data.get("ingredient_id"), user=user, request=request
        )
        qty = Decimal(str(data.get("quantity") or 0))
        if qty <= 0:
            raise RestaurantError("quantity must be positive.")
        unit = (data.get("unit") or ingredient.unit or "unit").strip() or "unit"
        unit_cost = Decimal(str(data.get("unit_cost") if data.get("unit_cost") is not None else ingredient.unit_cost))
        row = RecipeIngredient.objects.create(
            tenant_id=recipe.tenant_id,
            recipe=recipe,
            ingredient=ingredient,
            quantity=qty,
            unit=unit,
            unit_cost=unit_cost,
            notes=(data.get("notes") or "").strip(),
            created_by=user,
        )
        return row

    @staticmethod
    def soft_delete_table(*, table: DiningTable, user=None, request=None) -> DiningTable:
        table.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=table, user=user, request=request)
        return table

    @staticmethod
    def set_table_status(*, table: DiningTable, status: str, user=None) -> DiningTable:
        if status not in dict(DiningTable.STATUS_CHOICES):
            raise RestaurantError(f"Invalid table status: {status}")
        table.status = status
        table.updated_by = user
        table.save(update_fields=["status", "updated_by", "updated_at"])
        return table

    # --- Orders ---
    @staticmethod
    def list_orders(*, branch_id=None, status=None, user=None, request=None):
        qs = RestaurantOrder.active_objects().select_related(
            "branch", "table", "waiter_user"
        ).prefetch_related("lines")
        qs = RestaurantService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-opened_at")

    @staticmethod
    def get_order(*, pk, user=None, request=None):
        return RestaurantService.list_orders(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_order(*, data, user=None, request=None) -> RestaurantOrder:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        tenant_id = payload.get("tenant_id") or branch.tenant_id
        table = None
        if payload.get("table_id"):
            table = RestaurantService.get_table(
                pk=payload["table_id"], user=user, request=request
            )
            if not table.is_active:
                raise RestaurantError("Table is inactive.")
            if table.status not in (
                DiningTable.STATUS_FREE,
                DiningTable.STATUS_RESERVED,
            ):
                raise RestaurantError("Table is not available.")

        waiter_name = (payload.get("waiter_name") or "").strip()
        waiter_user = user if getattr(user, "is_authenticated", False) else None
        if waiter_user and not waiter_name:
            waiter_name = (
                waiter_user.get_full_name() or waiter_user.username or ""
            ).strip()

        order = RestaurantOrder.objects.create(
            tenant_id=tenant_id,
            branch=branch,
            table=table,
            order_number=RestaurantService._next_order_number(tenant_id=tenant_id),
            status=RestaurantOrder.STATUS_OPEN,
            service_type=payload.get("service_type") or RestaurantOrder.SERVICE_DINE_IN,
            waiter_user=waiter_user,
            waiter_name=waiter_name,
            guest_count=int(payload.get("guest_count") or 1),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        lines = payload.get("lines") or []
        for raw in lines:
            RestaurantService.add_line(
                order=order, data=raw, user=user, request=request, recalc=False
            )
        if table is not None:
            RestaurantService.set_table_status(
                table=table, status=DiningTable.STATUS_OCCUPIED, user=user
            )
        order.recalc_subtotal()
        return order

    @staticmethod
    @transaction.atomic
    def add_line(*, order: RestaurantOrder, data, user=None, request=None, recalc=True) -> OrderLine:
        if order.status not in RestaurantService.ORDER_OPEN_STATES:
            raise RestaurantError("Order is closed and cannot be modified.")
        item = RestaurantService.get_item(
            pk=data.get("menu_item_id"), user=user, request=request
        )
        if not item.is_available:
            raise RestaurantError("Cannot sell inactive menu item.")
        qty = Decimal(str(data.get("quantity") or 1))
        if qty <= 0:
            raise RestaurantError("quantity must be positive.")
        price = Decimal(str(data.get("unit_price") if data.get("unit_price") is not None else item.unit_price))
        line = OrderLine.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            menu_item=item,
            product_id=item.product_id,
            name=item.name,
            quantity=qty,
            unit_price=price,
            line_total=(qty * price).quantize(Decimal("0.01")),
            status=OrderLine.STATUS_QUEUED,
            notes=(data.get("notes") or "").strip(),
            created_by=user,
        )
        if recalc:
            order.recalc_subtotal()
        return line

    @staticmethod
    def ensure_menu_item_product(*, item: MenuItem, user=None) -> MenuItem:
        """Ensure MenuItem has a Product so POS Invoice lines can reference it."""
        if item.product_id:
            return item
        from decimal import Decimal

        from apps.products.models import Category, Product, Unit

        tenant_id = item.tenant_id
        cat = Category.active_objects().filter(
            tenant_id=tenant_id, name="Restaurant Menu"
        ).first()
        if cat is None:
            cat = Category.objects.create(
                tenant_id=tenant_id,
                name="Restaurant Menu",
                is_active=True,
                created_by=user,
            )
        unit = Unit.active_objects().filter(tenant_id=tenant_id).first()
        if unit is None:
            unit = Unit.objects.create(
                tenant_id=tenant_id,
                name="Each",
                abbreviation="ea",
                created_by=user,
            )
        sku = (item.sku or "").strip() or f"MENU-{str(item.id)[:8].upper()}"
        product = Product.active_objects().filter(tenant_id=tenant_id, sku=sku).first()
        if product is None:
            product = Product.objects.create(
                tenant_id=tenant_id,
                sku=sku,
                name=item.name,
                category=cat,
                unit=unit,
                cost_price=Decimal("0"),
                selling_price=item.unit_price or Decimal("0"),
                is_active=True,
                created_by=user,
            )
        item.product = product
        item.save(update_fields=["product", "updated_at"])
        return item

    @staticmethod
    def to_pos_items(*, order: RestaurantOrder, user=None) -> list[dict]:
        """Convert open restaurant order lines into PosService checkout items."""
        open_ok = {
            RestaurantOrder.STATUS_OPEN,
            RestaurantOrder.STATUS_SENT,
            RestaurantOrder.STATUS_READY,
            RestaurantOrder.STATUS_SERVED,
        }
        if order.status not in open_ok:
            raise RestaurantError(f"Order {order.order_number} is not open for payment.")
        items = []
        for line in order.lines.filter(deleted_at__isnull=True).exclude(
            status=OrderLine.STATUS_CANCELLED
        ):
            menu_item = line.menu_item
            if not line.product_id:
                menu_item = RestaurantService.ensure_menu_item_product(
                    item=menu_item, user=user
                )
                line.product_id = menu_item.product_id
                line.save(update_fields=["product_id", "updated_at"])
            items.append(
                {
                    "product_id": str(line.product_id),
                    "quantity": float(line.quantity),
                    "unit_price": float(line.unit_price),
                    "name": line.name,
                    "sku": getattr(menu_item, "sku", "") or "",
                }
            )
        if not items:
            raise RestaurantError("Order has no billable lines.")
        return items

    @staticmethod
    def serialize_order_for_pos(*, order: RestaurantOrder, user=None) -> dict:
        items = RestaurantService.to_pos_items(order=order, user=user)
        return {
            "order": {
                "id": str(order.id),
                "order_number": order.order_number,
                "table_id": str(order.table_id) if order.table_id else None,
                "table_code": order.table.code if order.table_id else None,
                "waiter_name": order.waiter_name or "",
                "subtotal": float(order.subtotal or 0),
                "status": order.status,
            },
            "items": items,
            "notes": (
                f"RestaurantOrder: {order.order_number}"
                + (f" | Table: {order.table.code}" if order.table_id else "")
            ),
        }

    @staticmethod
    @transaction.atomic
    def update_order_status(*, order: RestaurantOrder, status: str, user=None) -> RestaurantOrder:
        if status not in dict(RestaurantOrder.STATUS_CHOICES):
            raise RestaurantError(f"Invalid order status: {status}")
        current = order.status
        if current in (
            RestaurantOrder.STATUS_CANCELLED,
            RestaurantOrder.STATUS_VOIDED,
            RestaurantOrder.STATUS_REFUNDED,
        ):
            raise RestaurantError("Closed orders cannot transition further.")
        transitions = {
            RestaurantOrder.STATUS_DRAFT: {RestaurantOrder.STATUS_OPEN, RestaurantOrder.STATUS_CANCELLED},
            RestaurantOrder.STATUS_OPEN: {
                RestaurantOrder.STATUS_SUBMITTED,
                RestaurantOrder.STATUS_SENT,
                RestaurantOrder.STATUS_PAID,
                RestaurantOrder.STATUS_CANCELLED,
                RestaurantOrder.STATUS_VOIDED,
            },
            RestaurantOrder.STATUS_SUBMITTED: {
                RestaurantOrder.STATUS_PREPARING,
                RestaurantOrder.STATUS_SENT,
                RestaurantOrder.STATUS_CANCELLED,
            },
            RestaurantOrder.STATUS_PREPARING: {
                RestaurantOrder.STATUS_READY,
                RestaurantOrder.STATUS_CANCELLED,
            },
            RestaurantOrder.STATUS_SENT: {
                RestaurantOrder.STATUS_READY,
                RestaurantOrder.STATUS_PAID,
                RestaurantOrder.STATUS_CANCELLED,
            },
            RestaurantOrder.STATUS_READY: {
                RestaurantOrder.STATUS_SERVED,
                RestaurantOrder.STATUS_CANCELLED,
            },
            RestaurantOrder.STATUS_SERVED: {
                RestaurantOrder.STATUS_COMPLETED,
                RestaurantOrder.STATUS_PAID,
                RestaurantOrder.STATUS_CANCELLED,
            },
            RestaurantOrder.STATUS_COMPLETED: {
                RestaurantOrder.STATUS_PAID,
                RestaurantOrder.STATUS_REFUNDED,
            },
            RestaurantOrder.STATUS_PAID: {RestaurantOrder.STATUS_REFUNDED},
        }
        if current in transitions and status not in transitions[current]:
            raise RestaurantError(f"Invalid transition from '{current}' to '{status}'.")
        order.status = status
        order.updated_by = user
        if status in (
            RestaurantOrder.STATUS_PAID,
            RestaurantOrder.STATUS_CANCELLED,
            RestaurantOrder.STATUS_VOIDED,
            RestaurantOrder.STATUS_REFUNDED,
        ):
            order.closed_at = timezone.now()
            if order.table_id and status == RestaurantOrder.STATUS_PAID:
                RestaurantService.set_table_status(
                    table=order.table, status=DiningTable.STATUS_FREE, user=user
                )
            if order.table_id and status in (
                RestaurantOrder.STATUS_CANCELLED,
                RestaurantOrder.STATUS_VOIDED,
                RestaurantOrder.STATUS_REFUNDED,
            ):
                open_left = (
                    RestaurantOrder.active_objects()
                    .filter(
                        table_id=order.table_id,
                        status__in=list(RestaurantService.ORDER_OPEN_STATES),
                    )
                    .exclude(pk=order.pk)
                    .exists()
                )
                if not open_left:
                    RestaurantService.set_table_status(
                        table=order.table, status=DiningTable.STATUS_FREE, user=user
                    )
        order.save()
        write_audit(
            action="status",
            module="restaurant",
            entity=order,
            user=user,
            new_values={"from": current, "to": status},
        )
        return order

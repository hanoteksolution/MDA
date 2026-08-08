"""Restaurant floor + menu services (PHASE 15 skeleton)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.audit.services import write_audit
from apps.restaurant.models import (
    DiningTable,
    MenuCategory,
    MenuItem,
    OrderLine,
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
        qs = DiningTable.active_objects().select_related("branch")
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
        item = RestaurantService.get_item(
            pk=data.get("menu_item_id"), user=user, request=request
        )
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
        order.status = status
        order.updated_by = user
        if status in (RestaurantOrder.STATUS_PAID, RestaurantOrder.STATUS_CANCELLED):
            order.closed_at = timezone.now()
            if order.table_id and status == RestaurantOrder.STATUS_PAID:
                RestaurantService.set_table_status(
                    table=order.table, status=DiningTable.STATUS_FREE, user=user
                )
            if order.table_id and status == RestaurantOrder.STATUS_CANCELLED:
                open_left = (
                    RestaurantOrder.active_objects()
                    .filter(
                        table_id=order.table_id,
                        status__in=[
                            RestaurantOrder.STATUS_OPEN,
                            RestaurantOrder.STATUS_SENT,
                            RestaurantOrder.STATUS_READY,
                            RestaurantOrder.STATUS_SERVED,
                        ],
                    )
                    .exclude(pk=order.pk)
                    .exists()
                )
                if not open_left:
                    RestaurantService.set_table_status(
                        table=order.table, status=DiningTable.STATUS_FREE, user=user
                    )
        order.save()
        return order

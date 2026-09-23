"""Combos, promotions, loyalty, reservations, shifts, modifier-group links."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services import write_audit
from apps.restaurant.models import (
    LoyaltyMember,
    LoyaltyProgram,
    LoyaltyTier,
    MenuCombo,
    MenuComboItem,
    MenuItem,
    MenuItemModifierGroup,
    ModifierGroup,
    Promotion,
    StaffShift,
    TableReservation,
)
from apps.restaurant.services.restaurant_service import RestaurantError, RestaurantService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class CommerceError(RestaurantError):
    pass


class CommerceService:
    # --- Modifier group links ---
    @staticmethod
    def list_item_modifier_groups(*, menu_item_id, user=None, request=None):
        item = RestaurantService.get_item(pk=menu_item_id, user=user, request=request)
        return (
            MenuItemModifierGroup.active_objects()
            .filter(menu_item=item)
            .select_related("modifier_group")
            .order_by("sort_order")
        )

    @staticmethod
    @transaction.atomic
    def link_modifier_group(*, menu_item_id, modifier_group_id, sort_order=100, user=None, request=None):
        item = RestaurantService.get_item(pk=menu_item_id, user=user, request=request)
        group = apply_tenant_scope(
            ModifierGroup.active_objects(), user=user, request=request
        ).filter(pk=modifier_group_id).first()
        if not group:
            raise CommerceError("Modifier group not found.")
        payload = stamp_tenant_id({}, user=user, request=request)
        row, created = MenuItemModifierGroup.objects.get_or_create(
            tenant_id=payload.get("tenant_id") or item.tenant_id,
            menu_item=item,
            modifier_group=group,
            defaults={"sort_order": int(sort_order or 100), "created_by": user},
        )
        if not created and row.deleted_at:
            row.restore()
            row.sort_order = int(sort_order or 100)
            row.updated_by = user
            row.save()
        write_audit(action="create" if created else "update", module="restaurant", entity=row, user=user, request=request)
        return row

    # --- Combos ---
    @staticmethod
    def serialize_combo(row: MenuCombo) -> dict:
        items = [
            {
                "id": str(i.id),
                "menu_item_id": str(i.menu_item_id),
                "menu_item_name": i.menu_item.name if i.menu_item_id else "",
                "quantity": float(i.quantity or 1),
                "unit_price": float(i.menu_item.unit_price or 0) if i.menu_item_id else 0,
            }
            for i in row.items.filter(deleted_at__isnull=True).select_related("menu_item")
        ]
        regular = sum(Decimal(str(i["unit_price"])) * Decimal(str(i["quantity"])) for i in items)
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id),
            "name": row.name,
            "code": row.code,
            "description": row.description or "",
            "combo_price": float(row.combo_price or 0),
            "regular_total": float(regular),
            "savings": float(regular - Decimal(str(row.combo_price or 0))),
            "is_active": row.is_active,
            "pos_visible": row.pos_visible,
            "items": items,
            "notes": row.notes or "",
        }

    @staticmethod
    def list_combos(*, branch_id=None, user=None, request=None):
        qs = MenuCombo.active_objects().select_related("branch")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("name")

    @staticmethod
    @transaction.atomic
    def create_combo(*, data, user=None, request=None) -> MenuCombo:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        code = (payload.get("code") or "").strip() or name[:20].upper().replace(" ", "-")
        if not name:
            raise CommerceError("Combo name is required.")
        row = MenuCombo.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name=name,
            code=code,
            description=(payload.get("description") or "").strip(),
            combo_price=Decimal(str(payload.get("combo_price") or 0)),
            is_active=payload.get("is_active", True),
            pos_visible=payload.get("pos_visible", True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        for raw in payload.get("items") or []:
            mid = raw.get("menu_item_id")
            item = RestaurantService.get_item(pk=mid, user=user, request=request)
            MenuComboItem.objects.create(
                tenant_id=row.tenant_id,
                combo=row,
                menu_item=item,
                quantity=Decimal(str(raw.get("quantity") or 1)),
                sort_order=int(raw.get("sort_order") or 100),
                created_by=user,
            )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    def get_combo(*, pk, user=None, request=None) -> MenuCombo:
        return CommerceService.list_combos(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def update_combo(*, combo: MenuCombo, data, user=None, request=None) -> MenuCombo:
        payload = dict(data or {})
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise CommerceError("Combo name is required.")
            combo.name = name
        if "code" in payload:
            combo.code = (payload.get("code") or "").strip() or combo.code
        if "description" in payload:
            combo.description = (payload.get("description") or "").strip()
        if "combo_price" in payload:
            combo.combo_price = Decimal(str(payload.get("combo_price") or 0))
        if "is_active" in payload:
            combo.is_active = bool(payload.get("is_active"))
        if "pos_visible" in payload:
            combo.pos_visible = bool(payload.get("pos_visible"))
        if "notes" in payload:
            combo.notes = (payload.get("notes") or "").strip()
        combo.updated_by = user
        combo.save()
        if "items" in payload:
            combo.items.filter(deleted_at__isnull=True).update(
                deleted_at=timezone.now(), updated_by=user
            )
            for raw in payload.get("items") or []:
                mid = raw.get("menu_item_id")
                item = RestaurantService.get_item(pk=mid, user=user, request=request)
                MenuComboItem.objects.create(
                    tenant_id=combo.tenant_id,
                    combo=combo,
                    menu_item=item,
                    quantity=Decimal(str(raw.get("quantity") or 1)),
                    sort_order=int(raw.get("sort_order") or 100),
                    created_by=user,
                )
        write_audit(action="update", module="restaurant", entity=combo, user=user, request=request)
        return combo

    @staticmethod
    @transaction.atomic
    def archive_combo(*, combo: MenuCombo, user=None, request=None) -> MenuCombo:
        combo.is_active = False
        combo.pos_visible = False
        combo.updated_by = user
        combo.save(update_fields=["is_active", "pos_visible", "updated_by", "updated_at"])
        combo.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=combo, user=user, request=request)
        return combo

    # --- Promotions ---
    @staticmethod
    def serialize_promotion(row: Promotion) -> dict:
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id) if row.branch_id else None,
            "name": row.name,
            "code": row.code,
            "promotion_type": row.promotion_type,
            "percent_off": float(row.percent_off or 0),
            "amount_off": float(row.amount_off or 0),
            "coupon_code": row.coupon_code or "",
            "stackable": row.stackable,
            "priority": row.priority,
            "start_at": row.start_at.isoformat() if row.start_at else None,
            "end_at": row.end_at.isoformat() if row.end_at else None,
            "days_of_week": row.days_of_week or "",
            "time_start": row.time_start.isoformat() if row.time_start else None,
            "time_end": row.time_end.isoformat() if row.time_end else None,
            "menu_item_id": str(row.menu_item_id) if row.menu_item_id else None,
            "category_id": str(row.category_id) if row.category_id else None,
            "is_active": row.is_active,
            "notes": row.notes or "",
        }

    @staticmethod
    def list_promotions(*, branch_id=None, user=None, request=None):
        qs = Promotion.active_objects().select_related("branch", "menu_item", "category")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch_id__isnull=True))
        return qs.order_by("priority", "name")

    @staticmethod
    @transaction.atomic
    def create_promotion(*, data, user=None, request=None) -> Promotion:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = None
        if payload.get("branch_id"):
            branch = RestaurantService._require_branch(
                branch_id=payload.get("branch_id"), user=user, request=request
            )
        name = (payload.get("name") or "").strip()
        if not name:
            raise CommerceError("Promotion name is required.")
        row = Promotion.objects.create(
            tenant_id=payload.get("tenant_id") or (branch.tenant_id if branch else None),
            branch=branch,
            name=name,
            code=(payload.get("code") or name[:20].upper().replace(" ", "-")),
            promotion_type=payload.get("promotion_type") or Promotion.TYPE_PERCENT,
            percent_off=Decimal(str(payload.get("percent_off") or 0)),
            amount_off=Decimal(str(payload.get("amount_off") or 0)),
            coupon_code=(payload.get("coupon_code") or "").strip(),
            stackable=bool(payload.get("stackable")),
            priority=int(payload.get("priority") or 100),
            start_at=payload.get("start_at") or None,
            end_at=payload.get("end_at") or None,
            days_of_week=(payload.get("days_of_week") or "").strip(),
            time_start=payload.get("time_start") or None,
            time_end=payload.get("time_end") or None,
            menu_item_id=payload.get("menu_item_id") or None,
            category_id=payload.get("category_id") or None,
            is_active=payload.get("is_active", True),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    def get_promotion(*, pk, user=None, request=None) -> Promotion:
        return CommerceService.list_promotions(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def update_promotion(*, promotion: Promotion, data, user=None, request=None) -> Promotion:
        payload = dict(data or {})
        for field in (
            "name",
            "code",
            "promotion_type",
            "days_of_week",
            "notes",
            "coupon_code",
        ):
            if field in payload:
                setattr(promotion, field, (payload.get(field) or "").strip() if isinstance(payload.get(field), str) else payload.get(field))
        if "percent_off" in payload:
            promotion.percent_off = Decimal(str(payload.get("percent_off") or 0))
        if "amount_off" in payload:
            promotion.amount_off = Decimal(str(payload.get("amount_off") or 0))
        if "stackable" in payload:
            promotion.stackable = bool(payload.get("stackable"))
        if "priority" in payload:
            promotion.priority = int(payload.get("priority") or 100)
        if "is_active" in payload:
            promotion.is_active = bool(payload.get("is_active"))
        if "start_at" in payload:
            promotion.start_at = payload.get("start_at") or None
        if "end_at" in payload:
            promotion.end_at = payload.get("end_at") or None
        if "menu_item_id" in payload:
            promotion.menu_item_id = payload.get("menu_item_id") or None
        if "category_id" in payload:
            promotion.category_id = payload.get("category_id") or None
        if "name" in payload and not (promotion.name or "").strip():
            raise CommerceError("Promotion name is required.")
        promotion.updated_by = user
        promotion.save()
        write_audit(action="update", module="restaurant", entity=promotion, user=user, request=request)
        return promotion

    @staticmethod
    @transaction.atomic
    def archive_promotion(*, promotion: Promotion, user=None, request=None) -> Promotion:
        promotion.is_active = False
        promotion.updated_by = user
        promotion.save(update_fields=["is_active", "updated_by", "updated_at"])
        promotion.soft_delete(user=user)
        write_audit(action="delete", module="restaurant", entity=promotion, user=user, request=request)
        return promotion

    @staticmethod
    def apply_promotion_discount(*, amount, promotion: Promotion) -> Decimal:
        base = Decimal(str(amount or 0))
        if promotion.promotion_type in (
            Promotion.TYPE_PERCENT,
            Promotion.TYPE_HAPPY_HOUR,
            Promotion.TYPE_CATEGORY,
            Promotion.TYPE_PRODUCT,
        ):
            return (base * Decimal(str(promotion.percent_off or 0)) / Decimal("100")).quantize(
                Decimal("0.01")
            )
        if promotion.promotion_type == Promotion.TYPE_COUPON:
            if Decimal(str(promotion.percent_off or 0)) > 0:
                return (base * Decimal(str(promotion.percent_off or 0)) / Decimal("100")).quantize(
                    Decimal("0.01")
                )
            return min(base, Decimal(str(promotion.amount_off or 0)))
        if promotion.promotion_type == Promotion.TYPE_FIXED:
            return min(base, Decimal(str(promotion.amount_off or 0)))
        return Decimal("0")

    @staticmethod
    def resolve_active_promotion(
        *,
        code: str,
        branch_id=None,
        amount=None,
        user=None,
        request=None,
    ) -> tuple[Promotion | None, Decimal]:
        """Resolve coupon/code → (promotion, discount_amount)."""
        raw = (code or "").strip()
        if not raw:
            return None, Decimal("0")
        now = timezone.now()
        qs = CommerceService.list_promotions(
            branch_id=branch_id, user=user, request=request
        ).filter(is_active=True)
        promo = (
            qs.filter(Q(coupon_code__iexact=raw) | Q(code__iexact=raw))
            .order_by("priority", "name")
            .first()
        )
        if promo is None:
            raise CommerceError(f"Promotion code '{raw}' is not valid.")
        if promo.start_at and promo.start_at > now:
            raise CommerceError("Promotion has not started yet.")
        if promo.end_at and promo.end_at < now:
            raise CommerceError("Promotion has expired.")
        discount = CommerceService.apply_promotion_discount(amount=amount or 0, promotion=promo)
        return promo, discount

    # --- Loyalty ---
    @staticmethod
    def serialize_loyalty_program(row: LoyaltyProgram) -> dict:
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id),
            "name": row.name,
            "points_per_currency": float(row.points_per_currency or 1),
            "redemption_points": row.redemption_points,
            "redemption_value": float(row.redemption_value or 0),
            "birthday_bonus_points": row.birthday_bonus_points,
            "is_active": row.is_active,
            "tiers": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "code": t.code,
                    "min_points": t.min_points,
                }
                for t in row.tiers.filter(deleted_at__isnull=True)
            ],
            "settings": row.settings or {},
        }

    @staticmethod
    def get_or_create_program(*, branch_id, user=None, request=None) -> LoyaltyProgram:
        branch = RestaurantService._require_branch(branch_id=branch_id, user=user, request=request)
        row = (
            apply_tenant_scope(LoyaltyProgram.active_objects(), user=user, request=request)
            .filter(branch_id=branch.id)
            .first()
        )
        if row:
            return row
        payload = stamp_tenant_id({}, user=user, request=request)
        row = LoyaltyProgram.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            name="Café Rewards",
            created_by=user,
        )
        for name, code, pts, order in (
            ("Bronze", "bronze", 0, 1),
            ("Silver", "silver", 200, 2),
            ("Gold", "gold", 500, 3),
            ("VIP", "vip", 1000, 4),
        ):
            LoyaltyTier.objects.create(
                tenant_id=row.tenant_id,
                program=row,
                name=name,
                code=code,
                min_points=pts,
                sort_order=order * 100,
                created_by=user,
            )
        return row

    @staticmethod
    @transaction.atomic
    def update_loyalty_program(*, program: LoyaltyProgram, data, user=None, request=None) -> LoyaltyProgram:
        payload = dict(data or {})
        if "name" in payload:
            program.name = (payload.get("name") or "").strip() or program.name
        if "points_per_currency" in payload:
            program.points_per_currency = Decimal(str(payload.get("points_per_currency") or 1))
        if "redemption_points" in payload:
            program.redemption_points = int(payload.get("redemption_points") or 0)
        if "redemption_value" in payload:
            program.redemption_value = Decimal(str(payload.get("redemption_value") or 0))
        if "birthday_bonus_points" in payload:
            program.birthday_bonus_points = int(payload.get("birthday_bonus_points") or 0)
        if "is_active" in payload:
            program.is_active = bool(payload.get("is_active"))
        if "settings" in payload and isinstance(payload.get("settings"), dict):
            program.settings = payload.get("settings") or {}
        program.updated_by = user
        program.save()
        write_audit(action="update", module="restaurant", entity=program, user=user, request=request)
        return program

    @staticmethod
    @transaction.atomic
    def enroll_member(*, program_id, customer_id, user=None, request=None) -> LoyaltyMember:
        program = apply_tenant_scope(
            LoyaltyProgram.active_objects(), user=user, request=request
        ).filter(pk=program_id).first()
        if not program:
            raise CommerceError("Loyalty program not found.")
        row, _ = LoyaltyMember.objects.get_or_create(
            tenant_id=program.tenant_id,
            program=program,
            customer_id=customer_id,
            defaults={"created_by": user},
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    def serialize_member(row: LoyaltyMember) -> dict:
        return {
            "id": str(row.id),
            "program_id": str(row.program_id),
            "customer_id": str(row.customer_id),
            "tier_id": str(row.tier_id) if row.tier_id else None,
            "tier_name": row.tier.name if row.tier_id else "",
            "points_balance": float(row.points_balance or 0),
            "lifetime_points": float(row.lifetime_points or 0),
            "visit_count": row.visit_count,
            "is_active": row.is_active,
            "joined_at": row.joined_at.isoformat() if row.joined_at else None,
        }

    @staticmethod
    @transaction.atomic
    def earn_points(*, member: LoyaltyMember, spend_amount, user=None, request=None):
        program = member.program
        pts = (
            Decimal(str(spend_amount or 0)) * Decimal(str(program.points_per_currency or 1))
        ).quantize(Decimal("0.01"))
        member.points_balance = Decimal(str(member.points_balance or 0)) + pts
        member.lifetime_points = Decimal(str(member.lifetime_points or 0)) + pts
        member.visit_count = int(member.visit_count or 0) + 1
        tier = (
            program.tiers.filter(deleted_at__isnull=True, min_points__lte=member.lifetime_points)
            .order_by("-min_points")
            .first()
        )
        if tier:
            member.tier = tier
        member.updated_by = user
        member.save()
        write_audit(
            action="update",
            module="restaurant",
            entity=member,
            user=user,
            request=request,
            new_values={"earned": float(pts)},
        )
        return member

    # --- Reservations ---
    @staticmethod
    def serialize_reservation(row: TableReservation) -> dict:
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id),
            "customer_id": str(row.customer_id) if row.customer_id else None,
            "customer_name": row.customer_name,
            "phone": row.phone or "",
            "reserved_for": row.reserved_for.isoformat() if row.reserved_for else None,
            "guests": row.guests,
            "table_id": str(row.table_id) if row.table_id else None,
            "table_code": row.table.code if row.table_id else None,
            "status": row.status,
            "notes": row.notes or "",
        }

    @staticmethod
    def list_reservations(*, branch_id=None, status=None, user=None, request=None):
        qs = TableReservation.active_objects().select_related("branch", "table", "customer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("reserved_for")

    @staticmethod
    @transaction.atomic
    def create_reservation(*, data, user=None, request=None) -> TableReservation:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("customer_name") or "").strip()
        reserved_for = payload.get("reserved_for")
        if not name or not reserved_for:
            raise CommerceError("customer_name and reserved_for are required.")
        table_id = payload.get("table_id")
        if table_id:
            conflict = (
                TableReservation.active_objects()
                .filter(
                    tenant_id=branch.tenant_id,
                    table_id=table_id,
                    reserved_for=reserved_for,
                )
                .exclude(
                    status__in=[
                        TableReservation.STATUS_CANCELLED,
                        TableReservation.STATUS_NO_SHOW,
                        TableReservation.STATUS_COMPLETED,
                    ]
                )
                .exists()
            )
            if conflict:
                raise CommerceError("Table already reserved for that time.")
        row = TableReservation.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            customer_id=payload.get("customer_id") or None,
            customer_name=name,
            phone=(payload.get("phone") or "").strip(),
            reserved_for=reserved_for,
            guests=int(payload.get("guests") or 2),
            table_id=table_id or None,
            status=payload.get("status") or TableReservation.STATUS_PENDING,
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def update_reservation_status(*, reservation: TableReservation, status: str, user=None, request=None):
        if status not in dict(TableReservation.STATUS_CHOICES):
            raise CommerceError("Invalid reservation status.")
        reservation.status = status
        reservation.updated_by = user
        reservation.save(update_fields=["status", "updated_by", "updated_at"])
        if status == TableReservation.STATUS_SEATED and reservation.table_id:
            from apps.restaurant.models import DiningTable

            RestaurantService.set_table_status(
                table=reservation.table, status=DiningTable.STATUS_OCCUPIED, user=user
            )
        write_audit(action="status", module="restaurant", entity=reservation, user=user, request=request)
        return reservation

    # --- Shifts ---
    @staticmethod
    def serialize_shift(row: StaffShift) -> dict:
        return {
            "id": str(row.id),
            "branch_id": str(row.branch_id),
            "user_id": str(row.user_id),
            "user_name": getattr(row.user, "get_full_name", lambda: "")()
            or getattr(row.user, "username", "")
            or str(row.user_id),
            "role": row.role,
            "station_id": str(row.station_id) if row.station_id else None,
            "planned_start": row.planned_start.isoformat() if row.planned_start else None,
            "planned_end": row.planned_end.isoformat() if row.planned_end else None,
            "actual_start": row.actual_start.isoformat() if row.actual_start else None,
            "actual_end": row.actual_end.isoformat() if row.actual_end else None,
            "break_minutes": row.break_minutes,
            "status": row.status,
            "notes": row.notes or "",
        }

    @staticmethod
    def list_shifts(*, branch_id=None, user=None, request=None):
        qs = StaffShift.active_objects().select_related("user", "branch", "station")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("-planned_start")

    @staticmethod
    @transaction.atomic
    def create_shift(*, data, user=None, request=None) -> StaffShift:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        if not payload.get("user_id") or not payload.get("planned_start") or not payload.get("planned_end"):
            raise CommerceError("user_id, planned_start, planned_end required.")
        row = StaffShift.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            user_id=payload["user_id"],
            role=payload.get("role") or StaffShift.ROLE_BARISTA,
            station_id=payload.get("station_id") or None,
            planned_start=payload["planned_start"],
            planned_end=payload["planned_end"],
            break_minutes=int(payload.get("break_minutes") or 0),
            status=payload.get("status") or StaffShift.STATUS_SCHEDULED,
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(action="create", module="restaurant", entity=row, user=user, request=request)
        return row

    @staticmethod
    @transaction.atomic
    def open_shift(*, shift: StaffShift, user=None, request=None) -> StaffShift:
        shift.status = StaffShift.STATUS_OPEN
        shift.actual_start = timezone.now()
        shift.updated_by = user
        shift.save(update_fields=["status", "actual_start", "updated_by", "updated_at"])
        write_audit(action="open", module="restaurant", entity=shift, user=user, request=request)
        return shift

    @staticmethod
    @transaction.atomic
    def close_shift(*, shift: StaffShift, user=None, request=None) -> StaffShift:
        shift.status = StaffShift.STATUS_CLOSED
        shift.actual_end = timezone.now()
        shift.updated_by = user
        shift.save(update_fields=["status", "actual_end", "updated_by", "updated_at"])
        write_audit(action="close", module="restaurant", entity=shift, user=user, request=request)
        return shift

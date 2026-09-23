"""Barista queue / KDS board services."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.services import write_audit
from apps.restaurant.models import (
    BaristaProfile,
    OrderLine,
    RestaurantOrder,
)
from apps.restaurant.serializers.restaurant_serializers import serialize_order
from apps.restaurant.services.restaurant_service import RestaurantError, RestaurantService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class BaristaError(RestaurantError):
    pass


class BaristaService:
    QUEUE_STATUSES = {
        "NEW": {
            RestaurantOrder.STATUS_OPEN,
            RestaurantOrder.STATUS_SUBMITTED,
            RestaurantOrder.STATUS_SENT,
        },
        "PREPARING": {RestaurantOrder.STATUS_PREPARING},
        "READY": {RestaurantOrder.STATUS_READY},
    }

    @staticmethod
    def serialize_barista(row: BaristaProfile) -> dict:
        return {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "user_name": getattr(row.user, "get_full_name", lambda: "")()
            or getattr(row.user, "email", "")
            or str(row.user_id),
            "branch_id": str(row.branch_id),
            "barista_code": row.barista_code or "",
            "skill_level": row.skill_level,
            "specialization": row.specialization or "",
            "default_station_id": str(row.default_station_id)
            if row.default_station_id
            else None,
            "employment_status": row.employment_status,
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "certification": row.certification or "",
            "notes": row.notes or "",
        }

    @staticmethod
    def serialize_ticket(order: RestaurantOrder, *, station_id=None) -> dict:
        data = serialize_order(order, include_lines=True)
        now = timezone.now()
        opened = order.opened_at or order.created_at or now
        elapsed = int((now - opened).total_seconds())
        lines = data.get("lines") or []
        if station_id:
            lines = [
                ln
                for ln in lines
                if str(ln.get("kitchen_station_id") or "") == str(station_id)
            ]
            data["lines"] = lines
        data["elapsed_seconds"] = elapsed
        data["queue_number"] = order.queue_number or ""
        data["priority"] = order.priority
        data["barista_user_id"] = (
            str(order.barista_user_id) if order.barista_user_id else None
        )
        data["board_column"] = BaristaService._column_for(order.status)
        return data

    @staticmethod
    def _column_for(status: str) -> str:
        for col, statuses in BaristaService.QUEUE_STATUSES.items():
            if status in statuses:
                return col
        return "NEW"

    @staticmethod
    def queue(
        *,
        branch_id=None,
        station_id=None,
        user=None,
        request=None,
    ) -> dict:
        active = (
            list(BaristaService.QUEUE_STATUSES["NEW"])
            + list(BaristaService.QUEUE_STATUSES["PREPARING"])
            + list(BaristaService.QUEUE_STATUSES["READY"])
        )
        qs = RestaurantService.list_orders(
            branch_id=branch_id, user=user, request=request
        ).filter(status__in=active).select_related(
            "table", "barista_user", "waiter_user"
        ).prefetch_related("lines", "lines__menu_item")

        columns = {"NEW": [], "PREPARING": [], "READY": []}
        for order in qs.order_by("opened_at"):
            ticket = BaristaService.serialize_ticket(order, station_id=station_id)
            if station_id and not ticket.get("lines"):
                continue
            col = ticket["board_column"]
            columns.setdefault(col, []).append(ticket)
        return {
            "columns": columns,
            "counts": {k: len(v) for k, v in columns.items()},
            "generated_at": timezone.now().isoformat(),
        }

    @staticmethod
    @transaction.atomic
    def _transition(*, order: RestaurantOrder, action: str, user=None, request=None):
        now = timezone.now()
        if action == "accept":
            if order.status not in BaristaService.QUEUE_STATUSES["NEW"]:
                raise BaristaError("Only new/queued orders can be accepted.")
            order.status = RestaurantOrder.STATUS_PREPARING
            order.accepted_at = now
            order.barista_user = user
            order.lines.filter(deleted_at__isnull=True).exclude(
                status=OrderLine.STATUS_CANCELLED
            ).update(status=OrderLine.STATUS_PREP)
        elif action == "start":
            order.status = RestaurantOrder.STATUS_PREPARING
            if not order.accepted_at:
                order.accepted_at = now
            if user and not order.barista_user_id:
                order.barista_user = user
            order.lines.filter(deleted_at__isnull=True).exclude(
                status=OrderLine.STATUS_CANCELLED
            ).update(status=OrderLine.STATUS_PREP)
        elif action == "ready":
            order.status = RestaurantOrder.STATUS_READY
            order.ready_at = now
            order.lines.filter(deleted_at__isnull=True).exclude(
                status=OrderLine.STATUS_CANCELLED
            ).update(status=OrderLine.STATUS_DONE)
        elif action == "complete":
            order.status = RestaurantOrder.STATUS_SERVED
            order.served_at = now
            if not order.ready_at:
                order.ready_at = now
        else:
            raise BaristaError(f"Unknown barista action: {action}")

        order.updated_by = user
        order.save()
        write_audit(
            action=action,
            module="restaurant",
            entity=order,
            user=user,
            request=request,
            new_values={"status": order.status},
        )
        return order

    @staticmethod
    def accept(*, order, user=None, request=None):
        return BaristaService._transition(
            order=order, action="accept", user=user, request=request
        )

    @staticmethod
    def start(*, order, user=None, request=None):
        return BaristaService._transition(
            order=order, action="start", user=user, request=request
        )

    @staticmethod
    def ready(*, order, user=None, request=None):
        return BaristaService._transition(
            order=order, action="ready", user=user, request=request
        )

    @staticmethod
    def complete(*, order, user=None, request=None):
        return BaristaService._transition(
            order=order, action="complete", user=user, request=request
        )

    @staticmethod
    def list_baristas(*, branch_id=None, user=None, request=None):
        qs = BaristaProfile.active_objects().select_related(
            "user", "branch", "default_station"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("barista_code")

    @staticmethod
    @transaction.atomic
    def create_barista(*, data, user=None, request=None) -> BaristaProfile:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = RestaurantService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        user_id = payload.get("user_id")
        if not user_id:
            raise BaristaError("user_id is required.")
        row = BaristaProfile.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            user_id=user_id,
            barista_code=(payload.get("barista_code") or "").strip(),
            skill_level=payload.get("skill_level") or BaristaProfile.SKILL_BARISTA,
            specialization=(payload.get("specialization") or "").strip(),
            default_station_id=payload.get("default_station_id") or None,
            employment_status=payload.get("employment_status")
            or BaristaProfile.STATUS_ACTIVE,
            start_date=payload.get("start_date") or None,
            certification=(payload.get("certification") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        write_audit(
            action="create", module="restaurant", entity=row, user=user, request=request
        )
        return row

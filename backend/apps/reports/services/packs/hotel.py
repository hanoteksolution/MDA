"""Hotel report pack — occupancy, in-house, folios."""

from django.db.models import Count

from apps.hotel.models import Folio, Reservation, Room
from core.tenancy import apply_tenant_scope


def run(*, report, branch_id=None, date_from=None, date_to=None, user=None, request=None):
    if report == "Room Occupancy":
        qs = apply_tenant_scope(
            Room.active_objects().select_related("room_type", "branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        qs = qs.filter(is_active=True)
        grouped = (
            qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        rows = [{"status": r["status"], "count": r["count"]} for r in grouped]
        detail = [
            {
                "room": room.code,
                "type": room.room_type.name if room.room_type_id else "—",
                "status": room.status,
                "floor": room.floor or "—",
                "branch": room.branch.name if room.branch_id else "—",
            }
            for room in qs.order_by("code")[:100]
        ]
        return {
            "columns": ["room", "type", "status", "floor", "branch"],
            "rows": detail,
            "summary": rows,
        }

    if report == "In-House Guests":
        qs = apply_tenant_scope(
            Reservation.active_objects()
            .filter(status=Reservation.STATUS_CHECKED_IN)
            .select_related("guest", "room", "room_type", "branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "reservation": r.reservation_number,
                "guest": r.guest.full_name if r.guest_id else "—",
                "room": r.room.code if r.room_id else "—",
                "type": r.room_type.name if r.room_type_id else "—",
                "check_in": r.check_in_date.isoformat() if r.check_in_date else "—",
                "check_out": r.check_out_date.isoformat() if r.check_out_date else "—",
            }
            for r in qs.order_by("room__code")[:100]
        ]
        return {
            "columns": [
                "reservation",
                "guest",
                "room",
                "type",
                "check_in",
                "check_out",
            ],
            "rows": rows,
        }

    if report == "Open Folios":
        qs = apply_tenant_scope(
            Folio.active_objects()
            .filter(status=Folio.STATUS_OPEN)
            .select_related(
                "reservation",
                "reservation__guest",
                "reservation__room",
                "branch",
            ),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "reservation": f.reservation.reservation_number if f.reservation_id else "—",
                "guest": (
                    f.reservation.guest.full_name
                    if f.reservation_id and f.reservation.guest_id
                    else "—"
                ),
                "room": (
                    f.reservation.room.code
                    if f.reservation_id and f.reservation.room_id
                    else "—"
                ),
                "balance": float(f.balance or 0),
                "outstanding": float(
                    (f.balance or 0) - (getattr(f, "amount_paid", 0) or 0)
                ),
                "opened": f.opened_at.isoformat() if f.opened_at else "—",
            }
            for f in qs.order_by("-balance")[:100]
        ]
        return {
            "columns": [
                "reservation",
                "guest",
                "room",
                "balance",
                "outstanding",
                "opened",
            ],
            "rows": rows,
        }

    if report == "Arrivals & Departures":
        qs = apply_tenant_scope(
            Reservation.active_objects()
            .exclude(status=Reservation.STATUS_CANCELLED)
            .select_related("guest", "room", "room_type"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(check_in_date__gte=date_from)
        if date_to:
            qs = qs.filter(check_out_date__lte=date_to)
        rows = [
            {
                "reservation": r.reservation_number,
                "guest": r.guest.full_name if r.guest_id else "—",
                "status": r.status,
                "room": r.room.code if r.room_id else "—",
                "check_in": r.check_in_date.isoformat() if r.check_in_date else "—",
                "check_out": r.check_out_date.isoformat() if r.check_out_date else "—",
                "rate": float(r.rate_amount or 0),
            }
            for r in qs.order_by("check_in_date")[:100]
        ]
        return {
            "columns": [
                "reservation",
                "guest",
                "status",
                "room",
                "check_in",
                "check_out",
                "rate",
            ],
            "rows": rows,
        }

    return {"columns": [], "rows": []}

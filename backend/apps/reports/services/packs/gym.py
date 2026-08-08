"""Gym report pack (STEP 22)."""

from django.db.models import Count, Sum

from apps.gym.models import (
    Attendance,
    ClassBooking,
    Member,
    MembershipPlan,
    MembershipSubscription,
)
from core.tenancy import apply_tenant_scope


def run(*, report, branch_id=None, date_from=None, date_to=None, user=None, request=None):
    if report == "Active Members":
        qs = apply_tenant_scope(Member.active_objects(), user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "member": m.full_name,
                "number": m.membership_number,
                "status": m.status,
                "phone": m.phone or "—",
                "joined": m.joined_at.isoformat() if m.joined_at else "—",
            }
            for m in qs.order_by("full_name")[:100]
        ]
        return {"columns": ["member", "number", "status", "phone", "joined"], "rows": rows}

    if report == "Subscription Summary":
        qs = apply_tenant_scope(
            MembershipSubscription.active_objects().select_related("plan", "member"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(member__branch_id=branch_id)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        grouped = (
            qs.values("plan__name", "status")
            .annotate(count=Count("id"), revenue=Sum("price_paid"))
            .order_by("plan__name", "status")
        )
        rows = [
            {
                "plan": r["plan__name"] or "—",
                "status": r["status"],
                "count": r["count"],
                "revenue": float(r["revenue"] or 0),
            }
            for r in grouped
        ]
        return {"columns": ["plan", "status", "count", "revenue"], "rows": rows}

    if report == "Attendance Log":
        qs = apply_tenant_scope(
            Attendance.active_objects().select_related("member", "branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(check_in_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(check_in_at__date__lte=date_to)
        rows = [
            {
                "member": a.member.full_name if a.member_id else "—",
                "check_in": a.check_in_at.isoformat() if a.check_in_at else "—",
                "check_out": a.check_out_at.isoformat() if a.check_out_at else "—",
                "source": a.source,
                "branch": a.branch.name if a.branch_id else "—",
            }
            for a in qs.order_by("-check_in_at")[:100]
        ]
        return {
            "columns": ["member", "check_in", "check_out", "source", "branch"],
            "rows": rows,
        }

    if report == "Class Bookings":
        qs = apply_tenant_scope(
            ClassBooking.active_objects().select_related("member", "schedule", "schedule__gym_class"),
            user=user,
            request=request,
        )
        if date_from:
            qs = qs.filter(schedule__starts_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(schedule__starts_at__date__lte=date_to)
        rows = [
            {
                "member": b.member.full_name if b.member_id else "—",
                "class": b.schedule.gym_class.name if b.schedule_id and b.schedule.gym_class_id else "—",
                "starts": b.schedule.starts_at.isoformat() if b.schedule_id and b.schedule.starts_at else "—",
                "status": b.status,
            }
            for b in qs.order_by("-booked_at")[:100]
        ]
        return {"columns": ["member", "class", "starts", "status"], "rows": rows}

    if report == "Plan Catalog":
        qs = apply_tenant_scope(MembershipPlan.active_objects(), user=user, request=request)
        rows = [
            {
                "plan": p.name,
                "code": p.code,
                "duration_days": p.duration_days,
                "price": float(p.price),
                "active": p.is_active,
            }
            for p in qs.order_by("sort_order", "name")
        ]
        return {"columns": ["plan", "code", "duration_days", "price", "active"], "rows": rows}

    return {"columns": [], "rows": []}

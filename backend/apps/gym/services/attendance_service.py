"""Gym attendance check-in / check-out (STEP 16)."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.gym.models import Attendance, Member, MembershipSubscription
from apps.gym.services.subscription_service import SubscriptionService
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope


class AttendanceError(ValueError):
    pass


class AttendanceService:
    # Rapid double-submit guard (open visits are the primary duplicate rule).
    DUPLICATE_WINDOW_SECONDS = 3

    @staticmethod
    def list(
        *,
        member_id=None,
        branch_id=None,
        open_only=False,
        date_from=None,
        date_to=None,
        search=None,
        user=None,
        request=None,
    ):
        qs = Attendance.active_objects().select_related(
            "member", "subscription", "subscription__plan", "branch"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if open_only:
            qs = qs.filter(check_out_at__isnull=True)
        if date_from:
            qs = qs.filter(check_in_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(check_in_at__date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(member__full_name__icontains=search)
                | Q(member__membership_number__icontains=search)
                | Q(member__phone__icontains=search)
            )
        return qs.order_by("-check_in_at")

    @staticmethod
    def summary(*, user=None, request=None):
        today = timezone.localdate()
        qs = apply_tenant_scope(Attendance.active_objects(), user=user, request=request)
        today_qs = qs.filter(check_in_at__date=today)
        return {
            "today_checkins": today_qs.count(),
            "currently_inside": today_qs.filter(check_out_at__isnull=True).count(),
            "total": qs.count(),
        }

    @staticmethod
    def serialize(row: Attendance) -> dict:
        return {
            "id": str(row.id),
            "member_id": str(row.member_id),
            "member_name": row.member.full_name if row.member_id else "",
            "membership_number": row.member.membership_number if row.member_id else "",
            "subscription_id": str(row.subscription_id) if row.subscription_id else None,
            "plan_name": (
                row.subscription.plan.name
                if row.subscription_id and row.subscription.plan_id
                else None
            ),
            "branch_id": str(row.branch_id) if row.branch_id else None,
            "branch_name": row.branch.name if row.branch_id else None,
            "check_in_at": row.check_in_at.isoformat() if row.check_in_at else None,
            "check_out_at": row.check_out_at.isoformat() if row.check_out_at else None,
            "source": row.source,
            "notes": row.notes or "",
            "is_open": row.check_out_at is None,
        }

    @staticmethod
    def resolve_member(
        *,
        member_id=None,
        membership_number=None,
        barcode=None,
        qr_payload=None,
        user=None,
        request=None,
    ) -> tuple[Member, str]:
        """Return (member, source) from check-in identifiers."""
        qs = apply_tenant_scope(Member.active_objects(), user=user, request=request)

        if member_id:
            member = qs.filter(pk=member_id).first()
            if not member:
                raise AttendanceError("Member not found.")
            return member, Attendance.SOURCE_MANUAL

        code = (membership_number or barcode or qr_payload or "").strip()
        if not code:
            raise AttendanceError(
                "Provide member_id, membership_number, barcode, or qr_payload."
            )

        source = Attendance.SOURCE_MEMBERSHIP_NUMBER
        if barcode and not membership_number:
            source = Attendance.SOURCE_BARCODE
        if qr_payload and not membership_number and not barcode:
            source = Attendance.SOURCE_QR
            # QR may embed membership number directly or as mem:<number>
            if code.lower().startswith("mem:"):
                code = code.split(":", 1)[1].strip()

        member = qs.filter(membership_number__iexact=code).first()
        if member is None:
            member = qs.filter(phone__iexact=code).first()
        if member is None:
            raise AttendanceError("Member not found for that code.")
        if member.status == Member.STATUS_SUSPENDED:
            raise AttendanceError("Member is suspended.")
        if member.status == Member.STATUS_INACTIVE:
            raise AttendanceError("Member is inactive.")
        return member, source

    @staticmethod
    def active_subscription_for_member(member: Member) -> MembershipSubscription | None:
        subs = (
            MembershipSubscription.active_objects()
            .filter(member=member)
            .select_related("plan")
            .order_by("-activated_at", "-created_at")
        )
        for sub in subs:
            if SubscriptionService.is_access_allowed(sub):
                return sub
        return None

    @staticmethod
    def _assert_no_duplicate(member: Member, *, now=None):
        now = now or timezone.now()
        open_visit = (
            Attendance.active_objects()
            .filter(member=member, check_out_at__isnull=True)
            .order_by("-check_in_at")
            .first()
        )
        if open_visit is not None:
            raise AttendanceError(
                "Member already checked in. Check out first before a new visit."
            )
        # Guard rapid double-submit (same open visit race): recent check-in with no checkout yet
        # is already covered. Also reject a second create within a few seconds even if the
        # first row was somehow closed immediately (client double-click).
        window_start = now - timedelta(seconds=AttendanceService.DUPLICATE_WINDOW_SECONDS)
        recent = (
            Attendance.active_objects()
            .filter(member=member, check_in_at__gte=window_start, check_out_at__isnull=True)
            .exists()
        )
        if recent:
            raise AttendanceError("Duplicate check-in blocked.")

    @staticmethod
    @transaction.atomic
    def check_in(
        *,
        member_id=None,
        membership_number=None,
        barcode=None,
        qr_payload=None,
        branch_id=None,
        source=None,
        notes="",
        user=None,
        request=None,
        require_membership=True,
    ) -> Attendance:
        member, resolved_source = AttendanceService.resolve_member(
            member_id=member_id,
            membership_number=membership_number,
            barcode=barcode,
            qr_payload=qr_payload,
            user=user,
            request=request,
        )
        if source in {c[0] for c in Attendance.SOURCE_CHOICES}:
            resolved_source = source

        AttendanceService._assert_no_duplicate(member)

        sub = AttendanceService.active_subscription_for_member(member)
        if require_membership and sub is None:
            raise AttendanceError(
                "No active membership. Expired, frozen, or visit limit reached."
            )

        branch = None
        if branch_id:
            branch = apply_tenant_scope(
                Branch.active_objects(), user=user, request=request
            ).filter(pk=branch_id).first()
            if branch is None and member.tenant_id:
                branch = Branch.active_objects().filter(
                    pk=branch_id, tenant_id=member.tenant_id
                ).first()
            if branch is None:
                raise AttendanceError("Branch not found.")
        elif member.branch_id:
            branch = member.branch

        now = timezone.now()
        row = Attendance.objects.create(
            member=member,
            subscription=sub,
            branch=branch,
            check_in_at=now,
            source=resolved_source,
            notes=notes or "",
            tenant_id=member.tenant_id,
            created_by=user,
        )

        if sub is not None:
            MembershipSubscription.objects.filter(pk=sub.pk).update(
                visits_used=sub.visits_used + 1
            )
            sub.refresh_from_db(fields=["visits_used"])

        return row

    @staticmethod
    @transaction.atomic
    def check_out(
        *,
        attendance_id=None,
        member_id=None,
        membership_number=None,
        user=None,
        request=None,
        notes="",
    ) -> Attendance:
        qs = apply_tenant_scope(
            Attendance.active_objects().filter(check_out_at__isnull=True),
            user=user,
            request=request,
        ).select_related("member")

        row = None
        if attendance_id:
            row = qs.filter(pk=attendance_id).first()
        else:
            member, _ = AttendanceService.resolve_member(
                member_id=member_id,
                membership_number=membership_number,
                user=user,
                request=request,
            )
            row = qs.filter(member=member).order_by("-check_in_at").first()

        if row is None:
            raise AttendanceError("No open check-in found.")

        row.check_out_at = timezone.now()
        if notes:
            row.notes = (row.notes + "\n" if row.notes else "") + notes
        row.updated_by = user
        row.save(update_fields=["check_out_at", "notes", "updated_by", "updated_at"])
        return row

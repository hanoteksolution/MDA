"""Self-service gym member portal (STEP 28 mobile app)."""

from __future__ import annotations

from django.utils import timezone

from apps.gym.models import Member
from apps.gym.models.classes import ClassBooking
from apps.gym.services.attendance_service import AttendanceService
from apps.gym.services.class_service import BookingService
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import SubscriptionService
from apps.gym.services.workout_service import AssignmentService as WorkoutAssignmentService
from apps.platform.services.module_feature_service import ModuleFeatureService


class MemberPortalError(ValueError):
    def __init__(self, message: str, *, code: str = "MEMBER_PORTAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class MemberPortalService:
    @staticmethod
    def resolve_member(*, user) -> Member:
        if user is None or not getattr(user, "is_authenticated", False):
            raise MemberPortalError("Authentication required.", code="UNAUTHORIZED")
        member = (
            Member.active_objects()
            .select_related("branch", "customer")
            .filter(user_id=user.id)
            .first()
        )
        if member is None:
            raise MemberPortalError(
                "No gym member profile is linked to this account.",
                code="MEMBER_NOT_LINKED",
            )
        if member.status == Member.STATUS_SUSPENDED:
            raise MemberPortalError("Member account is suspended.", code="MEMBER_SUSPENDED")
        return member

    @staticmethod
    def qr_payload(*, member: Member) -> dict:
        payload = f"mem:{member.membership_number}"
        return {
            "payload": payload,
            "membership_number": member.membership_number,
            "member_id": str(member.id),
            "member_name": member.full_name,
            "format": "mem:{membership_number}",
        }

    @staticmethod
    def profile(*, user, request=None) -> dict:
        member = MemberPortalService.resolve_member(user=user)
        active_sub = AttendanceService.active_subscription_for_member(member)
        return {
            "member": MemberService.serialize(member),
            "active_subscription": (
                SubscriptionService.serialize(active_sub) if active_sub else None
            ),
        }

    @staticmethod
    def home(*, user, request=None) -> dict:
        member = MemberPortalService.resolve_member(user=user)
        member_id = str(member.id)
        today = timezone.localdate()
        features = ModuleFeatureService.resolve_features("gym", user=user, request=request)
        today_visits = 0
        open_visit = None
        if features.get("attendance"):
            attendance_qs = AttendanceService.list(
                member_id=member_id, user=user, request=request
            )
            today_visits = attendance_qs.filter(check_in_at__date=today).count()
            open_visit = attendance_qs.filter(check_out_at__isnull=True).first()
        upcoming_classes = []
        if features.get("classes"):
            upcoming_classes = list(
                BookingService.list(
                    member_id=member_id,
                    status=ClassBooking.STATUS_CONFIRMED,
                    user=user,
                    request=request,
                ).filter(schedule__starts_at__gte=timezone.now())[:5]
            )
        active_workouts = WorkoutAssignmentService.list(
            member_id=member_id,
            status="active",
            user=user,
            request=request,
        )
        active_sub = AttendanceService.active_subscription_for_member(member)
        return {
            "member": MemberService.serialize(member),
            "active_subscription": (
                SubscriptionService.serialize(active_sub) if active_sub else None
            ),
            "today_checkins": today_visits,
            "is_checked_in": open_visit is not None,
            "open_attendance_id": str(open_visit.id) if open_visit else None,
            "upcoming_classes": [
                BookingService.serialize(b) for b in upcoming_classes
            ],
            "active_workouts": [
                WorkoutAssignmentService.serialize(a) for a in active_workouts[:5]
            ],
            "features": features,
        }

    @staticmethod
    def link_user(*, member: Member, user, linked_by=None) -> Member:
        """Bind a portal user to a gym member (staff provisioning)."""
        if Member.active_objects().filter(user_id=user.id).exclude(pk=member.pk).exists():
            raise MemberPortalError(
                "This user is already linked to another member profile.",
                code="USER_ALREADY_LINKED",
            )
        member.user = user
        member.updated_by = linked_by
        member.save(update_fields=["user", "updated_by", "updated_at"])
        return member

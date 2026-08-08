"""Gym member self-service endpoints for the React Native app (STEP 28)."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.gym.services.attendance_service import AttendanceService
from apps.gym.services.class_service import BookingService
from apps.gym.services.feature_gate import gym_feature_required
from apps.gym.services.member_portal_service import MemberPortalError, MemberPortalService
from apps.gym.services.workout_service import AssignmentService as WorkoutAssignmentService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasModule, HasPermission


def _portal_permissions():
    return [
        IsAuthenticated,
        HasPermission("gym.member_portal"),
        HasModule("gym"),
    ]


@gym_feature_required("members")
class MemberPortalHomeView(APIView):
    permission_classes = _portal_permissions()

    def get(self, request):
        try:
            data = MemberPortalService.home(user=request.user, request=request)
        except MemberPortalError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_403_FORBIDDEN,
                code=getattr(exc, "code", "MEMBER_PORTAL_ERROR"),
            )
        return success_response(data=data)


@gym_feature_required("members")
class MemberPortalProfileView(APIView):
    permission_classes = _portal_permissions()

    def get(self, request):
        try:
            data = MemberPortalService.profile(user=request.user, request=request)
        except MemberPortalError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_403_FORBIDDEN,
                code=getattr(exc, "code", "MEMBER_PORTAL_ERROR"),
            )
        return success_response(data=data)


@gym_feature_required("members")
class MemberPortalQrView(APIView):
    permission_classes = _portal_permissions()

    def get(self, request):
        try:
            member = MemberPortalService.resolve_member(user=request.user)
            data = MemberPortalService.qr_payload(member=member)
        except MemberPortalError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_403_FORBIDDEN,
                code=getattr(exc, "code", "MEMBER_PORTAL_ERROR"),
            )
        return success_response(data=data)


@gym_feature_required("attendance")
class MemberPortalAttendanceView(APIView):
    permission_classes = _portal_permissions()

    def get(self, request):
        try:
            member = MemberPortalService.resolve_member(user=request.user)
            qs = AttendanceService.list(
                member_id=str(member.id),
                user=request.user,
                request=request,
            )
        except MemberPortalError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_403_FORBIDDEN,
                code=getattr(exc, "code", "MEMBER_PORTAL_ERROR"),
            )
        return paginate_queryset(
            request,
            qs,
            lambda items: [AttendanceService.serialize(a) for a in items],
        )


@gym_feature_required("members")
class MemberPortalWorkoutsView(APIView):
    permission_classes = _portal_permissions()

    def get(self, request):
        try:
            member = MemberPortalService.resolve_member(user=request.user)
            qs = WorkoutAssignmentService.list(
                member_id=str(member.id),
                status=request.query_params.get("status"),
                user=request.user,
                request=request,
            )
        except MemberPortalError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_403_FORBIDDEN,
                code=getattr(exc, "code", "MEMBER_PORTAL_ERROR"),
            )
        return paginate_queryset(
            request,
            qs,
            lambda items: [WorkoutAssignmentService.serialize(a) for a in items],
        )


@gym_feature_required("classes")
class MemberPortalClassesView(APIView):
    permission_classes = _portal_permissions()

    def get(self, request):
        try:
            member = MemberPortalService.resolve_member(user=request.user)
            qs = BookingService.list(
                member_id=str(member.id),
                status=request.query_params.get("status"),
                user=request.user,
                request=request,
            )
        except MemberPortalError as exc:
            return error_response(
                message=str(exc),
                status=status.HTTP_403_FORBIDDEN,
                code=getattr(exc, "code", "MEMBER_PORTAL_ERROR"),
            )
        return paginate_queryset(
            request,
            qs,
            lambda items: [BookingService.serialize(b) for b in items],
        )

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.gym.services.attendance_service import AttendanceError, AttendanceService
from apps.gym.services.class_service import BookingService, ClassError, ClassService
from apps.gym.services.member_service import MemberError, MemberService
from apps.gym.services.subscription_service import (
    PlanService,
    SubscriptionError,
    SubscriptionService,
)
from apps.gym.services.trainer_service import (
    AssignmentService,
    PTSessionService,
    TrainerError,
    TrainerService,
)
from apps.gym.services.workout_service import (
    AssignmentService as WorkoutAssignmentService,
    BodyMeasurementService,
    ExerciseService,
    ProgressService,
    WorkoutError,
    WorkoutPlanService,
    WorkoutSummaryService,
)
from apps.gym.services.gym_payment_service import GymPaymentError, GymPaymentService
from apps.gym.services.feature_gate import gym_feature_required
from apps.platform.services.module_feature_service import ModuleFeatureService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


class GymSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        features = ModuleFeatureService.resolve_features(
            "gym", user=request.user, request=request
        )
        data = {
            "members": MemberService.summary(user=request.user, request=request)
            if features.get("members")
            else {"total": 0, "active": 0, "inactive": 0, "suspended": 0},
            "subscriptions": SubscriptionService.summary(
                user=request.user, request=request
            )
            if features.get("members")
            else {
                "total": 0,
                "pending": 0,
                "active": 0,
                "frozen": 0,
                "expired": 0,
                "cancelled": 0,
            },
            "attendance": AttendanceService.summary(
                user=request.user, request=request
            )
            if features.get("attendance")
            else {"today_checkins": 0, "currently_inside": 0, "total": 0},
            "trainers": TrainerService.summary(user=request.user, request=request),
            "classes": BookingService.summary(user=request.user, request=request)
            if features.get("classes")
            else {
                "upcoming_sessions": 0,
                "active_bookings": 0,
                "waitlisted": 0,
                "class_templates": 0,
            },
            "workouts": WorkoutSummaryService.summary(user=request.user, request=request),
            "features": features,
        }
        return success_response(data=data)


@gym_feature_required("members")
class MemberListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = MemberService.list(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
            branch_id=request.query_params.get("branch_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [MemberService.serialize(m) for m in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            member = MemberService.create(
                data=request.data, user=request.user, request=request
            )
        except MemberError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=MemberService.serialize(member),
            message="Member created.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("members")
class MemberDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request, pk):
        try:
            member = MemberService.get(pk=pk, user=request.user, request=request)
        except Exception:
            return error_response(message="Member not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=MemberService.serialize(member))

    def put(self, request, pk):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            member = MemberService.get(pk=pk, user=request.user, request=request)
            member = MemberService.update(
                member=member, data=request.data, user=request.user, request=request
            )
        except MemberError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(message="Member not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(
            data=MemberService.serialize(member), message="Member updated."
        )

    def delete(self, request, pk):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            member = MemberService.get(pk=pk, user=request.user, request=request)
        except Exception:
            return error_response(message="Member not found.", status=status.HTTP_404_NOT_FOUND)
        MemberService.soft_delete(member=member, user=request.user)
        return success_response(message="Member deleted.")


@gym_feature_required("members")
class PlanListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param == "true":
            is_active = True
        elif is_active_param == "false":
            is_active = False
        qs = PlanService.list(
            search=request.query_params.get("search"),
            is_active=is_active,
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [PlanService.serialize(p) for p in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            plan = PlanService.create(
                data=request.data, user=request.user, request=request
            )
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PlanService.serialize(plan),
            message="Plan created.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("members")
class PlanDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request, pk):
        try:
            plan = PlanService.get(pk=pk, user=request.user, request=request)
        except Exception:
            return error_response(message="Plan not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=PlanService.serialize(plan))

    def put(self, request, pk):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            plan = PlanService.get(pk=pk, user=request.user, request=request)
            plan = PlanService.update(
                plan=plan, data=request.data, user=request.user, request=request
            )
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(message="Plan not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=PlanService.serialize(plan), message="Plan updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            plan = PlanService.get(pk=pk, user=request.user, request=request)
        except Exception:
            return error_response(message="Plan not found.", status=status.HTTP_404_NOT_FOUND)
        PlanService.soft_delete(plan=plan, user=request.user)
        return success_response(message="Plan deleted.")


@gym_feature_required("members")
class SubscriptionListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = SubscriptionService.list(
            member_id=request.query_params.get("member_id"),
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda rows: [
                SubscriptionService.serialize(SubscriptionService.expire_if_needed(s))
                for s in rows
            ],
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            sub = SubscriptionService.subscribe(
                member_id=data.get("member_id"),
                plan_id=data.get("plan_id"),
                start_date=data.get("start_date"),
                activate=bool(data.get("activate") or data.get("mark_paid")),
                payment_reference=data.get("payment_reference") or "",
                invoice_id=data.get("invoice_id"),
                price_paid=data.get("price_paid"),
                notes=data.get("notes") or "",
                user=request.user,
                request=request,
            )
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=SubscriptionService.serialize(sub),
            message="Subscription created.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("members")
class SubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request, pk):
        try:
            sub = SubscriptionService.get(pk=pk, user=request.user, request=request)
            sub = SubscriptionService.expire_if_needed(sub)
        except Exception:
            return error_response(
                message="Subscription not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(data=SubscriptionService.serialize(sub))


@gym_feature_required("members")
class SubscriptionActivateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            sub = SubscriptionService.get(pk=pk, user=request.user, request=request)
            sub = SubscriptionService.activate(
                subscription=sub,
                start_date=request.data.get("start_date"),
                payment_reference=request.data.get("payment_reference") or "",
                invoice_id=request.data.get("invoice_id"),
                price_paid=request.data.get("price_paid"),
                user=request.user,
                request=request,
            )
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Subscription not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=SubscriptionService.serialize(sub), message="Subscription activated."
        )


@gym_feature_required("members")
class SubscriptionFreezeView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            sub = SubscriptionService.get(pk=pk, user=request.user, request=request)
            sub = SubscriptionService.freeze(
                subscription=sub,
                days=request.data.get("days"),
                user=request.user,
            )
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Subscription not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=SubscriptionService.serialize(sub), message="Subscription frozen."
        )


@gym_feature_required("members")
class SubscriptionUnfreezeView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            sub = SubscriptionService.get(pk=pk, user=request.user, request=request)
            sub = SubscriptionService.unfreeze(subscription=sub, user=request.user)
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Subscription not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=SubscriptionService.serialize(sub), message="Subscription unfrozen."
        )


@gym_feature_required("members")
class SubscriptionCancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            sub = SubscriptionService.get(pk=pk, user=request.user, request=request)
            sub = SubscriptionService.cancel(
                subscription=sub,
                user=request.user,
                notes=request.data.get("notes") or "",
            )
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Subscription not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=SubscriptionService.serialize(sub), message="Subscription cancelled."
        )


@gym_feature_required("attendance")
class AttendanceListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        open_only = request.query_params.get("open_only") == "true"
        qs = AttendanceService.list(
            member_id=request.query_params.get("member_id"),
            branch_id=request.query_params.get("branch_id"),
            open_only=open_only,
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            search=request.query_params.get("search"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [AttendanceService.serialize(a) for a in items]
        )


@gym_feature_required("attendance")
class AttendanceCheckInView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.attendance.checkin")]

    def post(self, request):
        data = request.data
        try:
            row = AttendanceService.check_in(
                member_id=data.get("member_id"),
                membership_number=data.get("membership_number"),
                barcode=data.get("barcode"),
                qr_payload=data.get("qr_payload") or data.get("qr"),
                branch_id=data.get("branch_id"),
                source=data.get("source"),
                notes=data.get("notes") or "",
                user=request.user,
                request=request,
                require_membership=data.get("require_membership", True) is not False,
            )
        except AttendanceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=AttendanceService.serialize(row),
            message="Checked in.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("attendance")
class AttendanceCheckOutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.attendance.checkin")]

    def post(self, request):
        data = request.data
        try:
            row = AttendanceService.check_out(
                attendance_id=data.get("attendance_id") or data.get("id"),
                member_id=data.get("member_id"),
                membership_number=data.get("membership_number"),
                user=request.user,
                request=request,
                notes=data.get("notes") or "",
            )
        except AttendanceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=AttendanceService.serialize(row), message="Checked out."
        )


class TrainerListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = TrainerService.list(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [TrainerService.serialize(t) for t in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            trainer = TrainerService.create(
                data=request.data, user=request.user, request=request
            )
        except TrainerError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=TrainerService.serialize(trainer),
            message="Trainer created.",
            status=status.HTTP_201_CREATED,
        )


class TrainerDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request, pk):
        try:
            trainer = TrainerService.get(pk=pk, user=request.user, request=request)
        except Exception:
            return error_response(message="Trainer not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=TrainerService.serialize(trainer))

    def put(self, request, pk):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            trainer = TrainerService.get(pk=pk, user=request.user, request=request)
            trainer = TrainerService.update(
                trainer=trainer, data=request.data, user=request.user, request=request
            )
        except TrainerError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(message="Trainer not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(
            data=TrainerService.serialize(trainer), message="Trainer updated."
        )

    def delete(self, request, pk):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            trainer = TrainerService.get(pk=pk, user=request.user, request=request)
        except Exception:
            return error_response(message="Trainer not found.", status=status.HTTP_404_NOT_FOUND)
        TrainerService.soft_delete(trainer=trainer, user=request.user)
        return success_response(message="Trainer deleted.")


class AssignmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = AssignmentService.list(
            member_id=request.query_params.get("member_id"),
            trainer_id=request.query_params.get("trainer_id"),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [AssignmentService.serialize(a) for a in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            row = AssignmentService.assign(
                member_id=data.get("member_id"),
                trainer_id=data.get("trainer_id"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                notes=data.get("notes") or "",
                user=request.user,
                request=request,
            )
        except TrainerError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=AssignmentService.serialize(row),
            message="Trainer assigned.",
            status=status.HTTP_201_CREATED,
        )


class AssignmentEndView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            row = AssignmentService.list(user=request.user, request=request).get(pk=pk)
            row = AssignmentService.end(
                assignment=row,
                end_date=request.data.get("end_date"),
                user=request.user,
            )
        except TrainerError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Assignment not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=AssignmentService.serialize(row), message="Assignment ended."
        )


class PTSessionListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = PTSessionService.list(
            member_id=request.query_params.get("member_id"),
            trainer_id=request.query_params.get("trainer_id"),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [PTSessionService.serialize(s) for s in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            row = PTSessionService.schedule(
                member_id=data.get("member_id"),
                trainer_id=data.get("trainer_id"),
                scheduled_at=data.get("scheduled_at"),
                duration_minutes=data.get("duration_minutes") or 60,
                assignment_id=data.get("assignment_id"),
                notes=data.get("notes") or "",
                user=request.user,
                request=request,
            )
        except TrainerError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PTSessionService.serialize(row),
            message="PT session scheduled.",
            status=status.HTTP_201_CREATED,
        )


class PTSessionStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            row = PTSessionService.list(user=request.user, request=request).get(pk=pk)
            row = PTSessionService.set_status(
                session=row,
                status=request.data.get("status") or "",
                user=request.user,
            )
        except TrainerError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Session not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=PTSessionService.serialize(row), message="Session updated."
        )


class PTSessionCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            result = GymPaymentService.checkout_pt_session(
                session_id=pk,
                data=request.data,
                user=request.user,
                request=request,
            )
        except GymPaymentError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        msg = "PT session billed."
        if result.get("idempotent_replay"):
            msg = "PT checkout replayed (idempotent)."
        return success_response(
            data=result,
            message=msg,
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("classes")
class GymClassListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param == "true":
            is_active = True
        elif is_active_param == "false":
            is_active = False
        qs = ClassService.list_classes(
            search=request.query_params.get("search"),
            is_active=is_active,
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [ClassService.serialize_class(c) for c in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            obj = ClassService.create_class(
                data=request.data, user=request.user, request=request
            )
        except ClassError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ClassService.serialize_class(obj),
            message="Class created.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("classes")
class ClassScheduleListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        upcoming = request.query_params.get("upcoming", "true") != "false"
        qs = ClassService.list_schedules(
            gym_class_id=request.query_params.get("gym_class_id")
            or request.query_params.get("class_id"),
            upcoming_only=upcoming,
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [ClassService.serialize_schedule(s) for s in items],
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            sched = ClassService.create_schedule(
                data=request.data, user=request.user, request=request
            )
        except ClassError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ClassService.serialize_schedule(sched),
            message="Session scheduled.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("classes")
class ClassBookingListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = BookingService.list(
            schedule_id=request.query_params.get("schedule_id"),
            member_id=request.query_params.get("member_id"),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [BookingService.serialize(b) for b in items]
        )

    def post(self, request):
        if not (
            request.user.has_permission("gym.manage")
            or request.user.has_permission("gym.attendance.checkin")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            booking = BookingService.book(
                schedule_id=data.get("schedule_id"),
                member_id=data.get("member_id"),
                allow_waitlist=data.get("allow_waitlist", True) is not False,
                notes=data.get("notes") or "",
                user=request.user,
                request=request,
            )
        except ClassError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=BookingService.serialize(booking),
            message="Booked." if booking.status == "confirmed" else "Waitlisted.",
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("classes")
class ClassBookingCancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            booking = BookingService.cancel(
                booking_id=pk, user=request.user, request=request
            )
        except ClassError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Booking not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(
            data=BookingService.serialize(booking), message="Booking cancelled."
        )


@gym_feature_required("classes")
class ClassBookingCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            result = GymPaymentService.checkout_class_booking(
                booking_id=pk,
                data=request.data,
                user=request.user,
                request=request,
            )
        except GymPaymentError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        msg = "Class drop-in billed."
        if result.get("idempotent_replay"):
            msg = "Class checkout replayed (idempotent)."
        return success_response(
            data=result,
            message=msg,
            status=status.HTTP_201_CREATED,
        )


class ExerciseListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param == "true":
            is_active = True
        elif is_active_param == "false":
            is_active = False
        qs = ExerciseService.list(
            search=request.query_params.get("search"),
            muscle_group=request.query_params.get("muscle_group"),
            is_active=is_active,
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [ExerciseService.serialize(e) for e in items]
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            obj = ExerciseService.create(
                data=request.data, user=request.user, request=request
            )
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ExerciseService.serialize(obj),
            message="Exercise created.",
            status=status.HTTP_201_CREATED,
        )


class WorkoutPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param == "true":
            is_active = True
        elif is_active_param == "false":
            is_active = False
        qs = WorkoutPlanService.list(
            search=request.query_params.get("search"),
            is_active=is_active,
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [WorkoutPlanService.serialize(p) for p in items],
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            obj = WorkoutPlanService.create(
                data=request.data, user=request.user, request=request
            )
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=WorkoutPlanService.serialize(obj, include_days=True),
            message="Workout plan created.",
            status=status.HTTP_201_CREATED,
        )


class WorkoutPlanDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request, pk):
        try:
            plan = WorkoutPlanService.get(pk=pk, user=request.user, request=request)
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_404_NOT_FOUND)
        return success_response(
            data=WorkoutPlanService.serialize(plan, include_days=True)
        )


class WorkoutAssignmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = WorkoutAssignmentService.list(
            member_id=request.query_params.get("member_id"),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [WorkoutAssignmentService.serialize(a) for a in items],
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            obj = WorkoutAssignmentService.assign(
                data=request.data, user=request.user, request=request
            )
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=WorkoutAssignmentService.serialize(obj),
            message="Workout plan assigned.",
            status=status.HTTP_201_CREATED,
        )


class WorkoutProgressListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = ProgressService.list(
            member_id=request.query_params.get("member_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [ProgressService.serialize(p) for p in items],
        )

    def post(self, request):
        if not (
            request.user.has_permission("gym.manage")
            or request.user.has_permission("gym.attendance.checkin")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            obj = ProgressService.log(
                data=request.data, user=request.user, request=request
            )
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ProgressService.serialize(obj),
            message="Workout logged.",
            status=status.HTTP_201_CREATED,
        )


class BodyMeasurementListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        qs = BodyMeasurementService.list(
            member_id=request.query_params.get("member_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [BodyMeasurementService.serialize(m) for m in items],
        )

    def post(self, request):
        if not request.user.has_permission("gym.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            obj = BodyMeasurementService.record(
                data=request.data, user=request.user, request=request
            )
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=BodyMeasurementService.serialize(obj),
            message="Measurement recorded.",
            status=status.HTTP_201_CREATED,
        )


class BodyMeasurementChartView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.view")]

    def get(self, request):
        member_id = request.query_params.get("member_id")
        if not member_id:
            return error_response(
                message="member_id is required.", status=status.HTTP_400_BAD_REQUEST
            )
        try:
            points = BodyMeasurementService.chart_series(
                member_id=member_id,
                metric=request.query_params.get("metric") or "weight_kg",
                user=request.user,
                request=request,
            )
        except WorkoutError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data={"points": points})


@gym_feature_required("members")
class GymCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request):
        try:
            result = GymPaymentService.checkout_membership(
                data=request.data, user=request.user, request=request
            )
        except GymPaymentError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        msg = "Membership sold."
        if result.get("idempotent_replay"):
            msg = "Checkout replayed (idempotent)."
        return success_response(
            data=result,
            message=msg,
            status=status.HTTP_201_CREATED,
        )


@gym_feature_required("members")
class SubscriptionPayView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("gym.manage")]

    def post(self, request, pk):
        try:
            result = GymPaymentService.pay_pending_subscription(
                subscription_id=pk,
                data=request.data,
                user=request.user,
                request=request,
            )
        except GymPaymentError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(
                message="Subscription not found.", status=status.HTTP_404_NOT_FOUND
            )
        return success_response(data=result, message="Subscription paid and activated.")

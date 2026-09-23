from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.notifications.services.notification_service import NotificationService
from core.responses.api_response import success_response
from core.utils.pagination import paginate_queryset


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_read = request.query_params.get("is_read")
        if is_read is not None:
            is_read = is_read.lower() in ("1", "true", "yes")
        branch_ids = None
        if request.query_params.get("branch_id") or request.headers.get("X-Branch-Id"):
            from core.branching import resolve_branch_scope

            scope = resolve_branch_scope(request=request)  # 403 for a branch not yours
            branch_ids = None if scope.is_all else scope.branch_ids
        qs = NotificationService.list(
            user=request.user,
            is_read=is_read,
            notification_type=request.query_params.get("type"),
            branch_ids=branch_ids,
            severity=request.query_params.get("severity"),
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [NotificationService.serialize(n) for n in items]
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationService.unread_count(user=request.user, request=request)
        return success_response(data={"count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = NotificationService.mark_read(
            user=request.user,
            notification_id=notification_id,
            request=request,
        )
        return success_response(
            data=NotificationService.serialize(notification),
            message="Notification marked as read.",
        )


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = NotificationService.mark_all_read(user=request.user, request=request)
        return success_response(
            data={"updated": updated},
            message="All notifications marked as read.",
        )

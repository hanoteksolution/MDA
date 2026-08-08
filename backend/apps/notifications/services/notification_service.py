from __future__ import annotations

from datetime import timedelta
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.notifications.models import Notification
from core.tenancy import apply_tenant_scope

User = get_user_model()


class NotificationService:
    @staticmethod
    def serialize(n: Notification) -> dict:
        return {
            "id": str(n.id),
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "link": n.link,
            "is_read": n.is_read,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "metadata": n.metadata or {},
            "created_at": n.created_at.isoformat(),
        }

    @staticmethod
    def list(
        *,
        user,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        request=None,
    ):
        qs = Notification.active_objects().filter(user=user)
        qs = apply_tenant_scope(qs, user=user, request=request)
        if is_read is not None:
            qs = qs.filter(is_read=is_read)
        if notification_type:
            qs = qs.filter(notification_type=notification_type)
        return qs.order_by("-created_at")

    @staticmethod
    def unread_count(*, user, request=None) -> int:
        return NotificationService.list(user=user, is_read=False, request=request).count()

    @staticmethod
    def mark_read(*, user, notification_id, request=None) -> Notification:
        qs = Notification.active_objects().filter(user=user, id=notification_id)
        qs = apply_tenant_scope(qs, user=user, request=request)
        notification = qs.get()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return notification

    @staticmethod
    def mark_all_read(*, user, request=None) -> int:
        qs = Notification.active_objects().filter(user=user, is_read=False)
        qs = apply_tenant_scope(qs, user=user, request=request)
        now = timezone.now()
        return qs.update(is_read=True, read_at=now, updated_at=now)

    @staticmethod
    def tenant_users_with_permission(tenant, codename: str) -> list:
        users = User.objects.filter(
            tenant=tenant,
            is_active=True,
            deleted_at__isnull=True,
        )
        return [u for u in users if u.has_permission(codename)]

    @staticmethod
    def has_recent_duplicate(
        *,
        user,
        notification_type: str,
        dedupe_key: str,
        within_hours: int = 24,
    ) -> bool:
        cutoff = timezone.now() - timedelta(hours=within_hours)
        return Notification.active_objects().filter(
            user=user,
            notification_type=notification_type,
            metadata__dedupe_key=dedupe_key,
            created_at__gte=cutoff,
        ).exists()

    @staticmethod
    def notify_user(
        *,
        tenant,
        user,
        notification_type: str,
        title: str,
        message: str,
        link: str = "",
        metadata: Optional[dict] = None,
        dedupe_key: Optional[str] = None,
        dedupe_hours: int = 24,
    ) -> Notification | None:
        meta = dict(metadata or {})
        if dedupe_key:
            meta["dedupe_key"] = dedupe_key
            if NotificationService.has_recent_duplicate(
                user=user,
                notification_type=notification_type,
                dedupe_key=dedupe_key,
                within_hours=dedupe_hours,
            ):
                return None
        notification = Notification(
            tenant=tenant,
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            metadata=meta,
        )
        notification.save()
        return notification

    @staticmethod
    def notify_tenant_permission(
        *,
        tenant,
        permission_codename: str,
        notification_type: str,
        title: str,
        message: str,
        link: str = "",
        metadata: Optional[dict] = None,
        dedupe_key: Optional[str] = None,
        dedupe_hours: int = 24,
    ) -> int:
        created = 0
        for user in NotificationService.tenant_users_with_permission(tenant, permission_codename):
            if NotificationService.notify_user(
                tenant=tenant,
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                metadata=metadata,
                dedupe_key=dedupe_key,
                dedupe_hours=dedupe_hours,
            ):
                created += 1
        return created

    @staticmethod
    def notify_users(
        *,
        tenant,
        users: Iterable,
        notification_type: str,
        title: str,
        message: str,
        link: str = "",
        metadata: Optional[dict] = None,
        dedupe_key: Optional[str] = None,
        dedupe_hours: int = 24,
    ) -> int:
        created = 0
        for user in users:
            if NotificationService.notify_user(
                tenant=tenant,
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                metadata=metadata,
                dedupe_key=dedupe_key,
                dedupe_hours=dedupe_hours,
            ):
                created += 1
        return created

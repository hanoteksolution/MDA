from __future__ import annotations

from datetime import timedelta
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q
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
            "branch_id": str(n.branch_id) if n.branch_id else None,
            "severity": n.severity,
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "audience": n.audience,
            "action_url": n.action_url,
            "expires_at": n.expires_at.isoformat() if n.expires_at else None,
            "created_at": n.created_at.isoformat(),
        }

    @staticmethod
    def list(
        *,
        user,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        branch_ids=None,
        severity: Optional[str] = None,
        request=None,
    ):
        """``branch_ids``: only alerts for those branches (plus tenant-wide, branch-less ones)."""
        qs = Notification.active_objects().filter(user=user)
        qs = apply_tenant_scope(qs, user=user, request=request)
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        if branch_ids is not None:
            qs = qs.filter(Q(branch__isnull=True) | Q(branch_id__in=list(branch_ids)))
        if severity:
            qs = qs.filter(severity=severity)
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
        **extra,
    ) -> Notification | None:
        """``extra``: optional Phase 6 fields — branch, severity, entity_type, entity_id,
        audience, expires_at, action_url."""
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
            **extra,
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
        **extra,
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
                **extra,
            ):
                created += 1
        return created

    @staticmethod
    def branch_audience(branch, *, permission: str | None = None, managers_only: bool = False,
                        exclude=None) -> list:
        """Users who may act in ``branch`` — never a tenant-wide broadcast.

        Membership is the real branch permission (`has_branch_permission`), so a user with
        the codename globally but no access to this branch is not an audience member.
        """
        from core.branching import has_branch_permission, is_branch_manager

        users = []
        for user in User.objects.filter(
            tenant_id=branch.tenant_id, is_active=True, deleted_at__isnull=True
        ):
            if exclude is not None and user.pk == getattr(exclude, "pk", None):
                continue
            if permission and not has_branch_permission(user, permission, branch):
                continue
            if managers_only and not is_branch_manager(user, branch):
                continue
            users.append(user)
        return users

    @staticmethod
    def notify_branch(
        *,
        branch,
        notification_type: str,
        title: str,
        message: str,
        severity: str = Notification.SEVERITY_INFO,
        permission: str | None = None,
        managers_only: bool = False,
        entity_type: str = "",
        entity_id="",
        link: str = "",
        action_url: str = "",
        metadata: Optional[dict] = None,
        dedupe_key: Optional[str] = None,
        dedupe_hours: int = 24,
        exclude=None,
        expires_at=None,
    ) -> int:
        """Alert one branch's audience once per ``dedupe_key`` (per recipient)."""
        from apps.platform.models import Tenant

        tenant = Tenant.objects.filter(pk=branch.tenant_id).first()
        audience = (
            Notification.AUDIENCE_BRANCH_MANAGERS if managers_only else Notification.AUDIENCE_BRANCH
        )
        return NotificationService.notify_users(
            tenant=tenant,
            users=NotificationService.branch_audience(
                branch, permission=permission, managers_only=managers_only, exclude=exclude
            ),
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            metadata=metadata,
            dedupe_key=dedupe_key,
            dedupe_hours=dedupe_hours,
            branch=branch,
            severity=severity,
            entity_type=entity_type,
            entity_id=str(entity_id or ""),
            audience=audience,
            action_url=action_url or link,
            expires_at=expires_at,
        )

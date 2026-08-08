"""Login rate limiting / lockout after repeated failures (STEP 30)."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.authentication.models import LoginAttempt


class LoginLockoutService:
    @staticmethod
    def _max_attempts() -> int:
        return int(getattr(settings, "LOGIN_LOCKOUT_MAX_ATTEMPTS", 5))

    @staticmethod
    def _window_minutes() -> int:
        return int(getattr(settings, "LOGIN_LOCKOUT_WINDOW_MINUTES", 15))

    @staticmethod
    def _lockout_minutes() -> int:
        return int(getattr(settings, "LOGIN_LOCKOUT_DURATION_MINUTES", 30))

    @staticmethod
    def client_ip(request) -> str:
        if request is None:
            return ""
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR") or ""

    @staticmethod
    def normalize_username(username: str) -> str:
        return (username or "").strip().lower()

    @staticmethod
    def is_locked(*, username: str, request=None) -> tuple[bool, dict | None]:
        normalized = LoginLockoutService.normalize_username(username)
        if not normalized:
            return False, None

        window_start = timezone.now() - timedelta(minutes=LoginLockoutService._window_minutes())
        failures = LoginAttempt.objects.filter(
            username=normalized,
            succeeded=False,
            created_at__gte=window_start,
        )
        count = failures.count()
        if count < LoginLockoutService._max_attempts():
            return False, None

        last_failure = failures.order_by("-created_at").first()
        if last_failure is None:
            return False, None

        locked_until = last_failure.created_at + timedelta(
            minutes=LoginLockoutService._lockout_minutes()
        )
        now = timezone.now()
        if now >= locked_until:
            return False, None

        retry_after = max(int((locked_until - now).total_seconds()), 1)
        return True, {
            "locked_until": locked_until.isoformat(),
            "retry_after_seconds": retry_after,
            "failed_attempts": count,
        }

    @staticmethod
    def record_success(*, username: str, request=None) -> None:
        normalized = LoginLockoutService.normalize_username(username)
        if not normalized:
            return
        LoginAttempt.objects.create(
            username=normalized,
            ip_address=LoginLockoutService.client_ip(request) or None,
            succeeded=True,
        )

    @staticmethod
    def record_failure(*, username: str, request=None) -> None:
        normalized = LoginLockoutService.normalize_username(username)
        if not normalized:
            return
        LoginAttempt.objects.create(
            username=normalized,
            ip_address=LoginLockoutService.client_ip(request) or None,
            succeeded=False,
        )

    @staticmethod
    def lockout_message(details: dict | None) -> str:
        if not details:
            return "Too many failed login attempts. Try again later."
        seconds = details.get("retry_after_seconds") or 0
        minutes = max(seconds // 60, 1)
        if minutes >= 60:
            hours = max(minutes // 60, 1)
            return f"Too many failed login attempts. Try again in about {hours} hour(s)."
        return f"Too many failed login attempts. Try again in about {minutes} minute(s)."

from rest_framework import permissions

from apps.platform.services.module_service import tenant_has_module


def HasPermission(codename: str):
    """Return a DRF permission class that checks a single permission codename."""

    class _HasPermission(permissions.BasePermission):
        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            return request.user.has_permission(codename)

    _HasPermission.__name__ = f"HasPermission_{codename.replace('.', '_')}"
    _HasPermission.__qualname__ = _HasPermission.__name__
    return _HasPermission


def HasModule(code: str):
    """Return a DRF permission class that requires an enabled tenant module."""

    class _HasModule(permissions.BasePermission):
        message = f"Module '{code}' is not enabled for this business."

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            return tenant_has_module(code, user=request.user, request=request)

    safe = (code or "none").replace(".", "_").replace("-", "_")
    _HasModule.__name__ = f"HasModule_{safe}"
    _HasModule.__qualname__ = _HasModule.__name__
    return _HasModule


def require_permission(codename: str):
    """Alias for HasPermission — kept for backwards compatibility."""
    return HasPermission(codename)


def user_has_any(user, *codes: str) -> bool:
    """True if the user has any of the given permission codes (elevated admin included)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return any(user.has_permission(c) for c in codes)

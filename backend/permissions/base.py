from rest_framework import permissions


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


def require_permission(codename: str):
    """Alias for HasPermission — kept for backwards compatibility."""
    return HasPermission(codename)

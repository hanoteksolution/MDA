"""DRF throttling scopes for mobile / auth endpoints (STEP 27)."""

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """Stricter limit for login, refresh, and other credential exchange."""

    scope = "auth"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


__all__ = ["AnonRateThrottle", "AuthRateThrottle", "UserRateThrottle"]

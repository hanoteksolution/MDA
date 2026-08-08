"""Security response headers (STEP 30)."""

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add baseline browser security headers on every response."""

    def process_response(self, request, response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if getattr(settings, "SECURE_CROSS_ORIGIN_OPENER_POLICY", None):
            response.headers.setdefault(
                "Cross-Origin-Opener-Policy",
                settings.SECURE_CROSS_ORIGIN_OPENER_POLICY,
            )
        return response

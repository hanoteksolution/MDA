"""JWT authentication that rejects cross-tenant host misuse."""

from __future__ import annotations

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from apps.platform.services.tenant_resolver import user_matches_host_tenant


class TenantAwareJWTAuthentication(JWTAuthentication):
    """After JWT validation, ensure user may access the host-resolved tenant."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        if not getattr(settings, "TENANT_HOST_ENFORCEMENT", True):
            return user, validated_token

        tenant = getattr(request, "tenant", None)
        mode = getattr(request, "tenant_mode", None)
        if mode != "tenant" or tenant is None:
            return user, validated_token

        if not user_matches_host_tenant(user, tenant):
            raise AuthenticationFailed(
                detail="Your account does not belong to this business domain.",
                code="TENANT_HOST_MISMATCH",
            )
        return user, validated_token

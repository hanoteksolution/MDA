"""Bind tenant context from the request Host header."""

from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin

from apps.platform.services.tenant_resolver import (
    apply_mobile_tenant_slug_header,
    normalize_hostname,
    resolve_tenant_from_hostname,
)
from core.tenancy import clear_current_tenant, set_current_tenant, set_tenant_enforcement


class TenantResolutionMiddleware(MiddlewareMixin):
    """
    Resolve tenant from Host / X-Forwarded-Host and bind request + contextvars.

    Does not enforce auth mismatch (JWT is authenticated later in DRF).
    Enforcement lives in TenantAwareJWTAuthentication.
    """

    def process_request(self, request):
        clear_current_tenant()
        set_tenant_enforcement(False)

        forwarded = request.META.get("HTTP_X_FORWARDED_HOST")
        host_header = request.META.get("HTTP_HOST") or ""
        hostname = normalize_hostname(forwarded or host_header)

        resolution = resolve_tenant_from_hostname(hostname)
        slug_header = request.META.get("HTTP_X_TENANT_SLUG")
        resolution = apply_mobile_tenant_slug_header(
            resolution,
            hostname=hostname,
            tenant_slug_header=slug_header,
        )
        request.tenant_resolution = resolution
        request.tenant = resolution.tenant
        request.tenant_hostname = resolution.hostname
        request.tenant_mode = resolution.mode

        if resolution.tenant is not None:
            set_current_tenant(resolution.tenant)
            # Soft: context available; row-level enforcement still STEP 06
            set_tenant_enforcement(False)

        return None

    def process_response(self, request, response):
        clear_current_tenant()
        set_tenant_enforcement(False)
        if getattr(request, "tenant_mode", None):
            response["X-Tenant-Mode"] = request.tenant_mode
            if getattr(request, "tenant", None) is not None:
                response["X-Tenant-Slug"] = getattr(request.tenant, "slug", "") or ""
        return response

    def process_exception(self, request, exception):
        clear_current_tenant()
        set_tenant_enforcement(False)
        return None

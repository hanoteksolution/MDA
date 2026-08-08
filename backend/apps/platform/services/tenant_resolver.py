"""Resolve tenant from HTTP Host / X-Forwarded-Host (server-side only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from django.conf import settings

from apps.platform.services.domain_utils import (
    RESERVED_TENANT_SLUGS,
    get_tenant_base_domain,
    is_reserved_tenant_slug,
    normalize_tenant_slug,
)

ResolutionMode = Literal["platform", "tenant", "unknown"]


@dataclass(frozen=True)
class TenantResolution:
    mode: ResolutionMode
    hostname: str
    tenant: object | None = None
    subdomain: str | None = None
    domain_id: object | None = None
    reason: str = ""

    @property
    def tenant_id(self):
        if self.tenant is None:
            return None
        return getattr(self.tenant, "pk", None) or getattr(self.tenant, "id", None)


def normalize_hostname(host: str | None) -> str:
    if not host:
        return ""
    # X-Forwarded-Host may be a list
    host = host.split(",")[0].strip().lower()
    if ":" in host and not host.startswith("["):
        # strip port (keep IPv6 bracket form simple: skip)
        host = host.rsplit(":", 1)[0]
    return host.strip(".")


def get_platform_hosts() -> set[str]:
    base = get_tenant_base_domain().lower()
    configured = getattr(settings, "PLATFORM_HOSTS", None) or ""
    extra = {h.strip().lower() for h in str(configured).split(",") if h.strip()}
    defaults = {
        base,
        f"www.{base}",
        f"api.{base}",
        f"admin.{base}",
        f"app.{base}",
        f"platform.{base}",
        "localhost",
        "127.0.0.1",
        "tauri.localhost",
    }
    return defaults | extra


def extract_subdomain(hostname: str, base_domain: str | None = None) -> Optional[str]:
    base = (base_domain or get_tenant_base_domain()).lower().strip(".")
    host = hostname.lower().strip(".")
    if host == base:
        return None
    suffix = "." + base
    if not host.endswith(suffix):
        return None
    sub = host[: -len(suffix)]
    if not sub or "." in sub:
        return None
    return sub


def resolve_tenant_from_hostname(hostname: str) -> TenantResolution:
    """Map hostname → platform | tenant | unknown.

    Never trusts client-supplied tenant IDs — host mapping only.
    """
    host = normalize_hostname(hostname)
    if not host:
        return TenantResolution(mode="unknown", hostname="", reason="missing_host")

    if host in get_platform_hosts():
        return TenantResolution(mode="platform", hostname=host, reason="platform_host")

    # Exact TenantDomain match (custom or primary)
    from apps.platform.models import Tenant, TenantDomain

    domain_row = (
        TenantDomain.active_objects()
        .select_related("tenant", "tenant__business_type", "tenant__settings")
        .filter(domain=host, is_active=True, tenant__deleted_at__isnull=True)
        .first()
    )
    if domain_row and domain_row.tenant_id:
        tenant = domain_row.tenant
        if not tenant.is_active and tenant.status == Tenant.STATUS_CANCELLED:
            return TenantResolution(
                mode="unknown",
                hostname=host,
                subdomain=domain_row.subdomain or None,
                reason="tenant_cancelled",
            )
        return TenantResolution(
            mode="tenant",
            hostname=host,
            tenant=tenant,
            subdomain=domain_row.subdomain or extract_subdomain(host),
            domain_id=domain_row.id,
            reason="tenant_domain",
        )

    subdomain = extract_subdomain(host)
    if subdomain:
        if is_reserved_tenant_slug(subdomain) or subdomain in RESERVED_TENANT_SLUGS:
            return TenantResolution(
                mode="platform",
                hostname=host,
                subdomain=subdomain,
                reason="reserved_subdomain",
            )
        slug = normalize_tenant_slug(subdomain)
        tenant = (
            Tenant.objects.select_related("business_type", "settings")
            .filter(slug=slug, deleted_at__isnull=True)
            .first()
        )
        if tenant:
            return TenantResolution(
                mode="tenant",
                hostname=host,
                tenant=tenant,
                subdomain=slug,
                reason="tenant_slug",
            )
        return TenantResolution(
            mode="unknown",
            hostname=host,
            subdomain=slug,
            reason="unknown_subdomain",
        )

    return TenantResolution(mode="unknown", hostname=host, reason="unmanaged_host")


def resolve_tenant_from_slug(slug: str) -> TenantResolution:
    """Resolve tenant by slug (server-side lookup only — never trust client tenant IDs)."""
    from apps.platform.models import Tenant

    normalized = normalize_tenant_slug(slug or "")
    if not normalized:
        return TenantResolution(mode="unknown", hostname="", reason="missing_slug")
    if is_reserved_tenant_slug(normalized) or normalized in RESERVED_TENANT_SLUGS:
        return TenantResolution(
            mode="unknown",
            hostname="",
            subdomain=normalized,
            reason="reserved_slug",
        )
    tenant = (
        Tenant.objects.select_related("business_type", "settings")
        .filter(slug=normalized, deleted_at__isnull=True)
        .first()
    )
    if tenant:
        return TenantResolution(
            mode="tenant",
            hostname="",
            tenant=tenant,
            subdomain=normalized,
            reason="tenant_slug",
        )
    return TenantResolution(
        mode="unknown",
        hostname="",
        subdomain=normalized,
        reason="unknown_slug",
    )


def apply_mobile_tenant_slug_header(
    resolution: TenantResolution,
    *,
    hostname: str,
    tenant_slug_header: str | None,
) -> TenantResolution:
    """
    When the request hits a platform API host, allow mobile clients to supply
    X-Tenant-Slug so tenant context can be resolved without a tenant subdomain host.
    """
    slug = (tenant_slug_header or "").strip()
    if resolution.mode != "platform" or not slug or resolution.tenant is not None:
        return resolution

    header_resolution = resolve_tenant_from_slug(slug)
    if header_resolution.tenant is None:
        return resolution

    return TenantResolution(
        mode="tenant",
        hostname=hostname,
        tenant=header_resolution.tenant,
        subdomain=header_resolution.subdomain,
        reason="tenant_slug_header",
    )


def resolution_public_payload(resolution: TenantResolution) -> dict:
    tenant = resolution.tenant
    payload = {
        "mode": resolution.mode,
        "hostname": resolution.hostname,
        "subdomain": resolution.subdomain,
        "reason": resolution.reason,
        "base_domain": get_tenant_base_domain(),
        "tenant": None,
    }
    if tenant is not None:
        bt = getattr(tenant, "business_type", None)
        settings_row = getattr(tenant, "settings", None)
        branding = {}
        if settings_row is not None:
            branding = settings_row.branding or {}
        payload["tenant"] = {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status,
            "is_active": tenant.is_active,
            "currency": tenant.currency,
            "language": tenant.language,
            "timezone": tenant.timezone,
            "business_type_code": bt.code if bt else None,
            "business_type_name": bt.name if bt else None,
            "branding": branding,
        }
    return payload


def user_matches_host_tenant(user, tenant) -> bool:
    """Whether an authenticated user may operate on a host-resolved tenant."""
    if user is None or not getattr(user, "is_authenticated", False):
        return True
    if tenant is None:
        return True

    from apps.platform.services.platform_service import PlatformService

    if PlatformService.is_global_platform_admin(user):
        return True
    return PlatformService.user_can_access_tenant(user, tenant)

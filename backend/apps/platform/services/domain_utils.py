"""Canonical tenant subdomain / workspace URL normalization and validation.

TLS certificate provisioning is not part of workspace creation.
*.erp.safaritechno.com is covered by the platform wildcard certificate.
"""

from __future__ import annotations

import re
from typing import Any

from django.conf import settings

TENANT_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
MIN_SUBDOMAIN_LENGTH = 2
MAX_SUBDOMAIN_LENGTH = 63

# Backend-authoritative reserved list (do not duplicate on the frontend).
RESERVED_TENANT_SLUGS = frozenset(
    {
        "www",
        "api",
        "admin",
        "app",
        "apps",
        "auth",
        "login",
        "register",
        "signup",
        "billing",
        "payments",
        "payment",
        "sms",
        "integrations",
        "support",
        "help",
        "status",
        "docs",
        "static",
        "media",
        "assets",
        "files",
        "cdn",
        "mail",
        "email",
        "smtp",
        "ftp",
        "dev",
        "staging",
        "test",
        "demo",
        "dashboard",
        "portal",
        "system",
        "internal",
        "platform",
        "erp",
        "health",
        "null",
        "undefined",
        "localhost",
        "safaritechno",
        "safari",
    }
)

SUGGESTION_SUFFIXES = (
    "cafe",
    "coffee",
    "shop",
    "store",
    "hq",
    "co",
    "app",
    "group",
    "team",
)


class SubdomainError(ValueError):
    """Structured subdomain validation failure (invalid or reserved)."""

    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        self.reason = reason  # "invalid" | "reserved"


def get_tenant_base_domain() -> str:
    return getattr(settings, "TENANT_BASE_DOMAIN", None) or "erp.safaritechno.com"


def normalize_tenant_slug(value: str) -> str:
    """Normalize user input toward a DNS-safe subdomain (does not invent a new brand).

    Collapses whitespace/underscores/invalid characters to hyphens, but never trims a
    leading or trailing hyphen — a boundary hyphen makes the result invalid rather than
    silently rewriting what the user typed (validate_tenant_slug rejects it).
    """
    text = (value or "").strip().lower()
    text = text.replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text


def is_reserved_tenant_slug(slug: str) -> bool:
    return normalize_tenant_slug(slug) in RESERVED_TENANT_SLUGS


def validate_tenant_slug(slug: str) -> str:
    """Return a canonical slug or raise SubdomainError / ValueError."""
    normalized = normalize_tenant_slug(slug)
    if not normalized:
        raise SubdomainError("Subdomain / slug is required.", reason="invalid")
    if len(normalized) < MIN_SUBDOMAIN_LENGTH:
        raise SubdomainError(
            f"Subdomain must be at least {MIN_SUBDOMAIN_LENGTH} characters.",
            reason="invalid",
        )
    if len(normalized) > MAX_SUBDOMAIN_LENGTH:
        raise SubdomainError(
            f"Subdomain must be {MAX_SUBDOMAIN_LENGTH} characters or fewer.",
            reason="invalid",
        )
    if not normalized.isascii() or not TENANT_SLUG_PATTERN.fullmatch(normalized):
        raise SubdomainError(
            "Use only lowercase letters, numbers, and hyphens; "
            "do not start or end with a hyphen.",
            reason="invalid",
        )
    if is_reserved_tenant_slug(normalized):
        raise SubdomainError(f"Subdomain '{normalized}' is reserved.", reason="reserved")
    return normalized


def build_tenant_hostname(slug: str, *, base_domain: str | None = None) -> str:
    base = (base_domain or get_tenant_base_domain()).lstrip(".")
    return f"{validate_tenant_slug(slug)}.{base}"


def is_subdomain_taken(slug: str, *, ignore_registration_id=None) -> bool:
    """True when the slug cannot be claimed (live tenant/domain or live registration hold).

    Soft-deleted shops do not hold their name: it is released on claim
    (see ``release_deleted_subdomain``). ``ignore_registration_id`` lets a registration
    that is being provisioned claim the name it already holds.
    """
    from apps.platform.models import RegistrationRequest, Tenant, TenantDomain

    if Tenant.objects.filter(slug=slug, deleted_at__isnull=True).exists():
        return True
    hostname = f"{slug}.{get_tenant_base_domain()}".lower()
    if TenantDomain.objects.filter(
        domain__iexact=hostname,
        deleted_at__isnull=True,
        tenant__deleted_at__isnull=True,
    ).exists():
        return True
    live = {
        RegistrationRequest.STATUS_PENDING_EMAIL,
        RegistrationRequest.STATUS_VERIFIED,
        RegistrationRequest.STATUS_PROVISIONING,
        RegistrationRequest.STATUS_READY,
    }
    holds = RegistrationRequest.active_objects().filter(subdomain=slug, status__in=live)
    if ignore_registration_id:
        holds = holds.exclude(pk=ignore_registration_id)
    return holds.exists()


def release_deleted_subdomain(slug: str) -> None:
    """Free a slug/hostname still held by soft-deleted shops.

    Tenant.slug and TenantDomain.domain are unique even for soft-deleted rows, so a
    deleted shop would otherwise block its name forever. The old rows are renamed
    (data is kept) and their hostname is deactivated.
    """
    from django.db import transaction
    from django.utils import timezone

    from apps.platform.models import Tenant, TenantDomain

    base = get_tenant_base_domain().lstrip(".")
    with transaction.atomic():
        for tenant in Tenant.objects.filter(slug=slug, deleted_at__isnull=False):
            tenant.slug = f"{slug}-deleted-{tenant.id.hex[:8]}"[:100]
            tenant.save(update_fields=["slug", "updated_at"])
        for row in TenantDomain.objects.filter(
            domain__iexact=f"{slug}.{base}", tenant__deleted_at__isnull=False
        ):
            renamed = f"{slug}-deleted-{row.id.hex[:8]}"
            row.domain = f"{renamed}.{base}"[:255]
            row.subdomain = renamed[:100]
            row.is_active = False
            row.is_primary = False
            row.deleted_at = row.deleted_at or timezone.now()
            row.save(update_fields=["domain", "subdomain", "is_active", "is_primary", "deleted_at", "updated_at"])


def suggest_subdomains(base: str, *, limit: int = 3) -> list[str]:
    """Return available alternate slugs. Never invent a random numeric suffix."""
    root = normalize_tenant_slug(base)
    if not root:
        return []
    out: list[str] = []
    for suffix in SUGGESTION_SUFFIXES:
        candidate = f"{root}-{suffix}"[:MAX_SUBDOMAIN_LENGTH].rstrip("-")
        try:
            candidate = validate_tenant_slug(candidate)
        except (SubdomainError, ValueError):
            continue
        if is_subdomain_taken(candidate):
            continue
        out.append(candidate)
        if len(out) >= limit:
            break
    return out


def check_subdomain_availability(raw: str) -> dict[str, Any]:
    """Public availability payload — never includes tenant-private metadata."""
    requested = (raw or "").strip()
    try:
        normalized = validate_tenant_slug(requested)
    except SubdomainError as exc:
        # Cosmetic only: a boundary hyphen or an all-separator input is still invalid,
        # so trim it purely for a readable display value (validation already rejected it).
        display = normalize_tenant_slug(requested).strip("-") or None
        suggestions = suggest_subdomains(display or "") if exc.reason == "reserved" else []
        return {
            "requested": requested,
            "normalized": display,
            "available": False,
            "hostname": None,
            "reason": exc.reason,
            "suggestions": suggestions,
            # Back-compat keys used by older clients
            "slug": display,
            "normalized_value": display,
        }
    except ValueError as exc:
        display = normalize_tenant_slug(requested).strip("-") or None
        return {
            "requested": requested,
            "normalized": display,
            "available": False,
            "hostname": None,
            "reason": "invalid",
            "suggestions": [],
            "slug": display,
            "normalized_value": display,
            "message": str(exc),
        }

    if is_subdomain_taken(normalized):
        return {
            "requested": requested,
            "normalized": normalized,
            "available": False,
            "hostname": None,
            "reason": "taken",
            "suggestions": suggest_subdomains(normalized),
            "slug": normalized,
            "normalized_value": normalized,
        }

    hostname = f"{normalized}.{get_tenant_base_domain()}"
    return {
        "requested": requested,
        "normalized": normalized,
        "available": True,
        "hostname": hostname,
        "reason": None,
        "suggestions": [],
        "slug": normalized,
        "normalized_value": normalized,
    }

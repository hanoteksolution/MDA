"""Reserved subdomain / tenant slug names for SaaS host routing."""

from __future__ import annotations

from django.conf import settings
from django.utils.text import slugify

RESERVED_TENANT_SLUGS = frozenset(
    {
        "www",
        "api",
        "admin",
        "app",
        "apps",
        "support",
        "billing",
        "mail",
        "email",
        "static",
        "assets",
        "cdn",
        "media",
        "platform",
        "erp",
        "portal",
        "status",
        "health",
        "docs",
        "help",
        "null",
        "undefined",
        "test",
        "staging",
        "dev",
        "localhost",
        "safaritechno",
        "safari",
    }
)


def get_tenant_base_domain() -> str:
    return getattr(settings, "TENANT_BASE_DOMAIN", None) or "erp.safaritechno.com"


def normalize_tenant_slug(value: str) -> str:
    return (slugify(value or "") or "").strip().lower()


def is_reserved_tenant_slug(slug: str) -> bool:
    return normalize_tenant_slug(slug) in RESERVED_TENANT_SLUGS


def validate_tenant_slug(slug: str) -> str:
    normalized = normalize_tenant_slug(slug)
    if not normalized:
        raise ValueError("Subdomain / slug is required.")
    if len(normalized) < 2:
        raise ValueError("Subdomain must be at least 2 characters.")
    if is_reserved_tenant_slug(normalized):
        raise ValueError(f"Subdomain '{normalized}' is reserved.")
    return normalized


def build_tenant_hostname(slug: str, *, base_domain: str | None = None) -> str:
    base = (base_domain or get_tenant_base_domain()).lstrip(".")
    return f"{validate_tenant_slug(slug)}.{base}"

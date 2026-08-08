"""Request-scoped tenant context and queryset scoping helpers.

Do not trust client-supplied tenant IDs. Prefer host resolution, then user.tenant /
user.branch.company.tenant.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Optional

_current_tenant: ContextVar[Optional[Any]] = ContextVar("mda_current_tenant", default=None)
_tenant_enforcement: ContextVar[bool] = ContextVar("mda_tenant_enforcement", default=False)


def get_current_tenant():
    return _current_tenant.get()


def get_current_tenant_id():
    tenant = get_current_tenant()
    if tenant is None:
        return None
    return getattr(tenant, "pk", None) or getattr(tenant, "id", None)


def set_current_tenant(tenant) -> None:
    _current_tenant.set(tenant)


def clear_current_tenant() -> None:
    _current_tenant.set(None)


def is_tenant_enforcement_enabled() -> bool:
    """When True, tenant-scoped managers must filter by current tenant."""
    return _tenant_enforcement.get()


def set_tenant_enforcement(enabled: bool) -> None:
    _tenant_enforcement.set(bool(enabled))


@contextmanager
def tenant_context(tenant, *, enforce: bool = True) -> Iterator[None]:
    """Bind tenant for the duration of a block (tests, tasks, sync jobs)."""
    token_tenant = _current_tenant.set(tenant)
    token_enforce = _tenant_enforcement.set(enforce)
    try:
        yield
    finally:
        _current_tenant.reset(token_tenant)
        _tenant_enforcement.reset(token_enforce)


def _tenant_pk(tenant) -> Any:
    if tenant is None:
        return None
    return getattr(tenant, "pk", None) or getattr(tenant, "id", None) or tenant


def resolve_acting_tenant(*, request=None, user=None):
    """Resolve the tenant that should scope shop data for this actor."""
    if request is not None:
        host_tenant = getattr(request, "tenant", None)
        if host_tenant is not None:
            return host_tenant
        if user is None:
            user = getattr(request, "user", None)

    ctx = get_current_tenant()
    if ctx is not None:
        return ctx

    if user is None or not getattr(user, "is_authenticated", False):
        return None

    tenant = getattr(user, "tenant", None)
    if tenant is not None:
        return tenant

    branch = getattr(user, "branch", None)
    if branch is not None:
        company = getattr(branch, "company", None)
        if company is not None and getattr(company, "tenant_id", None):
            return company.tenant
    return None


def is_platform_unscoped_actor(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_platform_admin", False) or getattr(user, "is_superuser", False):
        return True
    try:
        from apps.platform.services.platform_service import PlatformService

        return PlatformService.is_global_platform_admin(user)
    except Exception:
        return False


def apply_tenant_scope(queryset, *, request=None, user=None, field: str = "tenant_id"):
    """Filter a queryset to the acting tenant. Fail closed for shop users without tenant."""
    tenant = resolve_acting_tenant(request=request, user=user)
    actor = user or (getattr(request, "user", None) if request is not None else None)
    if tenant is not None:
        return queryset.filter(**{field: _tenant_pk(tenant)})
    if is_platform_unscoped_actor(actor):
        return queryset
    if actor is not None and getattr(actor, "is_authenticated", False):
        return queryset.none()
    return queryset


def stamp_tenant_id(data: dict | None = None, *, request=None, user=None) -> dict:
    """Ensure create payloads include tenant_id when resolvable."""
    payload = dict(data or {})
    if payload.get("tenant_id") or payload.get("tenant"):
        return payload
    tenant = resolve_acting_tenant(request=request, user=user)
    if tenant is not None:
        payload["tenant_id"] = _tenant_pk(tenant)
    return payload


def ensure_legacy_unassigned_tenant():
    """Create/return the ops bucket for orphan rows during backfill."""
    from apps.platform.models import Tenant

    tenant, _ = Tenant.objects.get_or_create(
        slug="legacy-unassigned",
        defaults={
            "name": "Legacy Unassigned",
            "status": Tenant.STATUS_SUSPENDED,
            "is_active": False,
            "timezone": "UTC",
            "currency": "USD",
            "language": "en",
        },
    )
    return tenant

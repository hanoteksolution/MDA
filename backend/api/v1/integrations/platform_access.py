"""Platform-only access to integration infrastructure (providers, credentials, webhooks, reconciliation).

Provider rows stay tenant-scoped (unchanged architecture); only a global platform administrator may
read or change them, always for an explicitly selected tenant. Tenant users — including tenant admins
holding ``integrations.manage`` — get 403.
"""

from __future__ import annotations

import uuid

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import BasePermission

from apps.platform.models import Tenant
from apps.platform.services.platform_service import PlatformService


class IsPlatformIntegrationsAdmin(BasePermission):
    message = "Integration providers are managed by the platform administrator."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and PlatformService.is_global_platform_admin(user))


def parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def target_tenant(request) -> Tenant:
    """The tenant being managed, from ``tenant_id`` (query string, or body on writes)."""
    raw = request.query_params.get("tenant_id")
    if not raw and hasattr(request.data, "get"):
        raw = request.data.get("tenant_id")
    if not raw:
        raise ValidationError({"tenant_id": "Select the tenant whose integrations you are managing."})
    pk = parse_uuid(raw)
    tenant = Tenant.objects.filter(pk=pk, deleted_at__isnull=True).first() if pk else None
    if tenant is None or not PlatformService.user_can_access_tenant(request.user, tenant):
        raise NotFound("Tenant not found.")
    return tenant


def tenant_branch(tenant, branch_id):
    """A branch of the managed tenant, or None when the id is foreign/invalid."""
    from apps.settings_app.models import Branch

    pk = parse_uuid(branch_id)
    return Branch.objects.filter(pk=pk, tenant=tenant, deleted_at__isnull=True).first() if pk else None

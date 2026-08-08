"""Explicit AuditLog writes for mutations (no signals)."""

from __future__ import annotations

from apps.audit.repositories.audit_repository import AuditRepository


def write_audit(
    *,
    action: str,
    module: str,
    entity=None,
    entity_type: str = "",
    entity_id=None,
    user=None,
    request=None,
    old_values=None,
    new_values=None,
):
    tenant = None
    if entity is not None:
        tenant = getattr(entity, "tenant", None)
        entity_type = entity_type or entity.__class__.__name__
        if entity_id is None:
            entity_id = getattr(entity, "pk", None)
    return AuditRepository.create(
        user=user,
        action=action,
        module=module,
        entity_type=entity_type or "",
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        request=request,
        tenant=tenant,
    )

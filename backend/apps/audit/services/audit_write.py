"""Explicit AuditLog writes for mutations (no signals)."""

from __future__ import annotations

from apps.audit.repositories.audit_repository import AuditRepository


def _derive_branch_id(entity):
    """Best-effort branch for the row being mutated — derived, never guessed.

    Only relations that unambiguously identify a branch are followed:
    the entity's own ``branch``, or its warehouse's branch. An entity with no such
    relation records no branch rather than an inferred one.
    """
    if entity is None:
        return None
    branch_id = getattr(entity, "branch_id", None)
    if branch_id:
        return branch_id
    warehouse = getattr(entity, "warehouse", None)
    if warehouse is not None:
        return getattr(warehouse, "branch_id", None)
    return None


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
    branch=None,
):
    tenant = None
    if entity is not None:
        tenant = getattr(entity, "tenant", None)
        entity_type = entity_type or entity.__class__.__name__
        if entity_id is None:
            entity_id = getattr(entity, "pk", None)
    if branch is None:
        branch = _derive_branch_id(entity)
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
        branch=branch,
    )

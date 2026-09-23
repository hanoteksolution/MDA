"""Warehouse locations, cash registers and POS terminals.

The branch/warehouse relationship is validated here rather than inferred later:
a Warehouse belongs to exactly one Branch, and Warehouse, Branch and the row being
created must all share a tenant. Cross-tenant references are rejected outright.
"""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services.audit_write import write_audit
from apps.organization.models import CashRegister, OrgStatus, PosTerminal, StockLocation
from core.branching import assert_same_tenant, has_branch_permission
from core.tenancy import resolve_acting_tenant

MODULE = "organization"

#: Locations every warehouse gets so a movement always has somewhere to point.
DEFAULT_LOCATIONS = [
    {
        "code": "MAIN",
        "name": "Main Storage",
        "location_type": StockLocation.TYPE_STORAGE,
        "is_sellable": True,
        "is_default": True,
        "sort_order": 0,
    },
    {
        "code": "FLOOR",
        "name": "Shop Floor",
        "location_type": StockLocation.TYPE_SHOP_FLOOR,
        "is_sellable": True,
        "is_default": False,
        "sort_order": 1,
    },
    {
        "code": "RECV",
        "name": "Receiving",
        "location_type": StockLocation.TYPE_RECEIVING,
        "is_sellable": False,
        "is_default": False,
        "sort_order": 2,
    },
    {
        "code": "DAMAGED",
        "name": "Damaged Goods",
        "location_type": StockLocation.TYPE_DAMAGED,
        "is_sellable": False,
        "is_default": False,
        "sort_order": 3,
    },
]


def validate_warehouse_branch(warehouse, *, branch=None):
    """The warehouse rule: unambiguous branch ownership, no cross-tenant links."""
    branch = branch or getattr(warehouse, "branch", None)
    if branch is None:
        raise ValidationError({"branch": "Warehouse must belong to a branch."})
    assert_same_tenant(warehouse, branch, label="warehouse/branch")
    return True


class StockLocationService:
    @staticmethod
    def list_locations(*, warehouse=None, branch_ids=None, user=None, request=None, include_inactive=False):
        qs = StockLocation.active_objects().select_related("warehouse", "warehouse__branch")
        tenant = resolve_acting_tenant(request=request, user=user)
        if tenant is not None:
            qs = qs.filter(tenant_id=tenant.pk)
        if warehouse is not None:
            qs = qs.filter(warehouse=warehouse)
        if branch_ids is not None:
            qs = qs.filter(warehouse__branch_id__in=list(branch_ids))
        if not include_inactive:
            qs = qs.filter(status=OrgStatus.ACTIVE)
        return qs

    @staticmethod
    @transaction.atomic
    def create_location(*, warehouse, data, actor=None, request=None):
        validate_warehouse_branch(warehouse)
        if actor is not None and not has_branch_permission(actor, "inventory.adjust", warehouse.branch):
            raise PermissionDenied("You cannot manage locations in this branch.")

        parent = data.get("parent")
        if parent is not None and parent.warehouse_id != warehouse.pk:
            raise ValidationError({"parent": "Parent location must belong to the same warehouse."})

        make_default = data.pop("is_default", False)
        location = StockLocation.objects.create(
            warehouse=warehouse,
            tenant_id=warehouse.tenant_id,
            created_by=actor,
            **data,
        )
        if make_default:
            StockLocationService.set_default(location=location, actor=actor, request=request)
        write_audit(
            action="create",
            module=MODULE,
            entity=location,
            user=actor,
            request=request,
            new_values={
                "warehouse": str(warehouse.pk),
                "branch": str(warehouse.branch_id),
                "code": location.code,
                "location_type": location.location_type,
            },
        )
        return location

    @staticmethod
    @transaction.atomic
    def update_location(*, location, data, actor=None, request=None):
        if actor is not None and not has_branch_permission(
            actor, "inventory.adjust", location.warehouse.branch
        ):
            raise PermissionDenied("You cannot manage locations in this branch.")
        old = {"name": location.name, "status": location.status, "is_sellable": location.is_sellable}
        make_default = data.pop("is_default", None)
        for key, value in data.items():
            setattr(location, key, value)
        location.updated_by = actor
        location.full_clean(exclude=["tenant", "created_by", "updated_by", "deleted_by"])
        location.save()
        if make_default:
            StockLocationService.set_default(location=location, actor=actor, request=request)
        write_audit(
            action="update",
            module=MODULE,
            entity=location,
            user=actor,
            request=request,
            old_values=old,
            new_values={"name": location.name, "status": location.status, "is_sellable": location.is_sellable},
        )
        return location

    @staticmethod
    @transaction.atomic
    def set_default(*, location, actor=None, request=None):
        StockLocation.objects.filter(
            warehouse_id=location.warehouse_id, deleted_at__isnull=True
        ).exclude(pk=location.pk).update(is_default=False)
        if not location.is_default:
            location.is_default = True
            location.updated_by = actor
            location.save(update_fields=["is_default", "updated_by", "updated_at"])
        return location

    @staticmethod
    @transaction.atomic
    def delete_location(*, location, actor=None, request=None):
        if actor is not None and not has_branch_permission(
            actor, "inventory.adjust", location.warehouse.branch
        ):
            raise PermissionDenied("You cannot manage locations in this branch.")
        if location.is_default:
            raise ValidationError({"detail": "Cannot delete the warehouse's default location."})
        if location.children.filter(deleted_at__isnull=True).exists():
            raise ValidationError({"detail": "Cannot delete a location that has child locations."})
        write_audit(
            action="delete",
            module=MODULE,
            entity=location,
            user=actor,
            request=request,
            old_values={"code": location.code, "warehouse": str(location.warehouse_id)},
        )
        location.soft_delete(user=actor)
        return location

    @staticmethod
    @transaction.atomic
    def ensure_default_locations(*, warehouse, actor=None):
        """Idempotently create the standard locations for a warehouse.

        Returns the default location. Safe to call repeatedly (bootstrap, migration,
        and whenever a warehouse is created).
        """
        validate_warehouse_branch(warehouse)
        default_location = None
        for spec in DEFAULT_LOCATIONS:
            location = StockLocation.objects.filter(
                warehouse=warehouse, code=spec["code"], deleted_at__isnull=True
            ).first()
            if location is None:
                location = StockLocation.objects.create(
                    warehouse=warehouse,
                    tenant_id=warehouse.tenant_id,
                    created_by=actor,
                    **spec,
                )
            if spec["is_default"]:
                default_location = location
        existing_default = StockLocation.objects.filter(
            warehouse=warehouse, is_default=True, deleted_at__isnull=True
        ).first()
        if existing_default is None and default_location is not None:
            default_location.is_default = True
            default_location.save(update_fields=["is_default", "updated_at"])
            existing_default = default_location
        return existing_default or default_location


class CashRegisterService:
    @staticmethod
    def list_registers(*, branch_ids=None, user=None, request=None):
        qs = CashRegister.active_objects().select_related("branch")
        tenant = resolve_acting_tenant(request=request, user=user)
        if tenant is not None:
            qs = qs.filter(tenant_id=tenant.pk)
        if branch_ids is not None:
            qs = qs.filter(branch_id__in=list(branch_ids))
        return qs

    @staticmethod
    def _validate_cash_account(branch, data):
        """A register's GL account must belong to the same tenant as its branch."""
        account_id = data.get("cash_account_id") or getattr(data.get("cash_account"), "pk", None)
        if not account_id:
            return
        from apps.finance.models import Account

        account = Account.objects.filter(pk=account_id).first()
        if account is None:
            raise ValidationError({"cash_account_id": "Account not found."})
        if account.tenant_id and branch.tenant_id and str(account.tenant_id) != str(branch.tenant_id):
            raise ValidationError({"cash_account_id": "Account belongs to another tenant."})

    @staticmethod
    @transaction.atomic
    def create_register(*, branch, data, actor=None, request=None):
        if actor is not None and not has_branch_permission(actor, "pos.access", branch):
            raise PermissionDenied("You cannot manage cash registers in this branch.")
        CashRegisterService._validate_cash_account(branch, data)
        register = CashRegister.objects.create(
            branch=branch, tenant_id=branch.tenant_id, created_by=actor, **data
        )
        write_audit(
            action="create",
            module=MODULE,
            entity=register,
            user=actor,
            request=request,
            new_values={"branch": str(branch.pk), "code": register.code, "name": register.name},
        )
        return register

    @staticmethod
    @transaction.atomic
    def update_register(*, register, data, actor=None, request=None):
        if actor is not None and not has_branch_permission(actor, "pos.access", register.branch):
            raise PermissionDenied("You cannot manage cash registers in this branch.")
        CashRegisterService._validate_cash_account(register.branch, data)
        old = {"name": register.name, "status": register.status}
        for key, value in data.items():
            setattr(register, key, value)
        register.updated_by = actor
        register.save()
        write_audit(
            action="update",
            module=MODULE,
            entity=register,
            user=actor,
            request=request,
            old_values=old,
            new_values={"name": register.name, "status": register.status},
        )
        return register


class PosTerminalService:
    @staticmethod
    def list_terminals(*, branch_ids=None, user=None, request=None):
        qs = PosTerminal.active_objects().select_related(
            "branch", "default_warehouse", "default_location", "default_cash_register"
        )
        tenant = resolve_acting_tenant(request=request, user=user)
        if tenant is not None:
            qs = qs.filter(tenant_id=tenant.pk)
        if branch_ids is not None:
            qs = qs.filter(branch_id__in=list(branch_ids))
        return qs

    @staticmethod
    @transaction.atomic
    def create_terminal(*, branch, data, actor=None, request=None):
        if actor is not None and not has_branch_permission(actor, "pos.access", branch):
            raise PermissionDenied("You cannot manage terminals in this branch.")
        terminal = PosTerminal(branch=branch, tenant_id=branch.tenant_id, created_by=actor, **data)
        terminal.full_clean(exclude=["tenant", "created_by", "updated_by", "deleted_by"])
        terminal.save()
        write_audit(
            action="create",
            module=MODULE,
            entity=terminal,
            user=actor,
            request=request,
            new_values={"branch": str(branch.pk), "code": terminal.code, "name": terminal.name},
        )
        return terminal

    @staticmethod
    @transaction.atomic
    def update_terminal(*, terminal, data, actor=None, request=None):
        if actor is not None and not has_branch_permission(actor, "pos.access", terminal.branch):
            raise PermissionDenied("You cannot manage terminals in this branch.")
        old = {"name": terminal.name, "status": terminal.status}
        for key, value in data.items():
            setattr(terminal, key, value)
        terminal.updated_by = actor
        terminal.full_clean(exclude=["tenant", "created_by", "updated_by", "deleted_by"])
        terminal.save()
        write_audit(
            action="update",
            module=MODULE,
            entity=terminal,
            user=actor,
            request=request,
            old_values=old,
            new_values={"name": terminal.name, "status": terminal.status},
        )
        return terminal

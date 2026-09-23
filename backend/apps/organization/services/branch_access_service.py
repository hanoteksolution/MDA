"""Branch membership and access-profile management.

Every mutation here is audited and validated for tenant consistency. Granting branch
access can never grant a permission the target user does not already hold globally —
a profile intersects, it does not add (see ``core.branching.branch_permissions``).
"""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services.audit_write import write_audit
from apps.organization.models import BranchAccessProfile, UserBranchAccess
from core.branching import accessible_branches, has_branch_permission
from core.tenancy import resolve_acting_tenant

MODULE = "organization"

#: Seeded profiles. Codenames are intersected with the user's own permissions, so a
#: profile listing a codename the user lacks simply has no effect.
SYSTEM_PROFILES = [
    {
        "code": "BRANCH_MANAGER",
        "name": "Branch Manager",
        "is_manager": True,
        "grants_all_permissions": True,
        "permissions": None,
    },
    {
        "code": "BRANCH_STAFF",
        "name": "Branch Staff",
        "is_manager": False,
        "grants_all_permissions": False,
        "permissions": [
            "dashboard.view",
            "pos.access",
            "products.view",
            "inventory.view",
            "sales.view",
            "sales.create",
            "customers.view",
            "customers.create",
        ],
    },
    {
        "code": "BRANCH_VIEWER",
        "name": "Branch Viewer",
        "is_manager": False,
        "grants_all_permissions": False,
        "permissions": [
            "dashboard.view",
            "products.view",
            "inventory.view",
            "sales.view",
            "reports.view",
        ],
    },
]


def _resolve_tenant(*, user=None, request=None, branch=None):
    tenant = resolve_acting_tenant(request=request, user=user)
    if tenant is not None:
        return tenant
    return getattr(branch, "tenant", None)


class BranchAccessProfileService:
    @staticmethod
    def list_profiles(*, user=None, request=None):
        qs = BranchAccessProfile.active_objects().prefetch_related("permissions")
        tenant = resolve_acting_tenant(request=request, user=user)
        if tenant is not None:
            qs = qs.filter(tenant_id=tenant.pk)
        return qs.order_by("name")

    @staticmethod
    @transaction.atomic
    def create_profile(*, data, actor=None, request=None):
        from apps.authentication.models import Permission

        codenames = data.pop("permission_codenames", None) or []
        tenant = resolve_acting_tenant(request=request, user=actor)
        profile = BranchAccessProfile.objects.create(
            tenant_id=getattr(tenant, "pk", None),
            created_by=actor,
            **data,
        )
        if codenames:
            profile.permissions.set(Permission.objects.filter(codename__in=codenames))
        write_audit(
            action="create",
            module=MODULE,
            entity=profile,
            user=actor,
            request=request,
            new_values={"code": profile.code, "name": profile.name, "permissions": sorted(codenames)},
        )
        return profile

    @staticmethod
    @transaction.atomic
    def update_profile(*, profile, data, actor=None, request=None):
        from apps.authentication.models import Permission

        old = {
            "name": profile.name,
            "is_manager": profile.is_manager,
            "permissions": sorted(profile.permission_codenames()),
        }
        codenames = data.pop("permission_codenames", None)
        for key, value in data.items():
            setattr(profile, key, value)
        profile.updated_by = actor
        profile.save()
        if codenames is not None:
            profile.permissions.set(Permission.objects.filter(codename__in=codenames))
        write_audit(
            action="update",
            module=MODULE,
            entity=profile,
            user=actor,
            request=request,
            old_values=old,
            new_values={
                "name": profile.name,
                "is_manager": profile.is_manager,
                "permissions": sorted(profile.permission_codenames()),
            },
        )
        return profile

    @staticmethod
    @transaction.atomic
    def delete_profile(*, profile, actor=None, request=None):
        if profile.is_system:
            raise ValidationError({"detail": "System profiles cannot be deleted."})
        in_use = UserBranchAccess.objects.filter(
            access_profile=profile, deleted_at__isnull=True
        ).count()
        if in_use:
            raise ValidationError(
                {"detail": f"Profile is assigned to {in_use} branch access record(s)."}
            )
        write_audit(
            action="delete",
            module=MODULE,
            entity=profile,
            user=actor,
            request=request,
            old_values={"code": profile.code, "name": profile.name},
        )
        profile.soft_delete(user=actor)
        return profile

    @staticmethod
    def ensure_system_profiles(*, tenant):
        """Idempotently seed the built-in profiles for a tenant."""
        from apps.authentication.models import Permission

        created = []
        for spec in SYSTEM_PROFILES:
            profile = BranchAccessProfile.objects.filter(
                tenant_id=getattr(tenant, "pk", tenant), code=spec["code"], deleted_at__isnull=True
            ).first()
            if profile is None:
                profile = BranchAccessProfile.objects.create(
                    tenant_id=getattr(tenant, "pk", tenant),
                    code=spec["code"],
                    name=spec["name"],
                    is_manager=spec["is_manager"],
                    grants_all_permissions=spec["grants_all_permissions"],
                    is_system=True,
                )
                created.append(profile)
            if spec["permissions"] is not None:
                profile.permissions.set(
                    Permission.objects.filter(codename__in=spec["permissions"])
                )
        return created


class BranchAccessService:
    @staticmethod
    def list_access(*, actor=None, request=None, branch=None, target_user=None):
        qs = UserBranchAccess.objects.filter(deleted_at__isnull=True).select_related(
            "user", "branch", "access_profile"
        )
        tenant = resolve_acting_tenant(request=request, user=actor)
        if tenant is not None:
            qs = qs.filter(branch__tenant_id=tenant.pk)
        if branch is not None:
            qs = qs.filter(branch=branch)
        if target_user is not None:
            qs = qs.filter(user=target_user)
        if actor is not None and not getattr(actor, "is_superuser", False):
            visible = accessible_branches(actor, request=request).values_list("pk", flat=True)
            qs = qs.filter(branch_id__in=list(visible))
        return qs.order_by("user__username", "branch__name")

    @staticmethod
    def _validate(*, target_user, branch, actor, request):
        if branch is None or target_user is None:
            raise ValidationError({"detail": "User and branch are required."})

        branch_tenant = getattr(branch, "tenant_id", None)
        user_tenant = getattr(target_user, "tenant_id", None)
        if branch_tenant and user_tenant and str(branch_tenant) != str(user_tenant):
            raise ValidationError(
                {"branch": "Cannot grant access to a branch in another tenant."}
            )
        if actor is not None and not has_branch_permission(actor, "users.update", branch):
            raise PermissionDenied("You cannot manage access for this branch.")

    @staticmethod
    @transaction.atomic
    def grant(
        *,
        target_user,
        branch,
        access_profile=None,
        is_default=False,
        starts_on=None,
        ends_on=None,
        notes="",
        actor=None,
        request=None,
    ):
        BranchAccessService._validate(
            target_user=target_user, branch=branch, actor=actor, request=request
        )
        if ends_on and starts_on and ends_on < starts_on:
            raise ValidationError({"ends_on": "End date cannot precede the start date."})

        access, created = UserBranchAccess.objects.get_or_create(
            user=target_user,
            branch=branch,
            deleted_at__isnull=True,
            defaults={
                "tenant_id": getattr(branch, "tenant_id", None),
                "access_profile": access_profile,
                "is_default": is_default,
                "starts_on": starts_on,
                "ends_on": ends_on,
                "notes": notes,
                "created_by": actor,
            },
        )
        if not created:
            access.access_profile = access_profile
            access.status = UserBranchAccess.STATUS_ACTIVE
            access.starts_on = starts_on
            access.ends_on = ends_on
            access.notes = notes
            access.updated_by = actor
            access.save()
        if is_default:
            BranchAccessService.set_default(access=access, actor=actor, request=request)

        write_audit(
            action="create" if created else "update",
            module=MODULE,
            entity=access,
            user=actor,
            request=request,
            new_values={
                "user": str(target_user.pk),
                "branch": str(branch.pk),
                "branch_name": branch.name,
                "profile": getattr(access_profile, "code", None),
                "starts_on": str(starts_on) if starts_on else None,
                "ends_on": str(ends_on) if ends_on else None,
            },
        )
        return access

    @staticmethod
    @transaction.atomic
    def update(*, access, data, actor=None, request=None):
        BranchAccessService._validate(
            target_user=access.user, branch=access.branch, actor=actor, request=request
        )
        old = {
            "profile": getattr(access.access_profile, "code", None),
            "status": access.status,
            "starts_on": str(access.starts_on) if access.starts_on else None,
            "ends_on": str(access.ends_on) if access.ends_on else None,
        }
        make_default = data.pop("is_default", None)
        for key, value in data.items():
            setattr(access, key, value)
        if access.ends_on and access.starts_on and access.ends_on < access.starts_on:
            raise ValidationError({"ends_on": "End date cannot precede the start date."})
        access.updated_by = actor
        access.save()
        if make_default:
            BranchAccessService.set_default(access=access, actor=actor, request=request)
        write_audit(
            action="update",
            module=MODULE,
            entity=access,
            user=actor,
            request=request,
            old_values=old,
            new_values={
                "profile": getattr(access.access_profile, "code", None),
                "status": access.status,
                "starts_on": str(access.starts_on) if access.starts_on else None,
                "ends_on": str(access.ends_on) if access.ends_on else None,
            },
        )
        return access

    @staticmethod
    @transaction.atomic
    def set_default(*, access, actor=None, request=None):
        """Make this the user's default branch, leaving exactly one default.

        Every one of the user's access rows is locked in a **deterministic order**
        first. Without that, two concurrent "make this my default" requests lock their
        own row and then reach for each other's, which deadlocks on PostgreSQL.
        Ordering by primary key makes them serialise instead.
        """
        list(
            UserBranchAccess.objects.select_for_update()
            .filter(user_id=access.user_id, deleted_at__isnull=True)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        UserBranchAccess.objects.filter(
            user_id=access.user_id, deleted_at__isnull=True
        ).exclude(pk=access.pk).update(is_default=False)
        if not access.is_default:
            access.is_default = True
            access.updated_by = actor
            access.save(update_fields=["is_default", "updated_by", "updated_at"])
        return access

    @staticmethod
    @transaction.atomic
    def revoke(*, access, actor=None, request=None):
        BranchAccessService._validate(
            target_user=access.user, branch=access.branch, actor=actor, request=request
        )
        write_audit(
            action="delete",
            module=MODULE,
            entity=access,
            user=actor,
            request=request,
            old_values={
                "user": str(access.user_id),
                "branch": str(access.branch_id),
                "profile": getattr(access.access_profile, "code", None),
            },
        )
        access.soft_delete(user=actor)
        return access

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.repositories.audit_repository import AuditRepository
from apps.authentication.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserPermission,
    UserPermissionRevoke,
)


class AuthService:
    @staticmethod
    def login(*, username, password, request=None):
        user = authenticate(username=username, password=password)
        if not user:
            user = User.objects.filter(
                username__iexact=username.strip(),
                deleted_at__isnull=True,
                is_active=True,
            ).first()
            if user and user.check_password(password):
                pass
            else:
                user = None
        if not user or not user.is_active or user.is_deleted:
            return None, "Invalid credentials."

        refresh = RefreshToken.for_user(user)
        AuditRepository.create(
            user=user, action="login", module="auth", request=request
        )
        return user, {"access": str(refresh.access_token), "refresh": str(refresh)}

    @staticmethod
    def logout(*, user, refresh_token, request=None):
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        AuditRepository.create(
            user=user, action="logout", module="auth", request=request
        )


class UserService:
    # Roles multi-shop managers must never see or assign.
    PLATFORM_ELEVATED_ROLE_SLUGS = (
        "super_admin",
        "platform_admin",
        "shop_group_manager",
    )

    @staticmethod
    def is_scoped_manager(viewer) -> bool:
        """Multi-shop manager limited to own shops — not a global platform owner."""
        if not viewer or not getattr(viewer, "managed_shop_group_id", None):
            return False
        from apps.platform.services.platform_service import PlatformService

        return not PlatformService.is_global_platform_admin(viewer)

    @staticmethod
    def list_users(*, include_deleted=False, viewer=None, tenant_id=None):
        from django.db.models import Q

        from apps.platform.services.platform_service import PlatformService

        qs = User.objects.select_related(
            "role", "branch", "tenant", "created_by", "managed_shop_group"
        ).prefetch_related(
            "direct_permissions__permission",
            "revoked_permissions__permission",
            "role__role_permissions__permission",
        )
        if not include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        if viewer is not None and UserService.is_scoped_manager(viewer):
            qs = UserService._scope_users_for_manager(qs, viewer)
        elif viewer is not None and not PlatformService.is_global_platform_admin(viewer):
            # Shop staff: only users in their own tenant (unless they manage a group).
            if not viewer.managed_shop_group_id and not viewer.has_permission("platform.manage"):
                own = PlatformService.resolve_user_tenant(viewer)
                if own is not None:
                    qs = qs.filter(
                        Q(tenant_id=own.id) | Q(branch__company__tenant_id=own.id)
                    ).distinct()
        if tenant_id:
            qs = qs.filter(
                Q(tenant_id=tenant_id) | Q(branch__company__tenant_id=tenant_id)
            ).distinct()
        return qs

    @staticmethod
    def _resolve_tenant_for_write(*, actor=None, tenant_id=None):
        """Resolve which shop a user should belong to when creating/updating."""
        from apps.platform.models import Tenant
        from apps.platform.services.platform_service import PlatformService

        if tenant_id:
            tenant = Tenant.objects.filter(pk=tenant_id, deleted_at__isnull=True).first()
            if tenant is None:
                raise ValueError("Shop not found.")
            if actor is None:
                return tenant
            if PlatformService.is_global_platform_admin(actor):
                return tenant
            if actor.has_permission("platform.manage") and not UserService.is_scoped_manager(actor):
                return tenant
            accessible = PlatformService.accessible_tenant_ids(actor)
            if tenant.id in accessible:
                return tenant
            raise ValueError("You cannot assign users to that shop.")

        return PlatformService.resolve_user_tenant(actor)

    @staticmethod
    def _scope_users_for_manager(qs, viewer):
        """Only: self, users they created, and users belonging to shops in their group."""
        from django.db.models import Q

        from apps.platform.services.platform_service import PlatformService

        tenant_ids = PlatformService.accessible_tenant_ids(viewer)
        scope = Q(pk=viewer.pk) | Q(created_by_id=viewer.pk)
        if tenant_ids:
            scope |= Q(tenant_id__in=tenant_ids) | Q(
                branch__company__tenant_id__in=tenant_ids
            )

        qs = qs.filter(scope).distinct()
        # Never expose platform owners / other group managers (except self).
        elevated = Q(is_platform_admin=True) | Q(is_superuser=True) | Q(
            role__slug__in=UserService.PLATFORM_ELEVATED_ROLE_SLUGS
        )
        return qs.exclude(~Q(pk=viewer.pk) & elevated)

    @staticmethod
    def get_manageable_user(*, pk, viewer):
        try:
            return UserService.list_users(viewer=viewer).get(pk=pk)
        except User.DoesNotExist as exc:
            raise ValueError("User not found.") from exc

    @staticmethod
    def _assert_manager_may_assign_role(*, viewer, role_id):
        if not UserService.is_scoped_manager(viewer) or not role_id:
            return
        role = Role.objects.filter(pk=role_id, deleted_at__isnull=True).first()
        if not role:
            raise ValueError("Role not found.")
        if role.slug in UserService.PLATFORM_ELEVATED_ROLE_SLUGS:
            raise ValueError("You cannot assign that role.")

    @staticmethod
    def _set_direct_permissions(user, permission_ids, granted_by=None):
        UserPermission.objects.filter(user=user).delete()
        if not permission_ids:
            return
        permissions = list(
            Permission.objects.filter(id__in=permission_ids, deleted_at__isnull=True)
        )
        # Multi-shop managers may only grant permissions they themselves hold.
        if granted_by is not None and UserService.is_scoped_manager(granted_by):
            allowed = set(granted_by.get_permissions())
            permissions = [p for p in permissions if p.codename in allowed]
        # Never grant industry/module perms outside the target user's shop entitlements.
        tenant = getattr(user, "tenant", None)
        if tenant is None and user.tenant_id:
            from apps.platform.models import Tenant

            tenant = Tenant.objects.filter(pk=user.tenant_id).first()
        if tenant is not None:
            allowed_modules = UserService._permission_modules_for_tenant(tenant)
            permissions = [p for p in permissions if p.module in allowed_modules]
        UserPermission.objects.bulk_create(
            [
                UserPermission(user=user, permission=p, created_by=granted_by)
                for p in permissions
            ]
        )

    @staticmethod
    def _set_revoked_permissions(user, revoke_ids, revoked_by=None):
        """Store role-permission revokes for this user."""
        UserPermissionRevoke.objects.filter(user=user).delete()
        if not revoke_ids:
            return
        permissions = list(
            Permission.objects.filter(id__in=revoke_ids, deleted_at__isnull=True)
        )
        if revoked_by is not None and UserService.is_scoped_manager(revoked_by):
            # Can only revoke permissions the actor themselves holds (or held via role).
            allowed = set(revoked_by.get_permissions()) | set(
                revoked_by.get_role_permissions()
            )
            permissions = [p for p in permissions if p.codename in allowed]
        # Only revoke permissions that exist on the user's role (others are no-ops).
        role_codes = set(user.get_role_permissions())
        permissions = [p for p in permissions if p.codename in role_codes]
        UserPermissionRevoke.objects.bulk_create(
            [
                UserPermissionRevoke(user=user, permission=p, created_by=revoked_by)
                for p in permissions
            ]
        )

    @staticmethod
    def apply_effective_permission_selection(
        *, user, selected_ids, granted_by=None, assignable_qs=None
    ):
        """Split an effective checkbox selection into direct grants + role revokes.

        ``selected_ids`` is the set of permission UUIDs the editor wants the user
        to have. Role permissions not in that set become revokes; selected
        permissions not on the role become direct grants.
        """
        selected = {str(x) for x in (selected_ids or [])}
        role_ids = {
            str(rp.permission_id)
            for rp in user.role.role_permissions.filter(deleted_at__isnull=True)
        } if user.role_id else set()

        if assignable_qs is not None:
            assignable_ids = {str(p.id) for p in assignable_qs}
            selected &= assignable_ids
            # Only compute new revokes for role perms the editor can see. Keep
            # existing revokes outside that set so a partial catalog cannot wipe
            # (or silently restore) Administration / Users access.
            existing_revokes = {
                str(up.permission_id)
                for up in user.revoked_permissions.filter(deleted_at__isnull=True)
            }
            untouchable_revokes = existing_revokes - assignable_ids
            role_ids_assignable = role_ids & assignable_ids
            direct_ids = list(selected - role_ids)
            revoke_ids = list((role_ids_assignable - selected) | untouchable_revokes)
        else:
            direct_ids = list(selected - role_ids)
            revoke_ids = list(role_ids - selected)
        UserService._set_direct_permissions(user, direct_ids, granted_by)
        UserService._set_revoked_permissions(user, revoke_ids, granted_by)

    @staticmethod
    def list_assignable_permissions(*, viewer=None, tenant_id=None):
        """Permission catalog for Admin UI.

        - Scoped managers only see permissions they themselves hold.
        - Shop/tenant actors (and when ``tenant_id`` is provided) only see
          permission modules relevant to that shop's enabled modules.
        - Platform owners without a tenant filter see the full catalog.
        """
        from apps.platform.services.platform_service import PlatformService

        qs = Permission.active_objects().all()
        if viewer is not None and UserService.is_scoped_manager(viewer):
            # Include role baseline so managers can re-grant permissions they
            # revoked from themselves or from shop users.
            allowed = set(viewer.get_permissions()) | set(viewer.get_role_permissions())
            qs = qs.filter(codename__in=allowed)

        filter_tenant = None
        if tenant_id:
            filter_tenant = UserService._resolve_tenant_for_write(
                actor=viewer, tenant_id=tenant_id
            )
        elif viewer is not None and not PlatformService.is_global_platform_admin(viewer):
            # Shop admins / staff: scope to their own shop modules.
            # Multi-shop managers without an explicit tenant still see their grantable set.
            if not viewer.managed_shop_group_id and not viewer.has_permission("platform.manage"):
                filter_tenant = PlatformService.resolve_user_tenant(viewer)

        if filter_tenant is not None:
            allowed_modules = UserService._permission_modules_for_tenant(filter_tenant)
            qs = qs.filter(module__in=allowed_modules)

        return qs.order_by("module", "codename")

    @staticmethod
    def _permission_modules_for_tenant(tenant) -> set[str]:
        """Map tenant-enabled modules → Permission.module keys shown in the matrix."""
        from apps.platform.services.module_service import usable_module_codes

        enabled = usable_module_codes(tenant=tenant)
        # Always available for any shop (admin / ops surface).
        modules = {
            "dashboard",
            "users",
            "roles",
            "branches",
            "settings",
            "audit",
            "staff",
            "trash",
            "reports",
            "finance",
        }
        # Permission.module → required tenant module code(s). Any match includes it.
        gated = {
            "pos": {"pos"},
            "inventory": {"inventory"},
            "products": {"inventory"},
            "sales": {"sales"},
            "customers": {"sales"},
            "purchases": {"purchases"},
            "suppliers": {"purchases"},
            "gym": {"gym"},
            "restaurant": {"restaurant"},
            "hotel": {"hotel"},
            "pharmacy": {"pharmacy"},
            "futsal": {"futsal"},
            "school": {"school"},
            "property_management": {"property_management"},
            "housing_rental": {"housing_rental"},
            "office_rental": {"office_rental"},
            "projects": {"project_management"},
            "project_management": {"project_management"},
            "travel": {"travel_agency"},
            "travel_agency": {"travel_agency"},
        }
        for perm_module, required in gated.items():
            if enabled & required:
                modules.add(perm_module)
        # Never expose platform catalog to shop-scoped matrices.
        modules.discard("platform")
        return modules

    @staticmethod
    @transaction.atomic
    def create_user(*, data, created_by=None):
        from apps.platform.services.entitlement_service import EntitlementError, EntitlementService
        from apps.platform.services.platform_service import PlatformService

        data = dict(data)
        tenant_id = data.pop("tenant_id", None)
        # Ignore raw tenant FK from serializers; resolve explicitly.
        data.pop("tenant", None)
        tenant = UserService._resolve_tenant_for_write(actor=created_by, tenant_id=tenant_id)
        try:
            EntitlementService.assert_can_add_user(tenant=tenant, user=created_by)
        except EntitlementError as exc:
            raise ValueError(str(exc)) from exc

        password = data.pop("password")
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        permission_ids = data.pop("permission_ids", None)
        UserService._assert_manager_may_assign_role(viewer=created_by, role_id=role_id)
        user = User.objects.create_user(**data, password=password)
        if role_id:
            user.role_id = role_id
        if branch_id:
            user.branch_id = branch_id
        elif tenant is not None:
            default_branch = PlatformService.default_branch_for_tenant(tenant)
            if default_branch is not None:
                user.branch = default_branch
        if tenant is not None:
            user.tenant = tenant
        if created_by is not None:
            user.created_by = created_by
        user.save()
        if user.apply_elevated_flags():
            user.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])
        if permission_ids is not None and not user.is_elevated_admin:
            assignable = UserService.list_assignable_permissions(
                viewer=created_by,
                tenant_id=str(user.tenant_id) if user.tenant_id else None,
            )
            UserService.apply_effective_permission_selection(
                user=user,
                selected_ids=permission_ids,
                granted_by=created_by,
                assignable_qs=assignable,
            )
        return user

    @staticmethod
    @transaction.atomic
    def update_user(*, user, data, updated_by=None):
        from apps.platform.services.platform_service import PlatformService

        data = dict(data)
        password = data.pop("password", None)
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        permission_ids = data.pop("permission_ids", None)
        tenant_id = data.pop("tenant_id", None) if "tenant_id" in data else None
        data.pop("tenant", None)
        if role_id is not None:
            UserService._assert_manager_may_assign_role(viewer=updated_by, role_id=role_id)
        for key, value in data.items():
            setattr(user, key, value)
        if role_id is not None:
            user.role_id = role_id
        if branch_id is not None:
            user.branch_id = branch_id
        if tenant_id is not None:
            # Only platform / group managers may move users across shops.
            can_move = updated_by is not None and (
                PlatformService.is_global_platform_admin(updated_by)
                or updated_by.has_permission("platform.manage")
                or UserService.is_scoped_manager(updated_by)
            )
            if not can_move:
                raise ValueError("You cannot change this user's shop.")
            tenant = UserService._resolve_tenant_for_write(actor=updated_by, tenant_id=tenant_id)
            user.tenant = tenant
            if branch_id is None and tenant is not None:
                default_branch = PlatformService.default_branch_for_tenant(tenant)
                if default_branch is not None:
                    user.branch = default_branch
        if password:
            user.set_password(password)
        user.save()
        if user.apply_elevated_flags():
            user.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])
        if permission_ids is not None and not user.is_elevated_admin:
            assignable = UserService.list_assignable_permissions(
                viewer=updated_by,
                tenant_id=str(user.tenant_id) if user.tenant_id else None,
            )
            UserService.apply_effective_permission_selection(
                user=user,
                selected_ids=permission_ids,
                granted_by=updated_by,
                assignable_qs=assignable,
            )
        return user

    @staticmethod
    def deactivate(*, user, deactivated_by=None):
        if deactivated_by is not None and UserService.is_scoped_manager(deactivated_by):
            if user.pk == deactivated_by.pk:
                raise ValueError("You cannot deactivate your own account.")
            # Re-check scope
            UserService.get_manageable_user(pk=user.pk, viewer=deactivated_by)
        user.soft_delete(user=deactivated_by)
        return user

    @staticmethod
    def activate(*, user):
        user.deleted_at = None
        user.deleted_by = None
        user.is_active = True
        user.save(update_fields=["deleted_at", "deleted_by", "is_active"])
        return user


class RoleService:
    @staticmethod
    def list_roles(*, viewer=None):
        qs = Role.active_objects().prefetch_related("role_permissions__permission")
        if viewer is not None and UserService.is_scoped_manager(viewer):
            qs = qs.exclude(slug__in=UserService.PLATFORM_ELEVATED_ROLE_SLUGS)
        return qs

    @staticmethod
    @transaction.atomic
    def create_role(*, name, slug, description="", permission_ids=None, created_by=None):
        role = Role.objects.create(
            name=name,
            slug=slug,
            description=description,
            created_by=created_by,
        )
        if permission_ids:
            RoleService._set_permissions(role, permission_ids, created_by)
        return role

    @staticmethod
    @transaction.atomic
    def update_role(*, role, data, updated_by=None):
        permission_ids = data.pop("permission_ids", None)
        for key, value in data.items():
            setattr(role, key, value)
        role.updated_by = updated_by
        role.save()
        if permission_ids is not None and role.slug not in Role.ELEVATED_SLUGS:
            role.role_permissions.all().delete()
            RoleService._set_permissions(role, permission_ids, updated_by)
        return role

    @staticmethod
    def _set_permissions(role, permission_ids, user=None):
        permissions = Permission.objects.filter(id__in=permission_ids)
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=p, created_by=user)
                for p in permissions
            ]
        )

    @staticmethod
    def delete_role(*, role, deleted_by=None):
        if role.is_system:
            raise ValueError("System roles cannot be deleted.")
        role.soft_delete(user=deleted_by)
        return role

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.repositories.audit_repository import AuditRepository
from apps.authentication.models import Permission, Role, RolePermission, User, UserPermission


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
    def list_users(*, include_deleted=False, viewer=None):
        qs = User.objects.select_related(
            "role", "branch", "tenant", "created_by", "managed_shop_group"
        ).prefetch_related(
            "direct_permissions__permission",
            "role__role_permissions__permission",
        )
        if not include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        if viewer is not None and UserService.is_scoped_manager(viewer):
            qs = UserService._scope_users_for_manager(qs, viewer)
        return qs

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
        permissions = Permission.objects.filter(id__in=permission_ids, deleted_at__isnull=True)
        # Multi-shop managers may only grant permissions they themselves hold.
        if granted_by is not None and UserService.is_scoped_manager(granted_by):
            allowed = set(granted_by.get_permissions())
            permissions = [p for p in permissions if p.codename in allowed]
        UserPermission.objects.bulk_create(
            [
                UserPermission(user=user, permission=p, created_by=granted_by)
                for p in permissions
            ]
        )

    @staticmethod
    def list_assignable_permissions(*, viewer=None):
        """Permission catalog for Admin UI. Scoped managers see only what they can grant."""
        qs = Permission.active_objects().all()
        if viewer is not None and UserService.is_scoped_manager(viewer):
            allowed = set(viewer.get_permissions())
            qs = qs.filter(codename__in=allowed)
        return qs.order_by("module", "codename")

    @staticmethod
    @transaction.atomic
    def create_user(*, data, created_by=None):
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
        if created_by is not None:
            user.created_by = created_by
        user.save()
        if permission_ids is not None:
            UserService._set_direct_permissions(user, permission_ids, created_by)
        return user

    @staticmethod
    @transaction.atomic
    def update_user(*, user, data, updated_by=None):
        password = data.pop("password", None)
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        permission_ids = data.pop("permission_ids", None)
        if role_id is not None:
            UserService._assert_manager_may_assign_role(viewer=updated_by, role_id=role_id)
        for key, value in data.items():
            setattr(user, key, value)
        if role_id is not None:
            user.role_id = role_id
        if branch_id is not None:
            user.branch_id = branch_id
        if password:
            user.set_password(password)
        user.save()
        if permission_ids is not None:
            UserService._set_direct_permissions(user, permission_ids, updated_by)
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
        if permission_ids is not None:
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

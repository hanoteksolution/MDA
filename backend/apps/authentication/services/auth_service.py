from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.repositories.audit_repository import AuditRepository
from apps.authentication.models import Permission, Role, RolePermission, User


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
    @staticmethod
    def list_users(*, include_deleted=False):
        qs = User.objects.select_related("role", "branch")
        if not include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        return qs

    @staticmethod
    @transaction.atomic
    def create_user(*, data, created_by=None):
        password = data.pop("password")
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        user = User.objects.create_user(**data, password=password)
        if role_id:
            user.role_id = role_id
        if branch_id:
            user.branch_id = branch_id
        user.save()
        return user

    @staticmethod
    @transaction.atomic
    def update_user(*, user, data, updated_by=None):
        password = data.pop("password", None)
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        for key, value in data.items():
            setattr(user, key, value)
        if role_id is not None:
            user.role_id = role_id
        if branch_id is not None:
            user.branch_id = branch_id
        if password:
            user.set_password(password)
        user.save()
        return user

    @staticmethod
    def deactivate(*, user, deactivated_by=None):
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
    def list_roles():
        return Role.active_objects().prefetch_related("role_permissions__permission")

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

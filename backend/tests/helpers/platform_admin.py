"""A tenant-less Super Admin (global platform administrator) for platform-API tests."""

from __future__ import annotations

from rest_framework.test import APIClient

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role, User
from tests.helpers.shop_factory import auth_client_as

PLATFORM_INTEGRATIONS = "/api/v1/platform/integrations"


def make_superadmin(username: str = "platform_root") -> User:
    if not Role.objects.filter(slug="super_admin").exists():
        bootstrap_roles_and_permissions()
    user = User.objects.create_user(
        username=username, password="pass12345", role=Role.objects.get(slug="super_admin"),
        is_platform_admin=False, is_superuser=False,
    )
    user.apply_elevated_flags()
    user.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])
    return user


def superadmin_client(username: str = "platform_root") -> APIClient:
    return auth_client_as(APIClient(), make_superadmin(username))

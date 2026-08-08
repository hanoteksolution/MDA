"""Super Admin / Platform Admin have full access without extra permission grants."""

import pytest
from django.contrib.auth import get_user_model

from apps.authentication.bootstrap import PERMISSIONS, bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.authentication.serializers.auth_serializers import UserSerializer
from apps.platform.services.module_service import tenant_has_module, usable_module_codes
from core.tenancy import is_platform_unscoped_actor


@pytest.mark.django_db
def test_super_admin_has_full_access_without_direct_grants():
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="super_admin")
    user = get_user_model().objects.create_user(
        username="elevated_sa",
        password="pass12345",
        role=role,
        is_platform_admin=False,
        is_superuser=False,
    )

    assert user.is_elevated_admin is True
    assert user.has_permission("gym.manage") is True
    assert user.has_permission("platform.manage") is True
    assert user.has_permission("finance.approve") is True
    assert set(user.get_permissions()) >= {row[0] for row in PERMISSIONS}
    assert is_platform_unscoped_actor(user) is True
    assert "gym" in usable_module_codes(user=user)
    assert tenant_has_module("pharmacy", user=user) is True

    payload = UserSerializer(user).data
    assert payload["is_super_admin"] is True
    assert "gym.view" in payload["permissions"]
    assert "gym" in (payload.get("enabled_modules") or [])


@pytest.mark.django_db
def test_apply_elevated_flags_promotes_super_admin():
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="super_admin")
    user = get_user_model().objects.create_user(
        username="nassir_like",
        password="pass12345",
        role=role,
        is_platform_admin=False,
        is_superuser=False,
        is_staff=False,
    )
    assert user.apply_elevated_flags() is True
    user.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])
    user.refresh_from_db()
    assert user.is_platform_admin is True
    assert user.is_superuser is True
    assert user.is_staff is True


@pytest.mark.django_db
def test_cashier_still_needs_explicit_permissions():
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="cashier")
    user = get_user_model().objects.create_user(
        username="limited_cashier",
        password="pass12345",
        role=role,
    )
    assert user.is_elevated_admin is False
    assert user.has_permission("pos.access") is True
    assert user.has_permission("gym.manage") is False
    assert user.has_permission("platform.manage") is False

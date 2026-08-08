"""STEP 09 — role / permission matrix assertions."""

import pytest

from apps.authentication.bootstrap import PERMISSIONS, ROLE_PERMISSIONS, bootstrap_roles_and_permissions
from apps.authentication.models import Permission, Role, RolePermission


@pytest.mark.django_db
def test_bootstrap_seeds_all_permission_codenames():
    bootstrap_roles_and_permissions()
    expected = {code for code, _, _ in PERMISSIONS}
    actual = set(Permission.objects.filter(deleted_at__isnull=True).values_list("codename", flat=True))
    assert expected <= actual


@pytest.mark.django_db
def test_bootstrap_permission_modules_match_catalog():
    bootstrap_roles_and_permissions()
    by_code = {p.codename: p for p in Permission.objects.filter(deleted_at__isnull=True)}
    for code, name, module in PERMISSIONS:
        assert by_code[code].module == module
        assert by_code[code].name == name


@pytest.mark.django_db
def test_system_roles_exist():
    bootstrap_roles_and_permissions()
    for slug, name in Role.SYSTEM_ROLES:
        role = Role.objects.get(slug=slug)
        assert role.is_system is True
        assert role.name == name


@pytest.mark.django_db
def test_platform_admin_has_all_permissions():
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="platform_admin")
    codes = set(
        RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
            "permission__codename", flat=True
        )
    )
    expected = {code for code, _, _ in PERMISSIONS}
    assert expected <= codes


@pytest.mark.django_db
def test_cashier_scoped_to_pos():
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="cashier")
    codes = set(
        RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
            "permission__codename", flat=True
        )
    )
    assert "pos.access" in codes
    assert "platform.manage" not in codes
    assert "roles.delete" not in codes


@pytest.mark.django_db
def test_industry_role_matrix():
    bootstrap_roles_and_permissions()

    def codes_for(slug: str) -> set[str]:
        role = Role.objects.get(slug=slug)
        return set(
            RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
                "permission__codename", flat=True
            )
        )

    assert {"pharmacy.view", "pharmacy.manage", "pharmacy.dispense"} <= codes_for("pharmacist")
    assert {"gym.view", "gym.manage", "gym.attendance.checkin", "gym.members.create", "gym.members.update", "gym.members.delete"} <= codes_for("gym_manager")
    assert "gym.attendance.checkin" in codes_for("receptionist")
    assert "gym.manage" not in codes_for("receptionist")
    assert {"gym.members.create", "gym.members.update"} <= codes_for("receptionist")
    assert "gym.members.delete" not in codes_for("receptionist")
    assert {"gym.view", "gym.attendance.checkin"} <= codes_for("trainer")
    assert "gym.manage" not in codes_for("trainer")
    assert {"restaurant.view", "restaurant.floor"} <= codes_for("waiter")
    assert {"restaurant.view", "restaurant.kitchen"} <= codes_for("kitchen")
    assert "restaurant.manage" not in codes_for("kitchen")
    assert "futsal.finance" in codes_for("futsal_manager")
    assert "futsal.finance" not in codes_for("futsal_staff")


@pytest.mark.django_db
def test_role_permissions_dict_only_references_known_codenames():
    known = {code for code, _, _ in PERMISSIONS}
    for slug, codes in ROLE_PERMISSIONS.items():
        if codes == "*":
            continue
        unknown = set(codes) - known
        assert not unknown, f"{slug} references unknown permissions: {unknown}"


@pytest.mark.django_db
def test_industry_modules_present_in_catalog():
    modules = {module for _, _, module in PERMISSIONS}
    assert {"pharmacy", "gym", "restaurant", "futsal", "trash"} <= modules


@pytest.mark.django_db
def test_additive_bootstrap_keeps_custom_grant():
    bootstrap_roles_and_permissions()
    role = Role.objects.get(slug="cashier")
    extra = Permission.objects.get(codename="reports.view")
    RolePermission.objects.get_or_create(role=role, permission=extra)
    bootstrap_roles_and_permissions()
    codes = set(
        RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
            "permission__codename", flat=True
        )
    )
    assert "reports.view" in codes
    assert "pos.access" in codes

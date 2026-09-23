"""B2-9: per-branch permissions. A profile narrows; it can never widen."""

from __future__ import annotations

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.authentication.models import Permission
from apps.organization.models import UserBranchAccess
from core.branching import (
    BRANCH_HEADER_META,
    HasBranchPermission,
    branch_permissions,
    has_branch_permission,
    is_branch_manager,
)
from tests.helpers.branch_factory import (
    add_user,
    build_ahmed,
    build_branch_tenant,
    grant,
    make_profile,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="rbac-tenant")


def test_worked_example_different_rights_per_branch(ctx):
    """Ahmed: POS+Sales in Hodan, view-only in Bakaaro, nothing in Main."""
    ahmed = build_ahmed(ctx)
    hodan, bakaaro, main = ctx.branch("HODAN"), ctx.branch("BAKAARO"), ctx.branch("MAIN")

    assert has_branch_permission(ahmed, "pos.access", hodan) is True
    assert has_branch_permission(ahmed, "sales.create", hodan) is True
    assert has_branch_permission(ahmed, "inventory.view", hodan) is True

    assert has_branch_permission(ahmed, "inventory.view", bakaaro) is True
    assert has_branch_permission(ahmed, "pos.access", bakaaro) is False
    assert has_branch_permission(ahmed, "sales.create", bakaaro) is False

    for codename in ("pos.access", "sales.create", "inventory.view"):
        assert has_branch_permission(ahmed, codename, main) is False
    assert branch_permissions(ahmed, main) == set()


def test_profile_cannot_grant_a_permission_the_user_does_not_hold(ctx):
    """The critical property: branch access is not a privilege-escalation path."""
    cashier = add_user(ctx, username="cashier_user", role_slug="cashier")
    assert cashier.has_permission("finance.approve") is False

    over_broad = make_profile(
        tenant=ctx.tenant,
        code="TOO_MUCH",
        name="Over-broad",
        codenames=["finance.approve", "users.delete", "pos.access"],
    )
    grant(ctx, user=cashier, branch_code="HODAN", profile=over_broad)

    hodan = ctx.branch("HODAN")
    assert has_branch_permission(cashier, "finance.approve", hodan) is False
    assert has_branch_permission(cashier, "users.delete", hodan) is False
    # Only the intersection with what the role already grants survives.
    assert branch_permissions(cashier, hodan) <= set(cashier.get_permissions())


def test_access_without_a_profile_keeps_the_users_global_permissions(ctx):
    """No profile = no narrowing, which is how existing single-branch users behave."""
    manager = add_user(ctx, username="unprofiled", role_slug="branch_manager")
    grant(ctx, user=manager, branch_code="HODAN")
    assert branch_permissions(manager, ctx.branch("HODAN")) == set(manager.get_permissions())
    assert has_branch_permission(manager, "inventory.adjust", ctx.branch("HODAN")) is True


def test_revoked_global_permission_cannot_be_restored_by_a_branch_profile(ctx):
    """Effective = (role ∪ direct) − revokes, and only then intersected per branch."""
    from apps.authentication.models import UserPermissionRevoke

    user = add_user(ctx, username="revoked_user", role_slug="admin")
    permission = Permission.objects.get(codename="inventory.adjust")
    UserPermissionRevoke.objects.create(user=user, permission=permission)

    profile = make_profile(
        tenant=ctx.tenant, code="WITH_ADJUST", name="Adjuster", codenames=["inventory.adjust"]
    )
    grant(ctx, user=user, branch_code="HODAN", profile=profile)
    assert has_branch_permission(user, "inventory.adjust", ctx.branch("HODAN")) is False


def test_elevated_admin_has_every_permission_in_every_branch(ctx):
    admin = add_user(ctx, username="rbac_super", role_slug="super_admin")
    admin.is_superuser = True
    admin.is_platform_admin = True
    admin.save(update_fields=["is_superuser", "is_platform_admin"])
    for code in ctx.branches:
        assert has_branch_permission(admin, "finance.approve", ctx.branch(code)) is True
        assert is_branch_manager(admin, ctx.branch(code)) is True


def test_manager_flag_is_per_branch(ctx):
    manager_profile = make_profile(
        tenant=ctx.tenant,
        code="MGR",
        name="Manager",
        codenames=["dashboard.view", "inventory.view"],
        is_manager=True,
    )
    staff_profile = make_profile(
        tenant=ctx.tenant, code="STF", name="Staff", codenames=["inventory.view"]
    )
    user = add_user(ctx, username="mixed_manager", role_slug="admin")
    grant(ctx, user=user, branch_code="HODAN", profile=manager_profile)
    grant(ctx, user=user, branch_code="BAKAARO", profile=staff_profile)

    assert is_branch_manager(user, ctx.branch("HODAN")) is True
    assert is_branch_manager(user, ctx.branch("BAKAARO")) is False
    assert is_branch_manager(user, ctx.branch("MAIN")) is False


def test_suspending_access_removes_branch_permissions(ctx):
    ahmed = build_ahmed(ctx)
    access = UserBranchAccess.objects.get(user=ahmed, branch=ctx.branch("HODAN"))
    access.status = UserBranchAccess.STATUS_SUSPENDED
    access.save(update_fields=["status", "updated_at"])
    assert has_branch_permission(ahmed, "pos.access", ctx.branch("HODAN")) is False


def test_permissions_in_another_tenants_branch_are_never_granted(ctx):
    other = build_branch_tenant(slug="rbac-other", branch_codes=("REMOTE",))
    ahmed = build_ahmed(ctx)
    assert has_branch_permission(ahmed, "inventory.view", other.branch("REMOTE")) is False
    assert branch_permissions(ahmed, other.branch("REMOTE")) == set()


class _FakeView:
    """Stand-in for the DRF view argument ``has_permission`` never inspects."""


def _request(user, branch_id=None):
    factory = RequestFactory()
    meta = {BRANCH_HEADER_META: str(branch_id)} if branch_id is not None else {}
    request = factory.get("/api/v1/x/", **meta)
    request.user = user
    return request


class TestHasBranchPermission:
    """HasBranchPermission is the documented DRF integration point (BRANCH_AUTHORIZATION.md
    §4) for future phases (POS in Phase 5). It composes has_permission() with branch
    scope, so it must reject exactly what the underlying primitives reject."""

    def test_grants_when_the_permission_applies_in_the_scoped_branch(self, ctx):
        ahmed = build_ahmed(ctx)
        permission_class = HasBranchPermission("pos.access")()
        request = _request(ahmed, ctx.branch("HODAN").pk)
        assert permission_class.has_permission(request, _FakeView()) is True
        assert request.branch_scope.branch_ids == (ctx.branch("HODAN").pk,)

    def test_denies_when_the_permission_does_not_apply_in_that_branch(self, ctx):
        """Ahmed holds pos.access globally but not in Bakaaro. Requesting Bakaaro
        explicitly for a pos.access-scoped call raises — resolve_branch_scope treats
        an explicitly named, permission-ineligible branch the same as an inaccessible
        one (see test_branch_scope.py::test_permission_filter_narrows_scope_per_branch),
        and DRF's exception handling turns that into the 403, not a bare False."""
        ahmed = build_ahmed(ctx)
        permission_class = HasBranchPermission("pos.access")()
        request = _request(ahmed, ctx.branch("BAKAARO").pk)
        with pytest.raises(PermissionDenied):
            permission_class.has_permission(request, _FakeView())

    def test_denies_when_no_branch_has_the_permission_and_none_is_requested(self, ctx):
        """The user holds pos.access globally (admin role) but a profile narrows it
        away in the one branch they can reach. With no explicit branch id, the
        permission-filtered scope is simply empty, so has_permission() returns False
        rather than raising."""
        view_profile = make_profile(
            tenant=ctx.tenant, code="RBAC_HBP_VIEW", name="View only", codenames=["inventory.view"]
        )
        viewer = add_user(ctx, username="rbac_hbp_viewer", role_slug="admin")
        grant(ctx, user=viewer, branch_code="BAKAARO", profile=view_profile)
        permission_class = HasBranchPermission("pos.access")()
        request = _request(viewer)
        assert permission_class.has_permission(request, _FakeView()) is False

    def test_denies_a_user_who_lacks_the_permission_globally(self, ctx):
        cashier = add_user(ctx, username="rbac_hbp_cashier", role_slug="cashier")
        grant(ctx, user=cashier, branch_code="HODAN")
        permission_class = HasBranchPermission("finance.approve")()
        request = _request(cashier, ctx.branch("HODAN").pk)
        assert permission_class.has_permission(request, _FakeView()) is False

    def test_denies_an_unauthenticated_request(self, ctx):
        from django.contrib.auth.models import AnonymousUser

        permission_class = HasBranchPermission("pos.access")()
        request = _request(AnonymousUser())
        assert permission_class.has_permission(request, _FakeView()) is False

    def test_propagates_permission_denied_for_an_unauthorised_branch(self, ctx):
        """An out-of-scope branch id raises, matching resolve_branch_scope directly —
        DRF's exception handling (not a bare False) turns this into the 403."""
        ahmed = build_ahmed(ctx)
        permission_class = HasBranchPermission("pos.access")()
        request = _request(ahmed, ctx.branch("MAIN").pk)
        with pytest.raises(PermissionDenied):
            permission_class.has_permission(request, _FakeView())

    def test_propagates_validation_error_for_a_malformed_branch_id(self, ctx):
        ahmed = build_ahmed(ctx)
        permission_class = HasBranchPermission("pos.access")()
        request = _request(ahmed, "not-a-uuid")
        with pytest.raises(ValidationError):
            permission_class.has_permission(request, _FakeView())

    def test_rejects_the_all_selector_when_allow_all_is_false(self, ctx):
        ahmed = build_ahmed(ctx)
        permission_class = HasBranchPermission("pos.access", allow_all=False)()
        request = _request(ahmed, "all")
        with pytest.raises(ValidationError):
            permission_class.has_permission(request, _FakeView())

    def test_allows_the_all_selector_by_default_for_read_views(self, ctx):
        ahmed = build_ahmed(ctx)
        permission_class = HasBranchPermission("inventory.view")()
        request = _request(ahmed, "all")
        assert permission_class.has_permission(request, _FakeView()) is True
        assert request.branch_scope.requested_all is True

    def test_elevated_admin_passes_without_any_branch_access_rows(self, ctx):
        admin = add_user(ctx, username="rbac_hbp_admin", role_slug="super_admin")
        admin.is_superuser = True
        admin.is_platform_admin = True
        admin.save(update_fields=["is_superuser", "is_platform_admin"])
        permission_class = HasBranchPermission("finance.approve")()
        request = _request(admin, ctx.branch("MAIN").pk)
        assert permission_class.has_permission(request, _FakeView()) is True

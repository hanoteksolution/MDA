"""B2-4 .. B2-8: branch scope resolution is fail-closed and never widens."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.organization.models import UserBranchAccess
from core.branching import (
    BRANCH_HEADER_META,
    accessible_branches,
    default_branch_for,
    resolve_branch_scope,
)
from tests.helpers.branch_factory import add_user, build_ahmed, build_branch_tenant, grant

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="scope-tenant")


def request_for(user, branch_id=None):
    factory = RequestFactory()
    meta = {BRANCH_HEADER_META: str(branch_id)} if branch_id is not None else {}
    request = factory.get("/api/v1/organization/context/", **meta)
    request.user = user
    return request


def test_scope_rejects_unauthorised_branch_header(ctx):
    """B2-4: a branch the user does not hold is a 403, never a silent widen."""
    ahmed = build_ahmed(ctx)
    main_id = ctx.branch("MAIN").pk

    with pytest.raises(PermissionDenied):
        resolve_branch_scope(request=request_for(ahmed, main_id))

    # And the scope without a header still excludes MAIN.
    scope = resolve_branch_scope(request=request_for(ahmed))
    assert str(main_id) not in {str(b) for b in scope.branch_ids}
    assert scope.allows(main_id) is False


def test_scope_rejects_branch_of_another_tenant(ctx):
    """B2-4 / B2-10: a foreign-tenant branch id is indistinguishable from a bad one."""
    other = build_branch_tenant(slug="scope-other", branch_codes=("OTHER",))
    ahmed = build_ahmed(ctx)
    with pytest.raises(PermissionDenied):
        resolve_branch_scope(request=request_for(ahmed, other.branch("OTHER").pk))


def test_scope_rejects_malformed_branch_id(ctx):
    ahmed = build_ahmed(ctx)
    with pytest.raises(ValidationError):
        resolve_branch_scope(request=request_for(ahmed, "not-a-uuid"))


def test_scope_rejects_unknown_branch_id(ctx):
    ahmed = build_ahmed(ctx)
    with pytest.raises(PermissionDenied):
        resolve_branch_scope(request=request_for(ahmed, uuid.uuid4()))


def test_explicit_branch_narrows_scope(ctx):
    ahmed = build_ahmed(ctx)
    hodan = ctx.branch("HODAN")
    scope = resolve_branch_scope(request=request_for(ahmed, hodan.pk))
    assert scope.branch_ids == (hodan.pk,)
    assert scope.explicit is True
    assert scope.is_all is False
    assert scope.branch_id == hodan.pk
    assert scope.require_single() == hodan.pk


def test_all_selector_is_rejected_for_pos_and_stock_mutations(ctx):
    """B2-5: 'all branches' is meaningless for a write and must be refused."""
    ahmed = build_ahmed(ctx)
    request = request_for(ahmed, "all")

    with pytest.raises(ValidationError):
        resolve_branch_scope(request=request, allow_all=False)

    scope = resolve_branch_scope(request=request, allow_all=True)
    assert scope.requested_all is True
    with pytest.raises(ValidationError):
        scope.require_single("a POS sale")


def test_ambiguous_scope_is_rejected_for_single_branch_operations(ctx):
    """Two branches in scope and no selection is ambiguous, so a write must refuse."""
    owner = add_user(ctx, username="owner")
    grant(ctx, user=owner, branch_code="HODAN")
    grant(ctx, user=owner, branch_code="BAKAARO")
    scope = resolve_branch_scope(request=request_for(owner))
    assert len(scope.branch_ids) == 2
    with pytest.raises(ValidationError):
        scope.require_single("a stock adjustment")


def test_single_branch_user_needs_no_header_for_writes(ctx):
    """Backward compatibility: one branch is unambiguous even with no header sent."""
    staff = add_user(ctx, username="single_branch")
    grant(ctx, user=staff, branch_code="HODAN")
    scope = resolve_branch_scope(request=request_for(staff))
    assert scope.require_single("a POS sale") == ctx.branch("HODAN").pk


def test_legacy_user_without_access_rows_falls_back_to_user_branch(ctx):
    """B2-6: backfill safety — nobody is locked out before their rows exist."""
    legacy = add_user(ctx, username="legacy", legacy_branch="BAKAARO")
    assert not UserBranchAccess.objects.filter(user=legacy).exists()

    scope = resolve_branch_scope(request=request_for(legacy))
    assert scope.branch_ids == (ctx.branch("BAKAARO").pk,)
    assert default_branch_for(legacy) == ctx.branch("BAKAARO").pk


def test_user_with_access_rows_does_not_fall_back_to_user_branch(ctx):
    """Once rows exist they are authoritative: the legacy branch is not re-added."""
    user = add_user(ctx, username="migrated", legacy_branch="MAIN")
    grant(ctx, user=user, branch_code="HODAN")
    scope = resolve_branch_scope(request=request_for(user))
    assert scope.branch_ids == (ctx.branch("HODAN").pk,)
    assert scope.allows(ctx.branch("MAIN").pk) is False


def test_user_with_no_branch_at_all_gets_empty_scope(ctx):
    orphan = add_user(ctx, username="orphan")
    scope = resolve_branch_scope(request=request_for(orphan))
    assert scope.branch_ids == ()
    assert scope.is_empty is True
    with pytest.raises(PermissionDenied):
        scope.require_single("a POS sale")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": UserBranchAccess.STATUS_SUSPENDED},
        {"status": UserBranchAccess.STATUS_ENDED},
        {"starts_on": timezone.localdate() + timedelta(days=5)},
        {"ends_on": timezone.localdate() - timedelta(days=1)},
    ],
)
def test_non_effective_access_grants_nothing(ctx, kwargs):
    """B2-7: suspended, ended, future and expired grants all resolve to no access."""
    user = add_user(ctx, username=f"windowed_{abs(hash(str(kwargs)))}")
    grant(ctx, user=user, branch_code="HODAN", **kwargs)
    scope = resolve_branch_scope(request=request_for(user))
    assert scope.branch_ids == ()
    with pytest.raises(PermissionDenied):
        resolve_branch_scope(request=request_for(user, ctx.branch("HODAN").pk))


def test_inactive_branch_is_not_in_scope(ctx):
    user = add_user(ctx, username="inactive_branch_user")
    grant(ctx, user=user, branch_code="HODAN")
    branch = ctx.branch("HODAN")
    branch.is_active = False
    branch.save(update_fields=["is_active", "updated_at"])
    assert resolve_branch_scope(request=request_for(user)).branch_ids == ()


def test_elevated_admin_sees_every_branch_in_the_tenant(ctx):
    """B2-8: elevated admins bypass branch scope just as they bypass tenant scope."""
    admin = add_user(ctx, username="super", role_slug="super_admin")
    admin.is_platform_admin = True
    admin.is_superuser = True
    admin.save(update_fields=["is_platform_admin", "is_superuser"])

    scope = resolve_branch_scope(request=request_for(admin))
    assert len(scope.branch_ids) == 3
    assert scope.allows(ctx.branch("MAIN").pk) is True
    # Still tenant-bound: another tenant's branch is not reachable.
    other = build_branch_tenant(slug="scope-elevated-other", branch_codes=("X",))
    assert scope.allows(other.branch("X").pk) is False


def test_permission_filter_narrows_scope_per_branch(ctx):
    """Ahmed's POS scope is Hodan only; his inventory scope is Hodan + Bakaaro."""
    ahmed = build_ahmed(ctx)
    pos_scope = resolve_branch_scope(request=request_for(ahmed), permission="pos.access")
    assert pos_scope.branch_ids == (ctx.branch("HODAN").pk,)

    inv_scope = resolve_branch_scope(request=request_for(ahmed), permission="inventory.view")
    assert {str(b) for b in inv_scope.branch_ids} == {
        str(ctx.branch("HODAN").pk),
        str(ctx.branch("BAKAARO").pk),
    }

    with pytest.raises(PermissionDenied):
        resolve_branch_scope(
            request=request_for(ahmed, ctx.branch("BAKAARO").pk), permission="pos.access"
        )


def test_query_param_is_treated_as_untrusted_like_the_header(ctx):
    """Changing branch_id in the query string must not bypass authorisation either."""
    ahmed = build_ahmed(ctx)
    factory = RequestFactory()
    request = factory.get("/api/v1/x/", {"branch_id": str(ctx.branch("MAIN").pk)})
    request.user = ahmed
    with pytest.raises(PermissionDenied):
        resolve_branch_scope(request=request)


def test_scope_filter_narrows_a_queryset(ctx):
    from apps.inventory.models import Warehouse

    ahmed = build_ahmed(ctx)
    scope = resolve_branch_scope(request=request_for(ahmed, ctx.branch("HODAN").pk))
    warehouses = scope.filter(Warehouse.active_objects(), field_name="branch_id")
    assert [w.code for w in warehouses] == ["WH-HODAN"]


def test_empty_scope_filters_to_nothing_not_everything(ctx):
    from apps.inventory.models import Warehouse

    orphan = add_user(ctx, username="orphan_filter")
    scope = resolve_branch_scope(request=request_for(orphan))
    assert scope.filter(Warehouse.active_objects(), field_name="branch_id").count() == 0
    assert Warehouse.active_objects().count() == 3


def test_accessible_branches_is_empty_for_anonymous():
    from django.contrib.auth.models import AnonymousUser

    assert accessible_branches(AnonymousUser()).count() == 0
    with pytest.raises(PermissionDenied):
        resolve_branch_scope(user=AnonymousUser())

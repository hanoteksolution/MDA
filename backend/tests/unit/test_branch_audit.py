"""B2-13: branch mutations leave an audit trail that carries the branch."""

from __future__ import annotations

import pytest

from apps.audit.models import AuditLog
from apps.organization.services import (
    BranchAccessProfileService,
    BranchAccessService,
    CashRegisterService,
    StockLocationService,
)
from apps.settings_app.services.settings_service import BranchService
from tests.helpers.branch_factory import add_user, build_branch_tenant, make_profile

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="audit-tenant")


@pytest.fixture
def owner(ctx):
    user = add_user(ctx, username="audit_owner", role_slug="admin")
    from tests.helpers.branch_factory import grant

    for code in ctx.branches:
        grant(ctx, user=user, branch_code=code)
    return user


def latest(module="organization", action=None):
    qs = AuditLog.objects.filter(module=module)
    if action:
        qs = qs.filter(action=action)
    return qs.order_by("-timestamp").first()


def test_granting_branch_access_is_audited_with_the_branch(ctx, owner):
    target = add_user(ctx, username="audit_target", role_slug="cashier")
    branch = ctx.branch("HODAN")
    BranchAccessService.grant(target_user=target, branch=branch, actor=owner)

    entry = latest(action="create")
    assert entry is not None
    assert entry.user_id == owner.pk
    assert entry.entity_type == "UserBranchAccess"
    assert entry.new_values["branch"] == str(branch.pk)
    assert entry.branch_id == branch.pk


def test_revoking_branch_access_is_audited(ctx, owner):
    target = add_user(ctx, username="audit_revoke", role_slug="cashier")
    access = BranchAccessService.grant(
        target_user=target, branch=ctx.branch("BAKAARO"), actor=owner
    )
    BranchAccessService.revoke(access=access, actor=owner)

    entry = latest(action="delete")
    assert entry.entity_type == "UserBranchAccess"
    assert entry.old_values["branch"] == str(ctx.branch("BAKAARO").pk)
    assert entry.branch_id == ctx.branch("BAKAARO").pk


def test_location_creation_is_audited_with_the_branch(ctx, owner):
    warehouse = ctx.warehouse("HODAN")
    StockLocationService.create_location(
        warehouse=warehouse,
        data={"code": "AUD-1", "name": "Audited Location"},
        actor=owner,
    )
    entry = latest(action="create")
    assert entry.entity_type == "StockLocation"
    assert entry.new_values["branch"] == str(warehouse.branch_id)
    assert entry.branch_id == warehouse.branch_id


def test_cash_register_creation_is_audited(ctx, owner):
    CashRegisterService.create_register(
        branch=ctx.branch("HODAN"), data={"code": "REG-AUD", "name": "Audited"}, actor=owner
    )
    entry = latest(action="create")
    assert entry.entity_type == "CashRegister"
    assert entry.branch_id == ctx.branch("HODAN").pk


def test_access_profile_changes_are_audited(ctx, owner):
    profile = make_profile(
        tenant=ctx.tenant, code="AUDP", name="Audited profile", codenames=["inventory.view"]
    )
    BranchAccessProfileService.update_profile(
        profile=profile, data={"name": "Renamed"}, actor=owner
    )
    entry = latest(action="update")
    assert entry.entity_type == "BranchAccessProfile"
    assert entry.old_values["name"] == "Audited profile"
    assert entry.new_values["name"] == "Renamed"
    # A profile is tenant-wide, not branch-specific: no branch is invented for it.
    assert entry.branch_id is None


def test_branch_archive_is_audited(ctx, owner):
    branch = ctx.branch("BAKAARO")
    BranchService.archive_branch(branch=branch, user=owner)
    entry = latest(module="branches", action="update")
    assert entry is not None
    assert entry.entity_type == "Branch"
    assert entry.new_values["status"] == "ARCHIVED"
    assert entry.branch_id == branch.pk


def test_audit_rows_carry_the_tenant(ctx, owner):
    CashRegisterService.create_register(
        branch=ctx.branch("MAIN"), data={"code": "REG-T", "name": "Tenant check"}, actor=owner
    )
    entry = latest(action="create")
    assert entry.tenant_id == ctx.tenant.pk


def test_historical_audit_rows_keep_a_null_branch(ctx):
    """Forward-only: the column is added, historical rows are never back-dated."""
    row = AuditLog.objects.create(
        tenant=ctx.tenant, action="update", module="legacy", entity_type="Invoice"
    )
    assert row.branch_id is None

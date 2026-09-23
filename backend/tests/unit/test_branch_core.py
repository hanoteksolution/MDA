"""B2-1 / B2-2: the canonical Branch keeps working and gains a consistent status."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import BranchService
from tests.helpers.branch_factory import add_user, build_branch_tenant

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="core-tenant")


def test_branch_code_is_unique_within_a_tenant(ctx):
    """B2-1: the pre-existing (tenant, code) constraint still holds."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Branch.objects.create(
                tenant=ctx.tenant, company=ctx.company, name="Duplicate", code="HODAN"
            )


def test_branch_code_is_unique_within_a_company(ctx):
    """B2-1: the pre-existing (company, code) constraint still holds."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Branch.objects.create(
                tenant=None, company=ctx.company, name="Duplicate company code", code="HODAN"
            )


def test_same_code_in_two_tenants_is_allowed(ctx):
    other = build_branch_tenant(slug="core-other", branch_codes=("HODAN",))
    assert other.branch("HODAN").code == ctx.branch("HODAN").code
    assert other.branch("HODAN").tenant_id != ctx.branch("HODAN").tenant_id


def test_existing_branch_rows_survive_the_new_fields(ctx):
    """D1: extending in place must not disturb the 94 FKs already pointing at Branch."""
    branch = ctx.branch("MAIN")
    branch.refresh_from_db()
    assert branch.name == "Main"
    assert branch.company_id == ctx.company.pk
    assert branch.warehouses.count() == 1
    assert branch.status == Branch.STATUS_ACTIVE
    assert branch.branch_type == Branch.TYPE_RETAIL


def test_status_follows_is_active_in_both_directions(ctx):
    """B2-2: is_active stays the legacy source of truth and never diverges."""
    branch = ctx.branch("HODAN")

    branch.is_active = False
    branch.save()
    branch.refresh_from_db()
    assert branch.status == Branch.STATUS_INACTIVE

    branch.is_active = True
    branch.save()
    branch.refresh_from_db()
    assert branch.status == Branch.STATUS_ACTIVE

    branch.status = Branch.STATUS_ARCHIVED
    branch.save()
    branch.refresh_from_db()
    assert branch.is_active is False

    branch.status = Branch.STATUS_ACTIVE
    branch.save()
    branch.refresh_from_db()
    assert branch.is_active is True


def test_temporarily_closed_is_not_active(ctx):
    branch = ctx.branch("HODAN")
    branch.status = Branch.STATUS_TEMPORARILY_CLOSED
    branch.save()
    branch.refresh_from_db()
    assert branch.is_active is False
    assert branch.status == Branch.STATUS_TEMPORARILY_CLOSED


def test_archiving_a_branch_with_an_open_cashier_session_is_rejected(ctx):
    """B2-1: closing a branch out from under an open till would strand cash."""
    from apps.sales.models import CashierSession

    cashier = add_user(ctx, username="till_user", role_slug="cashier")
    branch = ctx.branch("HODAN")
    CashierSession.objects.create(
        tenant=ctx.tenant,
        branch=branch,
        cashier=cashier,
        opening_float=Decimal("100"),
        status="open",
    )
    with pytest.raises(ValidationError):
        BranchService.archive_branch(branch=branch, user=cashier)

    branch.refresh_from_db()
    assert branch.status == Branch.STATUS_ACTIVE


def test_archiving_a_quiet_branch_succeeds(ctx):
    owner = add_user(ctx, username="core_owner", role_slug="admin")
    branch = ctx.branch("BAKAARO")
    BranchService.archive_branch(branch=branch, user=owner)
    branch.refresh_from_db()
    assert branch.status == Branch.STATUS_ARCHIVED
    assert branch.is_active is False


def test_manager_link_is_optional_and_nullable(ctx):
    owner = add_user(ctx, username="branch_boss", role_slug="branch_manager")
    branch = ctx.branch("HODAN")
    assert branch.manager_id is None
    branch.manager = owner
    branch.save(update_fields=["manager", "updated_at"])
    branch.refresh_from_db()
    assert branch.manager_id == owner.pk


def test_default_branch_is_unique_per_company(ctx):
    owner = add_user(ctx, username="default_setter", role_slug="admin")
    BranchService.set_default(branch=ctx.branch("HODAN"), updated_by=owner)
    defaults = Branch.objects.filter(company=ctx.company, is_default=True)
    assert [b.code for b in defaults] == ["HODAN"]


def test_branch_without_a_company_cannot_be_created(ctx):
    """Open Question 1: no Company means no Branch — we never fabricate one."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Branch.objects.create(tenant=ctx.tenant, company=None, name="Orphan", code="ORPH")


def test_company_isolation_between_tenants(ctx):
    other = build_branch_tenant(slug="core-company-other", branch_codes=("X",))
    assert Company.objects.filter(tenant=ctx.tenant).count() == 1
    assert Company.objects.filter(tenant=other.tenant).count() == 1

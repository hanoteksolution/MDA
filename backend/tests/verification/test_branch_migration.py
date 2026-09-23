"""MIG-1 / MIG-2: the branch backfill resolves what it can and flags what it cannot.

These run the real `branch_migration_report` command against seeded data, so a
regression in a backfill rule is caught here rather than on a customer database.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.authentication.models import Role
from apps.inventory.models import Warehouse
from apps.organization.models import StockLocation, UserBranchAccess
from apps.organization.services import StockLocationService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from tests.helpers.branch_factory import add_user, build_branch_tenant, grant

pytestmark = pytest.mark.django_db


def run_report(**kwargs):
    out = StringIO()
    call_command("branch_migration_report", "--json", stdout=out, **kwargs)
    return json.loads(out.getvalue())


def checks_by_key(payload):
    return {c["check"]: c for c in payload["checks"]}


def test_seeded_multi_branch_tenant_reports_clean():
    """MIG-6 in miniature: a correctly migrated tenant has nothing to review."""
    ctx = build_branch_tenant(slug="mig-clean")
    user = add_user(ctx, username="mig_user", legacy_branch="MAIN")
    grant(ctx, user=user, branch_code="MAIN", is_default=True)

    checks = checks_by_key(run_report())
    assert checks["branch.default_per_tenant"]["status"] == "OK"
    assert checks["warehouse.default_location"]["unresolved"] == 0
    assert checks["warehouse.tenant_matches_branch"]["review_required"] == 0
    assert checks["access.user_branch_backfilled"]["unresolved"] == 0


def test_tenant_without_a_company_is_skipped_and_listed():
    """Open Question 1: skip, report the reason, never fabricate a Company."""
    Tenant.objects.create(name="No Company Co", slug="mig-no-company")
    payload = run_report()
    check = checks_by_key(payload)["tenant.company_present"]
    assert check["skipped"] >= 1
    assert any("mig-no-company" in d for d in check["details"])
    assert any("no Company" in d for d in check["details"])
    # Skipping is not silent, but it is also not a failure on its own.
    assert check["status"] in ("OK", "SKIPPED")


def test_branch_data_without_a_company_is_flagged_review_required():
    """The one case we refuse to guess: branch rows whose tenant has no Company."""
    tenant = Tenant.objects.create(name="Orphan Branch Co", slug="mig-orphan-branch")
    company = Company.objects.create(name="Temp", tenant=tenant)
    Branch.objects.create(tenant=tenant, company=company, name="Stray", code="STRAY")
    company.soft_delete()

    check = checks_by_key(run_report())["tenant.branch_data_without_company"]
    assert check["status"] == "REVIEW_REQUIRED"
    assert check["review_required"] >= 1


def test_missing_default_branch_is_reported_not_guessed():
    ctx = build_branch_tenant(slug="mig-no-default")
    Branch.objects.filter(tenant=ctx.tenant).update(is_default=False)
    check = checks_by_key(run_report(tenant="mig-no-default"))["branch.default_per_tenant"]
    assert check["status"] == "REVIEW_REQUIRED"
    assert check["unresolved"] == 1


def test_two_default_branches_are_reported_as_ambiguous():
    ctx = build_branch_tenant(slug="mig-two-defaults")
    Branch.objects.filter(tenant=ctx.tenant, code="HODAN").update(is_default=True)
    check = checks_by_key(run_report(tenant="mig-two-defaults"))["branch.default_per_tenant"]
    assert check["status"] == "REVIEW_REQUIRED"
    assert check["ambiguous"] == 1


def test_warehouse_without_a_default_location_is_unresolved():
    ctx = build_branch_tenant(slug="mig-no-location", with_locations=False)
    check = checks_by_key(run_report(tenant="mig-no-location"))["warehouse.default_location"]
    assert check["unresolved"] == len(ctx.warehouses)
    assert check["status"] == "REVIEW_REQUIRED"

    for code in ctx.warehouses:
        StockLocationService.ensure_default_locations(warehouse=ctx.warehouse(code))
    after = checks_by_key(run_report(tenant="mig-no-location"))["warehouse.default_location"]
    assert after["unresolved"] == 0


def test_cross_tenant_warehouse_is_flagged_review_required():
    ctx = build_branch_tenant(slug="mig-cross-a")
    other = build_branch_tenant(slug="mig-cross-b", branch_codes=("B1",))
    Warehouse.objects.create(
        tenant=ctx.tenant, branch=other.branch("B1"), name="Wrong tenant", code="WH-CROSS"
    )
    check = checks_by_key(run_report())["warehouse.tenant_matches_branch"]
    assert check["status"] == "REVIEW_REQUIRED"
    assert check["review_required"] >= 1


def test_legacy_user_branch_without_access_row_is_unresolved():
    ctx = build_branch_tenant(slug="mig-legacy-user")
    add_user(ctx, username="mig_legacy", legacy_branch="HODAN")
    check = checks_by_key(run_report(tenant="mig-legacy-user"))["access.user_branch_backfilled"]
    assert check["unresolved"] == 1
    assert check["status"] == "REVIEW_REQUIRED"


def test_backfill_creates_access_rows_from_legacy_user_branch():
    """MIG-2: users keep working; the row is derived, never invented."""
    ctx = build_branch_tenant(slug="mig-backfill")
    user = add_user(ctx, username="mig_backfill_user", legacy_branch="BAKAARO")
    assert not UserBranchAccess.objects.filter(user=user).exists()

    call_command("backfill_branch_access", verbosity=0)

    access = UserBranchAccess.objects.get(user=user)
    assert access.branch_id == ctx.branch("BAKAARO").pk
    assert access.is_default is True
    assert access.status == UserBranchAccess.STATUS_ACTIVE
    assert checks_by_key(run_report(tenant="mig-backfill"))["access.user_branch_backfilled"][
        "unresolved"
    ] == 0


def test_backfill_is_idempotent():
    ctx = build_branch_tenant(slug="mig-idempotent")
    add_user(ctx, username="mig_idem_user", legacy_branch="MAIN")
    call_command("backfill_branch_access", verbosity=0)
    call_command("backfill_branch_access", verbosity=0)
    assert UserBranchAccess.objects.filter(user__username="mig_idem_user").count() == 1


def test_backfill_does_not_copy_school_campus_access():
    """MIG-2: School authorisation stays in SchoolCampusAccess; nothing is cross-granted."""
    from apps.school.models import SchoolCampusAccess

    ctx = build_branch_tenant(slug="mig-school", modules=("school",))
    teacher = add_user(ctx, username="mig_teacher", role_slug="school_teacher")
    SchoolCampusAccess.objects.create(
        tenant=ctx.tenant, user=teacher, branch=ctx.branch("HODAN"), is_active=True
    )

    call_command("backfill_branch_access", verbosity=0)

    assert not UserBranchAccess.objects.filter(user=teacher).exists()
    assert SchoolCampusAccess.objects.filter(user=teacher).count() == 1


def test_backfill_skips_users_with_no_legacy_branch():
    ctx = build_branch_tenant(slug="mig-no-legacy")
    orphan = add_user(ctx, username="mig_orphan")
    call_command("backfill_branch_access", verbosity=0)
    assert not UserBranchAccess.objects.filter(user=orphan).exists()


def test_backfill_assigns_manager_profile_to_branch_managers():
    ctx = build_branch_tenant(slug="mig-manager")
    manager = add_user(ctx, username="mig_manager", role_slug="branch_manager", legacy_branch="HODAN")
    staff = add_user(ctx, username="mig_staff", role_slug="cashier", legacy_branch="HODAN")

    call_command("backfill_branch_access", verbosity=0)

    manager_access = UserBranchAccess.objects.get(user=manager)
    staff_access = UserBranchAccess.objects.get(user=staff)
    assert manager_access.access_profile is not None
    assert manager_access.access_profile.is_manager is True
    assert staff_access.access_profile is not None
    assert staff_access.access_profile.is_manager is False
    assert Role.objects.filter(slug="branch_manager").exists()


def test_journal_entries_without_a_branch_are_informational_not_failures():
    """Open Question 3: 'Unassigned' is an accepted, reported outcome."""
    build_branch_tenant(slug="mig-journal")
    check = checks_by_key(run_report())["finance.entry_branch"]
    assert check["status"] in ("OK", "INFO")


def test_report_is_read_only():
    ctx = build_branch_tenant(slug="mig-readonly")
    before = (
        Branch.objects.count(),
        Warehouse.objects.count(),
        StockLocation.objects.count(),
        UserBranchAccess.objects.count(),
    )
    run_report()
    after = (
        Branch.objects.count(),
        Warehouse.objects.count(),
        StockLocation.objects.count(),
        UserBranchAccess.objects.count(),
    )
    assert before == after
    assert ctx.tenant.pk is not None


# --------------------------------------------------------------------------- #
# MIG-3 (Phase 3, wave M2): StockMovement.branch / InventoryTransaction.branch
# --------------------------------------------------------------------------- #


def test_ledger_branch_is_backfilled_from_warehouse_branch():
    from decimal import Decimal

    from apps.inventory.models import InventoryTransaction, StockMovement
    from apps.inventory.services.inventory_service import InventoryService
    from tests.helpers.branch_factory import add_owner, add_product, set_inventory

    ctx = build_branch_tenant(slug="mig-ledger")
    owner = add_owner(ctx, username="mig_ledger_owner")
    product = add_product(ctx, sku="MIG-LEDGER-1")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    InventoryService.apply_sale_delta(
        product=product, warehouse=ctx.warehouse("HODAN"), quantity_delta=Decimal("-2"), user=owner
    )

    # New rows are stamped going forward — already resolved without a backfill run.
    movement = StockMovement.objects.filter(product=product).latest("created_at")
    assert movement.branch_id == ctx.branch("HODAN").pk

    checks = checks_by_key(run_report(tenant="mig-ledger"))
    assert checks["ledger.movement_branch"]["unresolved"] == 0
    assert checks["ledger.movement_branch"]["ambiguous"] == 0
    assert checks["ledger.transaction_branch"]["unresolved"] == 0


def test_ledger_backfill_resolves_historical_rows_created_without_a_branch():
    """Simulates a pre-Phase-3 row: create a movement/transaction the way the old
    code did (no branch), then prove the backfill command derives it correctly."""
    from decimal import Decimal

    from apps.inventory.models import Inventory, InventoryTransaction, StockMovement
    from tests.helpers.branch_factory import add_product, set_inventory

    ctx = build_branch_tenant(slug="mig-ledger-historical")
    product = add_product(ctx, sku="MIG-LEDGER-HIST")
    inv = set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))
    StockMovement.objects.create(
        tenant=ctx.tenant,
        product=product,
        warehouse=ctx.warehouse("HODAN"),
        movement_type="sale",
        quantity=Decimal("-1"),
    )
    InventoryTransaction.objects.create(
        tenant=ctx.tenant,
        inventory=inv,
        transaction_type="out",
        quantity_before=Decimal("5"),
        quantity_after=Decimal("4"),
        quantity_change=Decimal("-1"),
    )

    before = checks_by_key(run_report(tenant="mig-ledger-historical"))
    assert before["ledger.movement_branch"]["unresolved"] == 1
    assert before["ledger.transaction_branch"]["unresolved"] == 1

    out = StringIO()
    call_command("backfill_ledger_branch", "--json", stdout=out)
    result = json.loads(out.getvalue())["result"]
    assert result["unresolved"] == 0

    after = checks_by_key(run_report(tenant="mig-ledger-historical"))
    assert after["ledger.movement_branch"]["unresolved"] == 0
    assert after["ledger.transaction_branch"]["unresolved"] == 0

    movement = StockMovement.objects.get(product=product, movement_type="sale")
    assert movement.branch_id == ctx.branch("HODAN").pk


def test_ledger_backfill_is_idempotent():
    from decimal import Decimal

    from apps.inventory.models import StockMovement
    from tests.helpers.branch_factory import add_product, set_inventory

    ctx = build_branch_tenant(slug="mig-ledger-idempotent")
    product = add_product(ctx, sku="MIG-LEDGER-IDEMP")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))
    StockMovement.objects.create(
        tenant=ctx.tenant,
        product=product,
        warehouse=ctx.warehouse("HODAN"),
        movement_type="sale",
        quantity=Decimal("-1"),
    )
    call_command("backfill_ledger_branch", verbosity=0)
    call_command("backfill_ledger_branch", verbosity=0)  # second run: no-op, no error
    movement = StockMovement.objects.get(product=product)
    assert movement.branch_id == ctx.branch("HODAN").pk


def test_ledger_backfill_dry_run_makes_no_changes():
    from decimal import Decimal

    from apps.inventory.models import StockMovement
    from tests.helpers.branch_factory import add_product, set_inventory

    ctx = build_branch_tenant(slug="mig-ledger-dryrun")
    product = add_product(ctx, sku="MIG-LEDGER-DRYRUN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))
    StockMovement.objects.create(
        tenant=ctx.tenant,
        product=product,
        warehouse=ctx.warehouse("HODAN"),
        movement_type="sale",
        quantity=Decimal("-1"),
    )
    call_command("backfill_ledger_branch", "--dry-run", verbosity=0)
    movement = StockMovement.objects.get(product=product)
    assert movement.branch_id is None


# --------------------------------------------------------------------------- #
# MIG-4 (Phase 5, wave M4): default terminal/register + JournalLine.branch
# --------------------------------------------------------------------------- #


def _legacy_session(ctx, user, branch_code, *, status="open"):
    from apps.sales.models import CashierSession

    return CashierSession.objects.create(
        tenant=ctx.tenant, branch=ctx.branch(branch_code), cashier=user, status=status
    )


def test_pos_backfill_creates_one_default_terminal_for_pos_active_branches_only():
    from apps.organization.models import CashRegister, PosTerminal
    from apps.organization.services.backfill_service import backfill_pos_terminals

    ctx = build_branch_tenant(slug="mig-pos", branch_codes=("HODAN", "BAKAARO", "IDLE"))
    user = add_user(ctx, username="mig_pos_user", branches=("HODAN", "BAKAARO"))
    closed = _legacy_session(ctx, user, "HODAN", status="closed")
    live = _legacy_session(ctx, user, "HODAN")
    _legacy_session(ctx, user, "BAKAARO", status="closed")

    result = backfill_pos_terminals()

    assert result.total == 2 and result.unresolved == 0
    terminal = PosTerminal.objects.get(branch=ctx.branch("HODAN"))
    assert (terminal.code, terminal.name) == ("POS-1", "Main Terminal")
    assert terminal.default_warehouse_id == ctx.warehouse("HODAN").pk  # legacy warehouse, unchanged
    register = CashRegister.objects.get(branch=ctx.branch("HODAN"))
    assert register.code == "REG-1" and register.cash_account_id is None  # never guessed
    assert terminal.default_cash_register_id == register.pk
    for session in (closed, live):
        session.refresh_from_db()
        assert session.terminal_id == terminal.pk and session.register_id == register.pk
        assert session.warehouse_id == ctx.warehouse("HODAN").pk
    # No POS history -> nothing created.
    assert not PosTerminal.objects.filter(branch=ctx.branch("IDLE")).exists()


def test_pos_backfill_is_idempotent_and_reports_extra_open_shifts():
    from apps.organization.models import PosTerminal
    from apps.organization.services.backfill_service import backfill_pos_terminals
    from apps.sales.models import CashierSession

    ctx = build_branch_tenant(slug="mig-pos-open", branch_codes=("HODAN",))
    a = add_user(ctx, username="mig_pos_a", branches=("HODAN",))
    b = add_user(ctx, username="mig_pos_b", branches=("HODAN",))
    first = _legacy_session(ctx, a, "HODAN")
    second = _legacy_session(ctx, b, "HODAN")

    result = backfill_pos_terminals()
    again = backfill_pos_terminals()

    assert PosTerminal.objects.filter(branch=ctx.branch("HODAN")).count() == 1
    first.refresh_from_db()
    second.refresh_from_db()
    # One open shift per terminal: the oldest is attached, the other is flagged, not forced.
    assert first.terminal_id is not None and second.terminal_id is None
    assert result.review_required == 1 and again.review_required == 1
    assert CashierSession.objects.filter(status="open", terminal__isnull=False).count() == 1
    checks = checks_by_key(run_report(tenant="mig-pos-open"))
    assert checks["pos.session_terminal"]["unresolved"] == 1


def test_journal_line_branch_is_backfilled_from_its_entry_only():
    from apps.finance.models import Account, JournalEntry, JournalLine
    from apps.finance.services.chart_service import ChartService
    from apps.finance.services.journal_service import JournalService
    from apps.organization.services.backfill_service import backfill_journal_line_branch

    ctx = build_branch_tenant(slug="mig-jl", branch_codes=("HODAN",))
    owner = add_user(ctx, username="mig_jl_owner", branches=("HODAN",))
    ChartService.ensure_default_chart(tenant_id=ctx.tenant.pk)
    cash = Account.objects.get(tenant=ctx.tenant, code="1000")
    sales = Account.objects.get(tenant=ctx.tenant, code="4000")

    def entry(branch):
        return JournalService.create_entry(
            data={
                "tenant_id": ctx.tenant.pk,
                "description": "historic",
                "source_type": "invoice",
                "branch_id": branch.pk if branch else None,
                "lines": [
                    {"account_id": str(cash.pk), "debit": 10, "credit": 0},
                    {"account_id": str(sales.pk), "debit": 0, "credit": 10},
                ],
            },
            user=owner,
        )

    branched, unassigned = entry(ctx.branch("HODAN")), entry(None)
    # Simulate pre-Phase-5 rows: lines that never had a branch.
    JournalLine.objects.update(branch=None)

    result = backfill_journal_line_branch()

    assert result.resolved == 2 and result.skipped == 2
    assert {l.branch_id for l in JournalLine.objects.filter(entry=branched)} == {ctx.branch("HODAN").pk}
    assert {l.branch_id for l in JournalLine.objects.filter(entry=unassigned)} == {None}
    # The entry header is never inferred.
    assert JournalEntry.objects.get(pk=unassigned.pk).branch_id is None
    assert backfill_journal_line_branch().resolved == 0  # idempotent
    checks = checks_by_key(run_report(tenant="mig-jl"))
    assert checks["finance.line_branch"]["unresolved"] == 0


# --------------------------------------------------------------------------- #
# MIG-5 (Phase 6): AuditLog.branch is forward-only
# --------------------------------------------------------------------------- #


def test_audit_branch_is_forward_only_and_never_backdated():
    from apps.audit.models import AuditLog
    from apps.audit.services.audit_write import write_audit
    from apps.organization.services.backfill_service import run_all
    from tests.helpers.branch_factory import add_owner

    ctx = build_branch_tenant(slug="mig-audit")
    owner = add_owner(ctx, username="mig_audit_owner")
    warehouse = ctx.warehouse("HODAN")

    # A historical row: written before AuditLog.branch existed, about a branch-owned entity.
    historic = AuditLog.objects.create(
        tenant=ctx.tenant, user=owner, action="update", module="inventory",
        entity_type="Warehouse", entity_id=str(warehouse.pk),
    )
    assert historic.branch_id is None

    # Every backfill and the validation report leave it alone.
    run_all()
    call_command("backfill_ledger_branch", verbosity=0)
    run_report(tenant="mig-audit")
    historic.refresh_from_db()
    assert historic.branch_id is None

    # New writes are stamped from the entity's own branch; an entity with none records none.
    write_audit(action="update", module="inventory", entity=warehouse, user=owner)
    write_audit(action="update", module="inventory", entity=owner, user=owner)
    fresh = AuditLog.objects.filter(entity_id=str(warehouse.pk)).exclude(pk=historic.pk).get()
    assert fresh.branch_id == ctx.branch("HODAN").pk
    assert AuditLog.objects.get(entity_type="User", entity_id=str(owner.pk)).branch_id is None

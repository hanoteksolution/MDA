"""B5-1..B5-4: POS terminals, registers and shifts on top of the branch model."""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied

from apps.inventory.models import Inventory, StockMovement
from apps.organization.models import CashRegister, PosTerminal, StockLocation
from apps.sales.models import CashierSession, Invoice
from apps.sales.services.cashier_session_service import (
    CashierSessionError,
    CashierSessionService,
)
from apps.sales.services.pos_service import PosService
from apps.sales.services.refund_service import RefundService
from apps.sales.services.sequence_service import DocumentSequenceService
from tests.helpers.branch_factory import (
    add_product,
    add_user,
    build_branch_tenant,
    grant,
    make_profile,
    set_inventory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="bpos-tenant", branch_codes=("HODAN", "BAKAARO"))


@pytest.fixture
def cashier(ctx):
    return add_user(ctx, username="bpos_cashier", role_slug="cashier", branches=("HODAN",))


@pytest.fixture
def manager(ctx):
    """A branch manager: holds a manager access profile in Hodan (not just an admin role)."""
    user = add_user(ctx, username="bpos_manager", role_slug="admin")
    profile = make_profile(
        tenant=ctx.tenant, code="MGR", name="Manager", codenames=["pos.access"], is_manager=True
    )
    grant(ctx, user=user, branch_code="HODAN", profile=profile, is_default=True)
    return user


@pytest.fixture
def product(ctx):
    product = add_product(ctx, sku="BPOS-1")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("50"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("50"))
    return product


def make_terminal(ctx, branch_code="HODAN", *, code="POS-1", warehouse=None, location=None,
                  with_register=True):
    branch = ctx.branch(branch_code)
    warehouse = warehouse or ctx.warehouse(branch_code)
    register = None
    if with_register:
        register = CashRegister.objects.create(
            tenant=ctx.tenant, branch=branch, code=f"REG-{code}", name=f"Register {code}"
        )
    return PosTerminal.objects.create(
        tenant=ctx.tenant,
        branch=branch,
        code=code,
        name=f"Terminal {code}",
        default_warehouse=warehouse,
        default_location=location
        or StockLocation.objects.filter(warehouse=warehouse, is_default=True).first(),
        default_cash_register=register,
    )


def sell(ctx, user, product, *, qty="2", branch_code="HODAN", key=None, **extra):
    return PosService.checkout(
        data={
            "branch_id": str(ctx.branch(branch_code).pk),
            "customer_id": "walkin",
            "waiter_name": "Counter",
            "payment_method": "cash",
            "items": [{"product_id": str(product.pk), "quantity": qty, "unit_price": "10"}],
            "idempotency_key": key,
            **extra,
        },
        user=user,
    )


def on_hand(ctx, product, branch_code):
    return Inventory.objects.get(product=product, warehouse=ctx.warehouse(branch_code)).quantity


# --------------------------------------------------------------------------- #
# B5-1: a POS sale needs terminal + register + open shift, and draws from the
#       terminal's warehouse/location
# --------------------------------------------------------------------------- #


def test_sale_on_terminal_branch_requires_an_open_shift(ctx, cashier, product):
    make_terminal(ctx)
    with pytest.raises(CashierSessionError, match="Open a shift"):
        sell(ctx, cashier, product, key="b51-noshift")
    assert on_hand(ctx, product, "HODAN") == Decimal("50")
    assert Invoice.objects.count() == 0


def test_shift_binds_terminal_register_warehouse_and_location(ctx, cashier):
    terminal = make_terminal(ctx)
    session = CashierSessionService.open_session(
        user=cashier, branch_id=ctx.branch("HODAN").pk, opening_float=100
    )
    # A single active terminal is selected automatically; nothing is left to guess.
    assert session.terminal_id == terminal.pk
    assert session.register_id == terminal.default_cash_register_id
    assert session.warehouse_id == ctx.warehouse("HODAN").pk
    assert session.location_id == terminal.default_location_id


def test_terminal_without_register_cannot_open_a_shift(ctx, cashier):
    make_terminal(ctx, with_register=False)
    with pytest.raises(CashierSessionError, match="no cash register"):
        CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)


def test_sale_deducts_from_the_terminals_warehouse_and_location(ctx, cashier, product):
    from apps.inventory.models import Warehouse
    from apps.organization.services import StockLocationService

    # The terminal sells from a *second* warehouse, not the branch default.
    shop = Warehouse.objects.create(
        tenant=ctx.tenant, branch=ctx.branch("HODAN"), name="Shop", code="WH-SHOP", is_default=False
    )
    StockLocationService.ensure_default_locations(warehouse=shop)
    floor = StockLocation.objects.get(warehouse=shop, code="FLOOR")
    Inventory.objects.create(
        tenant=ctx.tenant, product=product, warehouse=shop, quantity=Decimal("20")
    )
    terminal = make_terminal(ctx, warehouse=shop, location=floor)
    CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)

    result = sell(ctx, cashier, product, qty="3", key="b51-wh")
    invoice = Invoice.objects.get(pk=result["invoice"]["id"])

    assert invoice.terminal_id == terminal.pk and invoice.warehouse_id == shop.pk
    assert Inventory.objects.get(product=product, warehouse=shop).quantity == Decimal("17")
    assert on_hand(ctx, product, "HODAN") == Decimal("50")  # branch default untouched
    movement = StockMovement.objects.get(reference_id=invoice.pk, movement_type="sale")
    assert movement.warehouse_id == shop.pk
    assert movement.location_id == floor.pk
    assert movement.branch_id == ctx.branch("HODAN").pk


def test_refund_returns_stock_to_the_warehouse_it_left(ctx, cashier, product):
    from apps.inventory.models import Warehouse
    from apps.organization.services import StockLocationService

    shop = Warehouse.objects.create(
        tenant=ctx.tenant, branch=ctx.branch("HODAN"), name="Shop", code="WH-SHOP", is_default=False
    )
    StockLocationService.ensure_default_locations(warehouse=shop)
    Inventory.objects.create(tenant=ctx.tenant, product=product, warehouse=shop, quantity=Decimal("20"))
    make_terminal(ctx, warehouse=shop)
    session = CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    invoice_id = sell(ctx, cashier, product, qty="4", key="b51-refund")["invoice"]["id"]

    RefundService.refund_invoice(
        invoice_id=invoice_id,
        items=[{"product_id": str(product.pk), "quantity": "4"}],
        reason="test",
        user=cashier,
        cashier_session_id=str(session.pk),
    )
    assert Inventory.objects.get(product=product, warehouse=shop).quantity == Decimal("20")
    assert on_hand(ctx, product, "HODAN") == Decimal("50")


def test_shift_of_another_branch_cannot_be_used_to_sell(ctx, product):
    both = add_user(ctx, username="bpos_both", role_slug="cashier", branches=("HODAN", "BAKAARO"))
    make_terminal(ctx, "HODAN")
    session = CashierSessionService.open_session(user=both, branch_id=ctx.branch("HODAN").pk)
    with pytest.raises(CashierSessionError, match="another branch"):
        sell(ctx, both, product, branch_code="BAKAARO", key="b51-xbranch", cashier_session_id=str(session.pk))


def test_branch_without_a_terminal_keeps_legacy_behaviour(ctx, cashier, product):
    """Additive: nothing is enforced until an operator creates a terminal."""
    result = sell(ctx, cashier, product, qty="2", key="b51-legacy")
    invoice = Invoice.objects.get(pk=result["invoice"]["id"])
    assert invoice.terminal_id is None and invoice.warehouse_id is None
    assert on_hand(ctx, product, "HODAN") == Decimal("48")


# --------------------------------------------------------------------------- #
# B5-2: no shift on a terminal of a branch the user cannot access
# --------------------------------------------------------------------------- #


def test_cannot_open_a_shift_on_a_terminal_of_an_inaccessible_branch(ctx, cashier):
    foreign = make_terminal(ctx, "BAKAARO")  # cashier only holds HODAN
    with pytest.raises(PermissionDenied):
        CashierSessionService.open_session(user=cashier, terminal_id=foreign.pk)
    assert CashierSession.objects.count() == 0


def test_terminal_must_match_the_selected_branch(ctx, manager):
    foreign = make_terminal(ctx, "BAKAARO")
    with pytest.raises(CashierSessionError, match="does not belong"):
        CashierSessionService.open_session(
            user=manager, branch_id=ctx.branch("HODAN").pk, terminal_id=foreign.pk
        )


def test_another_tenants_terminal_is_not_found(ctx, manager):
    other = build_branch_tenant(slug="bpos-other", branch_codes=("HODAN",))
    foreign = make_terminal(other, "HODAN")
    with pytest.raises(CashierSessionError, match="Terminal not found"):
        CashierSessionService.open_session(user=manager, terminal_id=foreign.pk)


def test_a_terminal_carries_one_open_shift_at_a_time(ctx, cashier):
    other = add_user(ctx, username="bpos_cashier2", role_slug="cashier", branches=("HODAN",))
    make_terminal(ctx)
    CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    with pytest.raises(CashierSessionError, match="already has an open shift"):
        CashierSessionService.open_session(user=other, branch_id=ctx.branch("HODAN").pk)


# --------------------------------------------------------------------------- #
# B5-3: shift close — expected vs counted, variance, re-close rejected
# --------------------------------------------------------------------------- #


def test_close_records_expected_counted_and_variance(ctx, cashier, product):
    make_terminal(ctx)
    session = CashierSessionService.open_session(
        user=cashier, branch_id=ctx.branch("HODAN").pk, opening_float=100
    )
    sell(ctx, cashier, product, qty="3", key="b53-sale")  # 30 cash
    CashierSessionService.record_cash_movement(
        session_id=session.pk, user=cashier, kind="out", amount=5, reason="Cleaning supplies"
    )

    closed = CashierSessionService.close_session(
        session_id=session.pk, user=cashier, closing_cash_counted=120, notes="short 5"
    )

    assert closed.expected_cash == Decimal("125.00")  # 100 + 30 - 5
    assert closed.closing_cash_counted == Decimal("120.00")
    assert closed.cash_variance == Decimal("-5.00")
    assert closed.total_sales == Decimal("30.00")
    assert closed.status == CashierSession.STATUS_CLOSED
    assert closed.variance_reason == "short 5"


def test_a_closed_shift_cannot_be_closed_again(ctx, cashier):
    make_terminal(ctx)
    session = CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    CashierSessionService.close_session(session_id=session.pk, user=cashier, closing_cash_counted=0)
    with pytest.raises(CashierSessionError, match="already closed"):
        CashierSessionService.close_session(session_id=session.pk, user=cashier, closing_cash_counted=0)


def test_terminal_shift_close_requires_a_counted_amount(ctx, cashier):
    make_terminal(ctx)
    session = CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    with pytest.raises(CashierSessionError, match="Count the drawer"):
        CashierSessionService.close_session(session_id=session.pk, user=cashier)
    assert CashierSession.objects.get(pk=session.pk).status == CashierSession.STATUS_OPEN


def test_variance_needs_a_manager_and_never_the_cashier_themselves(ctx, cashier, manager):
    make_terminal(ctx)
    session = CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    CashierSessionService.close_session(session_id=session.pk, user=cashier, closing_cash_counted=7)

    with pytest.raises(CashierSessionError, match="own variance"):
        CashierSessionService.approve_variance(session_id=session.pk, user=cashier)

    approved = CashierSessionService.approve_variance(
        session_id=session.pk, user=manager, reason="till shortage accepted"
    )
    assert approved.variance_approved_by_id == manager.pk and approved.variance_approved_at
    with pytest.raises(CashierSessionError, match="already approved"):
        CashierSessionService.approve_variance(session_id=session.pk, user=manager)


def test_shift_lifecycle_is_audited_with_its_branch(ctx, cashier):
    from apps.audit.models import AuditLog

    make_terminal(ctx)
    session = CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    CashierSessionService.close_session(session_id=session.pk, user=cashier, closing_cash_counted=0)
    events = [
        (row.new_values or {}).get("event")
        for row in AuditLog.objects.filter(module="pos", entity_id=str(session.pk))
    ]
    assert {"shift_opened", "shift_closed"} <= set(events)
    assert AuditLog.objects.filter(module="pos", branch=ctx.branch("HODAN")).count() >= 2


# --------------------------------------------------------------------------- #
# B5-4 (SQLite half): numbering is per branch. The concurrent proof runs on
# PostgreSQL in test_branch_postgresql.py.
# --------------------------------------------------------------------------- #


def test_document_sequences_are_independent_per_branch(ctx):
    a = DocumentSequenceService.allocate(branch=ctx.branch("HODAN"), kind="invoice")
    b = DocumentSequenceService.allocate(branch=ctx.branch("BAKAARO"), kind="invoice")
    a2 = DocumentSequenceService.allocate(branch=ctx.branch("HODAN"), kind="invoice")
    assert (a["serial"], b["serial"], a2["serial"]) == (1, 1, 2)
    assert len({a["number"], b["number"], a2["number"]}) == 3  # same serial, distinct numbers


# --------------------------------------------------------------------------- #
# Hold made against the branch default warehouse, checked out on a terminal
# whose warehouse is different (Phase 5 evidence gap).
# --------------------------------------------------------------------------- #


def test_hold_checkout_on_terminal_touches_only_the_terminal_warehouse(ctx, cashier, product):
    from apps.inventory.models import Warehouse
    from apps.organization.services import StockLocationService

    shop = Warehouse.objects.create(
        tenant=ctx.tenant, branch=ctx.branch("HODAN"), name="Shop", code="WH-SHOP", is_default=False
    )
    StockLocationService.ensure_default_locations(warehouse=shop)
    Inventory.objects.create(tenant=ctx.tenant, product=product, warehouse=shop, quantity=Decimal("20"))
    default_wh = ctx.warehouse("HODAN")

    # Hold first (no shift yet): reserves at the branch default warehouse.
    held = PosService.hold(
        data={
            "branch_id": str(ctx.branch("HODAN").pk),
            "customer_id": "walkin",
            "waiter_name": "Counter",
            "items": [{"product_id": str(product.pk), "quantity": "3", "unit_price": "10"}],
        },
        user=cashier,
    )
    hold_id = held["invoice"]["id"] if "invoice" in held else held["id"]
    default_inv = Inventory.objects.get(product=product, warehouse=default_wh)
    assert default_inv.reserved_quantity == Decimal("3")

    # Terminal sells from the *shop* warehouse; check the hold out there.
    make_terminal(ctx, warehouse=shop)
    CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    result = sell(ctx, cashier, product, qty="3", key="hold-co", hold_invoice_id=hold_id)
    invoice = Invoice.objects.get(pk=result["invoice"]["id"])
    assert str(invoice.pk) == str(hold_id) and invoice.warehouse_id == shop.pk

    default_inv.refresh_from_db()
    shop_inv = Inventory.objects.get(product=product, warehouse=shop)
    assert (default_inv.quantity, default_inv.reserved_quantity) == (Decimal("50"), Decimal("0"))
    assert (shop_inv.quantity, shop_inv.reserved_quantity) == (Decimal("17"), Decimal("0"))
    sales = StockMovement.objects.filter(reference_id=invoice.pk, movement_type="sale")
    assert {m.warehouse_id for m in sales} == {shop.pk}

    # Refund restores to the shop only.
    RefundService.refund_invoice(
        invoice_id=str(invoice.pk),
        items=[{"product_id": str(product.pk), "quantity": "3"}],
        reason="test",
        user=cashier,
        cashier_session_id=str(CashierSession.objects.get(cashier=cashier).pk),
    )
    default_inv.refresh_from_db()
    shop_inv.refresh_from_db()
    assert (default_inv.quantity, default_inv.reserved_quantity) == (Decimal("50"), Decimal("0"))
    assert shop_inv.quantity == Decimal("20")

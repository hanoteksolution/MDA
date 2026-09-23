"""B3-1 .. B3-5, B3-9: the ledger records every on-hand change, correctly and once,
with a branch and a location, and the on-hand/available invariants always hold.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.inventory.models import Inventory, InventoryTransaction, StockMovement
from apps.inventory.services.inventory_service import InventoryService
from tests.helpers.branch_factory import (
    add_owner,
    add_product,
    build_branch_tenant,
    set_inventory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="ledger-tenant")


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="ledger_owner")


@pytest.fixture
def product(ctx):
    return add_product(ctx, sku="LEDGER-1", minimum_stock=5)


def movements_for(product, warehouse):
    return StockMovement.objects.filter(product=product, warehouse=warehouse).order_by("created_at")


# --------------------------------------------------------------------------- #
# B3-1: every on-hand change writes a StockMovement carrying branch + location
# --------------------------------------------------------------------------- #


def test_sale_writes_a_movement_with_branch_and_location(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("20"))

    InventoryService.apply_sale_delta(
        product=product, warehouse=warehouse, quantity_delta=Decimal("-3"), user=owner
    )

    movement = movements_for(product, warehouse).latest("created_at")
    assert movement.movement_type == "sale"
    assert movement.quantity == Decimal("-3")
    assert movement.branch_id == ctx.branch("HODAN").pk
    assert movement.location_id is not None
    assert movement.performed_by_id == owner.pk


def test_receipt_writes_a_movement_with_branch_and_location(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    InventoryService.record_opening_balance(
        product=product, warehouse=warehouse, quantity=Decimal("10"), user=owner
    )
    movement = movements_for(product, warehouse).latest("created_at")
    assert movement.movement_type == "opening_balance"
    assert movement.branch_id == ctx.branch("HODAN").pk
    assert movement.location_id is not None


def test_damage_and_write_off_write_distinct_movement_types(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("20"))

    InventoryService.damage_stock(product=product, warehouse=warehouse, quantity=Decimal("2"), user=owner)
    InventoryService.write_off_stock(
        product=product, warehouse=warehouse, quantity=Decimal("2"), source="damaged", user=owner
    )

    types = list(movements_for(product, warehouse).values_list("movement_type", flat=True))
    assert "damage" in types
    assert "write_off" in types
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("18")  # 20 - 2 damaged
    assert inv.damaged_quantity == Decimal("0")  # 2 damaged, then written off


def test_purchase_return_writes_a_distinct_movement_type(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    InventoryService.receive_purchase_return(
        product=product, warehouse=warehouse, quantity=Decimal("4"), user=owner
    )
    movement = movements_for(product, warehouse).latest("created_at")
    assert movement.movement_type == "purchase_return"
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("6")


def test_purchase_return_cannot_remove_stock_that_is_not_there(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("2"))
    with pytest.raises(ValueError):
        InventoryService.receive_purchase_return(
            product=product, warehouse=warehouse, quantity=Decimal("5"), user=owner
        )


def test_reservation_alone_does_not_write_a_movement_but_does_write_a_transaction(ctx, owner, product):
    """A reservation doesn't move physical stock — only reserved_quantity changes.
    InventoryTransaction (the balance audit) is unconditional; StockMovement (a
    business event log) is not written unless notes are given — pre-existing,
    unchanged behaviour."""
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    before_count = movements_for(product, warehouse).count()

    InventoryService.reserve_quantity(
        product=product, warehouse=warehouse, quantity=Decimal("3"), user=owner
    )

    assert movements_for(product, warehouse).count() == before_count
    txn = InventoryTransaction.objects.filter(
        inventory__product=product, inventory__warehouse=warehouse, transaction_type="reserve"
    ).latest("created_at")
    assert txn.branch_id == ctx.branch("HODAN").pk


# --------------------------------------------------------------------------- #
# B3-2: ledger ⇔ balance invariant
# --------------------------------------------------------------------------- #


def test_ledger_sum_matches_on_hand_after_a_mixed_sequence(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    InventoryService.record_opening_balance(
        product=product, warehouse=warehouse, quantity=Decimal("50"), user=owner
    )
    InventoryService.apply_sale_delta(
        product=product, warehouse=warehouse, quantity_delta=Decimal("-10"), user=owner
    )
    InventoryService.apply_sale_delta(
        product=product, warehouse=warehouse, quantity_delta=Decimal("5"), user=owner  # a return
    )
    InventoryService.damage_stock(product=product, warehouse=warehouse, quantity=Decimal("3"), user=owner)

    total = sum(
        (m.quantity for m in movements_for(product, warehouse)), Decimal("0")
    )
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert total == inv.quantity == Decimal("42")  # 50 - 10 + 5 - 3


def test_ledger_records_the_clamped_delta_not_the_requested_one(ctx, owner, product):
    """apply_sale_delta clamps on-hand at zero (pre-existing policy). The movement
    must record what actually happened, or B3-2's invariant would break."""
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))

    InventoryService.apply_sale_delta(
        product=product, warehouse=warehouse, quantity_delta=Decimal("-20"), user=owner
    )

    movement = movements_for(product, warehouse).latest("created_at")
    assert movement.quantity == Decimal("-5")  # clamped, not -20
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("0")


# --------------------------------------------------------------------------- #
# B3-3: append-only — no update/delete of a posted movement
# --------------------------------------------------------------------------- #


def test_wrong_movement_is_corrected_by_a_new_reversing_movement(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))

    InventoryService.apply_sale_delta(
        product=product, warehouse=warehouse, quantity_delta=Decimal("-4"), user=owner,
        reference_id=None,
    )
    original = movements_for(product, warehouse).latest("created_at")

    # Correct it: a new return movement referencing the original, not an edit.
    InventoryService.apply_sale_delta(
        product=product,
        warehouse=warehouse,
        quantity_delta=Decimal("4"),
        reference_type="movement_reversal",
        reference_id=original.id,
        user=owner,
        notes="correcting a mis-scanned sale",
    )

    original.refresh_from_db()
    assert original.quantity == Decimal("-4")  # untouched
    reversal = movements_for(product, warehouse).latest("created_at")
    assert reversal.pk != original.pk
    assert reversal.reference_type == "movement_reversal"
    assert reversal.reference_id == original.id


# --------------------------------------------------------------------------- #
# B3-4: on-hand never goes negative
# --------------------------------------------------------------------------- #


def test_sale_clamps_at_zero_never_negative(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("3"))
    InventoryService.apply_sale_delta(
        product=product, warehouse=warehouse, quantity_delta=Decimal("-100"), user=owner
    )
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("0")


def test_damage_cannot_exceed_on_hand(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("2"))
    with pytest.raises(ValueError):
        InventoryService.damage_stock(product=product, warehouse=warehouse, quantity=Decimal("5"), user=owner)


def test_write_off_cannot_exceed_damaged_quantity(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    inv = set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    inv.damaged_quantity = Decimal("1")
    inv.save(update_fields=["damaged_quantity"])
    with pytest.raises(ValueError):
        InventoryService.write_off_stock(
            product=product, warehouse=warehouse, quantity=Decimal("5"), source="damaged", user=owner
        )


def test_move_stock_rejects_moving_more_than_available(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))
    with pytest.raises(ValueError):
        InventoryService.move_stock(
            product=product,
            source_warehouse=ctx.warehouse("HODAN"),
            destination_warehouse=ctx.warehouse("BAKAARO"),
            quantity=Decimal("10"),
            user=owner,
        )


def test_opening_balance_refuses_a_second_call(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    InventoryService.record_opening_balance(
        product=product, warehouse=warehouse, quantity=Decimal("10"), user=owner
    )
    with pytest.raises(ValueError):
        InventoryService.record_opening_balance(
            product=product, warehouse=warehouse, quantity=Decimal("5"), user=owner
        )


# --------------------------------------------------------------------------- #
# B3-5: available = on_hand - reserved, across reserve/unreserve/consume cycles
# --------------------------------------------------------------------------- #


def test_available_after_reserve_unreserve_consume_cycle(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))

    InventoryService.reserve_quantity(product=product, warehouse=warehouse, quantity=Decimal("4"), user=owner)
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.available_quantity == Decimal("6")

    InventoryService.unreserve_quantity(product=product, warehouse=warehouse, quantity=Decimal("1"), user=owner)
    inv.refresh_from_db()
    assert inv.available_quantity == Decimal("7")  # 10 - 3

    InventoryService.consume_reserved(product=product, warehouse=warehouse, quantity=Decimal("3"), user=owner)
    inv.refresh_from_db()
    assert inv.quantity == Decimal("7")
    assert inv.reserved_quantity == Decimal("0")
    assert inv.available_quantity == Decimal("7")


def test_reserve_rejects_exceeding_available_by_default(ctx, owner, product):
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))
    with pytest.raises(ValueError):
        InventoryService.reserve_quantity(
            product=product, warehouse=warehouse, quantity=Decimal("6"), user=owner
        )


def test_move_stock_moves_available_correctly_between_warehouses(ctx, owner, product):
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("20"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("5"))

    InventoryService.move_stock(
        product=product,
        source_warehouse=ctx.warehouse("HODAN"),
        destination_warehouse=ctx.warehouse("BAKAARO"),
        quantity=Decimal("8"),
        user=owner,
    )

    hodan = Inventory.objects.get(product=product, warehouse=ctx.warehouse("HODAN"))
    bakaaro = Inventory.objects.get(product=product, warehouse=ctx.warehouse("BAKAARO"))
    assert hodan.quantity == Decimal("12")
    assert bakaaro.quantity == Decimal("13")

    move_out = StockMovement.objects.filter(
        product=product, warehouse=ctx.warehouse("HODAN"), movement_type="warehouse_move"
    ).latest("created_at")
    assert move_out.destination_warehouse_id == ctx.warehouse("BAKAARO").pk
    assert move_out.quantity == Decimal("-8")
    # warehouse_move is never confused with the branch-transfer names.
    assert move_out.movement_type not in ("transfer_in", "transfer_out")


# --------------------------------------------------------------------------- #
# D2: the balance key is unchanged (second line of defence, Phase 2 asserted this too)
# --------------------------------------------------------------------------- #


def test_inventory_balance_key_still_product_warehouse_only():
    unique = [tuple(u) for u in Inventory._meta.unique_together]
    assert ("product", "warehouse") in unique
    assert not any(f.name == "location" for f in Inventory._meta.get_fields())
    assert not any(f.name == "branch" for f in Inventory._meta.get_fields())


def test_no_competing_authoritative_stock_field_exists():
    from apps.products.models import Product
    from apps.settings_app.models import Branch

    assert not any(f.name == "quantity" for f in Product._meta.get_fields())
    assert not any(f.name == "stock_quantity" for f in Branch._meta.get_fields())


# --------------------------------------------------------------------------- #
# B3-9: movement type vocabulary — new types are distinct, no duplicates
# --------------------------------------------------------------------------- #


def test_new_movement_types_are_registered_and_distinct():
    codes = {c[0] for c in StockMovement.MOVEMENT_TYPES}
    assert {
        "purchase_return",
        "warehouse_move",
        "damage",
        "write_off",
        "opening_balance",
    } <= codes
    assert len(codes) == len(StockMovement.MOVEMENT_TYPES)  # no duplicate values

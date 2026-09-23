"""B2-12: warehouse ownership is unambiguous and every warehouse has a location."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Warehouse
from apps.organization.models import CashRegister, OrgStatus, PosTerminal, StockLocation
from apps.organization.services import (
    CashRegisterService,
    PosTerminalService,
    StockLocationService,
    validate_warehouse_branch,
)
from tests.helpers.branch_factory import add_owner, build_branch_tenant

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="loc-tenant")


def test_every_warehouse_gets_a_default_location(ctx):
    for code in ctx.branches:
        warehouse = ctx.warehouse(code)
        defaults = StockLocation.active_objects().filter(warehouse=warehouse, is_default=True)
        assert defaults.count() == 1
        assert defaults.first().code == "MAIN"


def test_default_location_seeding_is_idempotent(ctx):
    warehouse = ctx.warehouse("HODAN")
    before = StockLocation.active_objects().filter(warehouse=warehouse).count()
    StockLocationService.ensure_default_locations(warehouse=warehouse)
    StockLocationService.ensure_default_locations(warehouse=warehouse)
    assert StockLocation.active_objects().filter(warehouse=warehouse).count() == before


def test_warehouse_belongs_to_exactly_one_branch(ctx):
    warehouse = ctx.warehouse("HODAN")
    assert warehouse.branch_id == ctx.branch("HODAN").pk
    assert validate_warehouse_branch(warehouse) is True


def test_warehouse_and_branch_must_share_a_tenant(ctx):
    """The warehouse rule: cross-tenant references are rejected, not inferred."""
    other = build_branch_tenant(slug="loc-other", branch_codes=("REMOTE",))
    stray = Warehouse(
        tenant=ctx.tenant, branch=other.branch("REMOTE"), name="Stray", code="WH-STRAY"
    )
    with pytest.raises(ValidationError):
        validate_warehouse_branch(stray)


def test_location_code_is_unique_per_warehouse(ctx):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            StockLocation.objects.create(
                tenant=ctx.tenant, warehouse=ctx.warehouse("HODAN"), code="MAIN", name="Clash"
            )


def test_same_location_code_in_two_warehouses_is_allowed(ctx):
    hodan = StockLocation.active_objects().get(warehouse=ctx.warehouse("HODAN"), code="MAIN")
    bakaaro = StockLocation.active_objects().get(warehouse=ctx.warehouse("BAKAARO"), code="MAIN")
    assert hodan.pk != bakaaro.pk


def test_location_types_cover_the_agreed_set(ctx):
    codes = {t[0] for t in StockLocation.TYPE_CHOICES}
    assert {
        "STORAGE",
        "SHOP_FLOOR",
        "RECEIVING",
        "DISPATCH",
        "DAMAGED",
        "RETURN",
        "OTHER",
    } <= codes


def test_damaged_and_transit_locations_are_not_sellable(ctx):
    damaged = StockLocation.active_objects().get(warehouse=ctx.warehouse("HODAN"), code="DAMAGED")
    assert damaged.is_sellable is False
    assert damaged.location_type == StockLocation.TYPE_DAMAGED


def test_location_hierarchy_supports_future_bin_level_stock(ctx):
    """D2: locations nest so per-bin balances can be added without a redesign."""
    warehouse = ctx.warehouse("HODAN")
    parent = StockLocation.active_objects().get(warehouse=warehouse, code="MAIN")
    shelf = StockLocation.objects.create(
        tenant=ctx.tenant, warehouse=warehouse, parent=parent, code="A-01", name="Aisle A Shelf 1"
    )
    assert shelf.parent_id == parent.pk
    assert list(parent.children.all()) == [shelf]


def test_parent_location_must_be_in_the_same_warehouse(ctx):
    foreign_parent = StockLocation.active_objects().get(
        warehouse=ctx.warehouse("BAKAARO"), code="MAIN"
    )
    bad = StockLocation(
        tenant=ctx.tenant,
        warehouse=ctx.warehouse("HODAN"),
        parent=foreign_parent,
        code="BAD",
        name="Bad",
    )
    with pytest.raises(DjangoValidationError):
        bad.clean()


def test_inventory_balance_key_is_unchanged_by_locations(ctx):
    """D2 is load-bearing: Inventory stays keyed on (product, warehouse)."""
    from apps.inventory.models import Inventory

    unique = [tuple(u) for u in Inventory._meta.unique_together]
    assert ("product", "warehouse") in unique
    assert not any(f.name == "location" for f in Inventory._meta.get_fields())


def test_deleting_the_default_location_is_refused(ctx):
    owner = add_owner(ctx, username="loc_owner")
    default = StockLocation.active_objects().get(warehouse=ctx.warehouse("HODAN"), code="MAIN")
    with pytest.raises(ValidationError):
        StockLocationService.delete_location(location=default, actor=owner)


def test_deleting_a_location_with_children_is_refused(ctx):
    owner = add_owner(ctx, username="loc_owner_2")
    warehouse = ctx.warehouse("HODAN")
    parent = StockLocation.objects.create(
        tenant=ctx.tenant, warehouse=warehouse, code="ZONE-A", name="Zone A"
    )
    StockLocation.objects.create(
        tenant=ctx.tenant, warehouse=warehouse, parent=parent, code="ZONE-A-1", name="Bin 1"
    )
    with pytest.raises(ValidationError):
        StockLocationService.delete_location(location=parent, actor=owner)


def test_setting_a_new_default_clears_the_old_one(ctx):
    owner = add_owner(ctx, username="loc_owner_3")
    warehouse = ctx.warehouse("HODAN")
    floor = StockLocation.active_objects().get(warehouse=warehouse, code="FLOOR")
    StockLocationService.set_default(location=floor, actor=owner)
    defaults = StockLocation.active_objects().filter(warehouse=warehouse, is_default=True)
    assert [d.code for d in defaults] == ["FLOOR"]


def test_terminal_and_register_are_distinct_models_scoped_to_a_branch(ctx):
    """PosTerminal != CashRegister, and both belong to exactly one branch."""
    owner = add_owner(ctx, username="struct_owner")
    branch = ctx.branch("HODAN")
    register = CashRegisterService.create_register(
        branch=branch, data={"code": "REG-1", "name": "Main Register"}, actor=owner
    )
    terminal = PosTerminalService.create_terminal(
        branch=branch,
        data={
            "code": "POS-1",
            "name": "Front Till",
            "default_warehouse": ctx.warehouse("HODAN"),
            "default_cash_register": register,
        },
        actor=owner,
    )
    assert isinstance(register, CashRegister) and isinstance(terminal, PosTerminal)
    assert terminal.branch_id == branch.pk == register.branch_id
    assert terminal.default_cash_register_id == register.pk
    assert register.cash_account_id is None  # never guessed by migration
    assert terminal.status == OrgStatus.ACTIVE


def test_terminal_cannot_point_at_another_branches_warehouse(ctx):
    owner = add_owner(ctx, username="struct_owner_2")
    with pytest.raises(DjangoValidationError):
        PosTerminalService.create_terminal(
            branch=ctx.branch("HODAN"),
            data={
                "code": "POS-X",
                "name": "Wrong warehouse",
                "default_warehouse": ctx.warehouse("BAKAARO"),
            },
            actor=owner,
        )


def test_terminal_cannot_point_at_another_branches_register(ctx):
    owner = add_owner(ctx, username="struct_owner_3")
    foreign_register = CashRegisterService.create_register(
        branch=ctx.branch("BAKAARO"), data={"code": "REG-B", "name": "Bakaaro"}, actor=owner
    )
    with pytest.raises(DjangoValidationError):
        PosTerminalService.create_terminal(
            branch=ctx.branch("HODAN"),
            data={"code": "POS-Y", "name": "Wrong register", "default_cash_register": foreign_register},
            actor=owner,
        )


def test_register_code_is_unique_per_branch(ctx):
    owner = add_owner(ctx, username="struct_owner_4")
    CashRegisterService.create_register(
        branch=ctx.branch("HODAN"), data={"code": "REG-1", "name": "First"}, actor=owner
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CashRegister.objects.create(
                tenant=ctx.tenant, branch=ctx.branch("HODAN"), code="REG-1", name="Clash"
            )

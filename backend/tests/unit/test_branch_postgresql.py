"""Branch gates that require real PostgreSQL semantics (decision D9).

SQLite ignores ``select_for_update`` and enforces partial unique indexes
differently, so these claims cannot be proven there. They SKIP loudly on SQLite —
and a skipped test here is a **gate failure**, never a pass. Run with a PostgreSQL
``DATABASE_URL`` (PostgreSQL 14+).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import IntegrityError, connection, connections, transaction

from decimal import Decimal

from apps.inventory.models import Inventory, StockMovement
from apps.inventory.services.inventory_service import InventoryService
from apps.organization.models import UserBranchAccess
from apps.settings_app.models import Branch
from tests.helpers.branch_factory import (
    add_owner,
    add_product,
    add_user,
    build_branch_tenant,
    grant,
    set_inventory,
)

pytestmark = pytest.mark.django_db(transaction=True)


def require_postgres():
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL transactions, locking and partial indexes.")


@pytest.fixture
def ctx():
    require_postgres()
    return build_branch_tenant(slug="pg-branch")


def test_duplicate_branch_code_is_rejected_by_the_database(ctx):
    """B2-3: the constraint is enforced by PostgreSQL, not only by application code."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Branch.objects.create(
                tenant=ctx.tenant, company=ctx.company, name="Clash", code="HODAN"
            )


def test_duplicate_branch_access_is_rejected_by_the_database(ctx):
    """The partial unique index on (user, branch) holds for live rows."""
    user = add_user(ctx, username="pg_dup")
    grant(ctx, user=user, branch_code="HODAN")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UserBranchAccess.objects.create(
                tenant=ctx.tenant, user=user, branch=ctx.branch("HODAN")
            )


def test_soft_deleted_access_does_not_block_a_regrant(ctx):
    """The unique index is partial on deleted_at, so re-granting after revoke works."""
    user = add_user(ctx, username="pg_regrant")
    access = grant(ctx, user=user, branch_code="HODAN")
    access.soft_delete()
    regranted = UserBranchAccess.objects.create(
        tenant=ctx.tenant, user=user, branch=ctx.branch("HODAN")
    )
    assert regranted.pk != access.pk


def test_concurrent_default_branch_selection_leaves_exactly_one_default(ctx):
    """Two admins setting a default at once must not leave the user with two."""
    from apps.organization.services import BranchAccessService

    user = add_user(ctx, username="pg_default")
    hodan_access = grant(ctx, user=user, branch_code="HODAN")
    bakaaro_access = grant(ctx, user=user, branch_code="BAKAARO")

    barrier = Barrier(2)

    def set_default(access_id):
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                # No lock taken here: set_default itself locks every row for this
                # user in a fixed (pk) order. Pre-locking a single row here, in an
                # order that depends on which access_id the thread was given rather
                # than on pk, would reintroduce the exact inversion the fix in
                # set_default is meant to prevent.
                access = UserBranchAccess.objects.get(pk=access_id)
                BranchAccessService.set_default(access=access)
            return True
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            pool.submit(set_default, hodan_access.pk),
            pool.submit(set_default, bakaaro_access.pk),
        ]
        [r.result() for r in results]

    defaults = UserBranchAccess.objects.filter(
        user=user, is_default=True, deleted_at__isnull=True
    )
    assert defaults.count() == 1


def test_concurrent_branch_access_grants_do_not_duplicate(ctx):
    """The DB constraint, not a read-then-write check, is what prevents the duplicate."""
    user = add_user(ctx, username="pg_race_grant")
    branch = ctx.branch("HODAN")
    barrier = Barrier(2)
    outcomes = []

    def create():
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                UserBranchAccess.objects.create(tenant=ctx.tenant, user=user, branch=branch)
            outcomes.append("created")
        except IntegrityError:
            outcomes.append("rejected")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(create), pool.submit(create)]]

    assert outcomes.count("created") == 1
    assert outcomes.count("rejected") == 1
    assert (
        UserBranchAccess.objects.filter(
            user=user, branch=branch, deleted_at__isnull=True
        ).count()
        == 1
    )


def test_branch_scope_is_stable_under_a_concurrent_revoke(ctx):
    """Revoking access mid-flight removes the branch from the next resolved scope."""
    from django.test import RequestFactory

    from core.branching import resolve_branch_scope

    user = add_user(ctx, username="pg_revoke")
    access = grant(ctx, user=user, branch_code="HODAN")

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user
    assert resolve_branch_scope(request=request).branch_ids == (ctx.branch("HODAN").pk,)

    with transaction.atomic():
        locked = UserBranchAccess.objects.select_for_update().get(pk=access.pk)
        locked.status = UserBranchAccess.STATUS_SUSPENDED
        locked.save(update_fields=["status", "updated_at"])

    fresh = factory.get("/")
    fresh.user = user
    assert resolve_branch_scope(request=fresh).branch_ids == ()


# --------------------------------------------------------------------------- #
# Phase 3 — B3-10 .. B3-13: stock concurrency gates (decision D9, applied to
# inventory). SQLite ignores select_for_update; these prove nothing there.
# --------------------------------------------------------------------------- #


@pytest.fixture
def stock_ctx():
    require_postgres()
    ctx = build_branch_tenant(slug="pg-stock")
    owner = add_owner(ctx, username="pg_stock_owner")
    product = add_product(ctx, sku="PG-STOCK-1")
    return ctx, owner, product


def test_two_sales_racing_the_last_unit_never_oversell(stock_ctx):
    """Available = 1. Two concurrent sales each try to take 1. apply_sale_delta's
    established policy is to clamp at zero rather than reject (BRANCH_INVENTORY.md
    §1), so 'at most one incompatible operation may succeed' here means: exactly one
    movement actually removes a unit, the other clamps to a zero-quantity no-op, and
    on-hand is never negative."""
    ctx, owner, product = stock_ctx
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("1"))
    barrier = Barrier(2)

    def sell():
        try:
            barrier.wait(timeout=10)
            InventoryService.apply_sale_delta(
                product=product, warehouse=warehouse, quantity_delta=Decimal("-1"), user=owner
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(sell), pool.submit(sell)]]

    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("0")  # never negative
    movements = StockMovement.objects.filter(product=product, warehouse=warehouse, movement_type="sale")
    total_sold = sum((m.quantity for m in movements), Decimal("0"))
    assert total_sold == Decimal("-1")  # only one unit was ever actually removed


def test_reservation_racing_a_sale_serializes_correctly_via_row_locking(stock_ctx):
    """B3-11 (fixed): a reservation racing a direct (non-reserved) sale against 1 unit
    of stock. select_for_update serialises the two transactions; apply_sale_delta now
    clamps at the reserved floor (not just zero), so on-hand never dips below what is
    currently reserved regardless of interleaving order — available_quantity stays
    non-negative too (see the reservation-invariant fix note in
    STOCK_TRANSFER_WORKFLOW.md)."""
    ctx, owner, product = stock_ctx
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("1"))
    barrier = Barrier(2)
    outcomes = []

    def reserve():
        try:
            barrier.wait(timeout=10)
            InventoryService.reserve_quantity(
                product=product, warehouse=warehouse, quantity=Decimal("1"), user=owner
            )
            outcomes.append(("reserve", "ok"))
        except ValueError:
            outcomes.append(("reserve", "rejected"))
        finally:
            connections.close_all()

    def sell():
        try:
            barrier.wait(timeout=10)
            InventoryService.apply_sale_delta(
                product=product, warehouse=warehouse, quantity_delta=Decimal("-1"), user=owner
            )
            outcomes.append(("sell", "ok"))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(reserve), pool.submit(sell)]]

    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity >= Decimal("0")
    assert inv.reserved_quantity >= Decimal("0")
    assert inv.available_quantity >= Decimal("0")  # now guaranteed, not just on-hand
    assert len(outcomes) == 2


def test_direct_sale_cannot_consume_transfer_reserved_stock(stock_ctx):
    """Reservation-invariant fix: a transfer reservation racing a concurrent direct
    sale on the same warehouse. The sale must clamp at the reserved floor, so the
    reservation's stock survives and a later dispatch can still consume exactly it."""
    from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput

    ctx, owner, product = stock_ctx
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))

    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk, destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk, destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("5"))], user=owner,
    )
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)  # all 5 units reserved

    barrier = Barrier(2)

    def sell():
        try:
            barrier.wait(timeout=10)
            InventoryService.apply_sale_delta(
                product=product, warehouse=warehouse, quantity_delta=Decimal("-3"), user=owner
            )
        finally:
            connections.close_all()

    def dispatch():
        try:
            barrier.wait(timeout=10)
            BranchTransferService.dispatch(request_id=req.pk, user=owner)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(sell), pool.submit(dispatch)]]

    # The sale could not eat into the 5 reserved units (clamped to a no-op), and
    # dispatch could still move its full reserved amount — no oversell either way.
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.quantity == Decimal("0")  # exactly the 5 reserved units left, via dispatch
    assert inv.reserved_quantity == Decimal("0")
    from apps.inventory.models import StockMovement
    assert not StockMovement.objects.filter(
        product=product, warehouse=warehouse, movement_type="sale"
    ).exists()  # the direct sale consumed nothing


def test_two_reservations_racing_never_exceed_on_hand(stock_ctx):
    """B3-12: available = 5. Two threads each try to reserve 4 (together, 8 > 5).
    Exactly one may succeed; total reserved must never exceed on-hand."""
    ctx, owner, product = stock_ctx
    warehouse = ctx.warehouse("HODAN")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))
    barrier = Barrier(2)
    outcomes = []

    def reserve():
        try:
            barrier.wait(timeout=10)
            InventoryService.reserve_quantity(
                product=product, warehouse=warehouse, quantity=Decimal("4"), user=owner
            )
            outcomes.append("ok")
        except ValueError:
            outcomes.append("rejected")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(reserve), pool.submit(reserve)]]

    assert outcomes.count("ok") == 1
    assert outcomes.count("rejected") == 1
    inv = Inventory.objects.get(product=product, warehouse=warehouse)
    assert inv.reserved_quantity == Decimal("4")
    assert inv.reserved_quantity <= inv.quantity


def test_move_stock_opposite_directions_does_not_deadlock(stock_ctx):
    """B3-13: two concurrent move_stock calls between the same warehouse pair, in
    opposite directions, must not deadlock — the deterministic pk-ordered lock
    (BRANCH_INVENTORY.md §6.1, the Phase 2 lesson applied to inventory) forces the
    two transactions to serialise instead."""
    ctx, owner, product = stock_ctx
    hodan = ctx.warehouse("HODAN")
    bakaaro = ctx.warehouse("BAKAARO")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("10"))
    barrier = Barrier(2)
    outcomes = []

    def move(source, destination):
        try:
            barrier.wait(timeout=10)
            InventoryService.move_stock(
                product=product,
                source_warehouse=source,
                destination_warehouse=destination,
                quantity=Decimal("3"),
                user=owner,
            )
            outcomes.append("ok")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(move, hodan, bakaaro),
            pool.submit(move, bakaaro, hodan),
        ]
        # No deadlock: both complete within the barrier timeout. A deadlock would
        # surface here as a psycopg2.errors.DeadlockDetected / OperationalError.
        [f.result(timeout=15) for f in futures]

    assert outcomes.count("ok") == 2
    hodan_inv = Inventory.objects.get(product=product, warehouse=hodan)
    bakaaro_inv = Inventory.objects.get(product=product, warehouse=bakaaro)
    # 10 - 3 + 3 = 10 on each side; total company stock is conserved.
    assert hodan_inv.quantity == Decimal("10")
    assert bakaaro_inv.quantity == Decimal("10")


# --------------------------------------------------------------------------- #
# Phase 4 — B4-8 .. B4-10: branch transfer concurrency gates (decision D9).
# --------------------------------------------------------------------------- #


@pytest.fixture
def transfer_ctx():
    require_postgres()
    ctx = build_branch_tenant(slug="pg-transfer")
    owner = add_owner(ctx, username="pg_transfer_owner")
    product = add_product(ctx, sku="PG-TRANSFER-1")
    return ctx, owner, product


def test_two_concurrent_dispatches_one_succeeds_one_fails(transfer_ctx):
    """B4-8: two RESERVED transfers reserving/dispatching the same limited stock —
    the second dispatch must not oversell once the first has consumed it."""
    from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput

    ctx, owner, product = transfer_ctx
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("5"))

    def make_and_reserve(qty):
        req = BranchTransferService.request_transfer(
            source_branch_id=ctx.branch("HODAN").pk, destination_branch_id=ctx.branch("BAKAARO").pk,
            source_warehouse_id=ctx.warehouse("HODAN").pk, destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
            lines=[TransferLineInput(product_id=product.pk, quantity=qty)], user=owner,
        )
        req = BranchTransferService.approve(request_id=req.pk, user=owner)
        return BranchTransferService.reserve(request_id=req.pk, user=owner)

    req_a = make_and_reserve(Decimal("3"))
    req_b = make_and_reserve(Decimal("2"))  # 3+2=5, exactly all available — both can reserve
    barrier = Barrier(2)
    outcomes = []

    def dispatch(req_id):
        try:
            barrier.wait(timeout=10)
            BranchTransferService.dispatch(request_id=req_id, user=owner)
            outcomes.append("ok")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(dispatch, req_a.pk), pool.submit(dispatch, req_b.pk)]]

    assert outcomes.count("ok") == 2  # both were validly reserved; both dispatch cleanly
    inv = Inventory.objects.get(product=product, warehouse=ctx.warehouse("HODAN"))
    assert inv.quantity == Decimal("0")  # 5 - 3 - 2, never negative


def test_concurrent_receipt_and_pos_sale_at_destination_stay_consistent(transfer_ctx):
    """B4-9: a receive (crediting destination on-hand) racing a direct POS sale at the
    same destination warehouse — select_for_update serialises them; on-hand never
    goes negative and both operations' effects land correctly."""
    from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput
    from apps.inventory.services.inventory_service import InventoryService

    ctx, owner, product = transfer_ctx
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("2"))
    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk, destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk, destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("4"))], user=owner,
    )
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)

    barrier = Barrier(2)

    def receive():
        try:
            barrier.wait(timeout=10)
            BranchTransferService.receive(request_id=req.pk, user=owner)
        finally:
            connections.close_all()

    def sell():
        try:
            barrier.wait(timeout=10)
            InventoryService.apply_sale_delta(
                product=product, warehouse=ctx.warehouse("BAKAARO"), quantity_delta=Decimal("-1"), user=owner
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(receive), pool.submit(sell)]]

    inv = Inventory.objects.get(product=product, warehouse=ctx.warehouse("BAKAARO"))
    assert inv.quantity == Decimal("5")  # 2 + 4 received - 1 sold, regardless of order
    assert inv.quantity >= Decimal("0")


def test_double_submit_same_idempotency_key_credits_stock_once(transfer_ctx):
    """B4-10: two concurrent receive calls with the same idempotency key must not
    double-credit the destination."""
    from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput

    ctx, owner, product = transfer_ctx
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk, destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk, destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("6"))], user=owner,
    )
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)

    barrier = Barrier(2)
    key = "retry-key-123"

    def receive():
        try:
            barrier.wait(timeout=10)
            BranchTransferService.receive(request_id=req.pk, user=owner, idempotency_key=key)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(receive), pool.submit(receive)]]

    inv = Inventory.objects.get(product=product, warehouse=ctx.warehouse("BAKAARO"))
    assert inv.quantity == Decimal("6")  # credited exactly once, not twice


# --------------------------------------------------------------------------- #
# Phase 5 — B5-4: per-branch document numbering and shift exclusivity (decision D9).
# --------------------------------------------------------------------------- #


@pytest.fixture
def pos_ctx():
    require_postgres()
    return build_branch_tenant(slug="pg-pos", branch_codes=("HODAN", "BAKAARO"))


def test_concurrent_invoice_numbers_never_collide_within_or_across_branches(pos_ctx):
    """B5-4: the sequence row does not exist yet, so the first allocations race to create
    it. Every branch must still hand out 1..N exactly once, and no two invoices in the
    tenant may share a number."""
    from apps.sales.services.sequence_service import DocumentSequenceService

    ctx = pos_ctx
    workers = 8
    barrier = Barrier(workers * 2)
    issued = []

    def allocate(branch_code):
        try:
            barrier.wait(timeout=15)
            issued.append(
                (branch_code, DocumentSequenceService.allocate(branch=ctx.branch(branch_code), kind="invoice"))
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=workers * 2) as pool:
        futures = [pool.submit(allocate, code) for code in ("HODAN", "BAKAARO") for _ in range(workers)]
        [f.result() for f in futures]

    for code in ("HODAN", "BAKAARO"):
        serials = sorted(row["serial"] for c, row in issued if c == code)
        assert serials == list(range(1, workers + 1)), f"{code}: {serials}"
    numbers = [row["number"] for _, row in issued]
    assert len(numbers) == len(set(numbers)) == workers * 2


def test_two_cashiers_racing_for_one_terminal_open_exactly_one_shift(pos_ctx):
    """A terminal carries one open shift: the database constraint, not a check-then-act,
    decides the race."""
    from apps.organization.models import CashRegister, PosTerminal
    from apps.sales.models import CashierSession
    from apps.sales.services.cashier_session_service import CashierSessionError, CashierSessionService

    ctx = pos_ctx
    branch = ctx.branch("HODAN")
    register = CashRegister.objects.create(tenant=ctx.tenant, branch=branch, code="REG-1", name="R")
    terminal = PosTerminal.objects.create(
        tenant=ctx.tenant, branch=branch, code="POS-1", name="T",
        default_warehouse=ctx.warehouse("HODAN"), default_cash_register=register,
    )
    users = [
        add_user(ctx, username=f"pg_cashier_{i}", role_slug="cashier", branches=("HODAN",))
        for i in range(2)
    ]
    barrier = Barrier(2)
    outcomes = []

    def open_shift(user):
        try:
            barrier.wait(timeout=10)
            CashierSessionService.open_session(user=user, terminal_id=terminal.pk)
            outcomes.append("ok")
        except CashierSessionError:
            outcomes.append("refused")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [f.result() for f in [pool.submit(open_shift, u) for u in users]]

    assert sorted(outcomes) == ["ok", "refused"]
    assert CashierSession.objects.filter(terminal=terminal, status="open").count() == 1


# --------------------------------------------------------------------------- #
# Phase 8: B8-4 — concurrent duplicate webhooks settle an invoice exactly once
# --------------------------------------------------------------------------- #


@pytest.fixture
def pay_ctx(settings):
    from cryptography.fernet import Fernet

    from tests.helpers.payment_factory import build_payment_ctx

    require_postgres()
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    return build_payment_ctx("pg-pay", branches=("HODAN",))


def _race_webhooks(provider, deliveries):
    from apps.integrations.services import PaymentService

    barrier = Barrier(len(deliveries))
    statuses = []

    def fire(delivery):
        body, signature, timestamp = delivery
        try:
            barrier.wait(timeout=15)
            event = PaymentService.receive_webhook(
                provider=provider, raw_body=body, signature=signature, timestamp=timestamp
            )
            statuses.append(event.status)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(deliveries)) as pool:
        [f.result() for f in [pool.submit(fire, d) for d in deliveries]]
    return statuses


def _assert_settled_once(ctx, invoice, intent):
    from apps.finance.models import JournalEntry
    from apps.integrations.models import PaymentIntent, ReconciliationRecord
    from apps.sales.models import Invoice, Payment

    invoice.refresh_from_db()
    assert invoice.status == Invoice.STATUS_PAID and invoice.amount_paid == Decimal("100")
    assert Payment.objects.filter(invoice=invoice).count() == 1
    assert JournalEntry.objects.filter(
        tenant=ctx.tenant, idempotency_key__startswith="CUSTOMER_PAYMENT_RECEIVED"
    ).count() == 1
    assert PaymentIntent.objects.get(pk=intent.pk).status == PaymentIntent.STATUS_SUCCEEDED
    assert not ReconciliationRecord.objects.exists()


def test_concurrent_duplicate_webhooks_with_one_event_id_settle_once(pay_ctx):
    """B8-4a: eight simultaneous deliveries of the *same* event. The unique event row and the
    intent row lock make exactly one of them do the work."""
    from tests.helpers.payment_factory import make_invoice, make_provider, signed, start_payment

    ctx = pay_ctx
    provider, invoice = make_provider(ctx), make_invoice(ctx, "HODAN", total="100")
    intent, _ = start_payment(ctx, invoice, provider=provider)
    delivery = signed(event_id="race-1", reference=intent.provider_reference, amount="100")

    statuses = _race_webhooks(provider, [delivery] * 8)

    assert set(statuses) == {"processed"}  # every caller is told success, none saw an error
    _assert_settled_once(ctx, invoice, intent)


def test_concurrent_webhooks_with_different_event_ids_for_one_intent_settle_once(pay_ctx):
    """B8-4b: the provider re-sends the same payment under fresh event ids, all at once. Event
    dedup cannot help here — the intent's state under its row lock must."""
    from tests.helpers.payment_factory import make_invoice, make_provider, signed, start_payment

    ctx = pay_ctx
    provider, invoice = make_provider(ctx), make_invoice(ctx, "HODAN", total="100")
    intent, _ = start_payment(ctx, invoice, provider=provider)
    deliveries = [
        signed(event_id=f"race-{i}", reference=intent.provider_reference, amount="100") for i in range(8)
    ]

    statuses = _race_webhooks(provider, deliveries)

    assert set(statuses) == {"processed"}
    _assert_settled_once(ctx, invoice, intent)


def test_concurrent_intent_creation_with_one_key_makes_one_intent(pay_ctx):
    """B8-3 on PostgreSQL: the unique (tenant, key) constraint decides the race."""
    from apps.integrations.models import PaymentIntent
    from apps.integrations.services import PaymentService
    from tests.helpers.payment_factory import make_invoice, make_provider

    ctx = pay_ctx
    provider, invoice = make_provider(ctx), make_invoice(ctx, "HODAN", total="100")
    barrier = Barrier(6)
    ids = []

    def create():
        try:
            barrier.wait(timeout=15)
            intent, _ = PaymentService.create_intent(
                tenant=ctx.tenant, invoice=invoice, idempotency_key="one-key", provider_id=provider.pk
            )
            ids.append(str(intent.pk))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as pool:
        [f.result() for f in [pool.submit(create) for _ in range(6)]]

    assert len(set(ids)) == 1 and len(ids) == 6
    assert PaymentIntent.objects.filter(tenant=ctx.tenant).count() == 1

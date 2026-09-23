# Branch Inventory — Phase 3

Companion to `MULTI_BRANCH_ARCHITECTURE.md`, `BRANCH_MIGRATION_PLAN.md`, `BRANCH_TEST_MATRIX.md` and
`BRANCH_AUTHORIZATION.md`. Written **before** any Phase 3 code, per the phase brief. It fixes the
inventory source of truth, the ledger design, the locking strategy, and the exact Phase 3/Phase 4
boundary, so no later developer can reinterpret them.

## 1. What already exists (inspected before deciding anything)

`backend/apps/inventory/models/stock.py` and `services/{inventory_service,transfer_service,
receiving_service}.py`:

* **`Inventory(product, warehouse)`** — unique together, the authoritative balance. Fields:
  `quantity` (on-hand), `reserved_quantity`, `damaged_quantity`, `returned_quantity`.
  `available_quantity` is a Python property = `quantity - reserved_quantity`. **No branch field** —
  branch is reached through `warehouse.branch`.
* **`StockMovement(product, warehouse, movement_type, quantity, reference_type, reference_id,
  notes)`** — a light business-event log. Six movement types today: `adjustment`, `purchase`,
  `sale`, `transfer_in`, `transfer_out`, `return`. No branch, no location, no before/after balance.
* **`InventoryTransaction(inventory, transaction_type, quantity_before, quantity_after,
  quantity_change, reference_type, reference_id)`** — a balance-audit trail keyed to one `Inventory`
  row. Six transaction types: `in`, `out`, `reserve`, `unreserve`, `damage`, `return`. No branch, no
  location.
* **One mutation boundary already exists**: every write path (`reserve_quantity`,
  `unreserve_quantity`, `consume_reserved`, `apply_sale_delta`, `apply_invoice_quantity_deltas`,
  `create_adjustment`, `PurchaseReceivingService.receive`, `StockTransferService.confirm`) goes
  through `InventoryService._locked_inventory`, which does
  `Inventory.objects.select_for_update().filter(pk=inv.pk).first()` inside `@transaction.atomic`,
  and every mutation writes both a `StockMovement` and an `InventoryTransaction` in the same
  transaction as the balance update. This is already correct and is **extended, not replaced**.
* **Negative stock policy is already established and is two different rules depending on path**:
  * `reserve_quantity` **rejects** a reservation that would exceed `available` unless the caller
    passes `allow_negative_available=True` (used by `StockTransferService.confirm` too).
  * `apply_sale_delta` **clamps** on-hand at zero rather than rejecting — "sell 150 with 100 on
    hand → stock becomes 0, not −50," so an oversold POS sale still completes but never produces a
    negative balance. This clamping is silent (no exception), which is different from "reject"; it
    is preserved exactly as-is (§4).
* **FEFO integration**: `apply_sale_delta` and `PurchaseReceivingService.receive` already call
  `apps.pharmacy.services.batch_service.BatchService` for batch-tracked products. Not touched.
* **`InventoryAdjustment`/`StockTransfer`** already carry a `branch` FK (part of the 94 pre-existing
  FKs from Phase 1's audit) — no migration needed for those two.
* **Existing API views hard-code `request.user.branch`** (`InventoryListView`,
  `InventorySummaryView`, `LowStockView`, `OutOfStockView`, `WarehouseListCreateView`) instead of
  going through Phase 2's `core.branching`. This means a user who only holds `UserBranchAccess`
  grants (no legacy `User.branch`) — the norm for anyone provisioned after Phase 2 — sees **no**
  branch filter applied at all today. This is the concrete, in-scope integration gap Phase 3 closes.
* **Reorder threshold**: `Product.minimum_stock` (`PositiveIntegerField`, default 5) already exists
  and is already used for low-stock/out-of-stock queries. No new threshold field is introduced.

## 2. Phase 3 / Phase 4 boundary

Read against `MULTI_BRANCH_ARCHITECTURE.md` §5 and `BRANCH_TEST_MATRIX.md` §4 (Phase 4 rows are
`B4-*`), the dividing line is:

| Phase 3 (this phase) | Phase 4 (deferred, not started here) |
|---|---|
| Ledger gains `branch` + `location` dimensions | The `BranchTransferRequest` state machine (REQUESTED → APPROVED → RESERVED → DISPATCHED → IN_TRANSIT → RECEIVED → COMPLETED) |
| Branch/warehouse balance aggregation (derived, read-only) | Any workflow that actually **moves** stock between branches |
| Cross-branch **visibility** (a number) | Cross-branch **reservation or dispatch** of another branch's stock |
| `StockLocation` recorded as ledger metadata for movements that already exist | `TRANSIT` as a real, ledger-backed state with dispatched/received quantities |
| POS shows "available elsewhere" as read-only info | POS or any workflow requesting/consuming another branch's stock |
| Concurrency proof for existing single-warehouse mutation paths (sale, reservation, adjustment, receipt, same-branch transfer) | Concurrency proof for the cross-branch transfer lifecycle |
| `StockTransfer`/`StockTransferService` — **left exactly as-is** | Enforcing the D4 same-branch guard on `StockTransfer` (already planned as migration wave M3, `inventory/0009_stocktransfer_same_branch_guard`, explicitly scheduled under Phase 4 in `BRANCH_MIGRATION_PLAN.md`) |

**Concretely deferred to Phase 4, not implemented here:** `BranchTransferRequest` and friends, the
same-branch guard on `StockTransfer` (`source_branch`/`destination_branch` denormalised columns),
`ReplenishmentRule`, and any "in transit" quantity that is not simply zero. Phase 3's `in_transit`
figure in the availability API is **always 0** in this phase, computed as
`Σ dispatched − Σ received` over `BranchTransferRequest` rows per D5 — a query that returns 0 today
because no such rows exist yet. It is a real formula wired to real (currently empty) data, not a
hard-coded stub the way `Product.quantity` would be.

## 3. Inventory source of truth — restated and enforced

**D2 is preserved exactly.** The authoritative balance is `Inventory(product, warehouse)`. This
phase adds **no** competing quantity field anywhere: no `Product.quantity`, no
`Branch.stock_quantity`, no per-location balance table. `StockLocation` remains ledger metadata —
verified by an explicit test that `Inventory`'s unique-together is still exactly
`(product, warehouse)` and it has no `location` field (already asserted in
`test_branch_locations.py::test_inventory_balance_key_is_unchanged_by_locations` from Phase 2; a
duplicate assertion is added to Phase 3's suite as a second line of defence).

### 3.1 Canonical quantity semantics (binding — do not reinterpret)

| Term | Definition | Where it lives |
|---|---|---|
| **On hand** | `Inventory.quantity` — physical units recorded as present in this warehouse right now. | `Inventory.quantity` |
| **Reserved** | `Inventory.reserved_quantity` — units on hand that are promised to something (a POS hold, a pending transfer) and must not be sold to someone else. | `Inventory.reserved_quantity` |
| **Available** | `on_hand − reserved`. The only number a POS or a customer-facing "can I sell this?" check may use. | `Inventory.available_quantity` (existing property, unchanged) |
| **Damaged** | `Inventory.damaged_quantity` — units physically present but not sellable. Tracked separately; **not** subtracted from on-hand today (pre-existing behaviour, not changed by this phase — see §8 known limitation). | `Inventory.damaged_quantity` |
| **Returned** | `Inventory.returned_quantity` — a counter of units that came back through a return path. Pre-existing, informational; not a location and not subtracted elsewhere. | `Inventory.returned_quantity` |
| **In transit** | `Σ dispatched − Σ received` across `BranchTransferRequest` lines for this product, at the *company* level (not tied to one warehouse). **Always 0 in Phase 3** — no such rows exist until Phase 4. | Computed, not stored; Phase 4 concept |
| **Branch stock** | `Σ Inventory.quantity` (and, separately, `Σ available`) over every active `Warehouse` owned by that branch. **Derived, never stored** (§4). | Computed on read |

No service may invent a different formula for "available." Every new Phase 3 code path calls the one
existing `Inventory.available_quantity` property or the one new `BranchStockService` aggregation
(§4) — never a local re-derivation.

## 4. Branch stock aggregation — derived, not materialized

Branch stock is **always** `SUM` over the branch's warehouses' `Inventory` rows, computed at read
time with a single aggregate query (`Sum("quantity")`, `Sum("reserved_quantity")`,
`available = on_hand_sum − reserved_sum` computed in Python from the two sums, not summed
per-row-then-subtracted — summing the pre-computed `available_quantity` property would require
fetching every row into Python; summing the two underlying columns in SQL and subtracting once is
both correct and avoids N+1).

No second mutable "branch quantity" field is introduced. A materialized aggregate was considered and
rejected: nothing in Phase 3's traffic pattern (POS checkout, a stock detail screen, an availability
lookup) is high enough volume to need it, and a cached aggregate is one more place for `on_hand` and
"branch total" to silently disagree — exactly the "different services inventing different formulas"
failure mode the brief warns against. Revisit only if a specific tenant's query load proves this
wrong, with numbers, not in advance of evidence.

## 5. Stock ledger — extend `StockMovement`, per D3

Per D3, `StockMovement` becomes the single canonical, append-only ledger. `InventoryTransaction` is
kept exactly as it is today: a before/after audit trail tied to one `Inventory` row. **No third
table.**

### 5.1 `StockMovement` gains (migration wave M2, nullable-first)

| Field | Type | Notes |
|---|---|---|
| `branch` | FK → `settings_app.Branch`, null | Backfilled from `warehouse.branch` — a pure FK dereference, 100% resolvable, per `BRANCH_MIGRATION_PLAN.md` §4.4. |
| `location` | FK → `organization.StockLocation`, null | Set going forward by every mutation path (defaults to the warehouse's default location when the caller doesn't specify one); historical rows stay `NULL` rather than guessed. |
| `destination_warehouse` | FK → `inventory.Warehouse`, null | Only meaningful for `warehouse_move`/`branch_transfer_*`; null for a sale, purchase, or adjustment. |
| `destination_location` | FK → `organization.StockLocation`, null | Same rule as `location`, for the destination side of a move. |
| `unit_cost` | Decimal, null | Recorded when known (purchase receipt, adjustment with a cost). Not backfilled historically — cost history before this field existed is not reconstructed. |
| `performed_by` | FK → `authentication.User`, null | Distinct from `created_by` (audit-model bookkeeping) so "who performed this movement" survives independent of soft-delete/audit conventions; populated going forward from the acting user. |
| `approved_by` | FK → `authentication.User`, null | Unused in Phase 3 (no movement type here requires approval); reserved for Phase 4's transfer approval step so that phase doesn't need another migration. |
| `metadata` | JSONField, default `{}` | Free-form, structured detail (e.g. `{"location_backfilled": true}`), never a place to smuggle a secret or bypass a real column. |

`InventoryTransaction` gains **only** `branch` (null, backfilled the same way — via
`inventory.warehouse.branch`) and `location` (null). Its shape (`quantity_before/after/change` tied
to one `Inventory` row) is otherwise untouched.

### 5.2 Movement type vocabulary

Existing six types are kept unchanged (renaming them would break every existing caller and report
for no benefit). New types are **added**, not aliased, mapping the brief's requested vocabulary onto
what already exists or genuinely doesn't:

| Requested | Decision |
|---|---|
| `PURCHASE_RECEIPT` | Already covered by existing `purchase`. Not duplicated. |
| `SALE` | Already covered by existing `sale`. Not duplicated. |
| `SALE_RETURN` | Already covered by existing `return` (used for both sale returns and reversed sales today — that is pre-existing, unchanged behaviour). Not duplicated. |
| `PURCHASE_RETURN` | **New**: `purchase_return` — returning stock to a supplier is a distinct business event from a customer sale return and was not previously representable. |
| `ADJUSTMENT_IN` / `ADJUSTMENT_OUT` | Existing `adjustment` already carries a signed `quantity`, so direction is already recoverable (`quantity > 0` / `< 0`). Not split into two enum values — that would be a duplicate representation of the same fact per the brief's own rule against duplicate enum values for one business event. |
| `WAREHOUSE_MOVE` | **New**: `warehouse_move` — a same-branch, cross-warehouse move (what `StockTransferService.confirm` produces today, currently mislabelled with the branch-transfer names `transfer_in`/`transfer_out`). `StockTransferService` is **not** changed to emit this in Phase 3 (touching a working Phase-4-adjacent service is out of scope); the new type exists so Phase 3's own `move_stock()` primitive (§6) has a correct name to write, and so Phase 4 can correct `StockTransferService` later without inventing a type then. |
| `BRANCH_TRANSFER_OUT` / `BRANCH_TRANSFER_IN` | Already exist as `transfer_out`/`transfer_in`. Not renamed (would break existing reports/tests). Phase 4's cross-branch workflow reuses these names. |
| `TRANSFER_RESERVATION` / `TRANSFER_RELEASE` | Phase 4 concept (reserving stock for a pending cross-branch transfer). Not added in Phase 3 — nothing produces these events yet, and adding unused enum values invites exactly the "invented state" the brief warns against. |
| `DAMAGE` | **New**: `damage` — moving on-hand into `damaged_quantity` was previously not a `StockMovement` event at all (only the `InventoryTransaction.transaction_type="damage"` existed, with no corresponding ledger row). Added as a real, callable mutation (§6). |
| `WRITE_OFF` | **New**: `write_off` — permanent removal of damaged/expired stock, distinct from `adjustment` (which is a correction to a *count*, not a disposal of *known-bad* stock). |
| `OPENING_BALANCE` | **New**: `opening_balance` — for a warehouse's very first stock figure, distinct from `adjustment` so a report can tell "this is where the numbers started" from "someone corrected a miscount later." Not backfilled onto historical `adjustment` rows — that would be guessing intent. |

### 5.3 Immutability

Every `StockMovement`/`InventoryTransaction` row is created once and never updated after the fact
(no code path calls `.save()` on an existing ledger row's quantity fields; `BaseModel`'s soft-delete
is the only mutation, and nothing in this phase soft-deletes a ledger row). A wrong movement is
corrected with a **new, reversing movement** referencing the original via `reference_type`/
`reference_id` (`reference_type="movement_reversal"`, `reference_id=<original movement id>`) plus a
note — never an edit. This matches the existing pattern (`apply_sale_delta`'s `return` movement is
already a reversal of a `sale` movement, not an edit to it).

## 6. The mutation boundary (extended, not replaced)

`InventoryService` remains the one authoritative place stock is mutated. Phase 3 adds:

* `damage_stock(product, warehouse, quantity, ...)` — on-hand → `damaged_quantity`, writes a `DAMAGE`
  movement + `InventoryTransaction(transaction_type="damage")` (the transaction type already existed
  with no matching movement — this closes that gap).
* `write_off_stock(product, warehouse, quantity, source="damaged"|"on_hand", ...)` — permanently
  removes stock, writes `WRITE_OFF`. When `source="damaged"`, on-hand (`Inventory.quantity`) does not
  change, so the accompanying `InventoryTransaction` records `quantity_before == quantity_after`
  (its schema only tracks on-hand, not `damaged_quantity`) — the real record of the event is the
  `StockMovement` row and its `metadata={"source": "damaged"}`. Noted here rather than left implicit.
* `receive_purchase_return(...)` — supplier return, writes `PURCHASE_RETURN`, decrements on-hand
  (rejects if it would go negative — a return can never remove stock that isn't there).
* `record_opening_balance(product, warehouse, quantity, ...)` — for a warehouse with no prior
  `Inventory` row; writes `OPENING_BALANCE`; refuses if a non-zero `Inventory` row already exists
  (this is a one-time starting figure, not a correction tool — use `adjust_stock`/`create_adjustment`
  for that).
* `move_stock(product, source_warehouse, destination_warehouse, quantity, ...)` — the *same-branch*
  primitive Phase 4's cross-branch service will call for the "on receipt, credit the destination"
  half of its workflow. In Phase 3 it is used only internally (by the new tests proving the pattern)
  and is **not** wired to `StockTransferService`, per §2. It writes `WAREHOUSE_MOVE`, not
  `transfer_in`/`transfer_out`, so it is unambiguously distinguishable from a `StockTransfer`.

All new methods share `_locked_inventory`'s locking discipline and the pattern:
`select_for_update` the affected `Inventory` row(s) → validate → mutate the balance → write the
ledger row(s) → return. Every one of them is `@transaction.atomic`.

### 6.1 Deterministic lock ordering (the Phase 2 lesson, applied here)

Phase 2's `set_default` deadlock (`BRANCH_TEST_MATRIX.md` §"PostgreSQL requirement") taught a
concrete rule: **when a single logical operation must lock more than one row, lock them in a fixed,
comparable order.** `StockTransferService.confirm` already does this correctly today
(`sorted(lines, key=lambda L: str(L.product_id))`), and `move_stock` follows the same rule: when
source and destination `Inventory` rows must both be locked, they are locked in ascending order of
`Inventory.pk` (not "source then destination"), so two concurrent moves between the same warehouse
pair in opposite directions cannot each hold one lock and wait for the other's.

## 7. Cross-branch visibility

### 7.1 What it is and isn't

Cross-branch availability is **read-only**: a number, optionally per other branch, never a mutation
capability. Viewing that Main has 18 units confers no right to reserve, transfer, or touch that
stock — Phase 4 owns the workflow for actually requesting it.

### 7.2 Authorization

The brief asks to distinguish "can operate branch inventory" from "can view cross-branch
availability." A new permission codename, `inventory.cross_branch_view`, is added and granted by
default to every role that already holds `pos.access` or `inventory.view` (`admin`, `branch_manager`,
`inventory_manager`, `cashier`, `sales_staff`, `pharmacist`, `read_only`) — so a cashier who could not
previously see the inventory list *at all* (the `cashier` role has `pos.access` but not
`inventory.view`) can still see "is this available somewhere else," which is the concrete POS
scenario the brief describes, without gaining the separate, broader `inventory.view` capability.

The endpoint's class-level permission is `inventory.view` **or** `inventory.cross_branch_view`
(`HasAnyPermission`) — a plain `HasPermission("inventory.view")`, tried first, would have blocked a
cashier before their request ever reached the view, defeating the whole point of granting them the
narrower permission. The branch-scope resolution for "which branch is the caller acting in" also
passes no permission filter (`get_branch_scope(request, permission=None)`) for the same reason:
filtering by `inventory.view` would again exclude a cashier who never held it.

Whether `other_branches` is populated is decided by `has_branch_permission(user, "inventory.
cross_branch_view", branch)` — the **branch-scoped** check, not a bare `user.has_permission(...)`.
This matters: a `BranchAccessProfile` narrows every permission consistently (`core.branching`'s
central rule), including this one, so a user whose profile in *this* branch does not list
`inventory.cross_branch_view` sees only their own branch's figures even if their role holds the
permission globally elsewhere. `other_branches` is then populated by iterating the tenant's active
branches — not the caller's own accessible-branch set — because visibility is explicitly a
tenant-wide read, distinct from operate permission. A user cannot see another tenant's branches
(tenant isolation still applies); a user *can* see the availability number for a branch they hold no
`UserBranchAccess` grant for, by design, because that is the whole point of the feature.

## 8. Known limitations (stated honestly, not glossed over)

1. **`damaged_quantity` is not subtracted from `available`** in this phase — that is pre-existing
   behaviour (`available_quantity = quantity - reserved_quantity` today, unchanged). Whether damaged
   stock should reduce sellable availability is a business-policy question outside Phase 3's mandate
   to answer unilaterally; flagged for the user, not silently changed.
2. **In-transit is always 0** until Phase 4's transfer workflow exists (§2). The formula is real; the
   data isn't yet.
3. **`StockTransferService` is not updated** to use the new `branch`/`location` ledger fields or the
   `WAREHOUSE_MOVE` type in this phase, to avoid touching Phase-4-adjacent code ahead of its own
   phase. Its existing `transfer_in`/`transfer_out` movements will simply have `branch=NULL` until
   Phase 4 (or a dedicated backfill) touches them — tracked as technical debt, not a Phase 3 defect,
   since `StockTransferService` was explicitly out of scope.
4. **Cross-branch visibility is a live query**, not a cache — correct at read time, with the N+1
   risks called out in §4 mitigated by aggregation, but there is no push/subscription mechanism; a
   dashboard polls.
5. **(RESOLVED 2026-09-21 — `apply_sale_delta` now clamps deductions at the reserved floor; see `STOCK_TRANSFER_WORKFLOW.md`. Original finding kept below.) `apply_sale_delta` (the direct, no-prior-hold sale path) did not consult `reserved_quantity`**
   — confirmed by inspection: nothing in that function reads or checks the field. This is pre-existing
   behaviour, not introduced by Phase 3. Concretely, a raw sale can race an unrelated reservation on
   the same `Inventory` row and drive `available_quantity` (`on_hand − reserved`) negative, even
   though `on_hand` itself never goes negative (`apply_sale_delta`'s own clamp still holds — proven
   under real PostgreSQL by `test_reservation_racing_a_sale_serializes_correctly_via_row_locking`).
   Only the reservation-aware path (`reserve_quantity` → `consume_reserved`) keeps `available`
   non-negative under a race. Whether every sale should be routed through a reservation first (so
   `available` is always protected) is a real product decision — changing it here would be silently
   changing established business policy, which the brief explicitly forbids; it is flagged for the
   user rather than fixed unilaterally.

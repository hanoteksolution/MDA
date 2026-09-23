# Stock Transfer Workflow — Phase 4

Companion to `BRANCH_INVENTORY.md` §2 (Phase 3/4 boundary) and §6 (`move_stock` primitive
this workflow reuses at the dispatch/receive edges via two new methods:
`InventoryService.dispatch_reserved` / `receive_transfer_in`).

## State machine

`REQUESTED → APPROVED → RESERVED → (DISPATCHED, transient) → IN_TRANSIT → RECEIVED → COMPLETED`,
plus `REJECTED` (from REQUESTED/APPROVED) and `CANCELLED` (from REQUESTED/APPROVED/RESERVED).

**DISPATCHED is not a resting status.** `dispatch()` decrements source on-hand and writes the
`transfer_out` movement, then persists `IN_TRANSIT` directly — there is no business-meaningful
moment where a request sits "dispatched but not yet in transit" in this system (no carrier
integration). The enum value exists for schema completeness / future use.

**COMPLETED requires an explicit `complete()` call** after `RECEIVED` — a deliberate manual closure
gate distinct from receipt, matching the brief's explicit inclusion of both states.

## Ledger timing (the invariant the brief calls out)

- **Reserve**: `Inventory.reserved_quantity` increases at the source. On-hand unchanged. No
  `StockMovement`.
- **Dispatch**: source on-hand decreases, `transfer_out` movement written. **Destination is not
  touched.**
- **Receive**: destination on-hand increases, `transfer_in` movement written. Partial receipt is
  supported per line (`quantity_received` accumulates, capped at `quantity_dispatched`; the excess
  requested-but-undispatched is never a thing since dispatch is header-level and moves the full
  reserved amount). Over-receipt (`> quantity_dispatched - quantity_received` remaining) raises.

## Idempotency

- `dispatch()`: idempotent by **status** — already `IN_TRANSIT`/`RECEIVED`/`COMPLETED` returns the
  current row unchanged (same pattern as the existing `StockTransferService.confirm`).
- `receive()`: idempotent by an optional **caller-supplied key**
  (`BranchTransferRequest.last_receipt_idempotency_key`). A repeated call with the same key is a
  no-op. `select_for_update` on the request row serialises concurrent submissions so the
  check-then-set is race-free (proven under PostgreSQL, B4-10).

## Reservation invariant (item 8) — FIXED

`apply_sale_delta` (the direct, no-hold POS/sales path) previously ignored `reserved_quantity`
entirely, so a direct sale could consume stock an active transfer reservation was holding. Fixed:
it now clamps at `max(reserved_quantity, 0)` instead of `0` — a sale can still oversell down to
that floor (unchanged clamp-not-reject policy), but never below it. `reserve()`/`dispatch()`
(via `reserve_quantity`/`unreserve_quantity`/`dispatch_reserved`) are unaffected — dispatch still
consumes its own reservation correctly. Proven under PostgreSQL:
`test_direct_sale_cannot_consume_transfer_reserved_stock` (concurrent sale + dispatch racing the
same reservation) and the strengthened `test_reservation_racing_a_sale_serializes_correctly_via_row_locking`
(`available_quantity >= 0` now holds, not just on-hand).

## D4: legacy `StockTransfer`

`StockTransferService.confirm()` now rejects a cross-branch pair
(`source.branch_id != destination.branch_id`) before doing anything. Historical confirmed rows are
untouched — the guard only applies to new confirmations; re-confirming an already-confirmed
(cross-branch or not) transfer is still the existing idempotent no-op.

## Notifications

`_notify_transfer_event` targets only users holding `inventory.transfer` **in the relevant branch**
(source for requested/dispatched-adjacent events, destination for received, both for
completed/cancelled) — never a tenant-wide broadcast. The acting user is excluded from their own
event's notifications. Reuses the existing `NotificationService.notify_users` / dedupe mechanism;
no schema change (`Notification.branch` remains a later, Phase 6 wave per the migration plan).

## Replenishment (item 5)

`ReplenishmentRule` (branch, product, minimum/target quantity, policy) plus
`ReplenishmentService.suggest_sources` (read-only ranking of other branches' available stock) and
`create_request_from_rule` (creates a `REQUESTED` transfer sized to reach the target). Every path —
including `policy=AUTO_CREATE_REQUEST` — only ever creates a `REQUESTED` row; nothing here calls
`approve`/`reserve`/`dispatch`/`receive`.

## Accounting (Phase 5)

Dispatch and receipt now post balance-sheet-only ledger entries (Dr/Cr Inventory in Transit, no
revenue, no P&L), with the unit cost fixed on the line at dispatch. Design, the short-receipt rule and
the account/event names are in `BRANCH_POS_FINANCE.md` §3 ("Internal transfers (D8)").

# POS, Sales, Purchases and Finance by Branch — Phase 5

Companion to `MULTI_BRANCH_ARCHITECTURE.md` (§2.3, §2.4, D8, D9), `BRANCH_MIGRATION_PLAN.md` (M4,
§4.5, §4.6) and `BRANCH_TEST_MATRIX.md` §5. Phase 5 reuses the Phase 2 models (`PosTerminal`,
`CashRegister`, `StockLocation`), the Phase 3 ledger stamping and the Phase 4 transfer workflow. It
adds no second POS, no second stock ledger and no second accounting engine.

## 1. POS: terminal → register → shift → warehouse

`CashierSession` **is** the POS shift. It gained `terminal`, `register`, `warehouse`, `location`,
`cash_in`, `cash_out`, `variance_reason` and `variance_approved_by/at` (all nullable; migration
`sales/0009`). `Invoice` gained nullable `terminal` and `warehouse` so the stock a sale drew from is
recorded on the sale itself.

**Opening a shift** (`CashierSessionService.open_session`)

* The terminal is resolved inside the acting tenant (another tenant's terminal is "not found" — no
  probing) and the user must hold `pos.access` **in that terminal's branch** (`has_branch_permission`).
  A terminal of a branch the user cannot act in is a 403 (B5-2).
* If the branch has exactly one active terminal it is selected automatically; with several the client
  must choose one.
* The register defaults to the terminal's; a terminal with no register cannot open a shift.
* Warehouse/location come from the terminal (falling back to the branch's own default warehouse —
  never another branch's).
* One open shift per terminal and per register is enforced by **partial unique indexes**
  (`uniq_open_session_per_terminal`, `uniq_open_session_per_register`), so two concurrent opens cannot
  both win. Proven on PostgreSQL.

**Selling** (`CashierSessionService.checkout_context`, called from `PosService.checkout`)

* A shift bound to a terminal fixes the sale's terminal and warehouse. The sale is stamped with them,
  and the stock movement carries the terminal's **location** and the warehouse's branch.
* A branch that has an **active terminal** may not sell without an open terminal shift (B5-1).
* A shift belonging to another branch is rejected.
* Refunds, deletes and restores of a terminal sale return stock to **the warehouse it left**
  (`sale_warehouse(invoice)`), not to the branch default.

**Legacy compatibility (deliberate).** A branch with *no* active terminal behaves exactly as before:
a shift is optional, stock comes from the branch's default warehouse. Enforcement therefore switches
on when an operator creates a terminal — or when the M4 backfill creates the default `POS-1` for a
branch that already has POS history (see §4). That is the one behavioural change existing tenants will
notice: after the migration, a cashier on such a branch must open a shift before selling.

**Closing a shift**

`expected = opening_float + cash payments + cash_in − cash_out − refunds`; `variance = counted −
expected`. A terminal shift requires a counted amount. Closing twice is rejected ("already closed").
A non-zero variance is recorded with its reason and can be **approved** by a branch manager
(`approve_variance`); the cashier can never approve their own variance. `record_cash_movement`
handles paid-in / paid-out with a mandatory reason. Open, close, cash in/out and approval each write an
audit row carrying the branch.

New endpoints: `POST /pos/sessions/cash-movement/`, `POST /pos/sessions/approve-variance/`;
`/pos/sessions/open/` accepts `terminal_id` / `register_id`.

**Document numbering (B5-4).** `DocumentSequence` was already per branch with a row lock and a
`(branch, kind)` unique key. Phase 5 fixes one real defect found while proving it on PostgreSQL: the
first-allocation `IntegrityError` fallback ran inside the outer transaction without a savepoint, so on
PostgreSQL a lost race poisoned the whole transaction instead of falling back to the row that won. It
now creates the row in a savepoint.

## 2. Purchases

`PurchaseReceivingService.receive` already wrote the branch and default location onto the ledger (via
the warehouse). Phase 5 closes the remaining gap: **the receiving warehouse must belong to the
purchase order's branch**, otherwise stock, ledger and payable would land on different branches. The
goods-received journal already carried `purchase_order.branch_id`; its lines now carry it too (§3).

## 3. Finance: branch is a dimension

* `JournalLine.branch` (nullable, migration `finance/0010`). `JournalService.create_entry` — the single
  choke point every posting goes through — stamps each line from its own `branch_id`, else the
  entry's. There is no second engine.
* **Validation.** Every branch named on an entry must belong to the entry's tenant
  (`JOURNAL_BRANCH_INVALID`). If an entry spans several branches (or a branch and Unassigned), **each
  must balance on its own** (`JOURNAL_BRANCH_IMBALANCE`); this is what keeps every per-branch trial
  balance balanced. Reversals mirror each original line's branch.
* **Reports.** `TrialBalanceSelector.run(branch_id=…)` and
  `AccountingEquationService.evaluate(branch_id=…)` accept `None` (consolidated), a branch id, or
  `"unassigned"`. `BranchFinanceService.trial_balance_by_branch` returns every branch, the
  **Unassigned** bucket and the consolidated TB, plus `reconciles` — an independent per-account check
  that Σ(branches) + Unassigned == company. Endpoints: `GET /finance/reports/trial-balance/?branch_id=`
  and `GET /finance/reports/trial-balance/by-branch/`; the equation endpoint takes `branch_id` too.
  A requested branch the caller cannot see is a **403**, never an empty success. `unassigned`,
  consolidated and the reconciliation are company-level and are only returned to callers who can see
  every branch.
* **Unassigned.** Historical entries with no branch are *not* guessed (plan §4.6). Their lines stay
  `NULL` and appear in the Unassigned bucket, so consolidated totals always reconcile.

### Internal transfers (D8)

`BranchTransferService` now posts a **balance-sheet-only** entry at each stage, in the caller's
transaction (a ledger failure rolls the stock movement back, so they cannot drift):

| Stage | Entry | Branch |
|---|---|---|
| Dispatch | Dr **1210 Inventory in Transit** / Cr 1200 Inventory | source |
| Receipt | Dr 1200 Inventory / Cr 1210 Inventory in Transit | destination |

No revenue, no COGS, no P&L. Company inventory (1200 + 1210) is unchanged; 1210 nets to zero
company-wide once everything dispatched is received (it is `+X` on the source and `−X` on the
destination in the meantime, which is exactly the "clearing account that nets to zero" of D8). Value is
`quantity × unit cost`, with the unit cost **fixed at dispatch** on the new
`BranchTransferLine.unit_cost` so a cost change during transit cannot leave a residual. A **short
receipt** leaves the shortfall visible in 1210; it is deliberately *not* written off to an expense —
that is a business decision (claim, write-off, re-count), not something to book silently.
Transfers dispatched before Phase 5 have no unit cost and post nothing.

New chart account `1210` (control account — no manual postings), mapping `DEFAULT_INVENTORY_IN_TRANSIT`,
event types `TRANSFER_DISPATCHED` / `TRANSFER_RECEIVED`, journal source type `transfer`.

## 4. Migrations (wave M4)

| Migration | Contents |
|---|---|
| `sales/0009_cashier_session_terminal_register` | `CashierSession` terminal/register/warehouse/location/cash_in/cash_out/variance fields, `Invoice.terminal/warehouse`, the two open-shift unique indexes. |
| `sales/0010_backfill_default_terminals` | §4.5. One `POS-1` + `REG-1` per branch with a session or invoice, warehouse = the branch's existing default (so stock behaviour is unchanged), register `cash_account` left NULL. Sessions attached. |
| `finance/0010_journalline_branch` | `JournalLine.branch`; `source_type` gains `transfer`. |
| `finance/0011_backfill_journalline_branch` | §4.6. `line.branch = entry.branch` where set. Entry headers are never inferred. |
| `inventory/0007_branchtransferline_unit_cost` | `BranchTransferLine.unit_cost` (nullable). |

Both backfills live in `apps/organization/services/backfill_service.py` and are idempotent (the
migrations are their runner; no separate management command was added). If a branch had several open shifts at once, the oldest is attached to the
terminal and the rest are left without one and reported as `review_required` — one open shift per
terminal is a hard constraint and they are not force-fitted. `branch_migration_report` gained
`pos.session_terminal`, `pos.branch_terminal` and `finance.line_branch` checks.

## 5. Frontend (FE-5)

`modules/pos/utils/checkoutGuard.ts` + `hooks/usePosShift.ts`: the POS refuses to open checkout with no
single branch selected, or — on a branch with terminals — without an open shift attached to a terminal,
and shows an inline "Open shift" bar (terminal picker when there are several). This is a usability
guard; the backend rejects the same sale independently.

## 6. Known limits

* Holds still reserve against the branch default warehouse and a hold does not itself pick a terminal.
  Checking a hold out on a terminal with a different warehouse releases the reservation from the
  default warehouse and deducts only from the terminal warehouse; a later refund restores only there
  (`test_hold_checkout_on_terminal_touches_only_the_terminal_warehouse`).
* Only `pos.access`-level branch permission gates opening a shift; there is no separate
  `pos.terminal.manage` permission (terminal/register CRUD keeps its Phase 2 rule).
* Multi-branch journals are supported by the model and validated per branch, but no posting path
  produces one yet (inter-branch settlement/due-to-due-from is future work).

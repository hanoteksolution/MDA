# Branch Operational Completion

Date: 2026-09-23. This builds on Branch Phases 1–9, which are already deployed. See `MULTI_BRANCH_ARCHITECTURE.md`, `BRANCH_INVENTORY.md`, `STOCK_TRANSFER_WORKFLOW.md`, `BRANCH_POS_FINANCE.md` and `BRANCH_REPORTS_NOTIFICATIONS.md`.

The working example is **AM Electronics** with three branches: Hodan, Bakaaro and KM4. It uses **no new models and no migrations**. The branch services were not rewritten; only the gaps listed below were closed.

## 1. Audit: what existed and what was missing

| Area | Before this work | Now |
|---|---|---|
| Branch core, RBAC, per-branch permissions (`core/branching.py`, `UserBranchAccess`, `BranchAccessProfile`) | Already complete | Unchanged |
| Warehouses and stock per branch (`Inventory(product, warehouse)` → `warehouse.branch`) | Already complete | Unchanged; no quantity field added to Product or Branch |
| POS terminals, registers, shifts, finance branch dimension, branch notifications | Already complete (Phases 5–6) | Unchanged |
| Transfer workflow backend (request → approve → reserve → dispatch/in transit → receive → complete; audit and notifications) | Already complete | Two gaps fixed (see §2) |
| **POS checkout branch** | **Backend gap (security).** `branch_id` from the request body was used without checking the caller's access to that branch. A user limited to Hodan could sell Bakaaro stock and deduct it; this was reproduced with a failing test. | Pinned to the caller's branch scope (§2) |
| **Product stock figures** (`total_stock` in product lists and on POS cards) | **Backend gap.** The figure summed every warehouse of the tenant, so Hodan appeared to hold Bakaaro's 12 units plus KM4's 4. | Scoped to the acting branch (§2) |
| Cross-branch availability API | Partial: other branches showed an `available` number only | Now includes on hand, reserved, in transit, warehouse detail where permitted, and open transfers |
| Cross-branch product search | Missing | `GET /inventory/cross-branch-search/` |
| Transfer request from the destination branch | **Backend gap.** Only the source branch could request, so Hodan could not ask Bakaaro for stock. | Either end can request (§2) |
| Branch reports: sales, stock value, P&L, cash (Phase 6) | Already complete, with reconciliation | Unchanged |
| Branch reports: purchases, inventory health, expenses, transfers | Missing | Added to the same service, with the same reconciliation gate |
| Branch overview list: manager, structure counts, figures | Missing | `GET /reports/branch-overview/` |
| **Global branch switcher** | **UI missing.** The `X-Branch-Id` header plumbing and `branchStore` existed, but nothing loaded branches. The header pill was a static button, so no screen could switch branch. | Switcher in the header (§3) |
| Transfers UI, Branch Management area, consolidated dashboard, branch reports UI | UI missing (no frontend caller of `/branch-transfers/` or `/reports/branch/`) | Built (§3) |
| POS "check other branches" | Missing (the inventory page had a badge-only lookup) | Built (§3) |

## 2. Backend changes (code only)

- **POS checkout** (`api/v1/pos/views.py::_checkout_data`): the branch is resolved through `get_branch_scope(permission="pos.access", allow_all=False, use_default=True)`.
  - A body `branch_id` the caller cannot sell in → **403**.
  - A body that disagrees with `X-Branch-Id` → **400**.
  - `all` → **400**.
  - No branch given → the caller's default branch.
  - Unscoped platform actors keep the legacy default.
  - Stock is then deducted only from that branch's warehouse.
- **Product stock** (`apps/products/serializers/catalog_serializers.py::stock_branch_ids`): stock figures come from the request's branch scope.
  - One selected branch → that branch.
  - No selection → the caller's accessible branches.
  - `all` → consolidated.
  - Elevated users → unfiltered.
  - A user with no branch access at all keeps the previous unfiltered figure, so single-shop users are not broken. That is a documented choice, not a widening.
- **Transfers** (`branch_transfer_service.request_transfer`):
  - The requester needs `inventory.transfer` at **either** end. Approve, reject, reserve, dispatch and cancel stay with the source; receive and complete stay with the destination.
  - Warehouses default to each branch's default warehouse.
  - A product from another tenant is refused.
  - The serializer adds `approved_by`, `dispatched_by`, `received_by`, warehouse names, line count, total quantity and product name.
- **Availability**: `branch_stock_service.product_availability(detail_branch_ids=…)` adds per-branch on hand, reserved and in transit. Warehouse rows appear only where the caller holds `inventory.view`. `open_transfers` lists the open transfers for the product. New endpoint: `CrossBranchSearchView`.
- **Reports** (`branch_report_service`): new reports `purchases`, `inventory` (snapshot), `expenses` and `transfers`, plus `branch_overview()`. The overview reuses `BranchReportService` figures, so the list, dashboard and reports always agree.
- **`/organization/my-branches/`** now returns `covers_all`. "All branches" is offered only to users who can see every branch; dashboards already refuse it otherwise.

## 3. Frontend

- **Header `BranchSwitcher`** (`components/branch/`):
  - Loads the branches the user may act in and shows the active branch. "All branches" appears only when `covers_all` is true, highlighted as a warning.
  - `AppShell` remounts the page on every switch (`key=scopeVersion`), so no screen keeps another branch's data.
  - Logout clears the stored branch.
  - The POS registers a guard: switching with a cart asks for confirmation and clears the cart, because the cart is persisted locally.
- **POS**:
  - Sells in the active branch, falling back to the user's own branch.
  - Shows "Selling in <branch>", and shows "Select a branch to sell" when "All branches" is active (checkout is blocked).
  - Clicking an out-of-stock card opens **Check other branches**: a per-branch table with a **Request transfer** option, which never sells.
- **`/branches`** (`reports.view`) has five tabs:
  - **Dashboard**: a local branch selector (All or a single branch) and a date range. KPIs come from the branch reports: sales, invoices, stock value, low/out of stock, purchases, net cash, expenses, ledger net profit and open transfers. A branch comparison table and a reconciliation badge follow.
  - **Branches**: DataTable with status, manager, warehouses, users, POS terminals, stock value, sales and indicators.
  - **Transfers**
  - **Stock across branches**: search.
  - **Reports**: 8 report types, per-branch rows plus the server's company total and a reconcile badge.
- **`/branches/:id`** has tabs Overview, Sales, Inventory, Purchases, Transfers, Finance, Users (from `branch-access`) and Reports.
- **`/branches/transfers`** (`inventory.transfer`):
  - DataTable with status and direction filters.
  - A detail dialog showing the lines (requested, reserved, dispatched, received, discrepancy), the timeline with actor and timestamp, and only the actions valid for the user's side. Reject asks for a reason inline.
  - A request form: search the product, choose the source branch; the destination is the active branch.
- **Navigation**: a "Branches" section (Branches, Branch transfers) gated by permission, and "Branch transfers" in the Inventory quick actions.
- **Reused components**: `PageLayout`, `TabNav`, `DataTable`, `KpiCard`, `Badge`, `appDialog` and `PlatformConfirmDialog`, which gained a `wide` option. No totals are computed in the frontend.

## 4. Tests

| Suite | Result |
|---|---|
| `tests/integration/test_branch_operational.py` (SQLite) | 20 passed |
| `tests/unit/test_branch_operational_postgresql.py` (PostgreSQL 14) | 3 passed, 0 skipped |
| Existing `tests/unit/test_branch_postgresql.py` (PostgreSQL 14) | 19 passed, 0 skipped |
| Frontend `modules/branches/branches.test.tsx` and `store/branchStore.test.ts` | 10 new + 1 new |
| Full Vitest | 211 passed |
| `npm run build` | PASS |
| Related backend regression (56 test files) | Only baseline failures: `pharmacy_rx_fefo` ×3 (identical at HEAD) and `tenant_isolation_api` ×3 errors (invalid `products` module fixture). 0 new. |

**What `test_branch_operational.py` covers:**

- Three-branch tenant with independent stock (Hodan 0, Bakaaro 12, KM4 4 with 1 reserved).
- Product lists are branch-scoped (Hodan shows 0, never 16; "all" shows 15).
- POS deducts only the acting branch; cross-branch sale → 403, body/header mismatch → 400, "all" → 400; the default branch is used when none is given.
- Cross-branch availability and search; the warehouse breakdown appears only where permitted; no cross-branch view without `inventory.cross_branch_view` in the acting branch.
- An inaccessible branch → 403.
- Destination request → source approve/reserve/dispatch → destination receive, with actors recorded. The destination cannot approve; a third branch cannot request.
- All 8 reports reconcile consolidated with branch totals, and the figures are checked.
- Branch overview for the tenant admin versus the branch manager (own branch only; others → 403).
- No cross-tenant leakage.

**What the PostgreSQL tests cover:**

- Six concurrent POS sales across 3 branches each touch only their own stock.
- Concurrent approve versus cancel of one request ends in one consistent outcome with no stock movement.
- Two branches racing to reserve the same KM4 stock: exactly one reservation succeeds, and reserved stock never exceeds on-hand.

**PostgreSQL target.** These ran with `DJANGO_SETTINGS_MODULE=config.settings.branch_verification` against the **host's PostgreSQL 14 on 127.0.0.1:5432**. pytest creates and drops its own `test_branch_verify` database there. Production (`mda_postgres`, PG16 on :5437) was **not touched**.

## 5. Findings and remaining gaps

The first four gaps originally listed here (the first-sale chart-of-accounts race, source-only cancellation, no push UI and oversell clamping) are handled in §7. What remains:

- **Oversell clamping.** Direct sales still clamp at zero or at the reserved floor, which is the existing, documented policy (`apply_sale_delta`). The UI shows the local shortage and the other branches instead of blocking.
- **Dashboard scope.** Existing module dashboards now receive the selected branch via `X-Branch-Id`, as designed in Phase 2. The consolidated view lives at `/branches`.
- **Not covered here.** Returns and refunds, and the purchase and receiving screens, keep their existing branch scoping; no new UI was added for them.
- **No browser E2E runner** is configured. The UI is covered by Vitest static-render tests and the production build.

## 6. Safety

Only code and tests changed. Nothing was deployed or migrated, no services were restarted, and no production data, TLS/DNS/Nginx or provider configuration was touched. School, SMS and payment code was not changed.

## 7. Final gaps (2026-09-23): cancellation, push transfers, first-sale finance race

These changes use no migrations and no new models.

### Transfer cancellation by either branch

- **Cancellable states** come from the state machine: `CANCELLABLE_STATUSES = REQUESTED, APPROVED, RESERVED`. These are the pre-dispatch states, before any stock has left the source.
- Once a transfer is `IN_TRANSIT`, `RECEIVED` or `COMPLETED`, cancelling returns **400** and no stock changes.
- **Who can cancel:** anyone holding `inventory.transfer` in the **source or the destination** branch. An uninvolved branch gets 403. Another tenant gets 404, because transfers are filtered to the caller's branches.
- **Reservation release:** cancelling a `RESERVED` transfer releases the source reservation through the existing `unreserve_quantity`. This behaviour is unchanged; it now also covers a destination-initiated cancel.
- **The record:** the audit row is the cancellation record. It holds `event=transfer_cancelled`, the previous status, the reason, the actor and the timestamp. The model has no `cancelled_*` columns, and none were added, to avoid a migration.
  - The transfer detail API exposes `cancelled_by`, `cancelled_at`, `cancel_reason` and the full `history`.
- **Notification:** the other branch is notified; the person who cancelled is not.
- **Idempotent:** repeating a cancel changes nothing and writes no second audit row.
- **UI:** "Cancel transfer" is offered to either side. It takes an optional reason, typed inline, then asks for confirmation. The detail shows the cancellation record and the history.

### Push: "Send stock to branch"

- **Same model, same state machine.** `POST /inventory/branch-transfers/` accepts `approve: true`, which runs the existing `approve()` in the same transaction.
  - `approve()` requires the source branch's permission, so a destination-only user trying to push another branch's stock gets **403**. The whole create rolls back and no transfer is left behind.
  - Creation still moves no stock. It moves at reserve and dispatch as before, and the destination still receives. Nothing ever writes another branch's inventory directly.
- **`GET /inventory/branch-transfers/destinations/`** (`inventory.transfer`) lists the company's branches (names only), so a Hodan manager can pick Bakaaro. Warehouses are listed only for branches where the caller has `inventory.view`; otherwise the destination's default warehouse is used. A chosen warehouse must belong to the destination branch (400 otherwise).
- **UI:** the `SendStockDialog` wizard goes destination branch → destination warehouse (when visible) → products and quantities (each capped at local available stock) → review → create. It opens from **Branch transfers → Send stock** and from **Inventory → Stock → Send to branch** on any row with stock available.

### First-sale finance concurrency

Inspecting the posting path showed that `AccountingPostingService` seeds the chart of accounts, account mappings, posting rules and the open financial period on first use, each with check-then-create. That left four races, all now fixed:

1. **Chart of accounts, mappings and posting rules.** Concurrent first sales each saw "no chart" and collided on `uniq_fin_account_tenant_code`.
   - Fix: `ChartService.ensure_finance_ready`. It takes a per-tenant lock only while something is missing, then re-checks and seeds. Steady-state postings never take the lock.
   - `ensure_default_chart` takes the same lock for its other callers.
2. **Periods.** No database constraint prevents duplicate periods.
   - Fix: `PeriodService._create_open_period` takes the lock and re-checks before creating the month's period.
3. **The lock itself.** The first version locked the tenant row with `SELECT … FOR UPDATE`. That deadlocked against the `FOR KEY SHARE` lock that every tenant-scoped foreign-key insert holds.
   - Fix: a transaction-scoped PostgreSQL advisory lock, `pg_advisory_xact_lock(hashtext('finance-seed:<tenant>'))`. It is released at commit or rollback, and skipped on SQLite, which has a single writer.
4. **Two races also affecting steady state, found by the new test:**
   - `_ensure_control_flags` ran an unconditional UPDATE over the control accounts on every posting and held those row locks until the sale committed, so concurrent sales deadlocked. It now updates only rows that actually need fixing (normally none).
   - Journal numbers are `count + 1`, so concurrent postings collided on `uniq_fin_je_tenant_number`. `JournalService._create_numbered` now inserts inside a savepoint and retries only on that constraint, up to 10 times. PostgreSQL makes the second insert wait for the first, so the recount then sees the committed row. Every other error propagates unchanged.

### Tests

| Suite | Result |
|---|---|
| `tests/integration/test_branch_final_gaps.py` (SQLite) | 15 passed |
| `tests/unit/test_finance_first_sale_postgresql.py` + `test_branch_operational_postgresql.py` (PostgreSQL 14) | 3 consecutive runs, 4/4 each, 0 skipped |
| Existing `tests/unit/test_branch_postgresql.py` (PostgreSQL 14) | 19/19, 0 skipped |
| Finance/POS/branch SQLite regression (44 files) | 403 passed, 2 failed. Both failures (`test_accounting_alerts_step35::test_scan_notifies_on_unbalanced_journal` and `test_backfill_health_step35::test_backfill_commit_posts_invoice_and_expense`) fail identically on a clean HEAD worktree, so they are pre-existing and 0 are new. |
| Frontend `branches.test.tsx` | Updated for the either-side cancel, plus send-stock gating |
| Full Vitest | 213 passed |
| `npm run build` | PASS |

**What `test_branch_final_gaps.py` covers:**

- The destination cancels at each pre-dispatch stage, and a reservation is released.
- The audit record, notification of the source, and idempotency.
- Cancellation is refused after dispatch, receipt and completion, with stock unchanged.
- An uninvolved branch and another tenant cannot cancel.
- A push follows the full lifecycle, and the destination receives nothing early.
- A push created without approval starts as `REQUESTED`.
- A push without source permission returns 403 and leaves nothing behind.
- The destination warehouse must belong to the destination branch.
- The destinations list shows warehouses only where the caller may see them.

**What `test_finance_first_sale_postgresql.py` covers:** eight simultaneous first sales across three branches of a brand-new tenant. Every sale must succeed. The test then checks that no account code, mapping, posting rule or period is duplicated; that there are exactly 8 invoices; that stock is deducted once per sale; that every journal entry is balanced; and that no journal idempotency key is duplicated.

Production (`mda_postgres`) was not touched. PostgreSQL tests use the host PG14 test database only.


# Branch Test Matrix

Companion to `MULTI_BRANCH_ARCHITECTURE.md` (§5 phase gates) and `BRANCH_MIGRATION_PLAN.md`.
It is the contract for what "the gate passed" means: every gate below names the tests that prove it,
where they live, and which database they must run on.

**Status column legend:** `TODO` = not yet written. Nothing in this matrix is written yet; the
column is updated as each phase lands, and the final report (brief §70) reports PASS/FAIL against
these IDs.

## 0. How these tests run

| | Command |
|---|---|
| One test | `cd backend && python3 -m pytest tests/unit/test_branch_core_step<N>.py::test_x -q` |
| A phase | `cd backend && python3 -m pytest -k "branch_core" -q` |
| Markers | `-m unit`, `-m integration`, `-m isolation`, `-m critical` (declared in `backend/pytest.ini`) |
| Full suite | `cd backend && python3 -m pytest tests -q` — **> 10 minutes**, run once per phase gate, not per edit |
| Frontend | `cd frontend && npm run test` (Vitest) |

Naming follows the existing convention in `backend/tests/unit/` (`test_<area>_step<N>.py`).
Branch files use `test_branch_<area>.py` so `-k branch_` selects the whole project's suite.

### PostgreSQL requirement (D9)

The default test database is **in-memory SQLite**, which silently ignores `select_for_update`.
Any test whose claim is about locking, race conditions, or constraint enforcement under concurrency
**must** run on PostgreSQL and must skip — loudly, never pass — elsewhere, following the existing
pattern in `tests/unit/test_school_postgresql.py`:

```python
if connection.vendor != 'postgresql':
    pytest.skip('Requires real PostgreSQL transactions and locking.')
```

Concurrency tests live in `tests/unit/test_branch_postgresql.py`. **A gate that depends on a PG-only
test cannot be declared PASS from a SQLite run** — it is reported as SKIPPED, which is a gate failure.

Run them with the dedicated settings module (added in Phase 2, mirroring the existing
`school_verification` precedent):

```
cd backend && DJANGO_SETTINGS_MODULE=config.settings.branch_verification \
    python3 -m pytest tests/unit/test_branch_postgresql.py
```

Connection is overridable via `BRANCH_VERIFY_PG_{NAME,USER,PASSWORD,HOST,PORT}`; it defaults to
`postgres@127.0.0.1:5432`. This environment has PostgreSQL 14.24 running, so these gates are
executable here and are **not** excused as "no database available".

**This gate is not a formality — it caught a real deadlock during Phase 2.** The first version of
`BranchAccessService.set_default` cleared every other row's `is_default` flag without first locking
those rows in a fixed order. Two concurrent "make this my default branch" requests for the same user
(one via Hodan's access row, one via Bakaaro's) each acquired their own row's lock first and then
waited on the other's, and PostgreSQL correctly raised `DeadlockDetected` rather than corrupting the
data. SQLite, which ignores `select_for_update`, would have let both writes through silently. The fix
locks every one of the user's access rows in `pk` order before mutating any of them, which forces the
two transactions to serialise instead of deadlocking; `test_concurrent_default_branch_selection_leaves_exactly_one_default`
in `test_branch_postgresql.py` is the regression test.

## 1. Baseline

Recorded 2026-09-19 on a dirty tree, before any branch code:
**12 failed, 9 errors** — `test_school_sis` (5F), `test_pharmacy_rx_fefo_step60` (3F),
`test_performance_step31` (6E), `test_tenant_isolation_api` (3E, "Unknown module code(s): products"),
and one failure each in `test_accounting_alerts_step35`, `test_backfill_health_step35`,
`test_demo_tenant_step39`, `test_tenant_foundation`. Pass count was not captured.

Every gate is measured **relative to this baseline**: a phase passes only if it adds zero new
failures. The baseline must be re-measured (not trusted) at the start of Phase 2, with the pass count
captured this time, and re-measured at Phase 9.

## 2. Phase 2 — Branch core, RBAC, warehouses, locations

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B2-1 | Branch CRUD honours `(tenant, code)` and `(company, code)` uniqueness; archiving a branch with open sessions is rejected | `tests/unit/test_branch_core.py` | any | TODO |
| B2-2 | `is_active` and `status` stay consistent in both directions | `tests/unit/test_branch_core.py` | any | TODO |
| B2-3 | Exactly one `is_default` branch per tenant is enforceable, including under concurrent writes | `tests/unit/test_branch_postgresql.py` | PG | TODO |
| B2-4 | `resolve_branch_scope` ignores an `X-Branch-Id` the user has no access to → 403, never a silent widen | `tests/unit/test_branch_scope.py` | any | TODO |
| B2-5 | `X-Branch-Id: all` is rejected by POS and stock-mutating endpoints | `tests/unit/test_branch_scope.py` | any | TODO |
| B2-6 | A user with zero `UserBranchAccess` rows falls back to `User.branch` (migration safety) | `tests/unit/test_branch_scope.py` | any | TODO |
| B2-7 | Expired / not-yet-started / suspended `UserBranchAccess` grants nothing | `tests/unit/test_branch_scope.py` | any | TODO |
| B2-8 | Elevated admins bypass branch scope exactly as they bypass tenant scope today | `tests/unit/test_branch_scope.py` | any | TODO |
| B2-9 | Branch-scoped permission check: a Branch Manager in branch A has no manager rights in branch B | `tests/unit/test_branch_rbac.py` | any | TODO |
| B2-10 | Cross-tenant: a user of tenant X cannot read, switch to, or reference a branch of tenant Y | `tests/integration/test_branch_isolation_api.py` (`-m isolation`) | any | TODO |
| B2-11 | Cross-branch list isolation on every branch-scoped endpoint shipped in this phase | `tests/integration/test_branch_isolation_api.py` | any | TODO |
| B2-12 | Warehouse belongs to exactly one branch; every warehouse has a default `StockLocation` | `tests/unit/test_branch_locations.py` | any | TODO |
| B2-13 | Branch mutations write audit rows carrying the branch | `tests/unit/test_branch_audit.py` | any | TODO |
| MIG-1 | M1 backfill: default branch per tenant, tenants without a company skipped and reported | `tests/verification/test_branch_migration.py` | any | TODO |
| MIG-2 | M1 backfill: default + transit locations, `UserBranchAccess` from `User.branch`; `SchoolCampusAccess` **not** copied | `tests/verification/test_branch_migration.py` | any | TODO |
| SCH-1 | School regression: `SchoolCampusAccess` behaviour, campus scoping and School tests unchanged | existing `tests/unit/test_school_*.py` | any + PG | TODO |
| FE-2 | Branch context store: switching branch refetches, and a forbidden branch id never enters the store | `frontend/src/store/branchStore.test.ts` | — | TODO |

**Gate:** B2-*, MIG-1, MIG-2 green; SCH-1 unchanged vs. baseline; full suite shows no new failures.

## 3. Phase 3 — Inventory and ledger

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B3-1 | Every stock change writes exactly one `StockMovement` with branch + location | `tests/unit/test_branch_ledger.py` | any | PASS |
| B3-2 | Ledger ⇔ balance invariant: Σ movements per (product, warehouse) == `Inventory.quantity` | `tests/unit/test_branch_ledger.py` | any | PASS |
| B3-3 | Corrections are reversing rows; no `StockMovement` row is ever updated or deleted | `tests/unit/test_branch_ledger.py` | any | PASS |
| B3-4 | On-hand never goes negative through any service path | `tests/unit/test_branch_ledger.py` | any | PASS |
| B3-5 | Available = quantity − reserved, per warehouse, after reserve/unreserve/consume cycles | `tests/unit/test_branch_ledger.py` | any | PASS |
| B3-6 | Cross-branch availability view: company total == Σ branch on-hand + in-transit (in-transit = 0 in Phase 3, per `BRANCH_INVENTORY.md` §2) | `tests/unit/test_branch_stock_views.py` | any | PASS |
| B3-7 | Branch A's stock endpoints never expose branch B's quantities without cross-branch-view permission; existing inventory views resolve branch scope via `core.branching`, not the legacy `request.user.branch` | `tests/integration/test_branch_isolation_api.py` | any | PASS |
| B3-8 | `inventory.cross_branch_view` gates the availability endpoint independently of `inventory.view`/`inventory.adjust` (operate ≠ view-elsewhere), and is itself branch-scoped via `has_branch_permission` (a profile narrows it like any other permission) | `tests/unit/test_branch_stock_views.py`, `tests/integration/test_branch_isolation_api.py` | any | PASS |
| B3-9 | New movement types (`purchase_return`, `warehouse_move`, `damage`, `write_off`, `opening_balance`) are distinct, non-duplicated events | `tests/unit/test_branch_ledger.py` | any | PASS |
| **B3-10** | **Two concurrent sales each requesting the last unit of a 1-unit balance: exactly one succeeds without oversell** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| **B3-11** | **A reservation racing a sale against the same available stock cannot double-allocate the last unit** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS (see note below) |
| **B3-12** | **Two reservations racing against limited stock: total reserved never exceeds on-hand** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| **B3-13** | **`move_stock` between the same two warehouses in opposite directions, run concurrently, does not deadlock (deterministic pk-ordered locking)** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| MIG-3 | M2 backfill: every `StockMovement.branch`/`InventoryTransaction.branch` equals `warehouse.branch`; zero NULLs | `tests/verification/test_branch_migration.py` | any | PASS |

**Gate:** B3-*, MIG-3 green; invariants B3-2 and B3-4 hold under the Phase 4 concurrency tests too. **Met** — 31 Phase 3 tests green (20 ledger + 11 stock-views on SQLite, plus 4 new PG-only concurrency tests and 8 new isolation tests layered on the existing files), full regression shows zero new failures against the Phase 2 baseline (see the Phase 3 completion report).

**B3-11 note:** proven under real PostgreSQL that on-hand never goes negative in this race. It originally did not prove `available` (on-hand − reserved) stayed non-negative, because `apply_sale_delta` ignored `reserved_quantity`; **fixed 2026-09-21** (clamps deductions at the reserved floor; PG test `test_direct_sale_cannot_consume_transfer_reserved_stock`). See `BRANCH_INVENTORY.md` §8 point 5 and the completion report's Technical Debt.

## 4. Phase 4 — Transfers, reservation, transit, receipt

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B4-1 | Request → approve → dispatch → in-transit → receive produces the expected ledger rows at each step, and **none** before dispatch | `tests/unit/test_branch_transfer.py` | any | PASS |
| B4-2 | Approval reserves at source; stock is not deducted at approval | `tests/unit/test_branch_transfer.py` | any | PASS |
| B4-3 | Destination is credited **only** at receipt | `tests/unit/test_branch_transfer.py` | any | PASS |
| B4-4 | Partial receipt: short/over/damaged quantities recorded as discrepancies; in-transit residual is correct | `tests/unit/test_branch_transfer.py` | any | PASS |
| B4-5 | Cancel/reject releases the reservation exactly once (idempotent) | `tests/unit/test_branch_transfer.py` | any | PASS |
| B4-6 | Invariant across the whole lifecycle: source + destination + in-transit == constant | `tests/unit/test_branch_transfer.py` | any | PASS |
| B4-7 | Same-branch transfers still use `StockTransfer`; a cross-branch `StockTransfer` is rejected (D4) | `tests/unit/test_branch_transfer.py` | any | PASS |
| **B4-8** | **Two concurrent dispatches of the same reserved stock: one succeeds, one fails; no oversell** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| **B4-9** | **Concurrent receipt + POS sale at destination: balances stay consistent under `select_for_update`** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| **B4-10** | **Double-submit of the same receipt (same idempotency key) credits stock once** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| B4-11 | Transfer state transitions emit notifications to the right branch audience | `tests/unit/test_branch_notifications.py` | any | PASS |

**Gate:** B4-1…B4-7 and B4-11 green on SQLite; **B4-8…B4-10 green on PostgreSQL 14** — a skip here
is a gate failure, not a pass. **Met** — 20 new tests (14 transfer + 3 notification + 3 PG-only),
full regression zero new failures vs. Phase 3 baseline (see completion report). The
reservation-invariant gap (direct sale ignoring `reserved_quantity`) was later fixed — see
`STOCK_TRANSFER_WORKFLOW.md`.

## 5. Phase 5 — POS, sales, purchases, finance

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B5-1 | A POS sale requires a terminal + register + open session and deducts from that terminal's warehouse/location | `tests/unit/test_branch_pos.py` | any | PASS |
| B5-2 | A session cannot be opened on a terminal of a branch the user has no access to | `tests/unit/test_branch_pos.py` | any | PASS |
| B5-3 | Shift close: expected vs. counted cash, variance recorded, re-close rejected | `tests/unit/test_branch_pos.py` | any | PASS |
| **B5-4** | **Document sequences are per branch; two branches cannot collide on receipt/invoice number (concurrent first allocation)** | `tests/unit/test_branch_postgresql.py` (+ SQLite half in `test_branch_pos.py`) | **PG** | PASS |
| B5-5 | Existing POS critical path unchanged | existing `tests/integration/test_critical_pos_checkout.py` | any | PASS |
| B5-6 | Purchases receive into a branch warehouse and stamp the branch on the ledger | `tests/unit/test_branch_purchases.py` | any | PASS |
| B5-7 | Branch is a finance **dimension**: every posted `JournalLine` carries the entry's branch | `tests/unit/test_branch_finance.py` | any | PASS |
| B5-8 | Trial balance is balanced per branch **and** consolidated; Σ branch TB == company TB | `tests/unit/test_branch_finance.py` | any | PASS |
| B5-9 | An internal transfer posts **no revenue and no P&L**; company inventory value is unchanged (D8) | `tests/unit/test_branch_finance.py` | any | PASS |
| B5-10 | Accounting equation holds per branch and consolidated | `tests/unit/test_branch_finance.py` | any | PASS |
| B5-11 | Unassigned (branch-less) journal lines appear in an "Unassigned" bucket and consolidated totals still reconcile | `tests/unit/test_branch_finance.py` | any | PASS |
| MIG-4 | M4 backfill: default terminal/register per POS-active branch; `JournalLine.branch` from its entry | `tests/verification/test_branch_migration.py` | any | PASS |
| FE-5 | POS UI blocks checkout when no branch/terminal is selected | `frontend/src/modules/pos/utils/checkoutGuard.test.ts` | — | PASS |

**Gate:** B5-*, MIG-4 green; existing finance suites (`test_finance_step*`, `test_general_ledger_step37`,
`test_accounting_equation_foundation`) unchanged vs. baseline. **Met** — 36 new SQLite tests (18 POS, incl. hold→terminal-warehouse checkout + refund,
2 purchases, 13 finance, 3 MIG-4 added to the verification file), 2 new PostgreSQL-only tests green
(not skipped), 6 new frontend tests. Full backend regression: 12 failed / 9 errors, the same count and
the same families as the Phase 4 baseline; the two failures that touch finance
(`test_accounting_alerts_step35`, `test_backfill_health_step35`) both hit the journal-immutability guard
on code Phase 5 did not change. B5-9 covers the clean-receipt case; a *short* receipt is also tested to
leave the shortfall visible in "Inventory in Transit" with no P&L (deliberately not written off —
`BRANCH_POS_FINANCE.md` §3).

## 6. Phase 6 — Reports, dashboards, notifications

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B6-1 | Every branch-aware report accepts single-branch, multi-branch and consolidated scope | `tests/unit/test_branch_reports.py` | any | PASS |
| B6-2 | **Consolidated == Σ branches** for sales, stock value, P&L and cash | `tests/unit/test_branch_reports.py` | any | PASS |
| B6-3 | A report request for a branch the user cannot access returns 403, not an empty success | `tests/integration/test_branch_isolation_api.py` | any | PASS |
| B6-4 | Dashboard widgets respect the active branch scope | `tests/unit/test_branch_reports.py` | any | PASS |
| B6-5 | Notifications carry branch, severity and entity; audience targeting is branch-scoped | `tests/unit/test_branch_notifications.py` | any | PASS |
| B6-6 | Low-stock / transfer / variance alerts fire once per event (no duplicate storms) | `tests/unit/test_branch_notifications.py` | any | PASS |
| MIG-5 | M5: `AuditLog.branch` is forward-only — historical rows stay NULL and are not back-dated | `tests/verification/test_branch_migration.py` | any | PASS |

**Gate:** B6-*, MIG-5 green; B6-2 is the hard gate. **Met** — 26 new tests (14 reports incl. parametrised
B6-1 over all four reports, 8 notifications, 3 isolation API, 1 MIG-5), green on SQLite and, for the report
and notification files, on PostgreSQL 14 (no Phase 6 row requires PG; run as a check on the aggregate SQL).
B6-2 asserts `consolidated == Σ branches (+ Unassigned for P&L)` for sales, stock value, P&L and cash, with
`reconciles` computed from an independent aggregate. Full backend regression: 12 failed / 9 errors, the
identical test names as the Phase 5 run; frontend 42/42, `tsc` clean apart from the known school error.

## 7. Phase 7 — SMS framework

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B7-1 | Provider registry resolves adapters; only `Mock` and generic `CustomHttp` exist (D7 — no invented provider APIs) | `tests/unit/test_sms_framework.py` | any | PASS |
| B7-2 | Template render + per-tenant/branch sender resolution | `tests/unit/test_sms_framework.py` | any | PASS |
| B7-3 | **Failure isolation:** a provider timeout/5xx/malformed response never breaks the business transaction that triggered it | `tests/unit/test_sms_framework.py` | any | PASS |
| B7-4 | Retry/backoff is bounded; a permanently failing send lands in a terminal state, not an infinite queue | `tests/unit/test_sms_framework.py` | any | PASS |
| B7-5 | `SmsLog` records status and provider reference and **never** the credential | `tests/unit/test_sms_framework.py` | any | PASS |
| SEC-1 | Credentials are Fernet-encrypted at rest; the API returns only `has_secret` + masked tail | `tests/unit/test_integration_secrets.py` | any | PASS |
| SEC-2 | Secrets never appear in logs, audit message text, API responses or serialised errors | `tests/unit/test_integration_secrets.py` | any | PASS |

**Gate:** B7-*, SEC-1, SEC-2 green. **Met** — 42 new tests (`test_sms_framework` 34 incl. parametrised failure
shapes, `test_integration_secrets` 8), green on SQLite and on PostgreSQL 14 (not required by any row; run
because dispatch takes a row lock — that run caught a real `FOR UPDATE` on a nullable outer join, fixed by
locking only the log row). Full backend regression: 12 failed / 9 errors, identical names to Phase 5/6.
Design and limits: `BRANCH_SMS_FRAMEWORK.md`.

## 8. Phase 8 — Payment framework

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| B8-1 | An invoice is marked PAID **only** by a verified server-side confirmation — never by a frontend "success" callback | `tests/unit/test_payment_framework.py` | any | PASS |
| B8-2 | Payment intent lifecycle: created → pending → succeeded/failed/expired, with no illegal transition | `tests/unit/test_payment_framework.py` | any | PASS |
| B8-3 | **Idempotency:** replaying the same intent key creates one payment and one journal entry | `tests/unit/test_payment_framework.py` | any | PASS |
| **B8-4** | **Concurrent duplicate webhooks for one intent settle the invoice exactly once** | `tests/unit/test_branch_postgresql.py` | **PG only** | PASS |
| B8-5 | Webhook signature verification rejects unsigned, wrongly-signed and replayed (stale-timestamp) payloads | `tests/unit/test_payment_framework.py` | any | PASS |
| B8-6 | Unverified webhooks are persisted as raw events and change no financial state | `tests/unit/test_payment_framework.py` | any | PASS |
| B8-7 | Reconciliation reports provider-vs-ledger mismatches instead of auto-correcting them | `tests/unit/test_payment_framework.py` | any | PASS |
| B8-8 | A payment is stamped with the branch of its invoice/terminal | `tests/unit/test_payment_framework.py` | any | PASS |
| SEC-3 | Provider credentials follow SEC-1/SEC-2; webhook secrets are never returned to the client | `tests/unit/test_integration_secrets.py` | any | PASS |

**Gate:** B8-1…B8-3, B8-5…B8-8, SEC-3 green on SQLite; **B8-4 green on PostgreSQL**. **Met** — see `BRANCH_PAYMENT_FRAMEWORK.md`. B8-4 is proven by 3 threaded tests (same event id ×8, different event ids ×8, one intent key ×6) that also run green on PostgreSQL 14.

## 9. Phase 9 — Regression, concurrency, browser, security

| ID | Assertion | Location | DB | Status |
|---|---|---|---|---|
| R-1 | Full backend suite re-measured; **zero new failures vs. the Phase 2 re-measured baseline**, pass count captured | `python3 -m pytest tests -q` | SQLite | PASS — 890 collected; 12 failed / 9 errors, identical names to the §1 baseline; ~834 passed, 35 skipped (all PG-only) |
| R-2 | Full suite on PostgreSQL 14, including every PG-only test above — no skips in the concurrency set | `python3 -m pytest tests -q` | **PG** | PASS — same 12 failed / 9 errors; **0 skipped**, every PG-only test ran |
| R-3 | Frontend `npm run test` green; `npm run build` (`tsc -b && vite build`) clean | `frontend/` | — | PARTIAL — `npm run test` 42/42 green; `vite build` clean; `tsc -b` fails only on pre-existing School `sis/config.ts` (3 errors, out of scope) |
| R-4 | Tenant isolation suites unchanged (`-m isolation`) | existing `tests/integration/` | any | PASS — isolation suites inside R-1/R-2, no new failures (3 `test_tenant_isolation_api` errors are baseline) |
| R-5 | School suites unchanged, SQLite and PostgreSQL | `tests/unit/test_school_*.py` | any + PG | PASS — School failures are the 5 baseline `test_school_sis`; `test_school_postgresql` ran and passed on PG. No School code touched |
| BR-1 | Browser walkthrough: login → switch branch → POS sale → transfer request → receive → report, recorded step by step | manual, scripted in the final report | — | API-LEVEL ONLY — `test_branch_walkthrough_api.py` (login→switch→POS→transfer→receive→report) PASS; real browser walkthrough NOT performed |
| BR-2 | Branch switcher shows only accessible branches; a forged `X-Branch-Id` in devtools is rejected by the API | manual + B2-4 | — | PARTIAL — forged header rejected (B2-4 + sweep, PASS); switcher list covered by `branchStore.test.ts`; not eyeballed in a browser |
| SEC-4 | No secret in the frontend bundle: `grep` the built assets for credential keys | `frontend/dist` after build | — | PASS — no credential key/secret pattern in `frontend/dist` |
| SEC-5 | Horizontal privilege escalation sweep: for each branch-scoped endpoint, a branch-A user calling it with a branch-B id gets 403/404, never data | `tests/integration/test_branch_isolation_api.py` | any | PASS after fix — `test_branch_isolation_sweep.py` (8 tests); found and fixed 4 leaks, see below |
| MIG-6 | `branch_migration_report` clean on a seeded multi-branch fixture (all §5 checks of the migration plan) | `tests/verification/test_branch_migration.py` | any | PASS — `test_branch_migration.py` 23 tests |

**Gate:** everything above; final report in the brief's PASS/FAIL format. **Met, with BR-1/BR-2 as manual gaps (§10.3) and R-3 limited by the pre-existing School `tsc` error.**

### Phase 9 findings (SEC-5 sweep)

A branch-A user holding every relevant permission, but only on HODAN, could reach BAKAARO/MAIN data through endpoints that were tenant-scoped but not branch-scoped. All four fixed (smallest change, each with a sweep test):

1. `GET /inventory/branch-transfers/` and `/<id>/` returned transfers between two foreign branches — `BranchTransferService.list` and `_locked` now keep only transfers touching a branch the caller can act in (either end); a foreign id is 404, a forged `branch_id` is 403.
2. `GET /pos/sessions/` listed every branch's shifts — `CashierSessionService.list` now branch-scopes (`pos.access`).
3. `GET /integrations/sms-providers/` and `/payment-providers/` listed providers bound to other branches — tenant-wide (no branch) providers stay visible; branch-bound ones only to accessible branches.
4. `PATCH` on those providers by id worked across branches (and could re-bind the provider to your branch) — now 404 unless the caller can manage that branch.

Not fixed / not done: M8 (constraint tightening) was **not** written — it ships in a later release per the migration plan.


## 10. Known limitations to state honestly in the final report

1. SQLite cannot prove any locking claim. Any PG-only test that ends up SKIPPED is reported as
   **not proven**, never as PASS.
2. The pre-existing baseline failures (§1) are not fixed by this project and are reported as
   pre-existing, with the measurement that shows they predate the branch work.
3. `BR-1`/`BR-2` are manual browser checks — no browser test runner is configured in
   `frontend/package.json`. They are reported as manual evidence, not as automated coverage.
4. Performance under many branches (`test_performance_step31` is already erroring at baseline) is out
   of scope unless the user asks for it.

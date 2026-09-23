# Branch Migration Plan

Companion to `MULTI_BRANCH_ARCHITECTURE.md`. It covers **schema and data migration only**: what
columns appear in which wave, how they are backfilled, how the backfill is validated, and when (and
only when) a column is allowed to become `NOT NULL`.

Two rules from the brief govern everything below:

* **Do not make `branch_id` required immediately.** Every new branch-bearing column ships nullable.
* **Do not guess historical branch data.** Where a row's branch cannot be *derived deterministically*
  from an existing relation, it stays `NULL` and is reported, never inferred.

## 1. Starting point (measured 2026-09-19)

Introspected from the current models (`DJANGO_SETTINGS_MODULE=config.settings.test`):

* **94 foreign keys already point at `settings_app.Branch`** across 24 apps. The great majority are
  already `null=False`, i.e. the data is present and needs no backfill: `sales.Invoice`,
  `sales.Payment`, `sales.CashierSession`, `sales.DocumentSequence`, `purchases.PurchaseOrder`,
  `inventory.Warehouse`, `inventory.StockTransfer`, `inventory.InventoryAdjustment`,
  `finance.SupplierPayment`, plus the vertical apps (restaurant, hotel, futsal, property, housing,
  office rental, travel) and all of `apps/school`.
* **Already nullable** (left as-is, no tightening in this project): `authentication.User.branch`,
  `authentication.StaffEvaluation.branch`, `customers.Customer.branch`, `finance.JournalEntry.branch`,
  `settings_app.Setting.branch`, `pharmacy.Prescription.branch`, the four `gym.*` models,
  `restaurant.Promotion`, `travel_agency.TravelExpense`, `property_management.Owner`,
  `office_rental.OfficeTenant`, `housing_rental.HousingTenant`, `hotel.Guest`,
  `school.AdmissionDocumentType`.
* **Core tables with no branch dimension at all** — these are what this project adds:
  `inventory.Inventory` (stays branch-free by D2; branch is reached through `Warehouse`),
  `inventory.StockMovement`, `inventory.InventoryTransaction`, `inventory.StockTransferLine`,
  `finance.JournalLine`, `audit.AuditLog`, `notifications.Notification`.
* Latest migration per app at the time of writing: `settings_app 0004`, `inventory 0003`,
  `sales 0008`, `purchases 0003`, `finance 0009`, `authentication 0009`, `notifications 0002`,
  `audit 0003`. New migrations are numbered after these; the working tree is dirty with unrelated
  in-progress work, so re-check the highest number before generating each migration.
* `Branch` requires `company` (`on_delete=CASCADE`) and is unique on `(tenant, code)` and on
  `(company, code)`. A branch cannot be created for a tenant that has no `Company` row.

## 2. Principles

1. **Additive first.** Each wave = `AddField(null=True)` / `CreateModel` only. No column is dropped,
   renamed, or re-typed, and no table is moved between apps. `Branch` itself is extended in place
   (D1) precisely so these 94 FKs never have to be rewritten.
2. **Backfill is a separate, reversible migration** from the schema change, so a failed backfill can
   be rolled back without reverting the column.
3. **Derivation only.** A backfill may read an existing FK chain (`movement.warehouse.branch`).
   It may not use "the tenant's only branch", "the most recent branch", or the acting user's branch
   as a substitute for missing data.
4. **Fail-open at runtime, fail-closed at authorisation.** A `NULL` branch on a historical row must
   not break reads: list endpoints treat `branch IS NULL` as "unassigned" and show it only to users
   with tenant-wide scope. Authorisation itself never widens (see `resolve_branch_scope`).
5. **Every `RunPython` has a real `reverse_code`.** Where the reverse is genuinely a no-op
   (idempotent row creation), use `migrations.RunPython.noop` and say why in a comment.
6. **`apps/school` is not touched.** No School table is altered, re-keyed, or backfilled by any wave
   in this plan (§7).
7. **A non-nullable `AddField` needs `db_default`, not just `default`.** Django's `default=` is an
   ORM-level convenience: it fills the field on a Python model instance and backfills existing rows at
   migration time, but on SQLite the column itself is left with no persisted default afterward. Any
   code that builds an INSERT from a model that predates the column — most concretely, School's own
   `tests/unit/test_school_migrations.py`, which recreates `Branch` through a historical, frozen model
   via `MigrationExecutor.migrate(target)` — omits the column entirely, and SQLite then enforces the
   `NOT NULL` constraint against a value nobody supplied. `settings_app/0005_branch_profile_fields`
   hit exactly this on `branch_type`; the fix was `db_default=` (Django 5.x) on every new non-nullable
   `Branch` column (`branch_type`, `status`, `legal_name`, `city`, `region`, `country`, `timezone`,
   `currency`, the four prefix fields, `notes`), which persists a real database-level default so the
   column resolves correctly regardless of which model version generated the INSERT. This is now the
   standing rule for every wave below: a nullable column needs nothing extra, but a non-nullable one
   needs `db_default` alongside `default`, not `default` alone.

## 3. Migration waves

Each wave ships with the phase that needs it and cannot merge before that phase's gate.

### M1 — Branch core, access, locations (Phase 2) — **shipped**

| Migration | Contents |
|---|---|
| `settings_app/0005_branch_profile_fields` | `AddField` on `Branch`: `branch_type`, `status`, `legal_name`, `manager`, `city`, `region`, `country`, `latitude`, `longitude`, `opening_date`, `timezone`, `currency`, `receipt_prefix`, `invoice_prefix`, `order_prefix`, `transfer_prefix`, `notes`, plus two indexes. All nullable or defaulted. |
| `organization/0001_initial` | `BranchAccessProfile`, `UserBranchAccess`, `StockLocation`, `PosTerminal`, `CashRegister`. New tables only. |
| `organization/0002_backfill_default_branch` | §4.1 |
| `organization/0003_backfill_stock_locations` | §4.2 |
| `organization/0004_backfill_user_branch_access` | §4.3 |
| `audit/0004_auditlog_branch` | `AuditLog.branch` (nullable, indexed). **Brought forward from M5** so Phase 2's own mutations are auditable with their branch from day one. Semantics are unchanged: forward-only, historical rows keep `NULL`. |

Deviations from the plan as first written, and why:

* **No `settings_app/0006_backfill_branch_status`.** `status` defaults to `ACTIVE` and the model's
  `save()` derives whichever of `status` / `is_active` was not the one changed, in both directions.
  Existing rows are all `is_active=True`, so a separate backfill pass would have been a no-op that
  still rewrote every row.
* **No `inventory/0004_warehouse_profile_fields`.** `warehouse_type` / `manager` / `status` are not
  needed by any Phase 2 gate; deferred rather than shipped unused. `Warehouse.default_location` was
  dropped in favour of `StockLocation.is_default`, which avoids a second source of truth (and a
  circular FK between `inventory` and `organization`).
* **`Branch.default_warehouse` / `default_*_account` deferred to Phase 5**, where finance actually
  reads them. Adding unused FKs into `settings_app` now would pull `finance` and `inventory` into
  its migration dependencies for no benefit.
* **`BranchAccessProfile.grants_all_permissions`** was added during implementation. Without it, a
  profile with an empty permission list is ambiguous between "everything" and "nothing" — and the
  backfill's manager profile carries no explicit list, so the implicit reading would have silently
  locked out every backfilled branch manager. The flag makes "no narrowing" explicit and keeps an
  empty list meaning exactly nothing.

`is_active` and `status` are kept in sync by the model's `save()` for the whole life of this project;
`is_active` is not removed.

### M2 — Ledger dimension (Phase 3)

| Migration | Contents |
|---|---|
| `inventory/0005_stockmovement_branch_location` | `StockMovement`: `branch` (null), `location` (null), `unit_cost` (null), `reason` (blank), `actor` (null), `metadata` (default dict); widen `movement_type` choices. `InventoryTransaction`: `branch` (null), `location` (null). |
| `inventory/0006_backfill_movement_branch` | §4.4 |
| `inventory/0007_movement_branch_indexes` | `(tenant, branch, product, created_at)` and `(tenant, branch, movement_type)` indexes. |

### M3 — Transfer workflow (Phase 4)

| Migration | Contents |
|---|---|
| `inventory/0008_branch_transfer_workflow` | `BranchTransferRequest`, `BranchTransferLine`, `BranchTransferShipment`, `BranchTransferEvent`, `ReplenishmentRule`. **New tables only — no backfill.** Historical `StockTransfer` rows are *not* converted. |
| `inventory/0009_stocktransfer_same_branch_guard` | Adds `source_branch`/`destination_branch` denormalised columns (null) + backfill from each warehouse, so the same-branch check (D4) is enforceable in a DB constraint later. Existing cross-branch rows are reported, not rewritten. |

### M4 — POS and finance dimension (Phase 5)

| Migration | Contents |
|---|---|
| `sales/0009_cashier_session_terminal_register` | `CashierSession`: `terminal`, `register`, `warehouse`, `location`, `cash_in`, `cash_out`, approval fields. All nullable. |
| `sales/0010_backfill_default_terminals` | §4.5 |
| `finance/0010_journalline_branch` | `JournalLine.branch` (null). |
| `finance/0011_backfill_journalline_branch` | §4.6 |

### M5 — Notifications (Phase 6)

| Migration | Contents |
|---|---|
| `notifications/0003_notification_branch_severity` | `branch` (null), `severity` (default `INFO`), `entity_type`, `entity_id`, `audience`, `expires_at`, `action_url`. |

`AuditLog.branch` was originally planned here and shipped early in M1 (see above) — **forward-only:
historical audit rows keep `NULL`**, because back-dating a branch onto an audit row would falsify the
audit trail. `write_audit` derives the branch only from the entity's own `branch`, or its
warehouse's branch; an entity with no such relation records no branch rather than an inferred one.

### M6 / M7 — Integrations (Phases 7 and 8)

`integrations/0001_initial` (`IntegrationCredential`, `SmsProvider`, `SmsTemplate`, `SmsLog`) and
`integrations/0002_payments` (`PaymentProviderConfig`, `PaymentIntent`, `PaymentWebhookEvent`,
`ReconciliationRecord`). New tables only; nothing to backfill. Requires the `cryptography`
dependency and `INTEGRATION_ENCRYPTION_KEY` in the environment (D6) — the app refuses to start the
integrations module without a key rather than falling back to plaintext.

### M8 — Constraint tightening (deferred, Phase 9 and after)

No column added by M1–M5 becomes `NOT NULL` inside this project unless §6's exit criteria are met for
it. M8 is written and reviewed in Phase 9 but is expected to ship in a **later, separate release**.

## 4. Backfill rules

Each rule is idempotent, chunked (2 000 rows per `bulk_update`), and logs a count per tenant.

### 4.1 Default branch per tenant

For each tenant, in this order:

1. Tenant has ≥ 1 branch with `is_default=True` → nothing to do.
2. Tenant has branches but none default → mark the **oldest `is_active` branch** (`created_at` asc,
   `id` asc as tiebreak) as `is_default=True`. If no branch is active, mark the oldest branch and
   report it.
3. Tenant has a `Company` but no branch → create `Branch(name="Main Branch", code="MAIN",
   is_default=True, status="ACTIVE")` against the oldest company. If code `MAIN` is taken by an
   inactive row, use `MAIN-1`, `MAIN-2`, …
4. Tenant has **no `Company`** → **skip and report**. Such a tenant also has no branch-scoped data
   (every branch FK chains through `Company`), so skipping is safe. Do **not** invent a company —
   legal name and tax id are real-world data we do not have.

Reverse is a **deliberate no-op**. Un-setting a default flag, or deleting a branch that other rows
may already reference, is more destructive than leaving it in place, and the accompanying schema
migration is reversible on its own. (The first draft of this plan proposed deleting marked branches
on reverse; that was dropped as more dangerous than the state it would undo.)

### 4.2 Default stock location per warehouse

For every `Warehouse`, create `StockLocation(code="MAIN", name="Main", location_type="STORAGE",
is_sellable=True, is_default=True)` if the warehouse has no default, and set
`Warehouse.default_location`. Deterministic, 1:1, fully reversible. Also create one
`location_type="TRANSIT"` location per branch, used by the transfer workflow in M3.

### 4.3 User branch access

For each `User` with `branch_id IS NOT NULL`, create
`UserBranchAccess(user, branch, is_default=True, status="ACTIVE", starts_on=user.created_at::date)`
with the access profile derived from the user's existing role: `branch_manager` → `Branch Manager`
profile, everything else → `Branch Staff`. Profiles are seeded by the same migration from the flat
codenames the roles already hold.

Explicitly **not** backfilled:

* `SchoolCampusAccess` is **not** copied into `UserBranchAccess`. School authorisation keeps its own
  table (D-School, architecture §6); copying it would silently grant retail branch access.
* Users with `branch_id IS NULL` get **no** access rows. They keep today's behaviour until an admin
  grants access — `resolve_branch_scope` falls back to `User.branch` while a user has zero
  `UserBranchAccess` rows, so nobody is locked out by the migration.

### 4.4 Stock movement branch

`StockMovement.branch = StockMovement.warehouse.branch` and
`StockMovement.location = warehouse.default_location`; same for `InventoryTransaction`. This is a
pure FK dereference — `Warehouse.branch` is already `NOT NULL`, so **every** historical row gets a
correct branch and none is guessed. Run as a chunked `UPDATE … FROM warehouses` on PostgreSQL.
Reverse sets both columns back to `NULL`.

Location is a *default* assignment, not a claim about where the goods physically were; it is recorded
as such (`metadata["location_backfilled"] = true`) so later bin-level reporting does not mistake it
for a real observation.

### 4.5 POS terminals and registers

For each branch that has at least one `CashierSession` **or** one `Invoice`, create one
`PosTerminal(code="POS-1", name="Main Terminal")` and one `CashRegister(code="REG-1",
name="Main Register")`, then set `CashierSession.terminal`/`register` for that branch's sessions.
Branches with no POS history get nothing (a terminal is created when POS is first configured).
`cash_account` on the register is left `NULL` — it is a real accounting choice, not derivable.

### 4.6 Journal line branch

`JournalLine.branch = JournalLine.entry.branch` where the entry's branch is set; otherwise `NULL`.
`JournalEntry.branch` itself is **not** backfilled: an entry's branch would have to be inferred from
its source document across a dozen event types, and a wrong branch on a posted journal line is a
financial misstatement. Unassigned lines are reported (§5) and shown as "Unassigned" in branch
finance reports so consolidated totals still reconcile (architecture §4, D8).

## 5. Validation

A management command `python3 manage.py branch_migration_report` (read-only, added in M1) prints, per
tenant:

| Check | Expected after backfill |
|---|---|
| Tenants with no company (skipped by 4.1) | listed explicitly, count reported |
| Tenants with ≥ 2 `is_default` branches | 0 |
| Tenants with 0 `is_default` branches (having ≥ 1 branch) | 0 |
| Warehouses with no default `StockLocation` | 0 |
| `StockMovement` / `InventoryTransaction` with `branch IS NULL` | 0 |
| `StockMovement.branch_id != warehouse.branch_id` | 0 |
| `StockTransfer` rows whose source and destination branch differ | listed (pre-existing data, D4) |
| `CashierSession` with POS activity and no terminal | 0 |
| `JournalLine.branch IS NULL` where `entry.branch IS NOT NULL` | 0 |
| `JournalLine` unassigned (entry has no branch) | reported as a number, expected > 0 |
| Users with `branch_id` and no `UserBranchAccess` | 0 |
| Sum of per-branch on-hand vs. `Inventory` total | equal |

The same checks run as tests in `tests/verification/test_branch_migration.py` against a seeded
multi-branch fixture (see `BRANCH_TEST_MATRIX.md`, rows MIG-1…MIG-6), so a regression in a backfill
is caught in CI rather than on a customer database.

## 6. Exit criteria before any `NOT NULL`

A column added by this plan may be tightened in M8 only when **all** of the following hold:

1. `branch_migration_report` shows **zero** `NULL`s for that column on every production tenant, on
   two consecutive runs at least 7 days apart.
2. Every write path for that table has been shown to stamp the branch — verified by a test, not by
   reading code — and has been live for at least one full reporting period.
3. The column is not one deliberately left nullable: `AuditLog.branch`, `JournalEntry.branch`,
   `JournalLine.branch`, `Notification.branch`, and `User.branch` stay nullable permanently
   (historical rows and tenant-wide records legitimately have no branch).
4. On PostgreSQL the constraint is added as `NOT VALID` first and validated in a second migration
   (`SeparateDatabaseAndState` + `RunSQL`), so the table is not rewritten under an `ACCESS EXCLUSIVE`
   lock. On SQLite (desktop) Django's table rebuild is acceptable — those databases are single-user
   and small.

## 7. School

No wave touches `apps/school`. The 20+ School tables that already carry `branch` keep their existing
`NOT NULL` FKs untouched, `SchoolCampusAccess` keeps its own semantics, and §4.3 explicitly does not
read or write it. If a School tenant has no retail data, M2–M4 backfills simply find zero rows. The
School work currently in the tree is uncommitted; branch migrations are numbered after whatever
School migrations exist at generation time, and branch commits stage by explicit path only.

## 8. Deployment runbook

Per environment, in order:

1. `git pull` on a tagged release; `pip install -r requirements.txt` (M6 adds `cryptography`).
2. **Back up the database** (`pg_dump -Fc`). This is the rollback of last resort and is mandatory
   before any wave containing a backfill.
3. `python3 manage.py migrate --plan` and read it. Confirm the wave contains no unexpected app.
4. `python3 manage.py migrate`. M1–M5 are online-safe: nullable `AddField` on PostgreSQL 11+ does not
   rewrite the table, and the backfills are chunked `UPDATE`s.
5. `python3 manage.py branch_migration_report` and compare against §5.
6. Smoke: log in, open the branch switcher, run one POS sale, one stock movement, one report.
7. On failure: `python3 manage.py migrate <app> <previous_number>` for the wave (every migration in
   M1–M5 is reversible), then restore from backup if a reverse itself fails.

Desktop (SQLite, `config.settings.desktop`) runs the same waves; because SQLite rebuilds tables on
`ALTER`, run the migration with the app closed and the database file backed up.

## 9. Open questions for the user

1. **Tenants with no `Company`** — confirm that skipping them (§4.1 case 4) is correct, or supply the
   company data to create.
2. **Pre-existing cross-branch `StockTransfer` rows** — leave as historical records (recommended), or
   convert them into completed `BranchTransferRequest`s? Conversion would fabricate dispatch/receipt
   timestamps that never existed.
3. **`JournalEntry.branch` gaps** — accept an "Unassigned" bucket in branch P&L (recommended), or
   fund a per-event-type derivation pass with accounting sign-off?

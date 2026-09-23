# Multi-Branch Architecture — Phase 1 Audit & Design

Status: **Phase 1 (audit + architecture + migration plan). No code has been changed.**
Audited: 2026-09-19, against the working tree on `main` (121 files uncommitted, including the School work).
Companion docs: [BRANCH_MIGRATION_PLAN.md](BRANCH_MIGRATION_PLAN.md), [BRANCH_TEST_MATRIX.md](BRANCH_TEST_MATRIX.md).

## 1. Domain vocabulary (non-negotiable)

```
Tenant (platform.Tenant)            the paying customer / isolation boundary
 └─ Company (settings_app.Company)  legal entity record (name, tax id, logo)
     └─ Branch                      operating unit: own staff, sales, cash, P&L
         └─ Warehouse               physical/logical stock holder, belongs to exactly one Branch
             └─ StockLocation       bin / shelf / shop floor inside one Warehouse
Branch
 └─ PosTerminal                     a device/lane; defaults to a warehouse + location + register
     └─ CashRegister                a cash drawer (its own ledger cash account); a terminal *references* one
```

Distinct from the above:

| Concept | What it is | Relationship |
|---|---|---|
| `platform.ShopGroup` | Several **tenants** owned by one organisation (e.g. a cafeteria chain). Cross-tenant. | Unrelated to Branch. Multi-branch is *within* one tenant; do not merge. |
| School **Campus** | Today implemented *as* a `Branch` row (`SchoolCampusAccess.branch`, `SubjectOffering.branch`, campus scoping in `apps/school/policies/access.py`). | See §6. |
| `BusinessUnit` (finance) | P&L slice by **industry module** (Gym vs Hotel). | Orthogonal to Branch; both are dimensions. |
| `CostCenter` (finance) | Free-form department/project dimension. | Orthogonal to Branch. |

## 2. Audit findings and classification

Legend: **KEEP** as is · **EXTEND** add fields/behaviour · **REFACTOR** change internals, keep contract · **MIGRATE** data move · **CREATE** new · **DEPRECATE** stop using.

### 2.1 Tenancy & organisation

| Item | Where | Finding | Class |
|---|---|---|---|
| Tenant scoping | `core/tenancy.py`, `core/models/tenant.py` | `TenantScopedModel` (nullable `tenant` FK), `apply_tenant_scope`, host-resolved tenant, fail-closed for shop users. Solid. | KEEP |
| `Company` | `settings_app/models/setting.py` | One row per legal entity; `Branch.company` is **required**. | KEEP |
| `Branch` | same file | Only `name, code, address, phone, email, is_active, is_default`. Unique `(tenant, code)`. No manager, type, status enum, city/region/country, geo, opening date, currency, timezone, prefixes, default accounts/warehouse. | EXTEND |
| `Setting` | same file | Already has optional `branch` and `company` FK → per-branch operational settings need no new store. | KEEP |
| `User.branch` | `authentication/models/user.py` | Single FK. Used as the *implicit* branch by inventory/POS/API views (`getattr(request.user.branch,"id")`). | KEEP as "home/default branch"; authorization moves to `UserBranchAccess` |
| Roles / permissions | same | **Global** `Role` (name unique across all tenants) with flat codename permissions: `(role ∪ direct) − revokes`. No branch scope. `has_permission(code)` is unscoped. `branch_manager` & `shop_group_manager` role slugs exist but nothing branch-specific enforces them. | EXTEND (scope-aware check) |
| School campus access | `school/models/foundation.py::SchoolCampusAccess` | A per-(user, branch) grant, School-only. Precedent for the generic model. | KEEP; later delegate to generic access |

### 2.2 Inventory

| Item | Finding | Class |
|---|---|---|
| `Warehouse` | FK `branch` (required, unique `(branch, code)`), `is_default`. Already 1 Branch : N Warehouses. | KEEP + EXTEND (type, manager, status) |
| `StockLocation` | **Does not exist.** | CREATE |
| `Inventory` | Balance per **(product, warehouse)**: `quantity, reserved_quantity, damaged_quantity, returned_quantity`. `available = quantity − reserved`. Product has **no** `quantity` field → the "no company-wide product.quantity" rule is already satisfied. | KEEP as warehouse-level balance; see D2 |
| Product variants | **None exist** (`grep` finds no Variant model). | Ledger `variant` column = nullable placeholder; do not invent a variant system in this project |
| Reservation | `InventoryService.reserve_quantity / unreserve_quantity / consume_reserved` with `_locked_inventory` (`select_for_update`). Used by POS holds. | KEEP — reuse for transfer reservation |
| Ledgers | **Two overlapping tables**: `StockMovement` (type, qty, reference, notes) and `InventoryTransaction` (before/after/change per inventory row). Neither has branch, location, unit cost, reason enum, actor beyond `created_by`, or the required movement types (only adjustment/purchase/sale/transfer_in/out/return). | EXTEND `StockMovement` as the canonical ledger; keep `InventoryTransaction` as per-balance audit trail (see D3) |
| `StockTransfer` (+Line) | **Immediate** `draft→confirmed`: source −qty, destination +qty in one atomic step. This is *exactly* the pattern the spec forbids for inter-branch moves. It also does **not** enforce same-branch (`branch` defaults to source's branch; destination may belong to another). No in-transit, no reservation, no receipt, no discrepancy. | KEEP restricted to same-branch warehouse-to-warehouse moves; CREATE `BranchTransferRequest` workflow for inter-branch (D4) |
| `InventoryAdjustment` | Warehouse + branch, draft→confirmed. | KEEP; emit new ledger fields |
| Warehouse resolution for sales | `InventoryService.resolve_warehouse_for_branch(branch)` = branch default warehouse. Invoices carry **no** warehouse. | REFACTOR (explicit warehouse on sale/POS) |
| Concurrency | Row locks via `select_for_update` (no-op on SQLite). Test DB is in-memory SQLite. | Concurrency gates must run on PostgreSQL (precedent: `tests/unit/test_school_postgresql.py`) |

### 2.3 POS / Sales / Purchases

| Item | Finding | Class |
|---|---|---|
| `Invoice`, `Quotation`, `Payment`, `Expense`, `SaleRefund`, `DocumentSequence` | All have required `branch` FK; per-branch document sequences already exist. No warehouse, terminal, register. | KEEP + EXTEND (nullable warehouse/terminal/register) |
| `CashierSession` | branch + cashier + opening float / counted / expected / variance. No terminal, register, warehouse, location, variance-approval, cash-in/out. | EXTEND (this *is* the POS Shift) |
| `PosTerminal`, `CashRegister` | Do not exist. | CREATE |
| `Payment` | Tender line: method enum (`cash, mobile, card, on_account, other`), free-text `reference`. No provider, intent, or verification. Trusts caller for success. | KEEP as tender; provider payments arrive via `PaymentIntent` and *create* a `Payment` only on verified success |
| `PurchaseOrder` | Required `branch`. No destination warehouse/location on receipt was found in the model; receiving goes through `receiving_service.py`. | EXTEND (explicit receiving warehouse) — verify in Phase 3 |

### 2.4 Finance

| Item | Finding | Class |
|---|---|---|
| Central engine | `posting_service`, `posting_rule_service`, `journal_service`, `equation_service`, immutability + maker-checker tests already exist. | KEEP — branch is a *dimension*, never a second engine |
| `JournalEntry.branch` | Nullable FK on the entry header. | KEEP |
| `JournalLine` | Has `cost_center`, `business_unit`; **no** `branch`. Entry-level branch is enough for single-branch entries but breaks for entries touching two branches (e.g. inter-branch settlement). | EXTEND (nullable `branch` on line, defaulting from entry) — decide in Phase 5 |
| Account mapping | `account_mapping.py`, posting rules exist. Branch default cash/sales/expense accounts need a branch-level override layer. | EXTEND |

### 2.5 Cross-cutting

| Item | Finding | Class |
|---|---|---|
| Notifications | `Notification` is per-user, in-app only, fixed 5-value type enum, has `link` + `metadata` but **no** branch, severity, entity type/id, audience, expiry. `NotificationService` is imperative (callers invoke it directly). No email/SMS channels. | EXTEND model; CREATE event dispatcher (subscribers, not direct calls) |
| Audit | `AuditLog` (tenant, user, action, module, entity, old/new JSON, IP). `write_audit()` is explicit. No branch column. | EXTEND (nullable `branch`) |
| Background jobs | Celery configured (`config/celery.py`, beat schedule, eager in tests). Tasks live in `notifications`, `finance`, `platform`. | KEEP |
| SMS | **None.** | CREATE |
| Payment gateways | **None.** No PaymentIntent, provider, webhook, or reconciliation. | CREATE |
| Secret storage | `core/security/secret_hygiene.py` only checks `SECRET_KEY`/DB password. **No `cryptography` dependency and no encrypted-credential store.** | CREATE (D6) |
| Reports | `reports/services/report_service.py` + packs; no consistent branch / multi-branch filter contract. | EXTEND |
| Frontend | No branch context store (only `authStore`, `uiStore`); branch id is sent ad-hoc in some API calls. No Organization workspace, no Integrations page, no notification center beyond `modules/notifications`. | CREATE |

## 3. Target model (new / changed)

Names are proposals; app placement in D1.

```
Branch (extend)
  + branch_type, status[ACTIVE|INACTIVE|TEMPORARILY_CLOSED|ARCHIVED] (is_active kept in sync), legal_name,
    manager FK(User), city, region, country, latitude, longitude, opening_date, timezone, currency,
    receipt_prefix, invoice_prefix, order_prefix, transfer_prefix,
    default_warehouse, default_cash_account, default_sales_account, default_expense_account, notes

BranchStaffAssignment / UserBranchAccess   user, branch, access_profile, is_default, starts_on, ends_on, status
BranchAccessProfile                        tenant, name, permission codenames (+ is_manager flag for assistant/primary)
Warehouse (extend)                          + warehouse_type, manager, status
StockLocation                               tenant, warehouse, code, name, location_type[STORAGE|SHOP_FLOOR|RECEIVING|TRANSIT|DAMAGED], is_sellable, is_default
PosTerminal                                 tenant, branch, code, name, default_warehouse, default_location, default_cash_register, status, device_identifier
CashRegister                                tenant, branch, code, name, cash_account, status
CashierSession (extend)                     + terminal, register, warehouse, location, cash_in, cash_out, approval fields
StockMovement (extend = canonical ledger)   + branch, location, unit_cost, reason, metadata, actor, extended movement types
BranchTransferRequest (+Line, +Shipment, +Event)
                                            see STOCK_TRANSFER_WORKFLOW.md (Phase 4)
ReplenishmentRule                           branch, product, min, target, policy[MANUAL|SUGGEST_ONLY|AUTO_CREATE_REQUEST]
Notification (extend)                       + branch, severity, entity_type, entity_id, audience, expires_at, action_url
IntegrationCredential / SmsProvider / SmsTemplate / SmsLog
PaymentProviderConfig / PaymentIntent / PaymentWebhookEvent / ReconciliationRecord
```

### Scope resolution (backend authoritative)

`core/branching.py` (new) exposes `resolve_branch_scope(request) -> BranchScope`:

1. Read the requested branch from header `X-Branch-Id` (or `all`). **Untrusted input.**
2. Intersect with the branches the user actually holds via active `UserBranchAccess` (date-window + status), inside the tenant already resolved by `core/tenancy`.
3. Return `BranchScope(branch_ids, is_all, permission_lookup)`. Anything not authorised → `403`/empty, never silently widened.
4. `has_branch_permission(user, codename, branch)` = profile permissions for that branch (elevated admins bypass, as today). Services accept a `BranchScope`; **POS / stock-mutating endpoints reject `is_all`** (ambiguous scope).

Fail-closed and additive: a user with *no* `UserBranchAccess` rows keeps today's behaviour (their `User.branch`) until backfilled — see the migration plan.

## 4. Key design decisions (please confirm before Phase 2)

| # | Decision | Recommendation | Why |
|---|---|---|---|
| D1 | Where does new code live? | New app `apps/organization` (UserBranchAccess, access profiles, StockLocation, PosTerminal, CashRegister, branch scope). `Branch` stays in `settings_app` (extended in place; renaming the table would touch ~60 FKs). Transfers in `apps/inventory`. SMS/payments in new `apps/integrations`. | Avoids a destructive `Branch` move; one owner per concept. |
| D2 | Location granularity of balances | Keep `Inventory` = (product, warehouse) as the authoritative, lockable balance. `StockLocation` is recorded on **ledger rows and transfer lines**; optional per-location balance is *derived* from the ledger. Every warehouse gets an auto-created default location. | Changing `Inventory`'s unique key to include location would break POS, holds, receiving, and 15+ callers. Availability/reservation stay simple and correct. Revisit only if per-bin stock counts are a hard requirement now. |
| D3 | Ledger | Extend `StockMovement` to be the single canonical ledger (append-only; corrections are reversing rows). `InventoryTransaction` stays as balance before/after audit. No third table. | "Never modify stock silently" without duplicating concepts. |
| D4 | Old `StockTransfer` | Keep for **same-branch** warehouse moves (add validation). Inter-branch always goes through `BranchTransferRequest`. Deprecate cross-branch use of `StockTransfer`. | Preserves the existing API/tests; enforces the "no instant source−/dest+" rule where it matters. |
| D5 | In-transit representation | `in_transit` is modelled by ledger rows (`TRANSFER_OUT` at dispatch; `TRANSFER_IN` at receipt) and per-line dispatched/received quantities on the transfer, plus a virtual "in transit" figure = Σ dispatched − Σ received − Σ discrepancy. No stock is credited to the destination until receipt. | Company stock = branch on-hand + in-transit, without a fake warehouse. |
| D6 | Secrets | Add `cryptography` (Fernet) with a key from env (`INTEGRATION_ENCRYPTION_KEY`, rotation-capable via MultiFernet). API returns only `has_secret: true` + masked tail. Never logged, never in audit text. | No existing encrypted store; env-only is insufficient for tenant-entered credentials. |
| D7 | Payments/SMS concrete providers | Build framework + `MockProvider` + generic `CustomHttp` SMS adapter only. No fabricated Somali provider endpoints. | Per spec §69. |
| D8 | Transfer accounting | Internal transfers post **no revenue and no P&L**. Ledger value moves between branch inventory dimension and an in-transit clearing asset; company inventory total is unchanged. If cost/profit centres are enabled, use a transfer-clearing account that nets to zero at company level. | Keeps `Assets = Liabilities + Equity` and TB balanced. |
| D9 | Concurrency proof | Gates run against PostgreSQL 14 (as School did). SQLite ignores `select_for_update`, so SQLite results cannot prove concurrency safety. | Honest verification. |

## 5. Phase plan and gates

| Phase | Scope | Gate to leave |
|---|---|---|
| 1 | Audit, architecture, migration plan (**this doc**) | Docs reviewed; D1–D9 confirmed |
| 2 | Branch core fields, UserBranchAccess + profiles, branch scope + enforcement, Warehouse/StockLocation, audit, Organization UI shell | Branch CRUD/RBAC/isolation tests green; existing baseline unchanged |
| 3 | Ledger extension, branch stock views, cross-branch availability | Ledger + availability tests; invariants (no negative, ledger ⇔ balance) |
| 4 | Transfer workflow, reservation, transit, receipt, notifications hooks | Concurrency tests on PostgreSQL |
| 5 | POS terminals/registers/shifts, sales/purchases/finance branch dimension | POS + finance branch isolation; TB balanced |
| 6 | Reports, dashboards, alert centre, notification center | Consolidated == Σ branches |
| 7 | SMS framework | Adapter + failure-isolation tests |
| 8 | Payment framework | Idempotency/webhook/reconciliation tests |
| 9 | Regression, concurrency, browser, security | Final report (§70 of the brief) |

## 6. School compatibility

* School today uses `Branch` as **Campus** (`SchoolCampusAccess.branch`, `SubjectOffering.branch`). That existing choice is **left untouched**; this project does not rename, migrate, or re-key any School table.
* Campus ≠ retail branch semantically (a campus has no POS, stock, or transfers). Branch-management UI and stock features are gated by module: a School-only tenant sees "Campuses" wording and none of the retail sub-navigation.
* `SchoolCampusAccess` remains the source of truth for School authorisation. When generic `UserBranchAccess` exists it is *read-compatible*: no School behaviour changes, and School access is not silently granted by (or revoked by) branch access. A later School phase may make Campus an explicit profile *on* Branch; that is out of scope here.
* Migrations must not touch `apps/school` tables. The School work in the tree is currently **uncommitted** (untracked `apps/school/`, several modified files); Branch phases must build on top of it without staging or reverting it.

## 7. Risks

1. **Dirty working tree** (121 modified/untracked files incl. School and cafeteria). Branch migrations are numbered after existing ones; commits must be scoped by path.
2. **Existing baseline is not green** — see the migration plan for the recorded baseline; new-regression counting is relative to it.
3. Implicit-branch code paths (`request.user.branch`) are widespread; they will be moved onto `BranchScope` incrementally, module by module, keeping the old fallback until each module is covered by tests.
4. SQLite test DB cannot prove locking behaviour (D9).

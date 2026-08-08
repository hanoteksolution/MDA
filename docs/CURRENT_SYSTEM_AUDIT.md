# Current System Audit Report

**Project:** MDA Retail ERP & POS  
**Audit date:** 2026-08-07  
**Scope:** Full repository discovery — backend, frontend, desktop, database models, platform layer, docs, infrastructure  
**Status:** Phase 0 complete — **no destructive refactoring performed**

---

## 1. Executive summary

MDA is a **working modular-monolith retail ERP/POS** with a hybrid deployment model:

| Layer | Actual stack |
|-------|----------------|
| Backend | Django 5 + DRF + SimpleJWT |
| Frontend | **React 19 + Vite 6 + React Router 7 + Zustand** (not Next.js) |
| Desktop | Tauri 2 shell + bundled local Django API (SQLite) |
| Database | PostgreSQL (cloud/VPS) · SQLite (dev/desktop) |
| Platform | Shop groups, tenants, subscriptions, Waafi/EVC billing, desktop sync |

The system is **far past the “planning phase”** described in the root README. Core POS, catalog, inventory adjustments, sales documents, platform multi-shop admin, and a futsal vertical are implemented.

It is **not yet** a secure shared-database multi-tenant SaaS ERP. Tenancy exists at the platform overlay; most operational tables lack `tenant_id` and tenant middleware.

---

## 2. Critical stack correction

| Master prompt assumption | Reality |
|--------------------------|---------|
| Next.js frontend | **Vite + React SPA** (`frontend/package.json`) |
| Pure cloud multi-tenant web ERP | **Hybrid:** desktop SQLite shops + cloud platform oversight |
| Schema-per-tenant | **Shared schema**; isolation incomplete |
| Full finance / Celery / Redis in use | Packages present or stubbed; **Celery/Redis unused**; finance app not installed |

All target architecture and migration plans must start from this reality.

---

## 3. Repository map

```
mda/
├── backend/          Django modular monolith + /api/v1
├── frontend/         React SPA (Vite)
├── desktop/          Tauri shell; sync engine folders mostly stubs
├── infrastructure/   Docker, nginx, VPS scripts
├── shared/           Empty placeholders (constants/schemas)
├── docs/             Architecture + product docs (partially outdated)
├── scripts/
└── Makefile
```

---

## 4. Backend audit

### 4.1 Installed Django apps

From `backend/config/settings/base.py`:

| App | Role | Maturity |
|-----|------|----------|
| `core` | BaseModel, pagination, exceptions | Solid |
| `apps.authentication` | User, Role, Permission, setup, staff eval | Solid |
| `apps.settings_app` | Company, Branch, Setting | Solid |
| `apps.audit` | AuditLog model | Partial (no v1 API wired) |
| `apps.products` | Category, Brand, Unit, Product | Solid |
| `apps.inventory` | Warehouse, Inventory, movements, adjustments | Partial |
| `apps.customers` | Customer | Solid (basic) |
| `apps.suppliers` | Supplier | Solid (basic) |
| `apps.purchases` | PurchaseOrder + items | Partial (no receiving) |
| `apps.sales` | Quotation, Invoice, Expense, sequences, POS | Strong |
| `apps.platform` | Tenant, ShopGroup, subscriptions, sync | Strong |
| `apps.futsal` | Courts, bookings, ledger | Niche complete |

**On disk but NOT in `INSTALLED_APPS`:** `apps/finance`, `apps/notifications`, `apps/reports` (stubs). Finance/reports live as API + analytics services only.

### 4.2 Base model pattern

`backend/core/models/base.py`:

- UUID primary keys
- Soft delete (`deleted_at`, `deleted_by`)
- Audit fields (`created_by`, `updated_by`, timestamps)

Money and quantities use **`DecimalField`** (typically 18,4 for shop ops; 12,2 for platform billing). Good foundation.

### 4.3 Authentication & RBAC

- **JWT** (SimpleJWT): access ~60m, refresh 7d, rotate + blacklist
- Custom RBAC: `Role`, `Permission`, `RolePermission`, `UserPermission`
- `HasPermission(codename)` factory; platform admins / superusers bypass
- Bootstrap catalog in `apps/authentication/bootstrap.py` (~50+ codenames)
- User links: `role`, `branch`, `tenant`, `managed_shop_group`, `is_platform_admin`

**KEEP** — extend with module-scoped and industry roles; do not replace with Django Groups.

### 4.4 Multi-tenancy (current)

Hierarchy in code:

```
ShopGroup → Tenant (shop) → Company → Branch → Warehouse / documents
```

| Model | Tenant linkage |
|-------|----------------|
| User | FK `tenant` |
| Company | FK `tenant` (nullable) |
| Platform models | Own tenant world |
| Product, Inventory, Invoice, PO, Customer, Supplier, Futsal | **No tenant_id** |

Operational isolation today relies on:

1. **Desktop mode:** one SQLite DB per shop (physical isolation)
2. **Cloud platform:** admin oversight + sync snapshots + `sync_secret`
3. **Ad hoc** `accessible_tenant_ids` for shop-group managers

There is **no** hostname/subdomain tenant middleware and **no** automatic queryset tenant scoping on shop APIs.

### 4.5 Domain relationship map (as implemented)

```
User ──role──► Role ──► Permission
  │
  ├── tenant ──► Tenant ──► ShopGroup
  │                 └── TenantSubscription ──► SubscriptionPlan
  │                              └── SubscriptionPayment
  └── branch ──► Branch ──► Company ──► Tenant?

Category ◄── Product ──► Brand, Unit
                │
                ▼
         Inventory (product × warehouse)
                │
         Warehouse ──► Branch
                │
         StockMovement / InventoryTransaction / InventoryAdjustment

Customer ◄── Invoice / Quotation ──► Branch
                │
           InvoiceItem ──► Product
                │
         (payment method encoded in Invoice.notes)

Supplier ◄── PurchaseOrder ──► Branch
                └── PurchaseOrderItem ──► Product

Expense ──► Branch   (lives in sales app)

Court / Team / Player / CourtBooking / FutsalLedgerEntry ──► Branch
```

### 4.6 POS transaction flow

**Entry:** `POST /api/v1/pos/checkout/` → `PosService.checkout` (`apps/sales/services/pos_service.py`, ~850 LOC)

1. Resolve branch + customer (or Walk-in)
2. Require waiter; compute discount/tax/total (quantize to 0.01)
3. Encode payment method / merchant / waiter into **`Invoice.notes`**
4. Create/update `Invoice` + `InvoiceItem` via `InvoiceService`
5. Stock deduction via `InventoryService.apply_invoice_quantity_deltas` (`select_for_update`)

**Also:** hold sales (`on_hold`), waiter performance, receipt numbers via `DocumentSequence`.

**Gaps:**

| Capability | Status |
|------------|--------|
| Payment entity / split payment rows | Missing (notes-based) |
| Cashier open/close sessions | Missing |
| Stock reservation on hold | Claimed; **actually deducts quantity**; `reserved_quantity` unused |
| Refunds / returns workflow | Incomplete vs target |
| Idempotency keys | Missing |

### 4.7 Inventory

**Implemented:** warehouses, stock list/low/out, adjustments with movement + transaction ledger, sale stock deltas with locking.

**Missing / incomplete:** warehouse transfers (types exist, no service), purchase receiving → stock in, batch/lot/serial/expiry, locations, proper reserve/unreserve.

### 4.8 Purchases

CRUD + summary only. Status can be set, but **no goods-receipt workflow** that increments inventory. `quantity_received` defaults unused.

### 4.9 Finance

- Real `Expense` model under sales
- `GET /api/v1/finance/summary/` — analytics / synthetic accounts
- No chart of accounts, journal entries, AR/AP ledgers
- KPI “expenses” may conflate PO totals vs `Expense` rows

### 4.10 Platform & sync

Strong platform service (~1456 LOC): tenants, subscriptions, Waafi payments, shop groups, KPIs.  
Sync: `sync_service` + `sync_catalog` — desktop push/pull with `tenant_slug` + `sync_secret`; `ShopSyncSnapshot`.

### 4.11 Middleware, Celery, cache

- Standard Django middleware only — **no tenant resolver**
- Celery/Redis in requirements but **not configured / not used**
- `backend/tasks/` empty

### 4.12 API surface (`/api/v1/`)

`health`, `sync`, `setup`, `platform`, `auth`, `users`, `roles`, `settings`, `dashboard`, `products`, `categories`, `brands`, `units`, `inventory`, `warehouses`, `customers`, `suppliers`, `purchases`, `sales`, `pos`, `finance`, `reports`, `futsal`

Not wired: `api/v1/audit/`, `api/v1/notifications/`

### 4.13 Tests

**No executable tests.** Unit/integration and app test dirs contain `.gitkeep` only. `config/settings/test.py` exists unused.

---

## 5. Frontend audit

### 5.1 Stack

React 19.2 · Vite 6 · React Router 7 · Zustand · Tailwind 3 · Radix/shadcn-style UI · Recharts · jsPDF / barcode / QR · Framer Motion · `@tauri-apps/api`

### 5.2 Structure

```
frontend/src/
  app/          router + route groups
  pages/        auth, dashboard
  layouts/      AppShell, Sidebar, Header
  modules/      pos, sales, products, inventory, purchases,
                customers, suppliers, finance, reports,
                settings, admin, platform, futsal
  services/api/ http.ts + domain clients
  store/        authStore, uiStore
  documents/    large PDF/print engine
  design-system/ tokens
```

### 5.3 Maturity by module

| Module | Maturity | Reuse for SaaS transform |
|--------|----------|--------------------------|
| POS | **High** | Keep/extend — do not rewrite |
| Platform | **High** | Extend for onboarding/billing UX |
| Sales | High–med | Keep |
| Products | Med–high | Keep; add attributes later |
| Inventory | Med | Extend receiving/transfers/batches |
| Purchases | Med | Extend receiving |
| Customers/Suppliers | Med | Extend CRM |
| Reports | Med | Extend |
| Admin (users/roles) | Med | Keep permission matrix |
| Finance | Low | Mostly summary UI |
| Notifications | Stub | Create |
| Futsal | Niche | Pattern for industry modules |

### 5.4 Auth & permissions (UI)

- JWT in `localStorage`; refresh rotation in `http.ts`
- `ProtectedRoute` + `PermissionGuard` + sidebar filtering
- Desktop provision / cloud connection flows

Frontend hiding is present; **backend enforcement remains source of truth**.

### 5.5 Design system

Emerald primary, CSS variables, shared DataTable/KPI/forms. Functional enterprise admin look. Not yet “Stripe/Linear premium” density, but reusable.

---

## 6. Desktop & offline

| Piece | Status |
|-------|--------|
| Tauri 2 shell + local API sidecar | Implemented |
| Connection config (cloud URL, tenant_slug, sync_secret) | Implemented |
| Frontend sync API calls to Django `/sync/*` | Implemented |
| `desktop/sync/{engine,queue,conflict,...}` | **Stubs only** |
| Client-side SQLite sync engine in Rust | **Not present** |

Offline reality = **local Django + SQLite**, not a separate offline sync package.

---

## 7. Database audit

### 7.1 Strengths

- UUID PKs, soft delete, Decimal money
- Branch-scoped document uniqueness (`branch` + number)
- Stock movement / transaction tables for auditability
- Platform billing tables with reference codes
- Inventory `select_for_update` on sale paths

### 7.2 Scalability / tenancy risks

1. **Global uniques** on `Product.sku`, `Product.barcode`, `Brand.name`, `Customer.customer_code`, `Supplier.supplier_code` — break shared multi-tenant catalogs
2. **No tenant_id** on operational tables — cross-tenant leak risk on shared Postgres
3. Soft-delete + unique constraints can collide on restore
4. Payment data in free-text notes — poor reporting/integrity
5. No batch/expiry indexes (pharmacy not started)
6. Missing composite indexes for tenant+branch+status query patterns (once tenant_id added)

### 7.3 Tenant readiness verdict

| Strategy | Fit today |
|----------|-----------|
| Shared schema + `tenant_id` + middleware | **Recommended next step** |
| Schema-per-tenant | High risk immediate migration; design later |
| DB-per-tenant (desktop) | Already works for hybrid shops |

---

## 8. Documentation drift

Existing docs under `docs/architecture/` and `docs/product/` still describe a **single-tenant offline desktop ERP** and omit live platform/tenant tables. `FEATURE_ROADMAP.md` lags implementation. Root README still says “Planning phase complete.”

This audit + companion docs supersede those for transform planning.

---

## 9. Gap analysis vs target SaaS ERP

Classification key: **KEEP** · **REFACTOR** · **EXTEND** · **REPLACE** · **CREATE**

| Domain | Verdict | Notes |
|--------|---------|-------|
| Modular monolith layout | KEEP | Adapt; don’t microservice |
| JWT + custom RBAC | EXTEND | Add industry roles, module gates |
| BaseModel / Decimal / soft delete | KEEP | |
| Company / Branch / Warehouse | KEEP | Add tenant FK chain |
| Platform Tenant / Subscription | EXTEND | Domains, business types, modules, plans features |
| Product catalog | EXTEND | Tenant scope + attribute engine |
| POS core | EXTEND | Payments entity, sessions, holds/reserve, refunds |
| Inventory ledger | EXTEND | Receiving, transfers, batches, FEFO |
| Purchases | EXTEND | GRN / receive workflow |
| Customers / Suppliers | EXTEND | Tenant scope, CRM, balances ledger |
| Expenses | REFACTOR | Move toward finance domain |
| Finance / GL | CREATE | Chart of accounts, journals |
| Pharmacy | CREATE | |
| Gym | CREATE | |
| Restaurant KDS | CREATE | Architecture later; POS waiter already partial |
| Futsal | KEEP | Reference industry module |
| Notifications | CREATE | |
| Celery / Redis | CREATE | Wire existing deps |
| Tenant middleware / isolation | CREATE | Mandatory before shared SaaS |
| Schema-per-tenant | CREATE (later) | Staged; not day-one |
| Audit API + coverage | EXTEND | |
| Next.js rewrite | DEFER | Preserve React SPA; evaluate later |
| React Native apps | CREATE (later) | Same `/api/v1` |
| Automated tests | CREATE | Mandatory for isolation + money paths |
| Feature flags / module marketplace | CREATE | |
| Subdomain routing | CREATE | After tenant resolution |

---

## 10. Technical debt (priority)

1. **No tenant isolation on shop data** (security-critical for shared cloud)
2. **Zero automated tests**
3. Payment method in `Invoice.notes`
4. Hold sales deduct stock instead of reserving
5. Purchase receiving not implemented
6. Transfers not implemented
7. Finance stubs / synthetic accounts
8. Docs and README outdated
9. Celery/Redis unused
10. Global unique SKU/barcode constraints

---

## 11. What must not be broken

During transform, treat as production-critical:

- POS checkout → invoice → stock deduction
- Document sequences per branch
- JWT login / refresh / permission checks
- Platform subscription + Waafi payment flows
- Desktop provision + sync with `sync_secret`
- Futsal bookings (existing customers)
- Soft-delete trash flows already used in UI

---

## 12. Recommended immediate next steps

1. ~~Approve this audit + companion docs~~ — done
2. ~~STEP 03 Core hygiene~~ — done (tenancy scaffolding, reserve primitives, pytest)
3. **Start STEP 04–06:** tenant foundation → domain resolution → shared-schema `tenant_id` + isolation tests
4. Keep React/Vite frontend; mobile clients will be **React Native** (same `/api/v1`)
5. Do not start Gym/Pharmacy until STEP 06 exit criteria pass

---

## 13. Companion documents

| Document | Purpose |
|----------|---------|
| [TARGET_ARCHITECTURE.md](./TARGET_ARCHITECTURE.md) | Target modular SaaS architecture |
| [MIGRATION_STRATEGY.md](./MIGRATION_STRATEGY.md) | Safe staged migration + rollback |
| [DATABASE_ERD.md](./DATABASE_ERD.md) | Current + target ERD |
| [ERP_TRANSFORMATION_ROADMAP.md](./ERP_TRANSFORMATION_ROADMAP.md) | Phased implementation roadmap |
| [MOBILE_ARCHITECTURE.md](./MOBILE_ARCHITECTURE.md) | React Native mobile clients |
| [architecture/HOLD_RESERVE_DESIGN.md](./architecture/HOLD_RESERVE_DESIGN.md) | POS hold → reserve design |

---

*End of current system audit.*

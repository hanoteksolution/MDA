# Target Architecture — Safari ERP / MDA Platform

**Status:** Target design (Phase 0)  
**Date:** 2026-08-07  
**Principle:** Evolve the existing modular monolith; do not rewrite or microservice prematurely.

---

## 1. Product vision

Transform MDA into a **secure, modular, multi-tenant, multi-industry SaaS ERP** with:

- Universal POS (retail, pharmacy, restaurant, gym, wholesale, …)
- Shared catalog, inventory, finance, CRM
- Industry modules (Pharmacy, Gym, Restaurant, Futsal, …)
- Platform billing & onboarding
- Web ERP + optional desktop hybrid + future React Native mobile
- Same Django `/api/v1` for all clients

Brand / hosting target (from product intent):

```
erp.safaritechno.com
{tenant}.erp.safaritechno.com
```

---

## 2. Non-negotiable principles

- Modular monolith first (extract services only under proven load)
- API-first; business rules on the backend
- Secure tenant isolation (never trust client-supplied tenant IDs alone)
- Decimal money; transactional stock/finance; auditable movements
- Incremental migration with rollback awareness
- **Reuse before rebuild** — especially POS, RBAC, platform billing

---

## 3. Stack decisions (reconciled with codebase)

| Layer | Target | Rationale |
|-------|--------|-----------|
| Backend | Django + DRF modular monolith | Already strong; keep |
| API | Versioned `/api/v1/` | Already present |
| DB | PostgreSQL | Cloud source of truth |
| Cache / queue | Redis + Celery | Wire existing deps |
| Web UI | **Keep React 19 + Vite SPA** for ERP | Working POS/platform; lowest risk |
| Next.js | **Optional later** for marketing / SSR tenant landing | Not a day-one rewrite |
| Desktop | Tauri + local API (hybrid) | Preserve for offline shops |
| Mobile | React Native later against same API | No separate backend |
| Isolation (near-term) | **Shared schema + `tenant_id` + middleware** | Safe vs current data |
| Isolation (long-term) | Evaluate schema-per-tenant | Only after shared-schema proven |

### Why not force Next.js immediately

The master prompt assumes Next.js. The codebase is a mature Vite SPA with POS, documents, and platform UI. A framework rewrite during tenancy/finance/pharmacy work multiplies risk. Target UX can still meet “premium SaaS admin” on React. Revisit Next.js when subdomain SSR, SEO, or BFF patterns clearly justify cost.

---

## 4. Logical architecture

```
                         SAFARI ERP / MDA
                              │
                    SaaS Platform Core
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
      Tenant               Billing                 IAM
   (resolve host)     (plans/modules)         (RBAC/JWT)
        │
        ▼
 Business Type + Module Engine
        │
 ┌──────┼─────────┬──────────┬───────────┬─────────┐
 │      │         │          │           │         │
POS Inventory Pharmacy     Gym      Restaurant  Futsal
 │      │         │          │           │         │
 └──────┴─────────┴──────────┴───────────┴─────────┘
                  │
            Shared Services
                  │
      ┌───────────┼────────────┬──────────┐
      │           │            │          │
   Finance    Reporting   Notifications  Audit
      │
      ▼
 PostgreSQL + Redis + Celery
      │
 ┌────┴──────────────┬──────────────┐
 │                   │              │
React SPA         Tauri Desktop   React Native
(Web ERP)         (hybrid offline) (later)
```

---

## 5. Backend module layout (adapt existing)

Keep `backend/apps/` naming; evolve toward clear domains:

```
apps/
  core/              # cross-cutting (or keep backend/core)
  authentication/    # IAM — KEEP/EXTEND
  platform/          # tenants, domains, plans, modules — EXTEND
  settings_app/      # company, branch, settings — EXTEND
  catalog/products/  # products + attributes — EXTEND
  inventory/         # stock ledger — EXTEND
  purchases/         # PO + GRN — EXTEND
  sales/ + pos/      # documents + POS — EXTEND
  payments/          # NEW (extract from notes)
  customers/         # CRM — EXTEND
  suppliers/         # EXTEND
  finance/           # CREATE (install + real models)
  accounting/        # may merge with finance
  reporting/         # CREATE or promote stubs
  notifications/     # CREATE
  audit/             # EXTEND
  pharmacy/          # CREATE
  gym/               # CREATE
  restaurant/        # CREATE (later)
  futsal/            # KEEP as industry module
  subscriptions/     # may stay under platform
```

Rules:

- No circular app imports; use services/events at boundaries
- Industry modules depend on core domains, never the reverse
- Feature enablement via `TenantModule` / feature flags

---

## 6. Multi-tenancy architecture

### 6.1 Entities (target)

| Entity | Purpose |
|--------|---------|
| `Tenant` | Business organization (extend existing) |
| `TenantDomain` | `arabica.erp…`, custom domains |
| `TenantSettings` | timezone, currency, locale, POS defaults |
| `BusinessType` | retail, pharmacy, gym, cafeteria, … |
| `Module` / `TenantModule` | enabled capabilities |
| `SubscriptionPlan` / `SubscriptionFeature` | SaaS entitlements |
| `TenantSubscription` | trial/active/grace/expired/suspended |

Extend existing `Tenant` / `SubscriptionPlan` / `TenantSubscription` rather than duplicating.

### 6.2 Request resolution flow

```
Request
  → Hostname
  → DomainResolver (TenantDomain | subdomain slug)
  → TenantResolver (active + subscription usable)
  → TenantContext (thread/async-local)
  → RBAC + module flags
  → Application (all queries tenant-scoped)
```

Never accept `tenant_id` from the client as the sole authority. Optional header may select branch **within** resolved tenant.

### 6.3 Isolation strategy (staged)

**Stage A (required first):** Shared PostgreSQL schema

- Add `tenant_id` (or FK) to all tenant-owned tables
- Unique constraints become `(tenant, sku)`, `(tenant, barcode)`, etc.
- Manager / queryset mixin + middleware enforcement
- Automated cross-tenant access tests

**Stage B (optional later):** Schema-per-tenant

- Provision `tenant_{slug}` schemas
- Control plane remains in `public`
- Only after Stage A stable + backup/restore drills

**Desktop hybrid remains valid:** single-tenant SQLite per shop continues to sync to cloud tenant.

---

## 7. Business type & module engine

`BusinessType` controls:

- Default enabled modules
- Default product attribute sets
- POS behavior profile (pharmacy FEFO, restaurant tables, gym memberships)
- Terminology and dashboard widgets
- Report packs

Do **not** fork the application per industry.

---

## 8. Catalog & dynamic attributes

Keep lean `Product` for transactional fields (sku, barcode, prices, unit, stock flags).

Add:

- `AttributeDefinition`, `AttributeOption`
- `ProductAttributeValue`
- `BusinessTypeAttribute`, `CategoryAttribute`

Types: text, int, decimal, bool, date, datetime, select, multi-select  
Flags: required, searchable, filterable, POS visible, reportable

Do **not** put batch expiry, serials, or money integrity into EAV.

---

## 9. Universal POS

```
Universal POS Core
  ├── Retail extension
  ├── Pharmacy extension (batch/FEFO)
  ├── Restaurant extension (tables/KDS)
  ├── Gym extension (memberships/services)
  └── Wholesale extension (tiers/MOQ)
```

Core capabilities (extend current POS):

- Search / barcode / categories / cart
- Customer, tax, discounts
- **Payment rows** (multi-tender), not notes
- Hold/resume with **reservation** semantics
- Refunds/returns
- Cashier sessions (open/close/reconcile)
- Permissions + audit
- Receipt printing (reuse documents engine)

---

## 10. Inventory

Target ledger-centric model (build on existing `StockMovement` / `InventoryTransaction`):

- Multi-branch / multi-warehouse / locations
- Adjustments, transfers, receiving, damage, returns
- Reserved vs available
- Reorder alerts
- Batch / lot / expiry / serial where module requires
- Immutable-enough movement history for every qty change

---

## 11. Industry modules (high level)

| Module | First slice | Depends on |
|--------|-------------|------------|
| Pharmacy | Medicine attrs, batches, FEFO POS, expiry reports | Catalog, Inventory, POS |
| Gym | Members, plans, subscriptions, attendance | Customers, Payments, POS |
| Restaurant | Tables, tickets, modifiers, recipes | POS, Inventory |
| Futsal | Existing | KEEP |

---

## 12. Finance foundation

- Chart of accounts, journal entries
- Cash/bank accounts, payment methods
- AR/AP from sales/purchases
- Expenses linked to GL
- P&amp;L, cash flow (reporting layer)
- Decimal only; period close later

Platform SaaS billing stays separate from tenant GL.

---

## 13. IAM / RBAC

Platform roles: Super Admin, Support, Billing  
Tenant roles: Owner, Admin, Manager, Cashier, Accountant, Inventory Manager, Pharmacist, Gym Manager, Receptionist, Trainer, Waiter, Kitchen, …

Permissions remain codename-based (`sales.refund`, `gym.attendance.checkin`, …). Backend enforces; UI hides.

---

## 14. Frontend architecture (React SPA)

Adapt existing structure; do not invent a parallel app:

```
app/
  (auth)/
  (platform)/     # platform admin
  (tenant)/       # module-aware shell
    dashboard/
    pos/
    inventory/
    …
    pharmacy/
    gym/
    settings/
```

Requirements:

- Module-aware navigation
- Permission-aware routes
- Tenant branding / business-type terminology
- Central API client (existing `services/api`)
- Premium dense admin UX (refine design tokens; avoid decorative excess)

---

## 15. Background processing & observability

Celery tasks: expiry scans, membership expiry, subscription checks, imports/exports, notifications, heavy reports.

Health: `/api/v1/health/`, DB, cache (no sensitive internals).

Structured logs + error monitoring + audit trail.

---

## 16. Deployment target

```
Internet → Cloudflare/DNS (*.erp.safaritechno.com)
  → Reverse proxy (nginx)
  → Static React SPA + Django API
  → PostgreSQL + Redis + Celery workers
```

Wildcard DNS + wildcard TLS. Desktop hybrid continues for offline-capable shops.

---

## 17. Security baseline

- Server-side tenant resolution
- Tenant-scoped object lookup
- Rate limits / brute-force protection
- Secure headers, validated uploads
- Secrets out of repo
- No passwords/tokens in audit payloads
- Cross-tenant automated tests mandatory

---

## 18. Out of scope for early phases

- Microservices split
- Immediate schema-per-tenant cutover
- Next.js rewrite
- React Native apps (API readiness first)
- Full hotel/school/hospital modules (module framework only)
- Naive bidirectional offline accounting sync

---

## 19. Success criteria (architecture)

1. Two tenants on one Postgres cannot read each other’s products/invoices
2. POS checkout remains transactional and fast
3. New industry module adds app + flags without core fork
4. Subscription/module middleware gates features safely
5. Desktop hybrid shops still sync to their cloud tenant
6. Documentation stays synchronized with implementation

---

*See also: [MIGRATION_STRATEGY.md](./MIGRATION_STRATEGY.md), [ERP_TRANSFORMATION_ROADMAP.md](./ERP_TRANSFORMATION_ROADMAP.md).*

# ERP Transform Roadmap

**Date:** 2026-08-07  
**Status:** Phase 0 complete — awaiting go-ahead before foundational coding  
**Source inputs:** Codebase audit + master SaaS ERP prompt  
**Stack reality:** Django + React/Vite/Tauri (not Next.js)

---

## How to use this document

For every step: **Analyze → Explain → Plan → DB → Backend → Frontend → Tests → Validate → Document → Stop Point.**

Risk: **L** low · **M** medium · **H** high · **C** critical (data/security/money)

Status: `done` · `ready` · `blocked` · `deferred`

---

## Gap summary (KEEP / REFACTOR / EXTEND / REPLACE / CREATE)

| Area | Action |
|------|--------|
| Modular Django apps + `/api/v1` | KEEP |
| JWT + custom RBAC | EXTEND |
| BaseModel, Decimal, soft delete | KEEP |
| Company / Branch / Warehouse | EXTEND (+ tenant) |
| Platform Tenant / Subscription / Waafi | EXTEND |
| POS + Invoice + stock delta | EXTEND (do not rewrite) |
| Inventory movements/adjustments | EXTEND |
| Purchases CRUD | EXTEND (+ receiving) |
| Customers / Suppliers | EXTEND |
| Futsal module | KEEP (pattern) |
| Expense in sales | REFACTOR → finance later |
| Payment-in-notes | REPLACE with Payment model |
| Hold “reserve” behavior | REFACTOR |
| Finance / notifications apps | CREATE |
| Tenant middleware + tenant_id | CREATE |
| BusinessType / modules / flags | CREATE |
| Attribute engine | CREATE |
| Pharmacy / Gym / Restaurant | CREATE |
| Celery/Redis wiring | CREATE |
| Automated tests | CREATE |
| Next.js rewrite | DEFERRED |
| Schema-per-tenant | DEFERRED (post shared-schema) |
| React Native apps | DEFERRED (API-ready first) |

---

## STEP 01 — Existing System Audit

| Field | Value |
|-------|--------|
| Phase | 0 |
| Section | Discovery |
| Task | Full codebase/database/frontend/desktop audit |
| Dependencies | None |
| Affected Files | Read-only; produced `docs/CURRENT_SYSTEM_AUDIT.md` |
| Database Changes | None |
| API Changes | None |
| Frontend Changes | None |
| Risk | L |
| Testing | N/A |
| Status | **done** |

---

## STEP 02 — Architecture & Migration Plan

| Field | Value |
|-------|--------|
| Phase | 0 |
| Section | Architecture |
| Task | Target architecture, ERD, migration strategy, this roadmap |
| Dependencies | STEP 01 |
| Affected Files | `docs/TARGET_ARCHITECTURE.md`, `docs/MIGRATION_STRATEGY.md`, `docs/DATABASE_ERD.md`, `docs/ERP_TRANSFORMATION_ROADMAP.md` |
| Database Changes | None (design only) |
| API Changes | None |
| Frontend Changes | None |
| Risk | L |
| Testing | N/A |
| Status | **done** |

**Stop point:** Do not begin Gym/Pharmacy/Next.js. Proceed only with STEP 03+ after explicit approval.

---

## STEP 03 — Core Refactoring (non-breaking hygiene)

| Field | Value |
|-------|--------|
| Phase | 1 |
| Section | Foundation |
| Task | Align stubs with reality: document installed apps; prepare `TenantScopedModel` mixin (unused); fix hold/reserve **design**; inventory transfer/receiving **interfaces**; standardize error envelope helper |
| Dependencies | STEP 02 |
| Affected Files (planned) | `backend/core/models/`, `backend/core/exceptions/`, docs; **no mass renames** |
| Database Changes | None or additive mixin-ready abstract only |
| API Changes | Additive only |
| Frontend Changes | None required |
| Risk | L–M |
| Testing | Introduce pytest smoke: health, login |
| Status | **done** (2026-08-07) |

**Delivered:**
- `core/tenancy.py` + `TenantScopedModel` / `TenantAwareManager` (not applied to live models yet)
- API error envelope with `code` / `details`
- `InventoryService.reserve_quantity` / `unreserve_quantity` / `consume_reserved`
- Transfer + receiving service interfaces (STEP 11)
- `docs/architecture/HOLD_RESERVE_DESIGN.md`
- pytest harness + smoke/unit tests

CREATE: tenancy context, tenant mixin, transfer/receiving interfaces, tests, hold design doc  
MODIFY: `api_response.py`, `inventory_service.py`, `pos_service` docstring, auth login error code  
MIGRATE: none  
DEPRECATE: none

**Stop point:** STEP 03 complete. Next = STEP 04 Tenant Foundation.

---

## STEP 04 — Tenant Foundation

| Field | Value |
|-------|--------|
| Phase | 2 |
| Section | Multi-tenancy |
| Task | Extend `Tenant` (business_type FK nullable, currency, language, status); add `TenantSettings`, `TenantDomain`; keep ShopGroup |
| Dependencies | STEP 03 |
| Affected Files | `apps/platform/models/`, serializers, `platform_service.py`, platform UI forms |
| Database Changes | New tables; additive columns on `tenants` |
| API Changes | Extend platform tenant CRUD |
| Frontend Changes | Platform tenant forms |
| Risk | M |
| Testing | Platform API create/list; slug reserved names |
| Status | **done** (2026-08-07) |

**Delivered:**
- `BusinessType` seeded (retail, pharmacy, gym, futsal, …)
- Extended `Tenant`: currency, language, status, business_type FK
- `TenantDomain` + `TenantSettings` with auto-provision on shop create
- Reserved slug validation (`domain_utils.py`)
- APIs: `/platform/business-types/`, `/slug-check/`, tenant `settings/` & `domains/`
- Frontend shop create/edit + detail show business type, currency, domain
- Tests for reserved slugs, provision, APIs

**Stop point:** STEP 04 complete. Next = STEP 05 Domain/Subdomain Resolution middleware.

---

## STEP 05 — Domain / Subdomain Resolution

| Field | Value |
|-------|--------|
| Phase | 3 |
| Section | Multi-tenancy |
| Task | Hostname → TenantDomain/slug resolver; middleware sets tenant context; platform hosts bypass |
| Dependencies | STEP 04 |
| Affected Files | `backend/core/` or `apps/platform/middleware.py`, `settings/base.py`, frontend host-aware API base |
| Database Changes | Uses `TenantDomain` |
| API Changes | None breaking; reject mismatched host vs user.tenant (non-platform) |
| Frontend Changes | Derive tenant branding from host |
| Risk | H |
| Testing | Host header resolution unit tests; mismatch → 403 |
| Status | **done** (2026-08-07) |

**Delivered:**
- `tenant_resolver.py` + `TenantResolutionMiddleware`
- `TenantAwareJWTAuthentication` + login host match
- Public `GET /platform/resolve-host/`
- Frontend `tenantHost.ts` + login branding
- Tests for resolve / mismatch / platform admin

**Stop point:** STEP 05 complete. STEP 06 Tenant Isolation follows (also complete).

---

## STEP 06 — Tenant Isolation (shared schema)

| Field | Value |
|-------|--------|
| Phase | 4 |
| Section | Security |
| Task | Add `tenant_id` to tenant-owned tables; backfill; scoped managers; composite uniques; cross-tenant tests |
| Dependencies | STEP 04–05 |
| Affected Files | All domain models/migrations; every queryset service; sync ingest |
| Database Changes | **C** — large additive + constraint changes |
| API Changes | Implicit filtering; IDs remain UUIDs |
| Frontend Changes | Minimal if APIs unchanged |
| Risk | **C** |
| Testing | **Mandatory** isolation suite |
| Status | **done** (2026-08-07) |

See `MIGRATION_STRATEGY.md` Stage A0–A3.

**Delivered:**
- `tenant` FK on Branch, Setting, Category, Brand, Unit, Product, Customer, Supplier, Warehouse, Inventory, StockMovement, InventoryTransaction, InventoryAdjustment, Quotation, Invoice, DocumentSequence, Expense, PurchaseOrder, AuditLog
- Composite uniques: `(tenant, sku)`, `(tenant, barcode)`, `(tenant, brand name)`, `(tenant, customer_code)`, `(tenant, supplier_code)`
- Backfill migration `platform.0009_backfill_tenant_isolation` (+ `legacy-unassigned` fallback)
- Service scoping via `apply_tenant_scope` / `stamp_tenant_id` (products, customers, suppliers, sales, purchases, inventory)
- API views pass `user=request.user` into list/get/create paths
- Isolation suite: `tests/unit/test_tenant_isolation.py`

**Gaps deferred:** analytics/POS walk-in customer lookups; default manager enforcement still off (explicit service scoping).
**Closed (2026-08-07):** Futsal models tenant-scoped (STEP 36).

**Stop point:** STEP 06–09 complete (isolation + modules + RBAC). Next = STEP 10 attributes or STEP 11 inventory. No pharmacy/gym apps until staging isolation re-verified.

---

## STEP 07 — Business Types

| Field | Value |
|-------|--------|
| Phase | 5 |
| Section | Configuration |
| Task | `BusinessType` catalog + seed (retail, supermarket, pharmacy, cafeteria, restaurant, electronics, fashion, hardware, wholesale, gym, salon, other, futsal) |
| Dependencies | STEP 04 |
| Affected Files | `apps/platform/` or `apps/settings_app/` |
| Database Changes | `business_types`, FK on Tenant |
| API Changes | List business types; tenant update |
| Frontend Changes | Onboarding + settings select |
| Risk | L |
| Testing | Seed + assign |
| Status | **done** (2026-08-07; delivered with STEP 04) |

---

## STEP 08 — Module System

| Field | Value |
|-------|--------|
| Phase | 5 |
| Section | Modules |
| Task | `Module`, `TenantModule`; gate APIs/nav by module + subscription |
| Dependencies | STEP 07; STEP 06 preferred |
| Affected Files | platform models; permission/module middleware; Sidebar |
| Database Changes | New tables + seeds (pos, inventory, pharmacy, gym, futsal, …) |
| API Changes | 403 when module disabled |
| Frontend Changes | Module-aware nav |
| Risk | M |
| Testing | Disabled module cannot call API |
| Status | **done** (2026-08-07) |

**Delivered:**
- `Module` + `TenantModule` models; migration `platform.0010_module_system` seeds catalog + backfills tenants from `BusinessType.default_modules`
- Shop provision syncs modules; platform APIs `GET /platform/modules/`, `GET|PUT /platform/tenants/:id/modules/`
- `ModuleGateMiddleware` → `403 MODULE_DISABLED` / `MODULE_DEPENDENCY` on gated path prefixes
- `HasModule` DRF helper; `/me` + login include `enabled_modules`
- Frontend `useModules` + Sidebar module filters

**Deferred to STEP 24:** plan feature ↔ module entitlements / grace. Feature-flag table optional later.

**Stop point:** STEP 08 complete. Next was STEP 09 (done).

---

## STEP 09 — RBAC Expansion

| Field | Value |
|-------|--------|
| Phase | 24 (prompt) / impl early |
| Section | IAM |
| Task | Add industry roles & permission codenames; keep bootstrap matrix |
| Dependencies | STEP 08 for module-linked perms |
| Affected Files | `bootstrap.py`, Role UI PermissionMatrix |
| Database Changes | Permission seed rows |
| API Changes | None |
| Frontend Changes | Matrix labels |
| Risk | L |
| Testing | Role matrix assertions |
| Status | **done** (2026-08-07) |

**Delivered:**
- Industry permissions: `pharmacy.*`, `gym.*`, `restaurant.*` (aligned with STEP 08 module codes)
- System roles: `pharmacist`, `gym_manager`, `receptionist`, `trainer`, `waiter`, `kitchen`
- Admin / branch_manager defaults include industry module perms; cafeteria cashier gets restaurant floor
- `PermissionMatrix` labels for pharmacy, gym, restaurant, trash
- Assertion suite: `tests/unit/test_rbac_bootstrap.py`

**Stop point:** STEP 09 complete. STEP 11 inventory receiving/transfers also complete. Next = STEP 10 or STEP 12.

---

## STEP 10 — Universal Catalog + Attributes

| Field | Value |
|-------|--------|
| Phase | 6 |
| Section | Catalog |
| Task | Tenant-scoped catalog constraints; AttributeDefinition engine; no industry columns on Product |
| Dependencies | STEP 06 |
| Affected Files | `apps/products/` |
| Database Changes | Attribute tables; unique (tenant, sku) |
| API Changes | Attribute CRUD; product payload extension |
| Frontend Changes | Dynamic fields on product form |
| Risk | M |
| Testing | Attribute validation; tenant SKU isolation |
| Status | **done** (2026-08-07) |

**Delivered:**
- Models: `AttributeDefinition`, `AttributeOption`, `ProductAttributeValue`, `BusinessTypeAttribute`, `CategoryAttribute`
- `AttributeService` — resolve applicable attrs, typed coerce/validate, product value persist
- Product create/update accepts `attributes`; detail payload includes values
- APIs: `/products/attributes/`, `/products/attributes/applicable/`, category assign
- Seed: system `strength` + `dosage_form` assigned to pharmacy business type
- FE: dynamic fields on product form from applicable attributes
- Tests: `tests/unit/test_catalog_step10.py`
- Tenant SKU uniqueness already present from STEP 06 (`uniq_product_tenant_sku`)

**Stop point:** STEP 10 complete. Next = STEP 13 pharmacy (after staging isolation re-verify) or deferred STEP 12 items (cashier sessions / refunds).

---

## STEP 11 — Inventory Improvements

| Field | Value |
|-------|--------|
| Phase | 8 |
| Section | Inventory |
| Task | Goods receipt from PO; warehouse transfers; fix reserve/unreserve; reorder alerts hook |
| Dependencies | STEP 06 |
| Affected Files | `apps/inventory/`, `apps/purchases/` |
| Database Changes | Transfer models; receipt models optional |
| API Changes | `/purchases/{id}/receive/`, `/inventory/transfers/` |
| Frontend Changes | Receive + transfer UIs |
| Risk | H (stock) |
| Testing | Receive increases stock; transfer conserves qty; concurrent safe |
| Status | **done** (2026-08-07) |

**Delivered:**
- `PurchaseReceivingService.receive` / `preview` — partial GRN, stock +, PO → received when complete
- `StockTransfer` / `StockTransferLine` + `StockTransferService` (draft → confirm/cancel); confirm conserves qty with `select_for_update`
- APIs: `POST/GET .../purchases/:id/receive/`, `/inventory/transfers/` (+ confirm/cancel)
- Reorder hook: `InventoryService.get_reorder_candidates` (wraps low-stock)
- Reserve primitives already present (POS hold wiring remains STEP 12)
- FE: receive-remaining on Purchases list; transfer API client methods
- Tests: `tests/unit/test_inventory_step11.py`

**Stop point:** STEP 11 complete. Next = STEP 10 (attributes) or STEP 12 (POS payments/hold→reserve).

---

## STEP 12 — Universal POS Improvements

| Field | Value |
|-------|--------|
| Phase | 7 |
| Section | POS |
| Task | Payment model + multi-tender; cashier sessions; hold uses reserved_quantity; refunds/returns foundation; idempotency key |
| Dependencies | STEP 06, STEP 11 (reserve) |
| Affected Files | `pos_service.py`, sales models, `modules/pos/` |
| Database Changes | `payments`, `cashier_sessions`; backfill from notes |
| API Changes | Extend checkout response; session endpoints |
| Frontend Changes | Tender UI, open/close shift |
| Risk | **C** |
| Testing | Checkout, split pay, hold/resume, concurrent stock |
| Status | **done** (2026-08-07) |

**Delivered (minimal slice):**
- Hold → `reserve_quantity` (on-hand unchanged); cancel hold → unreserve; checkout from hold → consume reserved
- `Payment` model + split tenders via `payments[]`; notes kept for back-compat
- Checkout `idempotency_key` (unique per tenant); replay returns prior sale
- POS catalog stock uses available (`quantity - reserved`)
- Fixed `list_holds(user=...)`
- FE: Split tender option + idempotency key
- Tests: `tests/unit/test_pos_step12.py`

**Delivered (STEP 12b — 2026-08-07):**
- `CashierSession` open/close with float, sales/refund totals, cash variance
- Checkout auto-links open session; explicit `cashier_session_id` supported
- `SaleRefund` + `SaleRefundItem` partial returns with stock restore
- API: `/pos/sessions/`, `/pos/sessions/current/`, `/pos/sessions/open|close/`, `/pos/refunds/`
- Permission: `sales.refund` (cashier role)
- FE API client: session + refund methods in `pos.ts`
- Tests: `tests/unit/test_pos_step12b.py`

**Stop point:** STEP 12 complete (core + sessions + refunds). Next = staging POS verification or additional tracks (import/export, restaurant/KDS).

---

## STEP 13 — Pharmacy

| Field | Value |
|-------|--------|
| Phase | 9 |
| Section | Pharmacy |
| Task | Batches, expiry alerts, FEFO allocation on POS, pharmacy reports |
| Dependencies | STEP 10–12, module `pharmacy` |
| Affected Files | NEW `apps/pharmacy/`, inventory batch, POS extension, frontend pharmacy module |
| Database Changes | `product_batches` / medicine batch tables |
| API Changes | `/api/v1/pharmacy/...` |
| Frontend Changes | Batch UI, expiry dashboard, POS batch hint |
| Risk | H |
| Testing | FEFO pick; expiry filters; sale deducts batch |
| Status | **done** (2026-08-07) — slice 1 |

**Delivered (slice 1):**
- NEW `apps/pharmacy`: `ProductBatch`, `BatchDispense` (tenant-scoped)
- `BatchService` — receive, FEFO plan/deduct, expiry list, summary (`TenantSettings.expiry_alert_days`)
- GRN hook creates batches when pharmacy module on or batch/expiry supplied
- POS/sale `apply_sale_delta` deducts FEFO when batches exist; returns restore dispenses
- APIs: `/api/v1/pharmacy/summary/`, `/batches/`, `/batches/expiring/`, `/batches/fefo-preview/`
- FE: Pharmacy page (batch table + expiry KPIs), sidebar gated by module `pharmacy`
- Tests: `tests/unit/test_pharmacy_step13.py`

**Deferred:** prescription dispense workflow, advanced pharmacy reports, POS on-screen batch picker UI.

**Stop point:** STEP 13 slice 1 complete. Next = STEP 14 Gym members, or deferred STEP 12 cashier/refunds. Re-verify tenant isolation on shared Postgres staging before multi-tenant pharmacy production.

---

## STEP 14 — Gym Members

| Field | Value |
|-------|--------|
| Phase | 11 |
| Section | Gym |
| Task | Member model + CRUD; link optional Customer |
| Dependencies | STEP 06, 08, 09 |
| Affected Files | NEW `apps/gym/`, frontend `modules/gym/` |
| Database Changes | `members` |
| API Changes | `/api/v1/gym/members/` |
| Frontend Changes | Members list/form |
| Risk | M |
| Testing | Tenant isolation on members |
| Status | **done** (2026-08-07) |

**Delivered:**
- NEW `apps/gym`: `Member` (tenant-scoped; optional `Customer` link)
- UQ(`tenant`, `membership_number`); auto `MEM-#####` when blank
- `MemberService` CRUD + summary; APIs `/api/v1/gym/summary/`, `/gym/members/`
- FE: Gym members list + create/edit form; sidebar gated by module `gym`
- Tests: `tests/unit/test_gym_step14.py`

**Stop point:** STEP 14 complete. Next = STEP 15 membership plans/subscriptions.

---

## STEP 15 — Gym Membership Plans & Subscriptions

| Field | Value |
|-------|--------|
| Phase | 12–13 |
| Section | Gym |
| Task | Plans + MembershipSubscription lifecycle |
| Dependencies | STEP 14, Payment/POS (STEP 12) |
| Affected Files | gym models/services |
| Database Changes | plans, subscriptions |
| API Changes | subscribe/freeze/cancel |
| Frontend Changes | Plans + sell membership |
| Risk | H (money/dates) |
| Testing | Expiry server-side; payment creates ACTIVE |
| Status | **done** (2026-08-07) |

**Delivered:**
- `MembershipPlan` + `MembershipSubscription` (tenant-scoped)
- Lifecycle: pending → activate/mark_paid → active; freeze/unfreeze (extends end); cancel; server-side expire
- APIs: `/gym/plans/`, `/gym/subscriptions/` (+ activate/freeze/unfreeze/cancel)
- FE: Gym tabs — Members / Plans / Sell membership + subscription actions
- Tests: `tests/unit/test_gym_step15.py`

**Stop point:** STEP 15 complete. Next = STEP 16 Gym attendance.

---

## STEP 16 — Gym Attendance

| Field | Value |
|-------|--------|
| Phase | 14 |
| Section | Gym |
| Task | Check-in/out with membership validation; QR/barcode/manual; duplicate protection |
| Dependencies | STEP 15 |
| Affected Files | gym attendance service/API/UI |
| Database Changes | `attendance` |
| API Changes | `/gym/attendance/check-in/` |
| Frontend Changes | Check-in console |
| Risk | M |
| Testing | Expired member rejected; duplicate blocked |
| Status | **done** (2026-08-07) |

**Delivered:**
- `Attendance` model (tenant-scoped; check-in/out, source qr|barcode|manual|membership_number)
- `AttendanceService` — membership validation via active subscription; open-visit duplicate block; visit counter++
- APIs: `/gym/attendance/`, `/gym/attendance/check-in/`, `/gym/attendance/check-out/`
- FE: Gym Check-in tab (console + recent visits)
- Tests: `tests/unit/test_gym_step16.py`

**Stop point:** STEP 16 complete. Next = STEP 17 trainers (or STEP 23 Celery).

---

## STEP 17 — Gym Trainers

| Field | Value |
|-------|--------|
| Phase | 15 |
| Section | Gym |
| Task | Trainer profiles, specialties, schedules, assignments, PT sessions |
| Dependencies | STEP 14 |
| Affected Files | gym trainers |
| Database Changes | trainer tables |
| API Changes | trainer endpoints |
| Frontend Changes | Trainer admin |
| Risk | L–M |
| Testing | Assignment CRUD |
| Status | **done** (2026-08-07) |

**Delivered:**
- Models: `Trainer`, `TrainerSpecialty`, `TrainerSchedule`, `MemberTrainerAssignment`, `PersonalTrainingSession`
- Services: create trainer (+ specialties/schedules), assign/end, schedule PT + status
- APIs: `/gym/trainers/`, `/gym/assignments/`, `/gym/pt-sessions/`
- FE: Gym Trainers tab (create, assign, end)
- Tests: `tests/unit/test_gym_step17.py`

**Stop point:** STEP 30 complete. Next = STEP 31 performance optimization.

---

## STEP 18 — Gym Classes & Booking

| Field | Value |
|-------|--------|
| Phase | 16 |
| Section | Gym |
| Task | Classes, schedules, capacity-safe booking, waitlist |
| Dependencies | STEP 15 |
| Affected Files | `apps/gym` models/services, `api/v1/gym`, Gym FE Classes tab |
| Database Changes | `GymClass`, `ClassSchedule`, `ClassBooking` (+ migration 0005) |
| API Changes | `/gym/classes/`, `/gym/class-schedules/`, `/gym/class-bookings/` (+ cancel) |
| Frontend Changes | Classes tab: templates, schedule, book/waitlist |
| Risk | H (concurrency) |
| Testing | `tests/unit/test_gym_step18.py` — capacity + waitlist promote |
| Status | **done** |

**Delivered:** `select_for_update` booking; confirmed under capacity else waitlist; cancel promotes earliest waitlist; FE Classes tab.

---

## STEP 19 — Gym Workouts & Body Progress

| Field | Value |
|-------|--------|
| Phase | 17–18 |
| Section | Gym |
| Task | Exercise library, workout plans, progress measurements |
| Dependencies | STEP 14, 17 |
| Affected Files | `apps/gym` workout models/services, `api/v1/gym`, Gym FE Workouts tab |
| Database Changes | Exercise, WorkoutPlan/Day/Exercise, assignments, progress, BodyMeasurement (+ 0006) |
| API Changes | `/gym/exercises/`, `/gym/workout-plans/`, assignments, progress, body-measurements + chart |
| Frontend Changes | Workouts tab: library, plans, assign, weight chart |
| Risk | L |
| Testing | `tests/unit/test_gym_step19.py` — plan days, progress, tenant isolation |
| Status | **done** |

**Delivered:** Exercise library; multi-day workout plans; member assignments; progress logs with sets; body measurements + chart series; tenant-scoped privacy.

---

## STEP 20 — Gym Payments Integration

| Field | Value |
|-------|--------|
| Phase | 19 |
| Section | Gym |
| Task | Sell memberships via central Payment + Invoice; no parallel ledger |
| Dependencies | STEP 12, 15 |
| Affected Files | `gym_payment_service`, `api/v1/gym/checkout`, Gym subscriptions sell UI |
| Database Changes | Reuses `MembershipSubscription.invoice` FK + plan service products |
| API Changes | `POST /gym/checkout/`, `POST /gym/subscriptions/:id/pay/` |
| Frontend Changes | Sell membership with payment method; collect payment on pending |
| Risk | H |
| Testing | `tests/unit/test_gym_step20.py` — invoice+payment→ACTIVE, idempotency, split |
| Status | **done** |

**Delivered:** Checkout creates Invoice + Payment row(s), links subscription; pay-later on_account; pay pending endpoint; idempotency via invoice key; auto CRM customer + plan product.

---

## STEP 21 — Finance Improvements

| Field | Value |
|-------|--------|
| Phase | 22 |
| Section | Finance |
| Task | Install finance app; CoA + journal foundation; wire expenses; fix KPI definitions |
| Dependencies | STEP 06, 12 |
| Affected Files | `apps/finance/`, `daily_ops_service`, analytics, Finance FE |
| Database Changes | `Account`, `JournalEntry`, `JournalLine` (+ migration 0001) |
| API Changes | `/finance/accounts/`, `/finance/journal/`, enhanced `/finance/summary/` |
| Frontend Changes | Journal tab with real entries; CoA codes; operating + PO expenses |
| Risk | H |
| Testing | `tests/unit/test_finance_step21.py` — balanced journal, expense posts, KPIs |
| Status | **done** |

**Delivered:** Default CoA bootstrap; balanced journal posting; expense→Dr expense/Cr cash; KPIs include operating expenses + purchases; ledger balances on summary.

---

## STEP 22 — Reports

| Field | Value |
|-------|--------|
| Phase | 28 |
| Section | Reporting |
| Task | Central reporting service; tenant + pharmacy + gym packs; export hooks |
| Dependencies | Domain data available |
| Affected Files | `apps/reports/`, `api/v1/reports/`, ReportsPage |
| Database Changes | None (query-based reports) |
| API Changes | `/reports/catalog/`, `/reports/data/`, `/reports/export/` |
| Frontend Changes | Module-filtered catalog; gym + pharmacy packs |
| Risk | M |
| Testing | `tests/unit/test_reports_step22.py` — catalog, gym/pharmacy snapshots, CSV |
| Status | **done** |

**Delivered:** `ReportService` catalog + run + CSV export; gym pack (members, subs, attendance, classes); pharmacy pack (batches, expiry, FEFO); module-gated catalog API.

---

## STEP 23 — Notifications + Celery

| Field | Value |
|-------|--------|
| Phase | 26–27 |
| Section | Platform services |
| Task | Wire Redis/Celery; notification model + channels; scheduled expiry/membership/subscription jobs |
| Dependencies | STEP 06; Docker compose update |
| Affected Files | `config/celery.py`, `apps/notifications/`, compose files |
| Database Changes | `notifications` table |
| API Changes | `/notifications/`, unread count, mark read |
| Frontend Changes | Notification drawer in header |
| Risk | M |
| Testing | `tests/unit/test_notifications_step23.py` — eager tasks, API, dedupe |
| Status | **done** |

**Delivered:** Celery + Redis config; scheduled low-stock, gym expiry, pharmacy batch scans; in-app feed + drawer; `/health/celery/` + `celery_status` CLI (2026-08-07 foundation verify).

---

## STEP 24 — Subscription / Billing Hardening

| Field | Value |
|-------|--------|
| Phase | 23 |
| Section | SaaS |
| Task | Plan features ↔ modules; enforce limits (users/branches); grace middleware; no data delete on expiry |
| Dependencies | STEP 08, existing Waafi flows |
| Affected Files | `PlanModule`, `EntitlementService`, subscription middleware |
| Database Changes | `plan_modules` table |
| API Changes | `/platform/entitlements/`; `SUBSCRIPTION_EXPIRED` / limit errors |
| Frontend Changes | Paywall banner + renew CTA |
| Risk | H |
| Testing | `tests/unit/test_entitlements_step24.py` — grace lock, limits, plan caps |
| Status | **done** |

**Delivered:** Plan↔module entitlements; write-block middleware after grace; user/branch limits; read-only retention.

---

## STEP 25 — Tenant Onboarding

| Field | Value |
|-------|--------|
| Phase | 44 |
| Section | SaaS |
| Task | Self-serve wizard: business → type → subdomain → plan → provision → first branch |
| Dependencies | STEP 04–08, 24 |
| Affected Files | `onboarding_service`, `api/v1/onboarding/`, OnboardingPage |
| Database Changes | None beyond existing |
| API Changes | `/onboarding/catalog/`, `/slug-check/`, `/provision/` |
| Frontend Changes | `/onboard` wizard + login CTA |
| Risk | M |
| Testing | `tests/unit/test_onboarding_step25.py` — reserved slug, idempotent provision |
| Status | **done** |

**Delivered:** Public catalog + slug check; idempotent self-serve provision; multi-step FE wizard.

---

## STEP 26 — Frontend UX Improvements

| Field | Value |
|-------|--------|
| Phase | 29–31 |
| Section | UI |
| Task | Design token refinement; denser tables; POS responsive/touch; module nav; empty/loading states |
| Dependencies | Ongoing |
| Affected Files | `design-system`, DataTable, Sidebar, TabNav, POS, EmptyState/LoadingState |
| Database Changes | None |
| API Changes | None |
| Frontend Changes | Density tokens, denser tables, shared empty/loading, module nav polish, POS touch targets |
| Risk | L |
| Testing | Manual smoke of lists + POS |
| Status | **done** (incremental; **not** Next.js rewrite) |

**Delivered:** Density/touch tokens; denser table cells; EmptyState + LoadingState; sidebar active rail + touch nav; POS larger tap targets.

---

## STEP 27 — Mobile API Foundation

| Field | Value |
|-------|--------|
| Phase | 32 |
| Section | Mobile |
| Task | Harden `/api/v1` for React Native: refresh, pagination, tenant headers/host, OpenAPI, rate limits |
| Dependencies | STEP 06, 09 |
| Affected Files | DRF settings, spectacular/openapi, throttling |
| Database Changes | None |
| API Changes | Documented contracts |
| Frontend Changes | None |
| Risk | M |
| Testing | Contract tests |
| Status | **done** |

**Delivered:**
- `drf-spectacular` OpenAPI at `/api/v1/schema/` + `/api/v1/docs/`
- DRF throttling (anon/user/auth scopes); login + refresh use `AuthRateThrottle`
- Mobile tenant context: `X-Tenant-Slug` header on platform API hosts
- `/api/v1/mobile/meta/` (public contract) + `/api/v1/mobile/bootstrap/` (authenticated)
- JWT refresh wrapped in standard success envelope
- Tests: `tests/unit/test_mobile_api_step27.py`

---

## STEP 28 — React Native Member App

| Field | Value |
|-------|--------|
| Phase | 33 |
| Section | Mobile |
| Task | React Native gym member app (login, QR, attendance, workouts, …) |
| Dependencies | STEP 16–20, 27 |
| Affected Files | NEW `mobile/` (future repo area) |
| Database Changes | None |
| API Changes | Consume existing |
| Frontend Changes | N/A |
| Risk | M |
| Testing | Device QA |
| Status | **done** (v0.1 scaffold) |

**Delivered:**
- `Member.user` portal link + `gym_member` role / `gym.member_portal` permission
- Member portal API: `/api/v1/mobile/gym/*` (home, profile, qr, attendance, workouts, classes)
- Expo app: `mobile/gym-member/` (login, home, QR, attendance, workouts, classes)
- Tests: `tests/unit/test_mobile_gym_step28.py`

---

## STEP 29 — Offline POS Foundation

| Field | Value |
|-------|--------|
| Phase | 35 |
| Section | Offline |
| Task | Real sync queue + idempotency; replace stub `desktop/sync`; explicit finance sync rules |
| Dependencies | STEP 06, 12 |
| Affected Files | `desktop/sync/`, sync API |
| Database Changes | sync outbox tables optional |
| API Changes | Idempotent ingest |
| Frontend Changes | Sync status UX |
| Risk | **C** |
| Testing | Replay-safe checkout sync |
| Status | **done** |

**Delivered:**
- `SyncOutboxEntry` (shop) + `SyncIngestReceipt` (cloud idempotent ingest)
- POS checkout enqueues outbox; sync run marks uploaded invoices synced
- Invoice push includes `idempotency_key` / `local_id`; cloud replay-safe
- `SyncFinancePolicy` — rejects journal/ledger/expense keys from shop push
- `GET /api/v1/sync/queue/` + desktop `SyncQueueBadge`
- `desktop/sync/` schema, queue types, engine bridge
- Tests: `tests/unit/test_sync_step29.py`

---

## STEP 30 — Security Hardening

| Field | Value |
|-------|--------|
| Phase | 36 |
| Section | Security |
| Task | Rate limits, lockout, headers, upload validation, secret hygiene, session/device optional |
| Dependencies | Ongoing |
| Affected Files | settings, middleware, auth |
| Database Changes | Optional login attempt table |
| API Changes | 429 responses |
| Frontend Changes | Friendly errors |
| Risk | M |
| Testing | Throttle + isolation regression |
| Status | **done** |

**Delivered:**
- `LoginAttempt` audit + `LoginLockoutService` (403 `ACCOUNT_LOCKED` after repeated failures)
- Auth throttle from STEP 27 retained; 429 `RATE_LIMITED` envelope
- `SecurityHeadersMiddleware` (nosniff, referrer-policy, permissions-policy, COOP)
- Production settings: HSTS, secure cookies, frame deny (env-configurable)
- `validate_production_secrets()` on startup (insecure SECRET_KEY warning)
- Pillow verify on image uploads
- Frontend friendly messages for 429 + account lockout
- Tests: `tests/unit/test_security_step30.py`

---

## STEP 31 — Performance Optimization

| Field | Value |
|-------|--------|
| Phase | 37–48 |
| Section | Performance |
| Task | POS search indexes; select_related audits; cache non-authoritative lists; pagination discipline |
| Dependencies | Measure first |
| Affected Files | serializers, views, indexes |
| Database Changes | Indexes |
| API Changes | None |
| Frontend Changes | Avoid over-fetch |
| Risk | M |
| Testing | Query count budgets on POS search |
| Status | **done** |

---

## STEP 32 — Testing Program

| Field | Value |
|-------|--------|
| Phase | 40 |
| Section | Quality |
| Task | Unit + API + integration + tenant isolation + critical E2E |
| Dependencies | Starts STEP 03; continuous |
| Affected Files | `backend/tests/`, frontend e2e later |
| Database Changes | None |
| API Changes | None |
| Frontend Changes | Optional |
| Risk | L (cost of not doing: C) |
| Testing | Self |
| Status | **done** |

Priority suites: isolation, POS checkout, receive stock, membership check-in, pharmacy batch sale.

---

## STEP 33 — Deployment

| Field | Value |
|-------|--------|
| Phase | 43 |
| Section | Ops |
| Task | Compose: Postgres + API + web + Redis + Celery; wildcard DNS/TLS runbook; update DEPLOYMENT.md |
| Dependencies | STEP 23 for workers |
| Affected Files | `docker-compose*.yml`, nginx, docs |
| Database Changes | None |
| API Changes | None |
| Frontend Changes | Static build pipeline |
| Risk | M |
| Testing | Staging deploy smoke |
| Status | **done** |

---

## STEP 34 — Monitoring & Backup

| Field | Value |
|-------|--------|
| Phase | 41–42 |
| Section | Ops |
| Task | Health endpoints expansion; logging; backup restore drill documentation; monitoring placeholders → real |
| Dependencies | STEP 33 |
| Affected Files | health API, infra scripts, docs |
| Database Changes | None |
| API Changes | `/health/database/`, `/health/cache/` |
| Frontend Changes | None |
| Risk | M |
| Testing | Restore drill checklist signed off |
| Status | **done** |

---

## Additional tracks (from master prompt)

| Track | Step alignment | Status |
|-------|----------------|--------|
| Restaurant / KDS | After STEP 12; new STEP 12b | deferred |
| CRM loyalty/tags | Extend customers after STEP 06 | ready later |
| Import/export | After catalog stable + Celery | ready later |
| Feature flags | With STEP 08 | ready |
| Module marketplace | Framework only in STEP 08 | ready |
| Schema-per-tenant | Post STEP 06 exit + ops | deferred |
| Next.js migration | Explicit separate epic | deferred |

---

## Suggested execution order (next 90 days)

```
STEP 03  Core hygiene + pytest harness          ✓
STEP 04  Tenant foundation models               ✓
STEP 05  Domain resolver                        ✓
STEP 06  tenant_id backfill + isolation tests    ✓
STEP 07  Business types                         ✓
STEP 08  Module system                          ✓
STEP 09  RBAC industry roles                    ✓
STEP 11  Receiving + transfers                  ✓
STEP 12  POS hold→reserve + split + idempotency + sessions/refunds ✓
STEP 10  Catalog attributes                     ✓
STEP 13  Pharmacy batches + FEFO (slice 1)      ✓
STEP 14  Gym members                            ✓
STEP 15  Gym plans & subscriptions              ✓
STEP 16  Gym attendance                         ✓
STEP 17  Gym trainers                           ✓
STEP 18  Gym classes & booking                  ✓
STEP 19  Gym workouts & body progress           ✓
STEP 20  Gym payments integration               ✓
STEP 21  Finance improvements                   ✓
STEP 22  Reports                                ✓
STEP 23  Notifications + Celery                 ✓
STEP 24  Subscription hardening                 ✓
STEP 25  Tenant onboarding                     ✓
STEP 26  Frontend UX improvements              ✓
STEP 27  Mobile API foundation                 ✓
STEP 28  React Native member app               ✓
STEP 29  Offline POS foundation                ✓
STEP 30  Security hardening                     ✓
STEP 31  Performance optimization               ✓
STEP 32  Testing program                        ✓
STEP 33  Deployment                             ✓
STEP 34  Monitoring & backup                    ✓
STEP 35  Central Accounting Engine (CAE)        ✓ (A–P; cutover = ops)
STEP 36  Futsal tenant isolation                ✓
STEP 37  Accounting equation foundation         ✓ (in progress hardening)
… then CAE implementation phases 04–40 (complete through P)
```

---

## STEP 35 — Central Accounting Engine (CAE)

| Field | Value |
|-------|--------|
| Phase | Post-foundation epic |
| Section | Finance / Platform |
| Task | Extend `apps/finance` into central posting engine; wire POS/purchases/gym/refunds; ledger-backed reports |
| Dependencies | STEP 21 (CoA + journals), STEP 12 (POS), STEP 11 (receiving) |
| Affected Files | `apps/finance/`, `pos_service.py`, `refund_service.py`, `receiving_service.py`, `gym_payment_service.py`, finance API/FE |
| Database Changes | `FinancialPeriod`, `AccountMapping`, `PostingRule`, `AccountingEvent`; extend `JournalEntry` |
| API Changes | `/finance/mappings/`, `/finance/reports/*`, posting health; optional `/accounting/` alias |
| Frontend Changes | Ledger drill-down, trial balance/P&L, account mapping admin, accounting health |
| Risk | **C** (money) |
| Testing | `tests/integration/accounting/` — POS→GL, refund reversal, idempotency, period close |
| Status | **complete** (Phases A–P, 2026-08-07) |

**Phase 01–03 delivered (docs):**
- `docs/accounting/` — audit, architecture, ERD, posting engine, events, mapping, module integration, reporting, security, testing, migration plan
- Decision: **extend `apps/finance`**, do not create duplicate `apps/accounting/` app
- Golden rule: business modules emit events; posting engine creates journals

**Phase A/B delivered (code):**
- Models: `FiscalYear`, `FinancialPeriod`, `AccountMapping`, `PostingRule`, `PostingRuleLine`, `AccountingEvent`
- Extended: `Account` (control flags), `JournalEntry` (source_module, idempotency_key, period FK)
- Services: `MappingService`, `PeriodService`, `AccountingPostingService`
- Expense posting routed through central engine (`EXPENSE_APPROVED` event)
- Migration: `0002_central_accounting_engine.py`
- Tests: `tests/unit/test_finance_step35.py` (8 tests); STEP 21 tests still pass

**Phase C delivered (2026-08-07):**
- POS checkout → `SALE_COMPLETED` via `AccountingPostingService.post_sale`
- Cash/card/mobile/split/on-account debits; Cr Revenue; Dr COGS / Cr Inventory when cost > 0
- Idempotent with invoice replay (same journal, no duplicate)
- Tests: `tests/unit/test_pos_accounting_step35.py` (4 tests)

**Phase D delivered (2026-08-07):**
- Refunds → `SALE_REFUNDED` via `post_refund` (Dr Sales Returns, Cr Cash; Dr Inventory / Cr COGS on stock restore)
- Purchase receive → `PURCHASE_RECEIVED` via `post_purchase_received` (Dr Inventory, Cr AP)
- Journal source types: `refund`, `purchase`
- Tests: refund + receive journal tests in `test_pos_accounting_step35.py`, `test_inventory_step11.py`

**Phase E delivered (2026-08-07):**
- Gym membership checkout → `GYM_MEMBERSHIP_SOLD` via `post_gym_membership` (Dr Cash/AR, Cr Membership Revenue)
- Trial balance selector + `GET /api/v1/finance/reports/trial-balance/`
- FE: `financeApi.trialBalance()`
- Tests: `tests/unit/test_gym_accounting_step35.py`

**Phase F delivered (2026-08-07):**
- P&L + Balance Sheet selectors (`/finance/reports/profit-loss/`, `/finance/reports/balance-sheet/`)
- `AccountingReversalService` — reverse posted journals without mutating originals
- Expense update → reverse + repost; expense delete → reverse then soft-delete
- Accounting health: `GET /finance/health/`
- FE: `profitLoss`, `balanceSheet`, `health`
- Tests: `tests/unit/test_finance_reports_step35.py`

**Phase G delivered (2026-08-07):**
- Cash flow report from cash/bank journal lines (`/finance/reports/cash-flow/`)
- Period lifecycle: list, soft-close, close, reopen, lock (`/finance/periods/`)
- Closed/locked periods block new postings
- FE: `cashFlow`, `periods`, `periodAction`
- Tests: `tests/unit/test_period_cashflow_step35.py`

**Phase H delivered (2026-08-07):**
- Finance page tabs: Trial Balance, P&L, Balance Sheet, Cash Flow, Periods, Health
- Date-range filters + period action buttons + health status panel
- Uses ledger API client methods added in Phases E–G

**Phase I delivered (2026-08-07):**
- AR aging from open invoices vs control account 1100 (`/finance/reports/ar-aging/`)
- AP aging from goods received vs control account 2000 (`/finance/reports/ap-aging/`)
- Age buckets: current / 1–30 / 31–60 / 61–90 / 90+
- FE tabs: AR Aging, AP Aging with reconcile badge
- Tests: `tests/unit/test_ar_ap_aging_step35.py`

**Phases J–P delivered (2026-08-07):**
- J vouchers · K bank rec · L tax GL · M backfill/health · N futsal · O Celery alerts
- P cutover: `AccountingCutoverService`, `accounting_cutover` CLI, `/finance/cutover/`, runbook, Health tab controls
- Tests: `tests/unit/test_cutover_step35.py`

**Stop point:** Phases A–P complete — CAE foundation epic done. Next is **ops**: run [ACCOUNTING_CUTOVER_RUNBOOK.md](accounting/ACCOUNTING_CUTOVER_RUNBOOK.md) on staging for a pilot tenant.

---

## STEP 36 — Futsal tenant isolation

| Field | Value |
|-------|--------|
| Phase | Post-foundation hardening |
| Section | Futsal / Security |
| Task | Close STEP 06 deferred gap: stamp `tenant_id` on all futsal tables; scope service/API |
| Dependencies | STEP 06 |
| Affected Files | `apps/futsal/`, `api/v1/futsal/views.py` |
| Database Changes | `tenant` FK on Court, Team, Player, CourtBooking, FutsalLedgerEntry; backfill from branch |
| Risk | **H** (cross-tenant IDOR) |
| Testing | `tests/unit/test_futsal_tenant_isolation.py` |
| Status | **complete** (2026-08-07) |

**Delivered:**
- All five futsal models use `TenantScopedModel`
- Migration `futsal.0002_tenant_isolation` backfills from `branch.tenant_id`
- `FutsalService` uses `apply_tenant_scope` / `stamp_tenant_id`; rejects foreign branch/team/court/customer
- Detail endpoints 404 cross-tenant

**Stop point:** STEP 36 complete. Remaining deferred isolation: analytics/POS walk-in lookups; optional global `TenantAwareManager`. Product tracks ready: import/export, CRM loyalty. Ops: CAE pilot cutover.

---

## STEP 37 — Accounting equation & double-entry hardening

| Field | Value |
|-------|--------|
| Phase | CAE integrity |
| Task | Enforce equation + normal-balance domain + journal validation (mega-prompt Phases 1–11, 18) **without** rebuilding finance |
| Status | **in progress** (foundation slice 2026-08-07) |

**Delivered this slice:**
- Audit: KEEP existing CAE; do not create `apps/accounting/`
- `AccountClass` / normal-balance domain (`apps/finance/domain/account_behavior.py`)
- `AccountingEquationService` + `GET /finance/equation/` + health check `accounting_equation`
- `JournalValidationService` with `UNBALANCED_JOURNAL` / `JOURNAL_CONTROL_ACCOUNT` codes
- DB CheckConstraints on journal lines (non-neg + XOR)
- Docs: `ACCOUNTING_FOUNDATION.md`, `ACCOUNTING_EQUATION.md`
- Tests: `test_accounting_equation_foundation.py`

**Next slices:** PostingRule runtime · posted immutability guards · GL ledger API · FE equation badge

---

## Definition of done (transform foundation)

- [x] Cross-tenant isolation tests green (unit suite; re-run on shared Postgres staging)
- [x] POS checkout + stock still correct (unit + integration: `test_pos_step12*.py`, `test_critical_pos_checkout.py`)
- [x] Desktop sync authenticated to tenant
- [x] Modules gate features (unit + middleware; re-verify on staging)
- [x] Celery running for at least one scheduled job (`docker compose ps celery celery-beat`; `GET /health/celery/?require_workers=1`; beat: notifications + accounting health)
- [x] Docs updated (`DEPLOYMENT.md`, wildcard TLS runbook; refresh `SYSTEM_ARCHITECTURE` incrementally)
- [x] No Next.js/React Native/schema-per-tenant cutover required for foundation success (stack remains Django + React/Vite; shared-schema `tenant_id`; RN mobile on same `/api/v1`)

**Foundation transform DoD: complete (2026-08-07).**

---

## Change log

| Date | Note |
|------|------|
| 2026-08-07 | Initial roadmap from full repo audit (Phase 0) |
| 2026-08-07 | STEP 12b cashier sessions + refunds complete |
| 2026-08-07 | STEP 35 CAE Phases A–P complete (cutover tooling + runbook) |
| 2026-08-07 | Desktop sync tenant auth/isolation (pull scope, ingest stamps, shop-verify) |
| 2026-08-07 | Celery worker/beat verified; `/health/celery/` + `celery_status`; foundation DoD closed |
| 2026-08-07 | STEP 36 Futsal tenant isolation (closes STEP 06 deferred gap) |
| 2026-08-07 | STEP 37 Accounting equation foundation (validator + journal validation + XOR constraints) |

---

*Do not start STEP 13+ until STEP 06 isolation exit criteria are met.*

# Current System Audit

**Date:** 2026-08-08  
**Scope:** `/home/ubuntu/projects/mda` (backend + frontend + mobile)

---

## Stack (do not assume Next.js)

| Layer | Reality |
|---|---|
| API | Django 5 + DRF, `/api/v1/`, explicit `APIView`s (almost no ViewSets) |
| Web | React 19 + Vite + React Router 7 |
| DB | PostgreSQL, **shared schema + `tenant_id`** |
| Auth | JWT + Role/Permission + elevated admin bypass |
| Desktop | Tauri (`HashRouter`) |
| Mobile | Expo RN: `mobile/staff`, `mobile/gym-member` |

---

## What to KEEP

- Tenant / TenantDomain / TenantModule / BusinessType / BusinessPreset / entitlements
- RBAC + `User.is_elevated_admin`
- POS (`PosService` + profiles: RETAIL, SUPERMARKET, PHARMACY, CAFETERIA, RESTAURANT, GYM, HOTEL_SERVICE)
- Sales: Invoice, Quotation, Payment, Expense, refunds, trash
- Products / Categories / Brands / Inventory / Warehouses / Adjustments / Transfers
- Purchases + receive
- Customers / Suppliers
- Central Accounting Engine: CoA, journals (immutable posted), periods, posting rules, AR/AP aging, vouchers, bank rec, BusinessUnit, CostCenter
- Gym members/plans/trainers + attendance/class/PT workflows
- Pharmacy batches + FEFO + prescriptions/dispense
- Restaurant menu/tables/orders → POS payload
- Hotel rooms/reservations/folios + check-in/out
- Property / housing / office lease + charge → invoice
- Futsal courts/teams/bookings (+ ledger outlier)
- Demo tenant engine + gym/pharmacy/restaurant/hotel/property seeders
- Hub increment 1: industry workspaces, switcher, sidebar, `/{ws}/pos` aliases

---

## Apps (`backend/apps/`)

platform · authentication · settings_app · finance · sales · products · inventory · purchases · customers · suppliers · gym · pharmacy · restaurant · hotel · property_management · housing_rental · office_rental · futsal · audit · notifications · reports

**Finance is not a TenantModule.** Always reachable via `finance.*` permissions.

---

## Architectural conflicts (industry-centric)

1. POS / Sales / Inventory / Purchases are **peer TenantModules**, not capabilities of an industry workspace (FE hub now hides them; API gates still independent).
2. Vertical APIs are mostly **list + create + workflow**, not full R/U/D.
3. FE verticals are **single mega-pages**; feature URLs (`/gym/classes`) did not switch tabs (fixed in this phase).
4. Dual parties: `Customer` vs Member / Guest / HousingTenant / OfficeTenant.
5. Dual catalogs: `Product` vs `MenuItem`; pharmacy batches on Product.
6. Futsal mini-ledger vs sales invoices elsewhere; `futsal` not in `SOURCE_MODULE_TO_BU`.
7. Expenses live in **sales**, post as RETAIL BU even for gym/hotel.
8. AuditLog exists but only products + login/logout write to it. No audit HTTP API.
9. Permissions are **coarse** (`gym.manage`) not `gym.members.create`.
10. `salon` BusinessType has no app.

---

## FE CRUD snapshot

| Area | List | Dedicated Create route | Edit route | Detail route |
|---|---|---|---|---|
| Products / Customers / Suppliers / POs / Invoices / Quotes / Users / Roles / Branches | Yes | Yes | Yes | No (except platform tenant/shop) |
| Categories / Expenses / Adjustments | Yes | Inline only | Inline | No |
| Warehouses / CoA / Journals / Pharmacy batches / Receipts | Yes | **Missing CTA** (APIs exist for warehouse/journal/batch) | Partial | No |
| Gym / Restaurant / Hotel / Property / Housing / Office / Futsal | Tab lists | Inline | Partial inline / workflow | No |
| Restaurant kitchen / Hotel guests page | Claimed in copy | **No real UI** | — | — |

PlaceholderPage exists but is **unrouted**. No live “Coming Soon” screens.

---

## Tests

~95 backend unit + 5 integration under `backend/tests/`. Accounting is the strongest suite. FE has **no** Vitest/Jest suite (tsc only).

# Mobile Architecture (Modular)

**Date:** 2026-08-07  
**Status:** EXTEND gym-member; staff app = full ERP (STEP 69)

Canonical broader mobile notes: `docs/MOBILE_ARCHITECTURE.md`.

---

## Current

- `mobile/gym-member/` — member portal; gated by gym module / permissions
- `mobile/staff/` — staff ERP: dashboard, POS, sales, inventory, purchases, customers, suppliers, finance, business units, reports, settings + venue KPIs
- Auth must resolve tenant (slug / host) like web
- **PHASE 24:** `GET /mobile/bootstrap/?audience=member|staff` returns `enabled_modules` + `mobile_nav`

---

## Target after login

```text
GET /mobile/bootstrap/?audience=staff → workspaces (staff_hub, dashboard/pos/sales/inventory/purchases/customers/suppliers/finance/business_units/reports/settings + venue staff, …)
  → Staff app: WorkspaceSwitcher → operational screens (not gym-only)
GET /mobile/bootstrap/ (or audience=member) → gym_member screens
  → Gym-member app Home nav
```

| Tenant modules | Mobile workspaces |
|----------------|-------------------|
| dashboard.view | dashboard_staff → KPIs, recent sales, low stock |
| pos + pos.access | pos_staff → product search + cash checkout |
| sales + sales.view | sales_staff → invoices |
| inventory + inventory.view | inventory_staff → stock + low stock |
| purchases + purchases.view | purchases_staff → purchase orders |
| sales + customers.view | customers_staff → customers |
| purchases + suppliers.view | suppliers_staff → suppliers |
| finance.view | finance_staff → summary + equation |
| finance.view | business_units_staff → BU list + P&L filter |
| reports.view | reports_staff → catalog + run |
| settings.view | settings_staff → company + branches |
| gym + member portal | gym_member → Home, QR, Attendance, Workouts, Classes |
| gym + gym.view | gym_staff → Gym overview |
| pharmacy + pharmacy.view | pharmacy_staff → Pharmacy overview |
| hotel + hotel.view | hotel_staff → Hotel overview |
| restaurant + restaurant.view | restaurant_staff → Restaurant overview |
| property_management + view | property_staff → Property overview |
| housing_rental + view (+ property core) | housing_staff → Housing overview |
| office_rental + view (+ property core) | office_staff → Office overview |
| futsal + futsal.view | futsal_staff → Futsal overview |
| multi staff | staff_hub switcher → module workspaces |

Gym member screens honor module features: `members` (workspace), `attendance`, `classes`.

Staff apps share the same entitlement / `mobile_nav` payload — no parallel module flags on device.

## Classification

| Piece | Action |
|-------|--------|
| Gym member app | KEEP / EXTEND |
| `MobileNavService` + bootstrap `mobile_nav` | **DONE** (member + staff audiences) |
| Dynamic module switcher RN | **DONE** full ERP (`mobile/staff`) |
| Offline POS mobile | separate roadmap (desktop sync exists) |

# Workspace Navigation

**Date:** 2026-08-08  
**Status:** Increment 1 — FE generated nav + switcher

---

## Switcher

Premium switcher lists **business workspaces + Finance + Administration**, not POS/Sales/Inventory as peers.

```
[ Restaurant ▼ ]
  Restaurant
  Gym
  Pharmacy
  ─────────
  Central Finance
  Administration
  All workspaces → /modules
```

Selecting Restaurant → `/restaurant` (dashboard / industry home).  
Selecting Gym → `/gym`.

---

## Dynamic nav formula

```
visible items =
  tenant usable modules
  ∩ workspace capability map
  ∩ workspace feature flags
  ∩ user permissions
  ∩ subscription entitlements
```

Do **not** hardcode a global “POS · Inventory · Sales” section as the tenant’s product.

When `activeWorkspace === restaurant`, sidebar shows:

```
Restaurant
  Dashboard
  POS
  Sales
  Menu / Products
  Inventory
  Purchasing
  Customers
  Suppliers
  Tables / Kitchen   (industry home tabs)
  Finance
  Reports
```

Links use **workspace-prefixed URLs** where aliases exist (`/restaurant/pos`). Industry-only screens stay on `/restaurant` until tabs are migrated.

---

## URL structure

Preferred:

```
/restaurant/dashboard   → /restaurant (home)
/restaurant/pos         → PosPage
/restaurant/sales       → SalesPage
/restaurant/products    → ProductsPage
/restaurant/inventory   → InventoryDashboardPage
/restaurant/purchasing  → PurchasesPage
/restaurant/customers   → CustomersPage
/restaurant/finance     → FinancePage   (same CAE)
/restaurant/reports     → ReportsPage

/gym/pos /gym/sales /gym/finance …
/pharmacy/pos /pharmacy/inventory …
/hotel/pos …
/property/housing /property/office /property/finance
/retail/pos /retail/sales /retail/inventory …
```

**Compatibility:** keep `/pos`, `/sales`, `/inventory`, `/housing`, `/office` working. Infer workspace from prefix first; flat engine URLs fall back to last focused industry or retail.

---

## Path → workspace

`workspaceFromPath` must prefer the **first segment** if it is an industry code:

`/restaurant/pos` → `restaurant` (not `pos`)

That keeps brand color + sidebar focus on the business, not the engine.

---

## Mobile (later increment)

Staff RN `MOBILE_NAV_CATALOG` uses the same peer model today (`pos_staff` beside `gym_staff`). **EXTEND** to industry-first groups; do not block web increment 1. See `docs/modular-erp/MOBILE_ARCHITECTURE.md`.

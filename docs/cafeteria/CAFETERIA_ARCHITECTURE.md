# Cafeteria + Barista — Architecture

**Date:** 2026-09-06  
**Principle:** User sees **CAFETERIA / BARISTA**; platform reuses **restaurant domain + shared engines**.

---

## Topology

```
CAFETERIA WORKSPACE (FE label + CafeteriaProfile)
        │
        ├── Dashboard / POS / Orders / Barista Queue / Kitchen
        ├── Menu / Variants / Modifiers / Recipes / Ingredients
        ├── Inventory / Waste / Purchasing / Suppliers / Customers
        ├── Loyalty* / Promotions* / Tables / Delivery
        ├── Cash Sessions / Payments / Tips / Expenses
        ├── Employees (BaristaProfile) / Shifts / Reports / Settings
        │
        ▼
DOMAIN: apps.restaurant  (single F&B engine)
        │
        ▼
SHARED SAFARI ERP
  POS · Sales · Inventory · Purchasing · Customers · Suppliers
  Payments · Central Accounting · IAM · Notifications · Audit · Reporting
```

\* Loyalty/promotions may start cafeteria-scoped; promote to shared engines when generalized.

---

## Non-goals

- No `CafeteriaPOS`, `CafeteriaAccounting`, `CafeteriaInventory` duplicate engines
- No second Invoice/Payment/CashSession model for cafeteria
- No silent recipe overwrite (version + activate)
- Frontend never authorizes money, stock, or refunds

---

## Bounded contexts

### 1. Workspace configuration

`CafeteriaProfile` (per tenant branch): identity, tax, receipt copy, order/invoice prefixes, feature toggles (table/takeaway/delivery/reservations/tips/service charge/loyalty/recipe deduction/negative stock), default warehouse + GL account refs.

### 2. Menu & production

Categories → Items → Variants/Sizes → Modifier groups → Recipes → Ingredients  
Stations route prep tickets (Coffee Bar, Cold Drinks, Kitchen, Bakery…).

### 3. Order orchestration

RestaurantOrder + OrderLine (+ OrderLineModifier)  
Service types: dine-in, takeaway, delivery, quick_sale  
Lifecycle includes barista stages: new → queued → accepted → preparing → ready → served/picked → completed/cancelled  
Payment via Universal POS (`serialize_order_for_pos` → checkout).

### 4. Inventory adapters

On paid/completed sale (when recipe deduction enabled): explode active recipe × qty × variant multiplier → inventory consumption (atomic with sale).  
WasteRecord → InventoryAdjustment/damage movement + optional CAE waste expense.

### 5. Finance overlay

Posting events reuse CAE rules (`SALE_COMPLETED`, inventory COGS, AP, waste, tip payable). Account mappings configurable on CafeteriaProfile / posting rules — not a parallel ledger.

---

## POS profile

| Flag | CAFETERIA (target) |
|------|--------------------|
| waiters | true |
| tables | profile-driven |
| modifiers | **true** |
| kitchen_ticket | **true** |
| batches | false |
| charge_to_room | hotel combo only |

Resolve `CAFETERIA` when business type / workspace is cafeteria even if module code is `restaurant`.

---

## Permission model

- Entitlement module remains `restaurant` (TenantModule).
- UI workspace code: `cafeteria`.
- Codenames: keep `restaurant.*` authoritative; add `cafeteria.*` aliases mapped to the same checks for barista/cashier role clarity.
- Backend permission classes accept either family where appropriate.

---

## Frontend IA (cafeteria nav)

Dashboard → POS → Orders → Barista Queue → Kitchen → Menu → Categories → Variants → Modifiers → Recipes → Ingredients → Inventory → Waste → Purchasing → Suppliers → Customers → Loyalty → Promotions → Tables → Delivery → Cash Sessions → Payments → Expenses → Employees → Finance → Reports → Settings → Audit

Shared capability routes reuse existing pages (`/cafeteria/pos`, `/cafeteria/inventory`, …). Industry routes render cafeteria-chrome pages that call restaurant APIs.

---

## Mobile

Same REST APIs. Roles: manager dashboard, barista queue (tablet), cashier POS, inventory receiving. No divergent business rules on device.

---

## Offline

Cache menu/prices/draft tickets only if platform offline POS path is enabled. Payments and journals remain online-first with idempotent sync — do not invent a cafeteria-only offline ledger.

---

## Transaction safety

Critical paths use `transaction.atomic()`, `select_for_update` on stock/order rows, and idempotency keys on checkout/payment. Sale complete without payment or without recipe deduction (when enabled) is a hard failure.

# Cafeteria + Barista — Current State Audit

**Date:** 2026-09-06  
**Scope:** Safari ERP existing platform before Cafeteria workspace build-out  
**Engine decision:** Cafeteria is a **workspace profile** over `apps.restaurant` + shared engines. **Do not** create `apps.cafeteria` as a duplicate domain engine.

---

## Executive verdict

| Area | Status | Action |
|------|--------|--------|
| Restaurant domain app | Present (menu, tables, orders, floors, stations, modifiers, ingredients, recipes) | **KEEP** / **EXTEND** |
| Cafeteria workspace FE shell | Thin alias of RestaurantPage (`/cafeteria`) | **EXTEND** |
| POS profile `CAFETERIA` | Exists; modifiers/kitchen_ticket **off** | **EXTEND** |
| Shared POS / Sales / Inventory / Purchasing / Finance | Mature | **KEEP** |
| CafeteriaProfile / settings | Missing | **CREATE** |
| OrderLine modifiers | Missing | **CREATE** |
| MenuItem ↔ ModifierGroup | Missing | **CREATE** |
| Variants / sizes | Missing (use modifiers or new variant model) | **CREATE** |
| Recipe → inventory deduction | Missing | **CREATE** (adapter) |
| Waste UI | Missing (inventory damage/adjustment exists) | **CREATE** (thin overlay) |
| Barista queue / KDS board | Partial (kitchen tab + statuses) | **EXTEND** |
| Loyalty / promotions engine | Missing platform-wide | **CREATE** (optional, cafeteria-scoped first) |
| Dedicated cafeteria Django app | Must not exist | **DEPRECATE** (never build) |

---

## Shared engines (KEEP)

| Engine | Location | Cafeteria use |
|--------|----------|---------------|
| Universal POS | `apps/sales/services/pos_service.py`, `api/v1/pos/` | Checkout, holds, refunds, cashier sessions |
| POS profiles | `apps/sales/services/pos_profile.py` | `CAFETERIA` / `RESTAURANT` capability flags |
| Sales | `apps/sales/` | Invoices, payments, expenses, refunds |
| Cashier sessions | `CashierSession` + POS session APIs | Open/close shift |
| Products | `apps/products/` | MenuItem → Product bridge (`module_code=restaurant`) |
| Inventory | `apps/inventory/` | Stock, movements, adjustments, transfers, damage |
| Purchasing | `apps/purchases/` | PR/PO/receiving |
| Suppliers / Customers | `apps/suppliers/`, `apps/customers/` | Embed under cafeteria nav |
| Finance / CAE | `apps/finance/` | Journals via posting rules |
| Reports | `apps/reports/` + restaurant pack | EXTEND barista/recipe packs |
| IAM | `apps/authentication/bootstrap.py` | `restaurant.*` (+ new `cafeteria.*` aliases) |
| Audit / Notifications | `apps/audit/`, `apps/notifications/` | KEEP |
| Branches | `settings_app.Branch` | Tenant + branch scope |

---

## Restaurant domain inventory

### Models (`backend/apps/restaurant/models/menu.py`)

| Model | Classification | Notes |
|-------|----------------|-------|
| MenuCategory | KEEP | EXTEND: code, image, color, parent, POS/mobile visibility, tax group, station |
| MenuItem | KEEP | EXTEND: station, prep time, featured/popular, channel flags, coffee JSON |
| DiningTable | KEEP | EXTEND: cleaning/blocked/out_of_service statuses |
| RestaurantFloor | KEEP | |
| KitchenStation | KEEP | EXTEND: station_type (coffee_bar, kitchen, bakery…) |
| ModifierGroup / Modifier | KEEP | CREATE MenuItem↔Group link |
| Ingredient | KEEP | EXTEND: min/reorder, expiry, conversion, supplier |
| Recipe / RecipeIngredient | KEEP | EXTEND: draft/active/archived; activate version |
| RestaurantOrder | KEEP | EXTEND: queue_number, barista, priority, tip/service charge fields where not on invoice |
| OrderLine | KEEP | CREATE OrderLineModifier; station routing |

### Services / API

- `RestaurantService` (~1100 LOC): summary, CRUD masters, order lifecycle, POS payload — **KEEP**, extend.
- API `/api/v1/restaurant/` — **KEEP**, add profile, barista board, waste, variants, recipe consume.
- Permissions: `restaurant.view|manage|menu.*|tables.*|kitchen|floor|orders.*` — **KEEP**; add cafeteria-facing codes.

### Frontend

| Path | Classification |
|------|----------------|
| `/restaurant/*` rich CRUD | KEEP |
| `/cafeteria` → RestaurantPage only | EXTEND (full nav mirror + barista IA) |
| POS under `/cafeteria/pos` | KEEP (shared PosPage) |
| Mobile `RestaurantWorkspaceScreen` | EXTEND barista queue |

---

## Gaps vs product vision

| Requirement | Gap |
|-------------|-----|
| CafeteriaProfile | CREATE |
| Premium cafeteria dashboard KPIs | EXTEND summary + FE dashboard |
| Barista Kanban board | EXTEND kitchen UI |
| Multi-station ticket split | EXTEND MenuItem.station + line filter |
| Sizes / variants | CREATE |
| Modifiers on ticket | CREATE OrderLineModifier + wire POS |
| Recipe auto-deduction | CREATE service adapter |
| Waste / spoilage | CREATE WasteRecord → inventory |
| Stock count | KEEP shared inventory; cafeteria UI |
| Loyalty / promotions / combos | CREATE (later phases; thin models) |
| Tips / service charges | EXTEND order + POS + accounting maps |
| Reservations | CREATE optional |
| Theoretical vs actual usage | CREATE report service |
| React Native barista mode | EXTEND |

---

## Classification summary

| Action | Items |
|--------|-------|
| **KEEP** | Restaurant app, shared POS/Sales/Inventory/Purchasing/Customers/Suppliers/Finance/IAM/Audit/Notifications, cashier sessions, Product bridge pattern |
| **EXTEND** | CAFETERIA POS caps, MenuItem/Ingredient/Recipe/Order fields, kitchen→barista board, cafeteria nav/routes, summary KPIs, demo seeder, report pack, mobile |
| **CREATE** | CafeteriaProfile, MenuItemModifierGroup, OrderLineModifier, MenuItemVariant, WasteRecord, BaristaProfile, recipe consumption adapter, optional loyalty/promo/combo/reservation |
| **MIGRATE** | Stale `docs/restaurant/*` matrices (0003 already shipped); cafeteria docs under `docs/cafeteria/` |
| **DEPRECATE** | Separate CafeteriaPOS / CafeteriaAccounting / CafeteriaInventory engines; standalone `apps.cafeteria` domain duplicate |

---

## Implementation order (this delivery)

1. Audit docs (this pack)  
2. CafeteriaProfile + settings API  
3. Domain extensions (variants, modifiers on lines, stations, barista)  
4. Recipe costing + inventory deduction  
5. Waste overlay  
6. Barista queue API + FE board  
7. Cafeteria dashboard + nav completeness  
8. POS profile enablement  
9. Accounting mappings  
10. Reports + permissions + tests  
11. Mobile barista screen  

Phases after core path (loyalty, full promotions, reservations) follow the same KEEP/EXTEND pattern and must not fork shared engines.

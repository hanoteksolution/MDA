# Cafeteria / Restaurant Architecture

**Date:** 2026-08-07  
**Status:** **CREATE** app skeleton shipped (PHASE 15) — KDS / POS pay bridge later

---

## App

Django app: `apps.restaurant` (module code `restaurant`; cafeteria is a BusinessType/preset label).

| Model | Purpose |
|-------|---------|
| MenuCategory | Floor menu groups |
| MenuItem | Sellable items (optional Product FK) |
| DiningTable | Floor tables |
| RestaurantOrder | Open ticket (not Invoice yet) |
| OrderLine | Ticket lines + prep status |

API: `/api/v1/restaurant/` — summary, categories, items, tables, orders  
FE: `/restaurant` — Orders / Menu / Tables tabs  
Demo seeder: `apps/platform/demo/restaurant.py`

Payment stays on **Universal POS** — Mark paid is a floor status only for now.

---

## Still later

- Kitchen display / ticket UI
- Modifiers
- Charge to Hotel folio
- POS “pay this table” bridge → Invoice + CAE

## Presets

`cafeteria`, `restaurant`, `gym_cafeteria` — combinations via TenantModule.

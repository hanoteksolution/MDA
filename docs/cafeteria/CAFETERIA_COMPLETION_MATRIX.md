# Cafeteria + Barista — Completion Matrix

**Date:** 2026-09-06  
**Status key:** ☐ Not started · ◐ In progress · ✓ Done · — N/A (shared engine UI)

| Capability | List | Create | Detail | Update | Archive | API | Perms | Audit | Tests | Notes |
|------------|:----:|:------:|:------:|:------:|:-------:|:---:|:-----:|:-----:|:-----:|-------|
| Docs / audit pack | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | Phase 1 |
| CafeteriaProfile | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | |
| Dashboard | ✓ | — | — | — | — | ✓ | ✓ | — | ✓ | KPIs + actions |
| POS (shared + profile) | — | — | — | — | — | ✓ | ✓ | ✓ | ✓ | CAFETERIA mods+KDS |
| Orders | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | tip/service PATCH |
| Barista Queue | ✓ | — | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | Web + RN |
| Kitchen Stations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | station_type |
| Menu Categories | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Menu Items | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Variants / Sizes | ✓ | ✓ | ✓ | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | detail UI + POS |
| Modifier Groups | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Modifiers on lines | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | POS customize |
| Add-ons / Combos | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | edit/archive |
| Recipes / Versions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | activate API |
| Recipe Costing | ✓ | — | ✓ | — | — | ✓ | ✓ | — | ✓ | |
| Ingredients / Units | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Inventory (shared) | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | KEEP |
| Recipe deduction | ✓ | — | — | — | — | ✓ | ✓ | ✓ | ✓ | on paid |
| Waste | ✓ | ✓ | ◐ | ◐ | ◐ | ✓ | ✓ | ✓ | ✓ | approve→stock+GL |
| Stock count (shared) | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | UI alias |
| Purchasing (shared) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | KEEP |
| Suppliers / Customers | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | KEEP |
| Loyalty / Promotions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | auto-apply + edit |
| Tables / Reservations | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | status updates |
| Delivery / Takeaway | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | service_type |
| Cash / Payments / Refunds | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | shared |
| Tips / Service charge | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | POS + GL post |
| Expenses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | shared |
| Baristas / Shifts | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | open/close |
| Accounting maps | ✓ | — | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | tip/service/waste |
| Reports pack | ✓ | — | — | — | — | ✓ | ✓ | — | ✓ | café reports seeded |
| Settings UI | ✓ | — | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | |
| RN barista | ✓ | — | ✓ | ✓ | — | — | — | — | ✓ | queue + actions |
| Cafeteria nav completeness | ✓ | — | — | — | — | — | — | — | ✓ | |
| E2E happy path | ✓ | — | — | — | — | — | — | — | ✓ | service-level |

## Production readiness

**Migrations:** `restaurant.0004` (barista extensions) + `restaurant.0005` (commerce overlays)

**Lean gaps closed:**
- Commerce detail PATCH/DELETE for combos & promotions; loyalty program PATCH
- POS auto-applies `promotion_code` (coupon/code) onto invoice discount; FE resolve/preview
- Enable/disable + archive actions in commerce UIs; loyalty settings editable
- E2E unit happy path: profile → menu/variant/mod → promo/combo/loyalty → order → barista → paid → archive promo

**Shared engines:** POS, inventory, purchasing, customers, suppliers, payments, and central accounting remain the system of record — cafeteria is the industry overlay, not a duplicate stack.

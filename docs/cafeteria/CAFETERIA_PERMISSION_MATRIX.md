# Cafeteria + Barista — Permission Matrix

**Date:** 2026-09-06  
**Module entitlement:** `restaurant`  
**Workspace code:** `cafeteria`

## Codename families

Backend accepts `restaurant.*` (authoritative) and `cafeteria.*` (workspace aliases) for the same capability where both exist.

| Codename | Description | Owner | Manager | Branch Mgr | Supervisor | Cashier | Barista | Sr Barista | Kitchen | Inventory | Purchasing | Accountant | Waiter | Delivery |
|----------|-------------|:-----:|:-------:|:----------:|:----------:|:-------:|:-------:|:----------:|:-------:|:---------:|:----------:|:----------:|:------:|:--------:|
| cafeteria.dashboard.view / restaurant.view | Dashboard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| cafeteria.pos.use / pos.access | POS | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | — | — | — | — | ○ | — |
| cafeteria.orders.* / restaurant.orders.* | Orders CRUD/workflow | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ○ | — | — | — | ✓ | ○ |
| cafeteria.barista.queue / restaurant.kitchen | Barista board | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — | — | — | — |
| cafeteria.menu.* / restaurant.menu.* | Menu | ✓ | ✓ | ✓ | ✓ | — | — | ○ | — | — | — | — | — | — |
| cafeteria.recipes.* | Recipes | ✓ | ✓ | ✓ | ○ | — | — | ○ | — | ✓ | — | ○ | — | — |
| cafeteria.inventory.* / inventory.* | Stock | ✓ | ✓ | ✓ | ○ | — | — | — | — | ✓ | ○ | ○ | — | — |
| cafeteria.purchasing.* / purchases.* | Buying | ✓ | ✓ | ✓ | ○ | — | — | — | — | ○ | ✓ | ○ | — | — |
| cafeteria.cash.* / pos sessions | Cash sessions | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | — | — |
| cafeteria.expenses.* | Expenses | ✓ | ✓ | ✓ | ○ | — | — | — | — | — | — | ✓ | — | — |
| cafeteria.reports.view / reports.view | Reports | ✓ | ✓ | ✓ | ✓ | ○ | ○ | ○ | — | ✓ | ✓ | ✓ | — | — |
| cafeteria.settings.* | Profile/settings | ✓ | ✓ | ✓ | — | — | — | — | — | — | — | ○ | — | — |
| cafeteria.waste.* | Waste | ✓ | ✓ | ✓ | ✓ | — | ○ | ✓ | ✓ | ✓ | — | ○ | — | — |

○ = limited / read or own-station only

Refunds, void, large discounts, price edits, stock adjustments, and purchase approve require elevated roles (Manager+ or explicit grant).

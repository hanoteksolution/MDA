# Cafeteria + Barista — API Matrix

**Date:** 2026-09-06  
**Base:** `/api/v1/`  
**Auth:** session/JWT + tenant scope. Permissions listed are preferred; `restaurant.manage` supersedes where noted.

| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET/PUT | `restaurant/cafeteria-profile/` | cafeteria.settings.* / restaurant.manage | branch_id query |
| GET | `restaurant/summary/` | restaurant.view | KPIs; EXTEND cafeteria metrics |
| GET/POST | `restaurant/categories/` | view / menu.create | |
| GET/PATCH/DELETE | `restaurant/categories/{id}/` | view / menu.update / menu.delete | soft delete |
| GET/POST | `restaurant/items/` | view / menu.create | |
| GET/PATCH/DELETE | `restaurant/items/{id}/` | view / menu.update / menu.delete | |
| POST | `restaurant/items/{id}/duplicate/` | menu.create | |
| GET/POST | `restaurant/items/{id}/variants/` | view / menu.update | |
| GET/PATCH/DELETE | `restaurant/variants/{id}/` | menu.* | |
| POST | `restaurant/items/{id}/modifier-groups/` | menu.update | link group |
| GET/POST | `restaurant/modifier-groups/` | menu.* | |
| GET/POST | `restaurant/modifiers/` | menu.* | |
| GET/POST | `restaurant/ingredients/` | view / manage | |
| GET/POST | `restaurant/recipes/` | recipes.* | |
| POST | `restaurant/recipes/{id}/activate/` | recipes.update | version activate |
| GET | `restaurant/recipes/{id}/costing/` | recipes.view | |
| GET/POST | `restaurant/stations/` | kitchen / manage | |
| GET/POST | `restaurant/floors/` | tables.* | |
| GET/POST | `restaurant/tables/` | tables.* | |
| PATCH | `restaurant/tables/{id}/status/` | floor | |
| GET/POST | `restaurant/orders/` | orders.* | |
| POST | `restaurant/orders/{id}/lines/` | orders.create/update | modifiers payload |
| POST | `restaurant/orders/{id}/status/` | orders.update / kitchen | |
| POST | `restaurant/orders/{id}/submit\|cancel\|void\|refund/` | matching orders.* | |
| GET | `restaurant/orders/{id}/pos/` | pos.access | POS bridge |
| GET | `restaurant/barista/queue/` | cafeteria.barista / kitchen | Kanban board |
| POST | `restaurant/barista/tickets/{id}/accept\|start\|ready\|complete/` | barista / kitchen | |
| GET/POST | `restaurant/waste/` | inventory.adjust / cafeteria.waste | posts stock |
| POST | `restaurant/waste/{id}/approve/` | manage | |
| GET/POST | `restaurant/baristas/` | cafeteria.staff / manage | |
| * | `pos/*` | pos.* | Shared checkout/sessions/refunds |
| * | `inventory/*` `purchases/*` `customers/*` `suppliers/*` `finance/*` `reports/*` | respective | Shared |

Idempotency: `Idempotency-Key` on checkout, refund, waste post, recipe consume.

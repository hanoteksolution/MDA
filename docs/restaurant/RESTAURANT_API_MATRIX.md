# RESTAURANT_API_MATRIX

Base prefix: `/api/v1/restaurant`

## Existing Endpoints

| Endpoint | Method(s) | Purpose | Status |
|---|---|---|---|
| `/summary/` | GET | Workspace KPI summary | COMPLETE |
| `/categories/` | GET, POST | Category list/create | COMPLETE |
| `/categories/{id}/` | GET, PUT, PATCH, DELETE | Category detail/update/delete | COMPLETE |
| `/items/` | GET, POST | Menu item list/create | COMPLETE |
| `/items/{id}/` | GET, PUT, PATCH, DELETE | Menu item detail/update/delete | COMPLETE |
| `/tables/` | GET, POST | Table list/create | COMPLETE |
| `/tables/{id}/` | GET, PUT, PATCH, DELETE | Table detail/update/delete | COMPLETE |
| `/tables/{id}/status/` | POST | Table status workflow update | PARTIAL |
| `/orders/` | GET, POST | Order list/create | PARTIAL |
| `/orders/{id}/` | GET | Order detail | PARTIAL |
| `/orders/{id}/status/` | POST | Order status update | PARTIAL |
| `/orders/{id}/submit/` | POST | Submit floor order | COMPLETE |
| `/orders/{id}/cancel/` | POST | Cancel order | COMPLETE |
| `/orders/{id}/void/` | POST | Void order | COMPLETE |
| `/orders/{id}/refund/` | POST | Refund order | COMPLETE |
| `/orders/{id}/lines/` | POST | Add line to order | PARTIAL |
| `/orders/{id}/pos/` | GET | POS payload bridge | PARTIAL |

## Required Missing APIs (priority)

| Endpoint | Method(s) | Purpose | Status |
|---|---|---|---|
| `/orders/{id}/payments/` | GET, POST | Restaurant payment records | MISSING |
| `/orders/{id}/timeline/` | GET | workflow + audit timeline | MISSING |
| `/kitchen/stations/` | CRUD | Kitchen station master | MISSING |
| `/kitchen/tickets/` | GET | Kitchen queue | MISSING |
| `/kitchen/tickets/{id}/accept|start|ready|complete|reject/` | POST | Kitchen lifecycle | MISSING |
| `/modifiers/groups/` + `/modifiers/` | CRUD | Modifiers | MISSING |
| `/recipes/` + `/ingredients/` | CRUD | Recipes + ingredients | MISSING |
| `/floors/` + `/table-groups/` | CRUD | Floor management | MISSING |
| `/inventory/*` restaurant views | workflow | Adjust/transfer/waste from restaurant context | MISSING |
| `/purchasing/*` restaurant views | workflow | PO/receiving in restaurant context | MISSING |
| `/cash-sessions/*` restaurant context | workflow | open/close/cash movement | MISSING |

## API Quality Gaps

- Pagination exists on list APIs but advanced filtering/sorting is limited.
- No idempotency keys on restaurant order creation.
- No explicit concurrency lock (`select_for_update`) around order transitions.
- No dedicated serializer classes for input validation (manual payload parsing in views/services).

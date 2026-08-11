# RESTAURANT_WORKFLOW_MATRIX

## Order Workflow

Target lifecycle:
`Draft -> Open -> Submitted -> Preparing -> Ready -> Served -> Completed`
with cancel/void/refund branches.

Current lifecycle in code:
`open -> sent -> ready -> served -> paid` (+ `cancelled`)

| Transition | Backend Rule | API | UI | Status |
|---|---|---|---|---|
| Open -> Sent | transition-guarded | `/orders/{id}/status/` | button exists | PARTIAL |
| Open -> Submitted | transition-guarded | `/orders/{id}/submit/` | button exists | COMPLETE |
| Sent -> Ready | basic status set | `/orders/{id}/status/` | implicit/manual | PARTIAL |
| Submitted -> Preparing | transition-guarded | `/orders/{id}/status/` | button exists | PARTIAL |
| Ready -> Served | transition-guarded | `/orders/{id}/status/` | button exists | PARTIAL |
| Served -> Completed | transition-guarded | `/orders/{id}/status/` | button exists | PARTIAL |
| Served/Open/Sent/Ready -> Paid | via POS pay-table or status endpoint | `/orders/{id}/status/` + POS bridge | button exists | PARTIAL |
| Any open state -> Cancelled | transition-guarded | `/orders/{id}/cancel/` | button exists | COMPLETE |
| Void | transition-guarded | `/orders/{id}/void/` | button exists | PARTIAL |
| Refund | transition-guarded | `/orders/{id}/refund/` | button exists | PARTIAL |

## Kitchen Workflow

| Workflow Capability | Status | Notes |
|---|---|---|
| Kitchen queue | PARTIAL | filtered orders tab only |
| Station routing | MISSING | no station model |
| Item-level prep transitions | MISSING | no dedicated APIs |
| SLA / delayed flags | MISSING | no timing rules |

## Table Workflow

| Workflow Capability | Status | Notes |
|---|---|---|
| Occupy on order create | COMPLETE | handled in `create_order` |
| Free on paid order | COMPLETE | handled in `update_order_status` |
| Free on cancelled if no open orders | COMPLETE | guarded check exists |
| Reserve/move/merge/split | MISSING | no API/model support |

## POS Payment Bridge Workflow

| Capability | Status | Notes |
|---|---|---|
| Convert order lines to POS payload | COMPLETE | `/orders/{id}/pos/` |
| Ensure menu item has product | COMPLETE | `ensure_menu_item_product` |
| Mark order paid after checkout | COMPLETE | in `PosService.checkout` |
| Prevent double charge via idempotency | PARTIAL | exists in POS checkout, not restaurant-native payment API |

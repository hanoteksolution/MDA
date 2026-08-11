# RESTAURANT_ARCHITECTURE

## Architectural Direction

Restaurant must remain an **industry workspace** that composes shared engines:

- Shared POS engine -> Restaurant POS profile/workflows
- Shared Sales engine -> Restaurant invoicing/sales context
- Shared Inventory engine -> Restaurant stock + ingredient context
- Shared Purchasing engine -> Restaurant procurement context
- Central Accounting Engine -> Restaurant journal/event mapping

No duplicate finance/sales/inventory engines are introduced.

## Current Topology

- Domain app: `backend/apps/restaurant`
- API: `backend/api/v1/restaurant`
- Frontend workspace: `frontend/src/modules/restaurant/pages/RestaurantPage.tsx`
- Workspace routing aliases: `frontend/src/app/workspaceRoutes.tsx`
- Shared POS bridge: `apps/sales/services/pos_service.py` + `RestaurantService.serialize_order_for_pos`

## Bounded Contexts (target)

### 1) Restaurant Core Domain

- Menu catalog (categories/items/availability)
- Floor operations (tables, occupancy, service state)
- Order orchestration (dine-in/takeaway/delivery lifecycle)
- Kitchen operations (ticket state, station routing)

### 2) Restaurant Supply Chain Layer

- Ingredient/recipe/margin model
- Restaurant-facing purchasing/receiving flows (backed by shared purchasing)
- Restaurant inventory controls (stock, transfers, adjustments, waste; backed by shared inventory)

### 3) Restaurant Finance Overlay

- Revenue/tax/payment mappings from restaurant operations to CAE
- Expense, waste valuation, shift settlement, and reconciliation views

## Implementation Principles

- Tenant and branch scoping are mandatory in all reads/writes.
- Backend enforces state transitions and invariants.
- Frontend never assumes authority on amounts/taxes/status.
- Mutations write audit entries through explicit service/repository calls.
- Posted financial records are immutable; corrections via reverse/adjustment only.

## Immediate Refactor Plan

1. Split monolithic `RestaurantPage.tsx` into dedicated pages:
   - dashboard, orders list/detail/edit, menu list/detail/edit, tables list/detail/edit
2. Expand restaurant API surface with workflow endpoints:
   - order submit/cancel/void/refund, kitchen item state transitions
3. Add missing restaurant domain tables incrementally:
   - floors, stations, modifiers, recipes, ingredients
4. Introduce restaurant integration services over shared engines:
   - stock/waste/purchase adapters (no duplicated engines)
5. Add comprehensive test layers:
   - API permissions, workflow transitions, accounting balance checks, tenant isolation

## Non-goals (for this restaurant-only delivery)

- No changes to Gym/Pharmacy/Hotel/Property features.
- No replacement of shared POS/Sales/Inventory/Purchasing/Finance engines.

# RESTAURANT_AUDIT

Date: 2026-08-11  
Scope: Existing Restaurant workspace only (`backend/apps/restaurant`, `api/v1/restaurant`, `frontend/src/modules/restaurant`, related shared engines used by Restaurant)

## Current State Summary

- Overall status: **PARTIAL**
- Core floor/menu/order skeleton exists and is wired end-to-end.
- Shared-engine integration exists for checkout/accounting via Universal POS + Sales invoice posting.
- Major production capabilities from the requested target model are still missing (modifiers, recipes, ingredients, floor plans, stations, purchasing workflows inside Restaurant workspace, inventory workflows inside Restaurant workspace, cashier sessions, restaurant-specific reporting depth).

## Backend Inventory

### Models (`backend/apps/restaurant/models/menu.py`)

- `MenuCategory` — **PARTIAL**
- `MenuItem` — **PARTIAL**
- `DiningTable` — **PARTIAL**
- `RestaurantOrder` — **PARTIAL**
- `OrderLine` — **PARTIAL**

Missing in restaurant domain: floors, table groups, modifier groups/modifiers, recipes, ingredients, kitchen stations, order payments, waste records, restaurant settings, shift/cash session domain records.

### Services (`backend/apps/restaurant/services/restaurant_service.py`)

- Implemented:
  - Summary KPIs
  - CRUD for categories/items/tables
  - Table status update
  - Order create/list/get
  - Add order line
  - Order status update
  - POS payload mapping + product-link bridge
- Status: **PARTIAL**

### API (`backend/api/v1/restaurant/views.py`, `urls.py`)

- Implemented endpoints:
  - `/summary/`
  - `/categories/`, `/categories/{id}/`
  - `/items/`, `/items/{id}/`
  - `/tables/`, `/tables/{id}/`, `/tables/{id}/status/`
  - `/orders/`, `/orders/{id}/`, `/orders/{id}/status/`, `/orders/{id}/lines/`, `/orders/{id}/pos/`
- Status: **PARTIAL**

### Permissions (`backend/apps/authentication/bootstrap.py`)

- Implemented restaurant codenames:
  - `restaurant.view`, `restaurant.manage`
  - `restaurant.menu.create|update|delete`
  - `restaurant.tables.create|update|delete`
  - `restaurant.floor`, `restaurant.kitchen`
- Status: **PARTIAL** (missing granular orders/inventory/purchasing/cash/finance/report permissions)

### Reporting (`backend/apps/reports/services/packs/restaurant.py`)

- Implemented pack reports:
  - Table Status
  - Open Orders
  - Orders by Status
  - Menu Catalog
- Status: **PARTIAL**

### Tests

- Existing:
  - `test_restaurant_step42.py`
  - `test_universal_pos_step43.py` (restaurant pay-table bridge coverage)
- Status: **PARTIAL**

## Frontend Inventory

### Restaurant module (`frontend/src/modules/restaurant/pages/RestaurantPage.tsx`)

- Single-page tabbed workspace:
  - Orders, Kitchen, Menu, Tables tabs
  - Inline create forms
  - DataTable usage for lists
- Status: **PARTIAL**

Gaps:
- No dedicated CRUD pages (`/new`, `/:id`, `/:id/edit`) for restaurant entities
- No advanced filters, saved views, bulk actions, import/export
- No robust workflow timeline/audit panel on order detail
- No enterprise POS screen embedded under restaurant context (relies on shared POS route)

### API client (`frontend/src/services/api/restaurant.ts`)

- Mirrors current backend coverage for categories/items/tables/orders.
- Status: **PARTIAL**

### Routing

- `workspaceRoutes.tsx` maps:
  - `/restaurant`, `/restaurant/kitchen`, `/restaurant/menu`, `/restaurant/tables`
  - shared engine aliases `/restaurant/pos`, `/restaurant/sales`, etc.
- Status: **PARTIAL**

## Shared Dependency Audit (Restaurant-relevant only)

- Shared POS (`apps/sales/services/pos_service.py`) — **COMPLETE for bridge use**, but Restaurant-specific order lifecycle controls are not fully enforced there.
- Shared Sales/Invoice posting to CAE — **PARTIAL** for Restaurant context tagging depth.
- Shared inventory/purchases engines — available, but Restaurant workspace does not yet provide first-class workflows for receiving/adjustment/waste/transfer.

## Classification (high-level)

- COMPLETE:
  - Restaurant basic tenant-scoped entities
  - Category/item/table/order skeleton CRUD APIs
  - Basic permissions + audit write hooks for existing mutations
  - Pay-table bridge to shared POS
- PARTIAL:
  - Dashboard
  - Kitchen flow
  - Order lifecycle
  - Menu/product management
  - Reports
  - Tests
- BROKEN:
  - None obvious at audit level; requires deeper execution tests.
- MISSING:
  - Modifiers, recipes, ingredients, floors/plans, stations, restaurant purchasing/inventory/waste/cash workflows, deep financial/reporting package.
- DUPLICATED:
  - No critical duplication found in Restaurant; shared-engine reuse pattern is mostly preserved.
- NEEDS_REFACTOR:
  - Monolithic `RestaurantPage.tsx` inline forms should be decomposed into dedicated routes and reusable form/detail components.

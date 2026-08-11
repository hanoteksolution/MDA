# RESTAURANT_TEST_MATRIX

## Existing Tests

| Test File | Coverage | Status |
|---|---|---|
| `backend/tests/unit/test_restaurant_step42.py` | demo seed + create-order table occupancy + pay close loop | PARTIAL |
| `backend/tests/unit/test_universal_pos_step43.py` | restaurant POS bridge + pay-table | PARTIAL |
| `backend/tests/unit/test_vertical_master_crud.py` | category/item/table patch/delete | PARTIAL |

No dedicated frontend restaurant test files currently present.

## Required Backend Test Expansion

| Area | Needed | Status |
|---|---|---|
| Permission matrix for restaurant codenames | yes | MISSING |
| Tenant isolation for every restaurant endpoint | yes | MISSING |
| Order status transition guard tests | yes | MISSING |
| Concurrency tests (`select_for_update`) for order/table transitions | yes | MISSING |
| Audit log assertions for all workflows | yes | PARTIAL |
| Accounting balancing on restaurant-originated events | yes | MISSING |
| Idempotency tests for checkout and restaurant workflow APIs | yes | PARTIAL |

## Required Frontend Test Expansion

| Area | Needed | Status |
|---|---|---|
| Restaurant page tab navigation behavior | yes | MISSING |
| CRUD form validation tests (category/item/table/order) | yes | MISSING |
| Permission-gated actions visibility | yes | MISSING |
| API error-state rendering tests | yes | MISSING |

## Required E2E Coverage

| Flow | Needed | Status |
|---|---|---|
| Create order -> send kitchen -> serve -> pay | yes | MISSING |
| Menu CRUD complete path | yes | MISSING |
| Table status and reassignment constraints | yes | MISSING |
| POS checkout for restaurant order with idempotency | yes | MISSING |
| Cancel/refund/void flows | yes | MISSING |

# Cafeteria + Barista — Test Matrix

**Date:** 2026-09-06

## Backend unit / API

| Area | Cases |
|------|-------|
| Profile | upsert, tenant isolation, branch unique |
| Menu CRUD | category/item create-update-archive-restore-duplicate |
| Variants | price + recipe multiplier |
| Modifiers | required min/max; line modifiers affect POS totals |
| Recipes | version activate; costing math; no silent overwrite |
| Inventory deduction | sell latte → beans/milk/cup movements; atomic with pay |
| Negative stock | blocked vs allowed per profile |
| Waste | reduces stock; accounting when enabled |
| Orders | lifecycle transitions; illegal skips rejected |
| Barista queue | accept/start/ready/complete; station filter |
| Payments | split pay validation; idempotent checkout |
| Refund | full/partial; stock return path; audit |
| Cash session | open/close/variance; closed immutable |
| Permissions | IDOR cross-tenant; barista cannot refund without grant |
| Accounting | balanced journals for sale/COGS/waste/tip |

## Frontend

POS cart + modifiers · DataTables · Barista board refresh · Forms validation · Permission-gated actions · Dashboard quick actions navigate for real

## E2E happy path

Create category → item → variant → modifiers → recipe → receive ingredients → open cash session → POS sell → barista queue → complete → payment → stock deducted → journal balanced → receipt

## Commands

```bash
cd backend && pytest tests/unit/test_cafeteria_*.py tests/unit/test_restaurant_*.py -q
cd frontend && npm run lint && npm run build
```

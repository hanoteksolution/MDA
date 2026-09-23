# Cafeteria + Barista — CRUD Matrix

**Date:** 2026-09-06  
**Legend:** L List · C Create · D Detail · U Update · A Archive/Delete · R Restore · Dup Duplicate · Imp/Exp Import/Export · B Bulk · W Workflow

| Entity | L | C | D | U | A | R | Dup | Imp | Exp | B | W | Engine |
|--------|---|---|---|---|---|---|-----|-----|-----|---|---|--------|
| CafeteriaProfile | ✓ | upsert | ✓ | ✓ | — | — | — | — | — | — | — | restaurant |
| MenuCategory | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | reorder | restaurant |
| MenuItem | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | activate | restaurant |
| MenuItemVariant | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | restaurant |
| ModifierGroup | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | restaurant |
| Modifier | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | restaurant |
| Add-on (modifier/flag) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | restaurant |
| Combo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | restaurant (CREATE) |
| Recipe | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | activate version | restaurant |
| RecipeIngredient | ✓ | ✓ | — | ✓ | ✓ | — | — | — | ✓ | — | — | restaurant |
| Ingredient | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | restaurant |
| KitchenStation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — | restaurant |
| Floor / Table | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | status | restaurant |
| Reservation | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | — | confirm/seat | restaurant (CREATE) |
| Order | ✓ | ✓ | ✓ | ✓ | cancel | — | — | — | ✓ | — | submit/prep/ready/pay | restaurant+POS |
| OrderLine | ✓ | ✓ | — | ✓ | cancel | — | — | — | — | — | prep states | restaurant |
| WasteRecord | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | approve | restaurant→inventory |
| Stock / Adjustment / Transfer / Count | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ | post | **inventory** |
| Purchase Request / PO / GRN | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | approve/receive | **purchases** |
| Supplier | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | **suppliers** |
| Customer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | **customers** |
| Loyalty member/tier | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | — | earn/redeem | CREATE |
| Promotion / Coupon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | activate | CREATE |
| Cashier Session | ✓ | open | ✓ | — | — | — | — | — | ✓ | — | close/reconcile | **sales/POS** |
| Payment / Refund | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | — | reverse | **sales** |
| Expense | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | approve/pay | **sales/finance** |
| BaristaProfile | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — | restaurant |
| Shift | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | — | start/end | EXTEND/HR |

All list pages must ship search, filters, sort, pagination, export, empty/loading/error states.

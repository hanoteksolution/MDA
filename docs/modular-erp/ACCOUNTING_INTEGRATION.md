# Accounting Integration (Modular ERP)

**Date:** 2026-08-07  
**Status:** KEEP Central Accounting Engine; EXTEND dimensions & mappings

---

## Rule

All modules emit **accounting events** → `apps/finance` → journals → GL.

**Forbidden:** `HotelAccounting`, `GymAccounting`, `PropertyAccounting` as separate ledgers.

See `docs/accounting/` for CAE detail (equation, posting rules, maker-checker, cost centers, cutover).

---

## Module revenue mappings (EXTEND seeds)

```text
RETAIL_SALES_REVENUE / DEFAULT_SALES_REVENUE
PHARMACY_SALES_REVENUE                       ← pharmacy POS (PHARMACY_SALE_COMPLETED)
CAFETERIA_REVENUE / RESTAURANT_REVENUE
GYM_MEMBERSHIP_REVENUE / GYM_SERVICE_REVENUE
HOTEL_ROOM_REVENUE / HOTEL_SERVICE_REVENUE   ← seeded; room settle uses HOTEL_ROOM_REVENUE
HOUSING_RENT_REVENUE / OFFICE_RENT_REVENUE   ← seeded (CoA 4200)
SECURITY_DEPOSIT_LIABILITY                   ← seeded (CoA 2200)
GYM_PERSONAL_TRAINING_REVENUE                ← used by PT checkout (GYM_SERVICE_SOLD)
```

Event types `HOTEL_ROOM_CHARGED` / `HOTEL_SERVICE_CHARGED` are registered; hotel check-out currently posts via `SALE_COMPLETED` + `CUSTOMER_PAYMENT_RECEIVED` (same CAE, no parallel ledger).

Housing / office lease charges post via the same sales path with `HOUSING_RENT_REVENUE` / `OFFICE_RENT_REVENUE` (deposits → `SECURITY_DEPOSIT_LIABILITY`).

Gym PT sessions post via `GYM_SERVICE_SOLD` + `GYM_PERSONAL_TRAINING_REVENUE` (`source_module=gym`, BusinessUnit GYM).

Gym class drop-ins post via `GYM_SERVICE_SOLD` + `GYM_CLASS_REVENUE` (same event family; mapping key distinguishes P&L lines).

Pharmacy POS (profile `PHARMACY`) posts via `PHARMACY_SALE_COMPLETED` + `PHARMACY_SALES_REVENUE` (`source_module=pharmacy`, BusinessUnit PHARM) — still one POS engine.

BusinessType must not hardcode debit/credit — PostingRules + AccountMappings do.

---

## Profitability dimensions

| Dimension | Status | Use |
|-----------|--------|-----|
| Branch | KEEP | Location |
| CostCenter | KEEP (STEP 37) | Dept / project |
| BusinessUnit | **KEEP** (PHASE 09) | Gym vs Cafeteria vs Hotel Rooms P&L |
| Module / source_module on journal | KEEP / EXTEND | Traceability |

Multi-module P&L = filter posted lines by `business_unit_id` / `cost_center_id` / source — **not** separate DBs.

Defaults seeded with chart: RETAIL, GYM, PHARM, REST, HOTEL, PROP, CORP. Journal lines auto-stamp from `source_module` when no explicit BU is passed. APIs: `GET/POST /finance/business-units/`, P&L + GL accept `business_unit_id`.

---

## Demo / cutover

Demo journals follow same immutability. Convert-to-real may KEEP data. Cutover runbook remains `docs/accounting/ACCOUNTING_CUTOVER_RUNBOOK.md`.

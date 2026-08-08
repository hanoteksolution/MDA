# Cost Centers

**Date:** 2026-08-07  
**Status:** STEP 37 — optional journal-line dimension

---

## Model

`CostCenter` (`finance_cost_centers`) — tenant-scoped `code` + `name` (+ optional parent).

`JournalLine.cost_center` — nullable FK. Automated postings leave it null; manual journals may set `cost_center_id` or `cost_center_code` per line.

## Defaults

Seeded with CoA ensure: **HQ**, **OPS**, **SALES**.

## API

| Method | Path |
|--------|------|
| GET/POST | `/api/v1/finance/cost-centers/` |
| GET | `/api/v1/finance/reports/general-ledger/?account_id=&cost_center_id=` |

## Out of scope (later)

Multi-currency · cost-center P&L report UI · forcing cost centers on expense categories

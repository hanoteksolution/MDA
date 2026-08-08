# Accounting Integration (Workspaces)

**Date:** 2026-08-08  
**Status:** KEEP central CAE — workspace is a posting dimension

---

## Rule

Finance remains **one Central Accounting Engine**.

Do not create RestaurantAccounting, GymAccounting, PharmacyAccounting, HotelAccounting.

```
Restaurant  →  Finance context  →  CAE  →  Journals / GL / P&L
Gym         →  Finance context  →  CAE  →  same CoA, same periods
Pharmacy    →  Finance context  →  CAE
Hotel       →  Finance context  →  CAE
Property    →  Finance context  →  CAE
```

All posting: double entry, journal entries, GL, CoA, accounting periods, cost centers, **business units**, branches, dimensions.

---

## Live mapping (KEEP)

| Workspace | `AccountingEvent.source_module` | `BusinessUnit` code |
|---|---|---|
| Retail | sales / pos / purchases | `RETAIL` |
| Gym | gym | `GYM` |
| Pharmacy | pharmacy | `PHARM` |
| Restaurant / Cafeteria | restaurant | `REST` |
| Hotel | hotel | `HOTEL` |
| Property / housing / office | property | `PROP` |
| Futsal | futsal (ledger outlier) | (map or MIGRATE to sales) |
| Corporate / admin | — | `CORP` |

Source: `apps.finance` `SOURCE_MODULE_TO_BU`, `PostingService`.

---

## Workspace UI → Finance

`/gym/finance` and `/restaurant/finance` are **aliases of `/finance`**.  
Increment 2: pre-select `BusinessUnit` from workspace.  
Never copy the Finance page.

---

## Classification

| Piece | Verdict |
|---|---|
| CAE, journals, periods, CoA, AR/AP aging, cash flow | **KEEP** |
| `BusinessUnit` | **KEEP** / **EXTEND** as workspace P&L slice |
| `CostCenter` | **KEEP** (orthogonal) |
| Finance as TenantModule | **EXTEND** later (optional catalog); not required for UX increment |
| Futsal mini-ledger | **MIGRATE** onto Invoice + CAE |
| Per-vertical accounting apps | **DEPRECATE** (must never exist) |

See also `docs/modular-erp/ACCOUNTING_INTEGRATION.md`.

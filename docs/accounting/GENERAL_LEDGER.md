# General Ledger API

**Date:** 2026-08-07  
**Selector:** `GeneralLedgerSelector`  
**Endpoint:** `GET /api/v1/finance/reports/general-ledger/`

---

## Query params

| Param | Required | Notes |
|-------|----------|-------|
| `account_id` or `account_code` | one of | Tenant-scoped account |
| `date_from` / `date_to` | no | Inclusive period |
| `limit` | no | Max lines (default 500, cap 2000) |

## Response

Opening balance (activity before `date_from`), period debit/credit, closing balance, and lines with **running balance** (normal-balance signed).

FE: Finance → **GL Ledger** tab + Accounts “Ledger” action. Equation badge uses `GET /finance/equation/`.

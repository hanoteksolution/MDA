# Financial Reporting

**Date:** 2026-08-07  
**Status:** Target design — Phases 30–33

---

## 1. Principle

> Official financial statements derive from **posted journal lines**, not from POS invoice tables.

Operational reports (sales by product, waiter performance) may query `Invoice`. **Trial balance, P&L, balance sheet, and cash flow** must query the general ledger.

Current state:

- `ChartService.account_balance` — aggregates posted `JournalLine` ✓ correct approach
- `FinanceSummaryService` — mixes ledger balances with invoice/PO KPIs — **dual truth**
- `ReportService` (STEP 22) — query-based packs for gym/pharmacy — operational, not GL-backed

Target: migrate official finance reports to `apps/finance/selectors/`.

---

## 2. Report catalog

| Report | Selector | Source |
|--------|----------|--------|
| General Ledger | `ledger.py` | Journal lines by account + date range |
| Trial Balance | `trial_balance.py` | Sum debits/credits per account |
| Profit & Loss | `profit_loss.py` | Revenue − expenses for period |
| Balance Sheet | `balance_sheet.py` | Assets = Liabilities + Equity |
| Cash Flow | `cash_flow.py` | Indirect method from P&L + BS changes |
| Account Statement | `ledger.py` | Single account drill-down |
| AR Aging | `receivables.py` | Sub-ledger + reconcile to 1100 |
| AP Aging | `payables.py` | Sub-ledger + reconcile to 2000 |
| Customer Statement | AR + invoices | Hybrid drill-down |
| Supplier Statement | AP + POs | Hybrid drill-down |
| Journal Report | `journal_service.list` | Filter by date/source |
| Tax Report | `tax_report.py` | Tax Payable collected / refunded |
| Cash Book | `bank_book.py` | Filter cash account 1000 |
| Bank Book | `bank_book.py` | Cash/bank/mobile accounts + reconciliation |

---

## 3. Selector pattern

```python
# apps/finance/selectors/trial_balance.py
class TrialBalanceSelector:
    @staticmethod
    def run(*, tenant_id, date_from, date_to, branch_id=None) -> list[dict]:
        # Query posted JournalLine in range
        # Group by account
        # Return [{code, name, debit, credit, balance}, ...]
```

All selectors:

- Use `apply_tenant_scope`
- Filter `entry__status = POSTED`
- Respect `FinancialPeriod` boundaries
- Return Decimal internally; float only at serialization

---

## 4. Drill-down chain

Example P&L drill-down:

```
Profit & Loss
  → Sales Revenue line $50,000
    → General Ledger (account 4000)
      → Journal JE-00123
        → Source: INV-2026-001245 (POS sale)
```

API shape:

```
GET /api/v1/finance/reports/profit-loss/?from=&to=
GET /api/v1/finance/reports/profit-loss/accounts/{id}/ledger/?from=&to=
GET /api/v1/finance/journal/{id}/   # includes source_module, source_reference
GET /api/v1/sales/invoices/{id}/    # operational detail
```

Frontend links journal → invoice via `source_id`.

---

## 5. API endpoints (target)

Extend `/api/v1/finance/reports/`:

```
GET /reports/trial-balance/
GET /reports/profit-loss/
GET /reports/balance-sheet/
GET /reports/cash-flow/
GET /reports/general-ledger/
GET /reports/ar-aging/
GET /reports/ap-aging/
```

Alias under `/api/v1/accounting/reports/` optional for spec alignment.

Permissions: `accounting.reports.view`

---

## 6. Relationship to STEP 22 ReportService

| ReportService pack | Role after CAE |
|--------------------|----------------|
| Gym members/attendance | Operational — keep |
| Pharmacy batches/expiry | Operational — keep |
| Finance P&L (if any) | **Replace** with ledger selector |
| CSV export | Reuse export infrastructure |

`ReportService` registers finance pack pointing to finance selectors instead of invoice aggregates.

---

## 7. Finance summary dashboard migration

`FinanceSummaryService` phases:

1. **Now:** ledger balances + invoice KPIs
2. **Transition:** show both with "operational vs ledger" badge when divergent
3. **Target:** ledger authoritative; operational KPIs labeled "Sales activity"

---

## 8. Frontend (React/Vite)

Extend `FinancePage` and add report routes:

```
/finance
/finance/reports/trial-balance
/finance/reports/profit-loss
/finance/journal/:id        # drill-down
```

Mobile (React Native): summary KPIs + trial balance snapshot — same API.

---

## 9. Performance

- Index `(tenant_id, entry_date, status)` on journal entries
- Materialized view for trial balance (optional, phase 38)
- Cache report snapshots per period after close (period locked → immutable)

---

## 10. Implementation priority

| Phase | Report |
|-------|--------|
| 30 | Trial Balance |
| 31 | Profit & Loss |
| 32 | Balance Sheet |
| 33 | Cash Flow (simplified) |
| Later | AR/AP aging after sub-ledger wiring |

---

*See also: [CENTRAL_ACCOUNTING_ARCHITECTURE.md](./CENTRAL_ACCOUNTING_ARCHITECTURE.md), [ACCOUNTING_TESTING.md](./ACCOUNTING_TESTING.md)*

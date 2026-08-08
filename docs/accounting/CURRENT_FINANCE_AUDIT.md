# Current Finance Audit

**Date:** 2026-08-07  
**Scope:** Phase 01–02 — audit existing finance architecture and POS/Sales/Purchase financial logic  
**Status:** Complete — no code changes in this phase

---

## 1. Executive summary

MDA has a **real but narrow** general-ledger foundation delivered in **STEP 21** (`apps/finance`). It supports:

- Tenant-scoped chart of accounts (16 default system accounts)
- Double-entry journal entries with balance validation
- Automatic posting for **operating expenses only** (Dr expense / Cr cash)
- Finance summary dashboard aggregating ledger + operational KPIs

**Critical gap:** POS, gym membership sales, purchases, refunds, and customer/supplier payments **do not post to the GL**. Operational documents (`Invoice`, `Payment`, `PurchaseOrder`) remain the de facto financial truth for revenue and AP analytics.

There is **no separate `apps/accounting/` app**. The target Central Accounting Engine will **extend `apps/finance`**, not duplicate it.

---

## 2. Inventory of existing financial code

### 2.1 Django apps

| App | Path | Role | Verdict |
|-----|------|------|---------|
| **finance** | `backend/apps/finance/` | CoA, journals, summary | **KEEP / EXTEND** |
| **sales** | `backend/apps/sales/` | Invoice, Payment, Expense, POS, refunds | **KEEP / EXTEND** (wire to GL) |
| **purchases** | `backend/apps/purchases/` | PO lifecycle, receiving hooks | **EXTEND** |
| **inventory** | `backend/apps/inventory/` | Stock movements (operational, not GL) | **KEEP** (emit accounting events) |
| **gym** | `backend/apps/gym/` | Membership checkout → Invoice/Payment | **EXTEND** |
| **pharmacy** | `backend/apps/pharmacy/` | Batch/FEFO; sales via POS | **EXTEND** |
| **futsal** | `backend/apps/futsal/` | Parallel `FutsalLedgerEntry` | **MIGRATE** or **DEPRECATE** |
| **reports** | `backend/apps/reports/` | P&L, expense packs (query-based) | **EXTEND** (ledger-backed) |
| **platform** | `backend/apps/platform/services/sync_finance_policy.py` | Blocks GL sync from desktop | **KEEP** |

### 2.2 Models (implemented)

| Model | Table | File | Notes |
|-------|-------|------|-------|
| `Account` | `finance_accounts` | `apps/finance/models/account.py` | CoA row; hierarchical via `parent`; tenant-scoped unique `code` |
| `JournalEntry` | `finance_journal_entries` | `apps/finance/models/journal.py` | Header: status, source_type, source_id, branch |
| `JournalLine` | `finance_journal_lines` | same | Debit/credit lines → `Account` |
| `Expense` | `sales_expenses` | `apps/sales/models/sales.py` | Operating expense; **only type wired to GL** |
| `Invoice` / `Payment` | `sales_invoices`, `sales_payments` | same | Operational sales; **no GL posting** |
| `SaleRefund` | `sale_refunds` | same | Stock restore; **no GL reversal** |
| `FutsalLedgerEntry` | `futsal_ledger_entries` | `apps/futsal/models/futsal.py` | Module-local income/expense; **not connected to GL** |

### 2.3 Models (missing vs target)

| Target concept | Status |
|----------------|--------|
| `FinancialPeriod` / `FiscalYear` | **Missing** |
| `PostingRule` | **Missing** |
| `AccountMapping` (semantic keys) | **Missing** — hardcoded codes in `ChartService` |
| `AccountingEvent` / outbox row | **Missing** — sync outbox exists for desktop, not accounting |
| `BankAccount` / `CashAccount` | **Missing** — single system account `1000` |
| Control account flags | **Missing** — no `is_control_account` |
| AR/AP sub-ledger entities | **Missing** — computed from invoices/POs in analytics |

### 2.4 Services

| Service | Path | What works | Gaps |
|---------|------|------------|------|
| `ChartService` | `apps/finance/services/chart_service.py` | Bootstrap 16 accounts; balances from posted lines; expense category→code map | No CRUD API; no business-type templates; hardcoded codes |
| `JournalService` | `apps/finance/services/journal_service.py` | List/serialize; balanced `create_entry`; **`post_expense` only** | No invoice/payment/purchase/refund posting; no reversal; `STATUS_VOID` unused |
| `FinanceSummaryService` | `apps/finance/services/summary_service.py` | Dashboard KPIs mixing ledger + operational | Dual truth when ledger sparse |
| `DailyOpsService` | `apps/sales/services/daily_ops_service.py` | Expense CRUD; **create** calls `JournalService.post_expense` | Update/delete do not adjust journals |
| `AnalyticsService` | `core/services/analytics_service.py` | Delegates to `FinanceSummaryService` | Legacy synthetic paths when no user context |
| `SyncFinancePolicy` | `apps/platform/services/sync_finance_policy.py` | Rejects GL keys from shop push | Correct boundary — GL stays cloud-authoritative |

**Missing entirely:** `AccountingPostingService`, `AccountingReversalService`, `PeriodService`, `ReconciliationService`.

---

## 3. Phase 02 — POS / Sales / Purchase financial logic

### 3.1 POS checkout (`pos_service.py`)

**Current flow:**

```
Cart → InvoiceService.create → Payment rows → Stock movement → Sync outbox
```

**Does NOT call:** `JournalService`, any posting service, or finance app.

**Operational data captured:** invoice totals, tender method(s), customer, discounts, tax, stock delta.

**Financial impact today:** reflected in analytics KPIs and invoice aggregates only — **not in GL**.

**Required target flow:**

```
Checkout → Invoice + Payment + Stock
         → AccountingEvent(SALE_COMPLETED)
         → AccountingPostingService
         → Journal (Dr Cash/AR, Cr Revenue; Dr COGS, Cr Inventory)
```

### 3.2 Sale refunds (`refund_service.py`)

- Restores inventory quantity
- Updates `Invoice.amount_refunded`
- **No journal reversal** (Dr Sales Returns / Cr Cash; inventory side per return policy)

### 3.3 Gym membership (`gym_payment_service.py`)

- Creates `Invoice` + `Payment`; activates subscription
- **No GL posting** — revenue appears in gym reports/analytics only

### 3.4 Operating expenses (`daily_ops_service.py`)

- **Create:** `JournalService.post_expense` — Dr category expense (6010–6090) / Cr `1000` Cash
- **Idempotent:** skips if journal already exists for `source_id`
- **Update/delete:** no journal adjustment or void

### 3.5 Purchases (`purchase_service.py`, `receiving_service.py`)

- PO CRUD and partial goods receipt
- Receiving increases inventory quantity + `StockMovement`
- **No GL:** no Dr Inventory / Cr AP on receive; no payment settlement journals

### 3.6 Pharmacy

- Batch/FEFO allocation on POS sale (inventory layer)
- Sales flow through universal POS — same GL gap as retail POS
- Purchase receiving uses inventory service — same AP gap

### 3.7 Futsal (parallel ledger)

- `FutsalLedgerEntry` with income/expense categories
- API at `/api/v1/futsal/ledger/` with `futsal.finance` permission
- **Not integrated** with `apps/finance` — violates "one financial source of truth"

---

## 4. API surface (today)

### Implemented — `/api/v1/finance/`

| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET | `/finance/summary/` | `finance.view` | KPIs, accounts, journals, expenses |
| GET | `/finance/accounts/` | `finance.view` | CoA with balances |
| GET/POST | `/finance/journal/` | view / `finance.create` | Manual journal create |

Files: `backend/api/v1/finance/views.py`, `urls.py`

### Related — `/api/v1/sales/expenses/`

Expense CRUD under sales namespace; create triggers journal posting.

### Not implemented (documented in API spec but absent)

- `/finance/dashboard`, `/finance/cash-flow`, `/finance/profit-analysis`
- Account CRUD
- Period management
- AR/AP endpoints
- Report endpoints under `/accounting/`

---

## 5. Frontend (today)

| File | Behavior |
|------|----------|
| `frontend/src/modules/finance/pages/FinancePage.tsx` | Read-only dashboard: KPIs, accounts, expenses, journal tabs |
| `frontend/src/services/api/finance.ts` | `summary`, `accounts`, `journal`, `createJournalEntry` — **UI only calls `summary`** |
| `frontend/src/modules/sales/pages/ExpensesPage.tsx` | Expense CRUD via sales API |

**Missing:** manual journal UI, account admin, period controls, drill-down to source documents, voucher workflows.

---

## 6. Tests (today)

| File | Coverage |
|------|----------|
| `tests/unit/test_finance_step21.py` | CoA bootstrap, balanced/unbalanced journal, expense posting, idempotency, summary KPIs, tenant isolation |
| `tests/unit/test_sync_step29.py` | Finance keys rejected from sync push |

**Not tested:** POS→GL, purchase→GL, gym→GL, refund reversal, period close, API integration, expense update/delete journal behavior.

---

## 7. KEEP / EXTEND / REFACTOR / MIGRATE / REPLACE / DEPRECATE

| Area | Verdict | Rationale |
|------|---------|-----------|
| `apps/finance` app name & models | **KEEP** | Solid STEP 21 foundation; extend in place |
| `Account`, `JournalEntry`, `JournalLine` | **KEEP / EXTEND** | Add fields for control accounts, source_module, idempotency |
| `ChartService.DEFAULT_ACCOUNTS` | **EXTEND** | Move to business-type templates + `AccountMapping` |
| `JournalService.post_expense` | **KEEP / EXTEND** | Becomes one handler in posting engine |
| Hardcoded account codes (`"1000"`, `"4000"`) | **REFACTOR** | Replace with semantic `AccountMapping` keys |
| `apps/sales.Expense` location | **REFACTOR** (later) | Move to finance domain; fix update/delete sync |
| `pos_service.py` checkout | **EXTEND** | Call posting engine after invoice/payment |
| `refund_service.py` | **EXTEND** | Emit reversal event |
| `gym_payment_service.py` | **EXTEND** | Same posting rules as POS |
| `receiving_service.py` | **EXTEND** | Dr Inventory / Cr AP on receive |
| `FutsalLedgerEntry` | **MIGRATE** | Post through central engine or deprecate |
| `AnalyticsService` synthetic finance | **DEPRECATE** | When tenant has authoritative ledger |
| `SyncFinancePolicy` | **KEEP** | GL remains cloud-authoritative |
| Separate `apps/accounting/` app | **REPLACE** (decision: don't create) | Extend `apps/finance` per existing conventions |

---

## 8. Gap matrix vs Central Accounting Engine spec

| Capability | Current | Target |
|------------|---------|--------|
| One posting engine | `post_expense` only | Event-driven `AccountingPostingService` |
| POS → GL | None | SALE_COMPLETED posting |
| Refund → reversal | None | AccountingReversalService |
| Purchase → AP | None | PURCHASE_RECEIVED posting |
| COGS on sale | Stock movement only | Dr COGS / Cr Inventory journal |
| AR/AP sub-ledgers | Invoice/PO aggregates | Journal-backed + reconciliation |
| Financial periods | None | OPEN/CLOSED/LOCKED enforcement |
| Account mapping | Hardcoded codes | Configurable semantic keys per tenant |
| Idempotent posting | Expense only | All automated postings |
| Source traceability | `source_type` + `source_id` on journal | + `source_module`, `source_reference` |
| Posted immutability | Status field exists | Enforce + reversal workflow |
| Accounting health monitor | None | Integrity dashboard |
| Official reports from GL | Partial (summary balances) | Trial balance, P&L, BS from ledger |

---

## 9. Data at risk during migration

These operational records must **not** be lost or double-counted when GL integration ships:

| Data | Location | Migration concern |
|------|----------|-------------------|
| Historical invoices | `sales_invoices` | Backfill journals or mark "pre-GL" period |
| Payments | `sales_payments` | Map tenders to cash/bank accounts |
| Expenses | `sales_expenses` | Already have journals (create path) — verify completeness |
| Purchase orders | `purchase_orders` | Receive events need retroactive AP if desired |
| Customer balances | Computed from invoices | Must reconcile with AR control account |
| Supplier balances | Computed from POs | Must reconcile with AP control account |
| Futsal ledger | `futsal_ledger_entries` | Migrate or archive |

See [ACCOUNTING_MIGRATION_PLAN.md](./ACCOUNTING_MIGRATION_PLAN.md).

---

## 10. Recommended immediate next phases

| Phase | Action |
|-------|--------|
| **03** | Approve architecture docs in `docs/accounting/` |
| **04–07** | Extend CoA (control flags, templates), add `FinancialPeriod`, harden journal immutability |
| **08–11** | `AccountMapping`, `PostingRule`, `AccountingEvent`, idempotency constraints |
| **12–13** | Reversal engine + POS integration (highest business impact) |
| **14–21** | Inventory accounting, AR/AP, vouchers, expenses hardening |
| **22–24** | Pharmacy, gym, restaurant posting rules |
| **30–34** | Ledger-backed reports + health monitor |

---

## 11. Key file index

```
backend/apps/finance/
  models/account.py
  models/journal.py
  services/chart_service.py
  services/journal_service.py
  services/summary_service.py
  migrations/0001_initial.py

backend/api/v1/finance/
  urls.py, views.py

backend/apps/sales/
  models/sales.py              — Invoice, Payment, Expense, SaleRefund
  services/pos_service.py      — checkout (no GL)
  services/refund_service.py   — refunds (no GL)
  services/daily_ops_service.py — expense → journal bridge

backend/apps/gym/services/gym_payment_service.py
backend/apps/inventory/services/receiving_service.py
backend/apps/futsal/             — parallel ledger
backend/apps/platform/services/sync_finance_policy.py

frontend/src/modules/finance/pages/FinancePage.tsx
frontend/src/services/api/finance.ts

backend/tests/unit/test_finance_step21.py
docs/ERP_TRANSFORMATION_ROADMAP.md — STEP 21
```

---

*Next document: [CENTRAL_ACCOUNTING_ARCHITECTURE.md](./CENTRAL_ACCOUNTING_ARCHITECTURE.md)*

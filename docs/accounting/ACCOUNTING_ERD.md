# Accounting ERD

**Date:** 2026-08-07  
**Status:** Target schema — extends existing `apps/finance` models

---

## 1. Entity relationship overview

```
Tenant
  │
  ├── FiscalYear
  │     └── FinancialPeriod (OPEN | SOFT_CLOSED | CLOSED | LOCKED)
  │
  ├── Account (Chart of Accounts)
  │     ├── parent → Account (self-FK, hierarchy)
  │     └── JournalLine → many
  │
  ├── AccountMapping (semantic key → Account)
  │
  ├── PostingRule (event_type → debit/credit mapping keys)
  │
  ├── JournalEntry
  │     ├── branch → Branch
  │     ├── lines → JournalLine[]
  │     └── reverses → JournalEntry (optional FK)
  │
  ├── AccountingEvent (lifecycle + idempotency)
  │
  └── CostCenter (phase 26)

── Operational sources (other apps) ──

Invoice (sales) ──source──▶ JournalEntry
Payment (sales) ──source──▶ JournalEntry
Expense (sales) ──source──▶ JournalEntry  ✓ wired today
PurchaseOrder (purchases) ──source──▶ JournalEntry
SaleRefund (sales) ──source──▶ JournalEntry (reversal)
GymSubscription (gym) ──source──▶ JournalEntry
```

---

## 2. Existing tables (KEEP — extend)

### `finance_accounts` — `Account`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK → platform.Tenant | nullable today; enforce in A3 |
| code | varchar(20) | unique per tenant |
| name | varchar(150) | |
| account_type | asset/liability/equity/revenue/expense | |
| parent_id | FK self | hierarchy |
| is_system | bool | protect from delete |
| is_active | bool | |
| description | text | |
| **is_control_account** | bool | **NEW** — AR, AP, Inventory |
| **allow_manual_posting** | bool | **NEW** — default True |
| created_at, updated_at, deleted_at | | BaseModel |

**No `balance` column.** Balance derived from posted `JournalLine` aggregates.

### `finance_journal_entries` — `JournalEntry`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK | |
| entry_number | varchar(50) | JE-00001; unique per tenant |
| entry_date | date | |
| description | varchar(255) | |
| status | draft/posted/void | extend: pending_approval, reversed |
| source_type | manual/expense/payment/invoice | |
| source_id | UUID nullable | |
| **source_module** | varchar(30) | **NEW** — sales, purchases, gym |
| **source_reference** | varchar(100) | **NEW** — INV-2026-001 |
| **idempotency_key** | varchar(100) | **NEW** — unique per tenant when set |
| **financial_period_id** | FK | **NEW** |
| **reverses_entry_id** | FK self | **NEW** — reversal link |
| branch_id | FK → Branch | |
| notes | text | |
| created_at, updated_at, deleted_at | | |

Unique constraints (target):

```sql
UNIQUE (tenant_id, entry_number) WHERE deleted_at IS NULL
UNIQUE (tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL
UNIQUE (tenant_id, source_module, source_type, source_id, event_type) -- via AccountingEvent
```

### `finance_journal_lines` — `JournalLine`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| entry_id | FK → JournalEntry | CASCADE |
| account_id | FK → Account | PROTECT |
| debit | decimal(18,4) | |
| credit | decimal(18,4) | |
| memo | varchar(255) | |
| **cost_center_id** | FK | **NEW** — optional |
| created_at, updated_at, deleted_at | | |

Rule: exactly one of debit/credit > 0 per line; entry sum(debit) = sum(credit).

---

## 3. New tables

### `finance_fiscal_years` — `FiscalYear`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK | |
| name | varchar(50) | e.g. "FY 2026" |
| start_date | date | |
| end_date | date | |
| is_closed | bool | |
| created_at, updated_at, deleted_at | | |

### `finance_periods` — `FinancialPeriod`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK | |
| fiscal_year_id | FK | |
| name | varchar(50) | e.g. "2026-08" |
| start_date | date | |
| end_date | date | |
| status | open/soft_closed/closed/locked | |
| closed_at | datetime nullable | |
| closed_by_id | FK User nullable | |

### `finance_account_mappings` — `AccountMapping`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK | |
| mapping_key | varchar(50) | DEFAULT_CASH, DEFAULT_SALES_REVENUE |
| account_id | FK → Account | resolved account |
| business_type_code | varchar(50) blank | optional override per industry |
| is_active | bool | |

Unique: `(tenant_id, mapping_key, business_type_code)`

### `finance_posting_rules` — `PostingRule`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK nullable | null = system template |
| event_type | varchar(50) | SALE_COMPLETED |
| business_type_code | varchar(50) blank | |
| name | varchar(100) | |
| debit_mapping_key | varchar(50) | semantic key |
| credit_mapping_key | varchar(50) | |
| conditions | JSONField | e.g. `{"payment_method": "cash"}` |
| priority | int | lower = first match |
| is_active | bool | |

Multi-line rules: use `PostingRuleLine` child table (debit/credit keys + amount_expr).

### `finance_accounting_events` — `AccountingEvent`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK | |
| event_type | varchar(50) | |
| source_module | varchar(30) | |
| source_type | varchar(30) | |
| source_id | UUID | |
| source_reference | varchar(100) | |
| idempotency_key | varchar(100) | |
| occurred_at | datetime | business event time |
| payload | JSONField | amounts, line items, context |
| status | pending/processing/posted/failed/reversed | |
| journal_entry_id | FK nullable | result |
| processed_at | datetime nullable | |
| error | text | |
| retry_count | int | |
| created_at, updated_at | | |

Unique: `(tenant_id, idempotency_key)` when not null.

---

## 4. Operational source tables (reference — not owned by finance)

### Sales (`apps/sales`)

| Table | GL link today | Target |
|-------|---------------|--------|
| `sales_invoices` | None | SALE_COMPLETED → journal |
| `sales_payments` | None | may combine with invoice or separate PAYMENT_RECEIVED |
| `sales_expenses` | `source_id` on journal | KEEP; add reversal on delete |
| `sale_refunds` | None | SALE_REFUNDED → reversal journal |

### Purchases (`apps/purchases`)

| Table | GL link today | Target |
|-------|---------------|--------|
| `purchase_orders` | None | no journal on PO create |
| receiving records | None | PURCHASE_RECEIVED → Dr Inventory / Cr AP |

### Inventory (`apps/inventory`)

| Table | Role |
|-------|------|
| `inventory` | Quantity — operational |
| `stock_movements` | Audit trail — operational |
| GL impact via accounting events, not direct balance edits |

### Gym (`apps/gym`)

| Table | GL link today | Target |
|-------|---------------|--------|
| `gym_subscriptions` | FK to Invoice | GYM_MEMBERSHIP_SOLD via invoice posting |

---

## 5. Default chart of accounts (current bootstrap)

From `ChartService.DEFAULT_ACCOUNTS`:

| Code | Name | Type |
|------|------|------|
| 1000 | Cash & Bank | Asset |
| 1100 | Accounts Receivable | Asset (control) |
| 1200 | Inventory | Asset (control) |
| 2000 | Accounts Payable | Liability (control) |
| 3000 | Owner's Equity | Equity |
| 4000 | Sales Revenue | Revenue |
| 5000 | Cost of Goods Sold | Expense |
| 6000–6090 | Operating expense categories | Expense |

Target: mark 1100, 1200, 2000 as `is_control_account=True`.

---

## 6. Journal status lifecycle

```
DRAFT → PENDING_APPROVAL → APPROVED → POSTED
                                         │
                                    REVERSED (via reversal entry)
POSTED → immutable (no UPDATE on lines)
CANCELLED (draft only)
```

Current implementation posts directly to `posted` — add draft workflow in phase 35.

---

## 7. Indexes (recommended)

```sql
-- Ledger queries
CREATE INDEX idx_jl_account_entry ON finance_journal_lines(account_id, entry_id);
CREATE INDEX idx_je_tenant_date ON finance_journal_entries(tenant_id, entry_date, status);

-- Event processing
CREATE INDEX idx_ae_status ON finance_accounting_events(tenant_id, status, occurred_at);

-- Traceability
CREATE INDEX idx_je_source ON finance_journal_entries(tenant_id, source_module, source_type, source_id);
```

STEP 21 migration already indexes `entry_date`, `source_id`, account `code`.

---

## 8. Migration from current schema

| Step | Action |
|------|--------|
| 1 | Add nullable new columns to `JournalEntry`, `Account` |
| 2 | Create `FinancialPeriod`, seed open period per tenant |
| 3 | Create `AccountMapping` from hardcoded `EXPENSE_CATEGORY_ACCOUNT` + defaults |
| 4 | Create `PostingRule` seeds for SALE_COMPLETED, EXPENSE_APPROVED |
| 5 | Backfill `source_module='sales'` on existing expense journals |
| 6 | Add `AccountingEvent` for new postings only; optional historical backfill |

No drop or rename of existing tables.

---

*See also: [POSTING_ENGINE.md](./POSTING_ENGINE.md), [ACCOUNT_MAPPING.md](./ACCOUNT_MAPPING.md)*

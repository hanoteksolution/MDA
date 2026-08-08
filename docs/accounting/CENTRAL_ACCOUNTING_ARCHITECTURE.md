# Central Accounting Architecture

**Date:** 2026-08-07  
**Status:** Target design — Phase 03  
**Principle:** Extend `apps/finance`; do not create a parallel accounting app

---

## 1. Architectural rule

> **No ERP module may create its own independent accounting system.**

Business modules own **operational** data. The Central Accounting Engine owns **financial** truth.

```
                     ERP BUSINESS MODULES
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
      POS                 Sales              Purchases
       │                    │                    │
   Pharmacy              Inventory              Gym
       │                    │                    │
 Restaurant             Expenses             Services
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
                 BUSINESS TRANSACTION LAYER
                            │
                            ▼
                   ACCOUNTING EVENT LAYER
                            │
                            ▼
              ┌─────────────────────────────┐
              │ CENTRAL ACCOUNTING ENGINE   │
              │  (apps/finance — extended)  │
              └──────────────┬──────────────┘
                             │
                             ▼
                    GENERAL LEDGER
                             │
                   FINANCIAL REPORTING
```

---

## 2. Golden accounting rule

```
Business modules → business transactions
Central Accounting Engine → accounting records (journals)
```

**Forbidden patterns:**

- POS creating debit/credit rows directly
- Gym maintaining `GymFinance` tables
- Hardcoded `account_id = 17` in business services
- Updating posted journal lines in place
- Maintaining `Account.balance` without ledger derivation

**Required pattern:**

```
POS checkout complete
  → emit AccountingEvent(SALE_COMPLETED)
  → AccountingPostingService.post(event)
  → resolve period, rules, mappings
  → JournalEntry + JournalLines
  → validate debit = credit
  → status = POSTED
```

---

## 3. Module responsibilities

| Module | Owns (operational) | Does NOT own |
|--------|-------------------|--------------|
| POS / Sales | Sale, items, payments, receipt, discounts | Journals, GL, CoA |
| Inventory | Quantity, warehouses, movements, batches | Inventory asset GL balance (accounting posts it) |
| Purchases | PO, receiving, supplier relationship | AP control account |
| Gym | Members, plans, attendance | Membership revenue GL |
| Pharmacy | Batches, expiry, prescriptions | Pharmacy revenue GL |
| Restaurant | Tables, orders, KDS | Restaurant revenue GL |
| Expenses | Expense request/approval workflow | Expense account postings |
| **Finance** | CoA, journals, periods, mappings, rules, reports | Sales carts, stock quantities |

---

## 4. Django domain layout (adapted to existing repo)

Extend `apps/finance` rather than creating `apps/accounting/`:

```
backend/apps/finance/
├── models/
│   ├── account.py              # EXISTS — extend control flags
│   ├── journal.py              # EXISTS — extend source_module, idempotency
│   ├── financial_period.py     # NEW
│   ├── fiscal_year.py          # NEW
│   ├── posting_rule.py         # NEW
│   ├── account_mapping.py      # NEW
│   ├── accounting_event.py     # NEW (or platform outbox extension)
│   └── cost_center.py          # NEW (phase 26)
├── services/
│   ├── chart_service.py        # EXISTS — extend templates
│   ├── journal_service.py      # EXISTS — becomes lower-level primitive
│   ├── posting_service.py      # NEW — central posting engine
│   ├── reversal_service.py     # NEW
│   ├── period_service.py       # NEW
│   ├── settlement_service.py   # NEW (AR/AP payments)
│   ├── reconciliation_service.py # NEW
│   └── summary_service.py      # EXISTS — ledger-first KPIs
├── selectors/
│   ├── ledger.py               # NEW
│   ├── trial_balance.py        # NEW
│   ├── profit_loss.py          # NEW
│   ├── balance_sheet.py        # NEW
│   └── cash_flow.py            # NEW
├── validators/
│   └── posting_validators.py   # NEW — balance, period, control account
├── events/
│   └── event_types.py          # NEW — SALE_COMPLETED, etc.
├── permissions/
│   └── bootstrap.py            # NEW — accounting.* codenames
├── api/                        # via backend/api/v1/finance/ (+ alias /accounting/)
└── tests/
```

API remains at `/api/v1/finance/` for backward compatibility. Add `/api/v1/accounting/` as an alias namespace in a later phase if needed.

---

## 5. Core components

### 5.1 AccountingPostingService

Single entry point for automated posting:

```python
AccountingPostingService.post(
    event_type="SALE_COMPLETED",
    tenant=tenant,
    source_module="sales",
    source_type="invoice",
    source_id=invoice.id,
    source_reference=invoice.invoice_number,
    occurred_at=invoice.issue_date,
    context={...},  # payment_method, amounts, line items
    idempotency_key=f"invoice:{invoice.id}:sale",
    user=user,
)
```

Pipeline:

1. Validate event payload
2. Resolve tenant + branch
3. Resolve financial period (reject if closed/locked)
4. Check idempotency (return existing journal if duplicate)
5. Load posting rules (event_type + business_type + conditions)
6. Resolve account mappings → concrete `Account` rows
7. Build journal lines
8. Validate debit = credit
9. Create `JournalEntry` + `JournalLine` rows (status POSTED)
10. Mark `AccountingEvent` as POSTED

All within `transaction.atomic()` with the originating business operation when synchronous.

### 5.2 JournalService (existing — role change)

Becomes a **low-level primitive** used by `AccountingPostingService`:

- Line validation
- Entry numbering
- Manual journal creation (finance users)
- Serialization

Business modules must **not** call `JournalService.create_entry` directly except through posting service or explicit manual journal API.

### 5.3 AccountingReversalService

For refunds, voids, corrections:

```
Original journal (POSTED, immutable)
  → Reversal journal (swapped debits/credits)
  → Optional corrected journal
```

Never DELETE or UPDATE posted lines.

### 5.4 PeriodService

```
Transaction date → FiscalYear → FinancialPeriod
```

Period statuses: `OPEN`, `SOFT_CLOSED`, `CLOSED`, `LOCKED`

Posting engine rejects unauthorized postings to non-open periods.

### 5.5 AccountMapping

Semantic keys resolved per tenant:

```
DEFAULT_CASH          → Account code 1000 (or tenant override)
DEFAULT_SALES_REVENUE → Account code 4000
DEFAULT_COGS          → Account code 5000
GYM_MEMBERSHIP_REVENUE → tenant-specific account
```

Business modules pass semantic keys; posting engine resolves IDs.

---

## 6. Transaction boundaries

Critical operations must be atomic:

```python
with transaction.atomic():
    invoice = create_sale(...)
    apply_stock(...)
    record_payments(...)
    AccountingPostingService.post(...)  # same transaction
```

If posting fails → full rollback. No "sale completed but accounting missing" unless using durable outbox (see below).

### 6.1 Transactional outbox (async path)

For Celery-backed posting (optional for non-critical paths):

```
DB transaction:
  ├── business row
  └── AccountingEvent(status=PENDING)
commit
  → Celery worker
  → AccountingPostingService.post(event)
```

Existing sync outbox (`apps/platform`) handles desktop sync — **separate concern**. Accounting events may reuse similar patterns but must not conflate with shop push.

---

## 7. Idempotency

Every automated posting carries:

- `idempotency_key` (caller-provided or deterministic)
- Unique constraint: `(tenant, source_module, source_type, source_id, event_type)` for posted events

Replay of POS checkout with same `idempotency_key` → return existing journal, no duplicate.

**Already implemented for expenses** in `JournalService.post_expense` — generalize this pattern.

---

## 8. Source traceability

Extend `JournalEntry`:

| Field | Example |
|-------|---------|
| `source_module` | `sales`, `purchases`, `gym` |
| `source_type` | `invoice`, `expense`, `payment` (exists) |
| `source_id` | UUID (exists) |
| `source_reference` | `INV-2026-001245` |
| `idempotency_key` | `pos:checkout:abc123` |

Enables drill-down: POS Sale ↔ Journal ↔ GL account balance.

---

## 9. Tenant isolation

All accounting models use `TenantScopedModel` (already on `Account`, `JournalEntry`).

- Account codes unique per tenant (constraint exists)
- Journals scoped via `apply_tenant_scope`
- Posting rules and mappings tenant-scoped
- Business-type templates copied at tenant provisioning — then customizable

---

## 10. Business-type templates

On tenant create (extend `ChartService.ensure_default_chart`):

| Business type | Template |
|---------------|----------|
| General retail | Current 16-account default |
| Pharmacy | + Pharmacy Sales Revenue, batch COGS notes |
| Gym | + Membership Revenue, PT Revenue, Class Revenue |
| Restaurant | + Restaurant Sales Revenue |
| Wholesale | + Trade discounts, freight |

Templates seed CoA + default `AccountMapping` rows. Tenants may add accounts but system accounts are protected.

---

## 11. Control accounts

Extend `Account`:

```python
is_control_account = models.BooleanField(default=False)
allow_manual_posting = models.BooleanField(default=True)
```

Control accounts (AR, AP, Inventory) restrict manual journal lines unless user has `accounting.journals.post_control`.

Sub-ledger totals must reconcile with control account GL balance.

---

## 12. Sync / desktop boundary

`SyncFinancePolicy` **correctly** forbids shop push of journals/accounts.

Desktop POS may sync operational invoices; cloud posting engine creates authoritative GL entries.

Do not change this boundary without explicit multi-master accounting design.

---

## 13. Frontend architecture

Web (React/Vite) and mobile (React Native) consume the same `/api/v1/finance/` API.

- Complex configuration (CoA edit, period close, posting rules) → web-first
- Operational finance (receipts, payments, expense capture, summary) → web + mobile

No separate mobile finance logic.

---

## 14. Relationship to STEP 21

STEP 21 delivered Phase 04–07 **partially**:

| Phase | STEP 21 status | Remaining |
|-------|----------------|-----------|
| 04 Chart of Accounts | Default bootstrap | Templates, CRUD, control flags |
| 05 Financial Periods | Not started | Full engine |
| 06 Journal Engine | Manual + expense | Immutability enforcement |
| 07 General Ledger | Balance from lines | Selectors, official reports |
| 08–11 | Not started | Mapping, rules, events, idempotency |
| 12–13 | Not started | Reversal + POS |
| 14+ | Not started | Module integrations |

This architecture doc is the blueprint for **STEP 35+** (Central Accounting Engine epic).

---

## 15. Non-negotiable principles (checklist)

1. One Central Accounting Engine (`apps/finance`)
2. One GL per tenant
3. Double-entry; debit = credit always
4. Business modules never maintain independent financial truth
5. Every financial event traceable to source
6. Posted journals immutable
7. Corrections via reversal
8. Duplicate posting prevented
9. Closed periods protected
10. Transaction-safe posting
11. Decimal/NUMERIC for money
12. Strict tenant isolation
13. AR/AP reconcile with control accounts
14. Inventory GL reconciles with valuation
15. Financial statements from posted ledger
16. Configurable account mappings
17. Recoverable accounting events
18. Failed postings visible and safely retryable
19. Auditable critical actions

---

*See also: [ACCOUNTING_ERD.md](./ACCOUNTING_ERD.md), [POSTING_ENGINE.md](./POSTING_ENGINE.md), [MODULE_INTEGRATION.md](./MODULE_INTEGRATION.md)*

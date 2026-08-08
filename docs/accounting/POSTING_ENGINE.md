# Posting Engine

**Date:** 2026-08-07  
**Status:** Target design — Phase 09  
**Service:** `AccountingPostingService` (to be created in `apps/finance/services/posting_service.py`)

---

## 1. Purpose

The Central Posting Engine is the **only** automated path from business events to journal entries.

Existing `JournalService.post_expense` becomes one **handler** registered with the engine. All new integrations (POS, purchases, gym, refunds) use the same pipeline.

---

## 2. Posting pipeline

```
AccountingEvent (or inline call)
        │
        ▼
┌───────────────────┐
│ Validate payload  │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Resolve tenant    │  apply_tenant_scope / stamp_tenant_id
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Idempotency check │  return existing journal if duplicate key
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Resolve period    │  PeriodService.resolve(date) → reject if locked
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Load posting rules│  match event_type + business_type + conditions
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Resolve mappings  │  semantic keys → Account rows
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Build journal lines│ compute amounts from payload
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Validate balance  │  sum(debit) == sum(credit)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Create entry      │  JournalService.create_entry (internal)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Mark event POSTED │
└───────────────────┘
```

---

## 3. Service interface (proposed)

```python
class AccountingPostingService:
    @staticmethod
    @transaction.atomic
    def post(
        *,
        event_type: str,
        tenant_id,
        source_module: str,
        source_type: str,
        source_id,
        source_reference: str = "",
        occurred_at=None,
        payload: dict,
        idempotency_key: str,
        user=None,
        branch_id=None,
        sync: bool = True,  # False → enqueue AccountingEvent only
    ) -> JournalEntry:
        ...

    @staticmethod
    def post_from_event(accounting_event: AccountingEvent) -> JournalEntry:
        """Celery worker entry point."""
        ...
```

---

## 4. Posting rules

### 4.1 Rule model

Rules are **configurable per tenant** with system defaults seeded at provisioning.

```python
PostingRule:
  event_type          # SALE_COMPLETED
  business_type_code  # optional filter
  conditions          # JSON: {"payment_method": "cash"}
  priority            # lower wins
  lines[]             # PostingRuleLine: side, mapping_key, amount_expr
```

### 4.2 Standard rules (system seeds)

#### Cash sale — `SALE_COMPLETED` (payment_method=cash|card|mobile)

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `DEFAULT_CASH` / bank / mobile | `total_amount` |
| Credit | `DEFAULT_SALES_REVENUE` | `total_amount − tax_amount` |
| Credit | `DEFAULT_TAX_PAYABLE` | `tax_amount` (when > 0) |

#### Credit / on-account sale — `SALE_COMPLETED` (payment_method=on_account)

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `DEFAULT_RECEIVABLE` | `total_amount` |
| Credit | `DEFAULT_SALES_REVENUE` | `total_amount − tax_amount` |
| Credit | `DEFAULT_TAX_PAYABLE` | `tax_amount` (when > 0) |

#### COGS — `SALE_COMPLETED` (always when inventory tracked)

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `DEFAULT_COGS` | `cost_total` |
| Credit | `DEFAULT_INVENTORY` | `cost_total` |

COGS amount computed from invoice line cost × qty at posting time.

#### Operating expense — `EXPENSE_APPROVED` (exists today as `post_expense`)

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `EXPENSE_{category}` | `amount` |
| Credit | `DEFAULT_CASH` | `amount` |

#### Purchase received — `PURCHASE_RECEIVED`

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `DEFAULT_INVENTORY` | `receive_total` |
| Credit | `DEFAULT_PAYABLE` | `receive_total` |

#### Supplier payment — `SUPPLIER_PAYMENT_COMPLETED`

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `DEFAULT_PAYABLE` | `amount` |
| Credit | `DEFAULT_CASH` | `amount` |

#### Sale refund — `SALE_REFUNDED`

| Line | Mapping key | Amount |
|------|-------------|--------|
| Debit | `DEFAULT_SALES_RETURNS` | `refund_amount − tax_amount` |
| Debit | `DEFAULT_TAX_PAYABLE` | `tax_amount` (proportional when > 0) |
| Credit | `DEFAULT_CASH` or `DEFAULT_RECEIVABLE` | `refund_amount` |

Plus optional inventory return lines (Dr Inventory / Cr COGS) when stock restored.

#### Gym membership — `GYM_MEMBERSHIP_SOLD`

Same as cash/credit sale but credit line uses `GYM_MEMBERSHIP_REVENUE` mapping key.

---

## 5. Amount expressions

Posting rule lines reference payload fields:

| Expression | Source |
|------------|--------|
| `total_amount` | Invoice total |
| `cost_total` | Sum of line cost × qty |
| `tax_amount` | Invoice tax (future: `DEFAULT_TAX_PAYABLE`) |
| `amount` | Generic single amount |
| `receive_total` | PO receive line totals |

Future: formula support for multi-currency, discounts ex-tax.

---

## 6. Idempotency

### 6.1 Key format (recommended)

```
{event_type}:{source_module}:{source_type}:{source_id}
```

Examples:

```
SALE_COMPLETED:sales:invoice:550e8400-e29b-41d4-a716-446655440000
EXPENSE_APPROVED:sales:expense:...
SALE_REFUNDED:sales:sale_refund:...
```

POS checkout may also pass client `idempotency_key` — engine stores both.

### 6.2 Existing pattern (expense)

```python
# journal_service.py — post_expense
existing = JournalEntry.active_objects().filter(
    tenant_id=tenant_id,
    source_type=JournalEntry.SOURCE_EXPENSE,
    source_id=expense.id,
    status=JournalEntry.STATUS_POSTED,
).first()
if existing:
    return existing
```

Generalize to `AccountingEvent` table with unique constraint on `idempotency_key`.

---

## 7. Period enforcement

Before creating journal:

```python
period = PeriodService.resolve(tenant_id, occurred_at)
if period.status in (CLOSED, LOCKED):
    raise PostingError("Financial period is closed.")
if period.status == SOFT_CLOSED and not user.has_perm("accounting.periods.post_soft_closed"):
    raise PostingError("Period soft-closed.")
```

Until `FinancialPeriod` ships, default to permissive mode with logged warning.

---

## 8. Control account validation

Before posting lines:

```python
for line in lines:
    if line.account.is_control_account and not line.account.allow_manual_posting:
        if source_type == "manual":
            raise PostingError("Control account requires sub-ledger posting.")
```

Automated postings from invoice/payment handlers are allowed on control accounts.

---

## 9. Integration points (call sites)

| Call site | Event | When |
|-----------|-------|------|
| `pos_service.py` | `SALE_COMPLETED` | After invoice paid + stock applied |
| `refund_service.py` | `SALE_REFUNDED` | After refund persisted |
| `daily_ops_service.py` | `EXPENSE_APPROVED` | Replace direct `post_expense` call |
| `receiving_service.py` | `PURCHASE_RECEIVED` | After stock increased |
| `gym_payment_service.py` | `GYM_MEMBERSHIP_SOLD` | After invoice + payment |
| Future: supplier payment | `SUPPLIER_PAYMENT_COMPLETED` | On payment record |

**Never** in: DRF views, serializers, frontend, Django signals without outbox.

---

## 10. Error handling

| Failure | Behavior (sync) | Behavior (async) |
|---------|-----------------|------------------|
| Unbalanced lines | Rollback business txn | Mark event FAILED |
| Period closed | Rollback | Mark FAILED, alert admin |
| Missing mapping | Rollback | Mark FAILED with clear error |
| Duplicate idempotency | Return existing journal | No-op success |

Failed events visible at `/api/v1/finance/health/` or dedicated accounting health endpoint.

---

## 11. Reversal (see ReversalService)

Posting engine does **not** delete entries. Refunds call:

```python
AccountingReversalService.reverse(
    original_entry=journal,
    event_type="SALE_REFUNDED",
    ...
)
```

Creates new journal with swapped lines linked via `reverses_entry_id`.

---

## 12. Implementation phases

| Phase | Deliverable |
|-------|-------------|
| 9a | `PostingRule` + `AccountMapping` models + seeds |
| 9b | `AccountingPostingService.post` skeleton |
| 9c | Migrate `post_expense` to engine |
| 9d | POS `SALE_COMPLETED` handler |
| 9e | Refund reversal handler |
| 9f | Purchase receive handler |

---

*See also: [ACCOUNTING_EVENTS.md](./ACCOUNTING_EVENTS.md), [ACCOUNT_MAPPING.md](./ACCOUNT_MAPPING.md)*

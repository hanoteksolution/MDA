# Accounting Events

**Date:** 2026-08-07  
**Status:** Target design — Phase 10

---

## 1. Purpose

Accounting events are the **standardized contract** between business modules and the Central Accounting Engine.

Business modules emit events describing *what happened*. The posting engine decides *financial impact* via rules and mappings.

---

## 2. Event catalog

### Sales / POS

| Event type | Trigger | Source |
|------------|---------|--------|
| `SALE_COMPLETED` | POS/gym checkout paid | `sales.invoice` |
| `SALE_REFUNDED` | Partial/full refund processed | `sales.sale_refund` |
| `SALE_VOIDED` | Invoice voided before settlement | `sales.invoice` |
| `CUSTOMER_INVOICE_POSTED` | Non-POS invoice finalized | `sales.invoice` |
| `CUSTOMER_PAYMENT_RECEIVED` | AR payment on account | `sales.payment` via voucher |

### Purchases

| Event type | Trigger | Source |
|------------|---------|--------|
| `PURCHASE_RECEIVED` | Goods receipt confirmed | `purchases` / inventory receive |
| `SUPPLIER_BILL_POSTED` | Supplier invoice recorded | future supplier bill model |
| `SUPPLIER_PAYMENT_COMPLETED` | Payment to supplier | `finance.SupplierPayment` via voucher |

### Expenses

| Event type | Trigger | Source |
|------------|---------|--------|
| `EXPENSE_APPROVED` | Expense created/approved | `sales.expense` ✓ wired |
| `EXPENSE_PAID` | Separate payment of accrued expense | future |

### Inventory

| Event type | Trigger | Source |
|------------|---------|--------|
| `INVENTORY_ADJUSTED` | Manual adjustment approved | `inventory.adjustment` |
| `INVENTORY_WRITTEN_OFF` | Damage/expiry write-off | pharmacy/inventory |

### Gym

| Event type | Trigger | Source |
|------------|---------|--------|
| `GYM_MEMBERSHIP_SOLD` | Membership checkout | `gym` via invoice |
| `GYM_SERVICE_SOLD` | PT/class fee | future |

### Pharmacy / Restaurant

| Event type | Trigger | Source |
|------------|---------|--------|
| `PHARMACY_SALE_COMPLETED` | Alias of `SALE_COMPLETED` with pharmacy revenue mapping | POS |
| `RESTAURANT_ORDER_PAID` | Alias of `SALE_COMPLETED` with restaurant mapping | POS/KDS |

### Futsal

| Event type | Trigger | Source |
|------------|---------|--------|
| `FUTSAL_INCOME_RECORDED` | Booking payment or income ledger entry | `futsal.FutsalLedgerEntry` |
| `FUTSAL_EXPENSE_RECORDED` | Expense ledger entry | `futsal.FutsalLedgerEntry` |

### Banking / Vouchers

| Event type | Trigger | Source |
|------------|---------|--------|
| `BANK_TRANSFER_COMPLETED` | Inter-account transfer | finance voucher |
| `RECEIPT_VOUCHER_POSTED` | Manual receipt | finance |
| `PAYMENT_VOUCHER_POSTED` | Manual payment | finance |
| `JOURNAL_VOUCHER_POSTED` | Manual adjusting entry | finance |

### Credit / Debit notes

| Event type | Trigger | Source |
|------------|---------|--------|
| `CREDIT_NOTE_POSTED` | Customer credit note | sales |
| `DEBIT_NOTE_POSTED` | Supplier debit note | purchases |

---

## 3. Event payload schema

Standard envelope:

```json
{
  "event_type": "SALE_COMPLETED",
  "tenant_id": "uuid",
  "source_module": "sales",
  "source_type": "invoice",
  "source_id": "uuid",
  "source_reference": "INV-2026-001245",
  "idempotency_key": "SALE_COMPLETED:sales:invoice:uuid",
  "occurred_at": "2026-08-07T10:30:00Z",
  "branch_id": "uuid",
  "payload": {
    "total_amount": "100.00",
    "subtotal": "95.00",
    "tax_amount": "5.00",
    "discount_amount": "0.00",
    "cost_total": "60.00",
    "payment_method": "cash",
    "payments": [
      {"method": "cash", "amount": "100.00"}
    ],
    "customer_id": "uuid",
    "lines": [
      {
        "product_id": "uuid",
        "quantity": "2",
        "unit_price": "50.00",
        "line_total": "100.00",
        "unit_cost": "30.00"
      }
    ]
  }
}
```

Business modules construct payload from their domain objects — **no account IDs in payload**.

---

## 4. AccountingEvent model lifecycle

```
PENDING → PROCESSING → POSTED
              │
              └──→ FAILED (retryable)
POSTED → REVERSED (via reversal event)
```

| Status | Meaning |
|--------|---------|
| `PENDING` | Persisted in outbox; not yet processed |
| `PROCESSING` | Worker claimed event |
| `POSTED` | Journal created; `journal_entry_id` set |
| `FAILED` | Error stored; admin can retry |
| `REVERSED` | Original event negated by reversal |

Fields: see [ACCOUNTING_ERD.md](./ACCOUNTING_ERD.md#finance_accounting_events--accountingevent)

---

## 5. Sync vs async emission

### Synchronous (default for money-critical paths)

Used by POS checkout, refunds, expense create — same DB transaction as business row.

```python
with transaction.atomic():
    invoice = create_invoice(...)
    AccountingPostingService.post(event_type="SALE_COMPLETED", ...)
```

### Asynchronous (optional)

For high-volume or non-critical backfill:

```python
with transaction.atomic():
    invoice = create_invoice(...)
    AccountingEvent.objects.create(status=PENDING, ...)
# Celery: process_accounting_event.delay(event.id)
```

**Rule:** If async, business module must not report "fully complete" to user until POSTED, OR show explicit "accounting pending" state.

Current codebase: no accounting async — recommend sync for Phase 13 (POS).

---

## 6. Event → handler registry

```python
EVENT_HANDLERS = {
    "SALE_COMPLETED": SaleCompletedHandler,
    "SALE_REFUNDED": SaleRefundedHandler,
    "EXPENSE_APPROVED": ExpenseApprovedHandler,
    "PURCHASE_RECEIVED": PurchaseReceivedHandler,
    "GYM_MEMBERSHIP_SOLD": GymMembershipSoldHandler,
    ...
}
```

Each handler:

1. Validates required payload keys
2. Selects posting rules for event + tenant business type
3. Delegates line building to posting engine

---

## 7. Relationship to sync outbox (STEP 29)

| Concern | Table / service | Purpose |
|---------|-----------------|---------|
| Desktop → cloud sync | Platform sync outbox | Operational invoice/inventory sync |
| Accounting events | `finance_accounting_events` | Cloud GL posting |

Do not merge these. Desktop pushes operational data; cloud posting engine creates journals.

`SyncFinancePolicy` forbids journal push from shop — **keep**.

---

## 8. Event versioning

Payload may include `"schema_version": 1` for forward compatibility.

Breaking payload changes require new handler version or migration of pending events.

---

## 9. Implementation priority

| Priority | Event | Rationale |
|----------|-------|-----------|
| P0 | `EXPENSE_APPROVED` | Migrate existing `post_expense` |
| P0 | `SALE_COMPLETED` | Highest volume; POS |
| P1 | `SALE_REFUNDED` | Money accuracy |
| P1 | `PURCHASE_RECEIVED` | AP + inventory asset |
| P2 | `GYM_MEMBERSHIP_SOLD` | Same handler as sale with mapping |
| P2 | `CUSTOMER_PAYMENT_RECEIVED` | AR settlement |
| P3 | Inventory adjust/write-off | Pharmacy expiry |

---

*See also: [POSTING_ENGINE.md](./POSTING_ENGINE.md), [MODULE_INTEGRATION.md](./MODULE_INTEGRATION.md)*

# Module Integration

**Date:** 2026-08-07  
**Status:** Target design — Phases 13–24

---

## 1. Integration principle

Every module integration follows the same pattern:

```
Module service completes business transaction
  → build event payload (operational data only)
  → AccountingPostingService.post(...) OR AccountingEvent enqueue
  → journal created with source traceability
```

Modules **never** import `JournalLine` or call `Account.objects.get(code=...)`.

---

## 2. POS → Central Accounting Engine

### Current state

File: `backend/apps/sales/services/pos_service.py`

```
checkout → InvoiceService → Payment → stock → sync outbox
(no finance calls)
```

### Target state

```python
# At end of successful checkout, inside existing transaction.atomic():
AccountingPostingService.post(
    event_type="SALE_COMPLETED",
    tenant_id=invoice.tenant_id,
    source_module="sales",
    source_type="invoice",
    source_id=invoice.id,
    source_reference=invoice.invoice_number,
    occurred_at=invoice.issue_date,
    payload={
        "total_amount": str(invoice.total_amount),
        "cost_total": str(computed_cost_total),
        "payment_method": primary_method,
        "payments": [...],
        "lines": [...],
    },
    idempotency_key=f"SALE_COMPLETED:sales:invoice:{invoice.id}",
    user=user,
    branch_id=invoice.branch_id,
)
```

### Postings generated

**Revenue leg (cash example):**

| Account | Debit | Credit |
|---------|-------|--------|
| Cash | 100 | |
| Sales Revenue | | 100 |

**COGS leg (when inventory tracked):**

| Account | Debit | Credit |
|---------|-------|--------|
| COGS | 60 | |
| Inventory | | 60 |

**On-account sale:** Debit AR instead of Cash.

### Refunds

File: `backend/apps/sales/services/refund_service.py`

After refund persisted:

```python
AccountingPostingService.post(
    event_type="SALE_REFUNDED",
    ...
    payload={"refund_amount": ..., "restore_inventory": True, ...},
)
```

Or `AccountingReversalService.reverse(original_sale_journal, ...)`.

---

## 3. Pharmacy → Central Accounting Engine

Pharmacy does **not** get separate accounting.

```
Pharmacy batch allocation (inventory)
  → Universal POS checkout
  → SALE_COMPLETED (or PHARMACY_SALE_COMPLETED alias)
  → posting rule uses PHARMACY_SALES_REVENUE mapping key
```

Purchase receiving:

```
PurchaseReceivingService.receive(...)
  → PURCHASE_RECEIVED event
  → Dr Inventory / Cr AP
```

Batch expiry write-off:

```
INVENTORY_WRITTEN_OFF event
  → Dr Inventory Loss / Cr Inventory
```

---

## 4. Gym → Central Accounting Engine

File: `backend/apps/gym/services/gym_payment_service.py`

Current: creates Invoice + Payment, activates subscription.

Target: same as POS with gym revenue mapping.

```python
event_type="GYM_MEMBERSHIP_SOLD"  # or SALE_COMPLETED with gym mapping
credit_mapping_key="GYM_MEMBERSHIP_REVENUE"
```

Personal training / class fees: same engine, different mapping keys.

**Do not create** `GymFinance` or `GymAccounting` apps.

---

## 5. Restaurant / Cafeteria → Central Accounting Engine

Deferred track (STEP 12b restaurant/KDS). When built:

```
Restaurant order paid
  → POS checkout (existing)
  → SALE_COMPLETED
  → RESTAURANT_SALES_REVENUE mapping
```

Kitchen/inventory consumption may trigger COGS at order completion or at sale — configurable posting rule condition.

---

## 6. Purchases → Central Accounting Engine

### PO create

**No journal.** Operational document only.

### Goods receive

File: `backend/apps/inventory/services/receiving_service.py`

After stock increased:

```python
AccountingPostingService.post(
    event_type="PURCHASE_RECEIVED",
    source_module="purchases",
    source_type="purchase_receive",
    source_id=receive_batch_id,
    payload={
        "receive_total": str(total_cost),
        "supplier_id": str(po.supplier_id),
        "lines": [...],
    },
    ...
)
```

| Account | Debit | Credit |
|---------|-------|--------|
| Inventory | receive_total | |
| Accounts Payable | | receive_total |

### Supplier payment

File: `backend/apps/finance/services/voucher_service.py`

```
VoucherService.record_supplier_payment(...)
  → SUPPLIER_PAYMENT_COMPLETED
  Dr AP / Cr Cash|Bank|Mobile
```

API: `POST /finance/vouchers/supplier-payments/`

### Customer receipt

```
VoucherService.record_customer_receipt(...)
  → CUSTOMER_PAYMENT_RECEIVED
  Dr Cash|Bank|Mobile / Cr AR
```

API: `POST /finance/vouchers/receipts/`

---

## 7. Inventory → Central Accounting Engine

Inventory module owns **quantity**. Accounting owns **value**.

| Operational event | Accounting event |
|-------------------|------------------|
| Sale stock deduct | COGS via SALE_COMPLETED |
| Receive stock | PURCHASE_RECEIVED |
| Manual adjustment (+/- qty) | INVENTORY_ADJUSTED |
| Damage/expiry | INVENTORY_WRITTEN_OFF |
| Transfer between warehouses | Optional inter-warehouse (same entity, no GL) or reclass |

Never update `Account` balance when `Inventory.quantity` changes — always emit event.

---

## 8. Expenses → Central Accounting Engine

File: `backend/apps/sales/services/daily_ops_service.py`

**Today:** `JournalService.post_expense` on create only.

**Target:**

| Action | Event |
|--------|-------|
| Create expense | `EXPENSE_APPROVED` via posting engine |
| Update amount | Reverse original + post corrected (or adjustment event) |
| Delete expense | Reversal journal |

Move `Expense` model to `apps/finance` in a later refactor phase — not blocking integration.

---

## 9. Futsal — migration path

Current operational ledger: `FutsalLedgerEntry` at `/api/v1/futsal/ledger/`.

**Status (Phase N):** Option A implemented — dual-write.

| Operational action | Accounting event | Journal |
|--------------------|------------------|---------|
| Booking with `amount_paid > 0` | `FUTSAL_INCOME_RECORDED` | Dr Cash / Cr Futsal Revenue (4100) |
| Manual income ledger entry | `FUTSAL_INCOME_RECORDED` | same |
| Manual expense ledger entry | `FUTSAL_EXPENSE_RECORDED` | Dr Futsal Expense (6080) / Cr Cash |

Mappings: `FUTSAL_REVENUE` → 4100, `FUTSAL_EXPENSE` → 6080.

Futsal module P&L summary still reads `FutsalLedgerEntry` for ops KPIs; official statements use the GL.

---

## 10. Sync / desktop integration

Desktop POS syncs operational invoices via `SyncFinancePolicy`-allowed fields.

Cloud receives invoice → **optional** retroactive `SALE_COMPLETED` posting job if invoice originated offline.

Rules:

- Shop never pushes journals
- Cloud posting uses same `AccountingPostingService`
- Idempotency key includes `device_id` + `local_id` from sync payload

---

## 11. Integration checklist per module

| Module | Event(s) | Phase | Status |
|--------|----------|-------|--------|
| Expenses | EXPENSE_APPROVED | 21 | Partial (direct post_expense) |
| POS | SALE_COMPLETED, SALE_REFUNDED | 13–14 | Not started |
| Purchases | PURCHASE_RECEIVED | 17–18 | Not started |
| Gym | GYM_MEMBERSHIP_SOLD | 23 | Not started |
| Pharmacy | via POS + write-off | 22 | Not started |
| Restaurant | via POS | 24 | Deferred |
| Futsal | `FUTSAL_INCOME_RECORDED`, `FUTSAL_EXPENSE_RECORDED` | N | Dual-write to GL |

---

## 12. Files to modify (implementation reference)

```
backend/apps/sales/services/pos_service.py          — add posting call
backend/apps/sales/services/refund_service.py       — add reversal
backend/apps/sales/services/daily_ops_service.py    — migrate to engine
backend/apps/gym/services/gym_payment_service.py    — add posting call
backend/apps/inventory/services/receiving_service.py — add posting call
backend/apps/finance/services/posting_service.py    — NEW
backend/apps/futsal/services/futsal_service.py      — migrate or deprecate
```

---

*See also: [ACCOUNTING_EVENTS.md](./ACCOUNTING_EVENTS.md), [POSTING_ENGINE.md](./POSTING_ENGINE.md)*

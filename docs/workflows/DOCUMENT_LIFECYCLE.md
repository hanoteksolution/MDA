# Document Lifecycle

Version: 1.0

Defines status transitions for all transactional documents. Resolves the POS vs invoice inventory rule:

- **POS sales** decrement inventory immediately on checkout (status → `completed`).
- **Invoices** (non-POS) affect finance on issue but only decrement inventory when linked sale reaches `completed`.

---

## Sales / POS

### Statuses

| Status | Description |
|--------|-------------|
| `draft` | Cart open, no inventory impact |
| `confirmed` | Order placed, stock reserved (optional) |
| `completed` | Paid and finalized — inventory decremented, receipt created |
| `partially_paid` | Partial payment received |
| `cancelled` | Voided before completion — release reserved stock |
| `returned` | Full or partial return processed |

### Transitions

```
draft → confirmed → completed
draft → completed          (POS fast path: skip confirmed)
draft → cancelled
confirmed → completed
confirmed → cancelled
completed → returned
partially_paid → completed
partially_paid → returned
```

### Side Effects by Status

| Transition | Inventory | Finance | Receipt | Audit |
|------------|-----------|---------|---------|-------|
| → `confirmed` | Reserve stock (optional) | None | None | Yes |
| → `completed` | Decrement stock | Create revenue + COGS entries | Generate receipt | Yes |
| → `cancelled` | Release reserved stock | None | None | Yes |
| → `returned` | Increment stock | Reverse revenue/COGS | Return receipt | Yes |

### POS Fast Path

POS checkout goes directly `draft → completed`:

1. Validate stock availability
2. Decrement inventory + create stock_movement + inventory_transaction
3. Create sale record with status `completed`
4. Record payment(s)
5. Generate receipt
6. Create audit log
7. Update customer history (if customer attached)

---

## Quotations

### Statuses

| Status | Description |
|--------|-------------|
| `draft` | Being prepared |
| `sent` | Delivered to customer |
| `accepted` | Customer accepted |
| `expired` | Past valid_until date |
| `converted` | Converted to invoice or sale |
| `cancelled` | Voided |

### Transitions

```
draft → sent → accepted → converted
draft → sent → expired
draft → cancelled
sent → cancelled
accepted → converted
```

### Side Effects

- **No inventory impact** at any status
- **No finance impact** at any status
- `converted` creates invoice or sale; quotation becomes read-only

### Convert Rules

- `accepted → converted`: Admin, Branch Manager, Sales Staff
- Creates invoice in `draft` status with quotation line items copied
- Links `invoice.quotation_id` to source quotation

---

## Invoices

### Statuses

| Status | Description |
|--------|-------------|
| `draft` | Being prepared |
| `issued` | Sent to customer, finance entries created |
| `paid` | Fully paid |
| `partially_paid` | Partial payment received |
| `overdue` | Past due_date with outstanding balance |
| `void` | Cancelled after issue |

### Transitions

```
draft → issued → paid
draft → issued → partially_paid → paid
draft → issued → overdue → paid
draft → cancelled (while draft)
issued → void
```

### Side Effects

| Transition | Inventory | Finance |
|------------|-----------|---------|
| → `issued` | None (unless linked sale completes) | Create accounts receivable entry |
| → `paid` | None | Record payment, close receivable |
| → `void` | None | Reverse receivable entry |

### Inventory Rule

Invoice alone does **not** reduce inventory. Inventory decrements when:

1. Linked sale reaches `completed`, OR
2. Invoice is converted to sale and sale completes

---

## Receipts

Receipts are **generated documents**, not stateful workflows.

- Created automatically when sale reaches `completed`
- Linked 1:1 to sale (`receipt.sale_id`)
- Printable immediately after creation
- No status transitions — immutable after creation

---

## Purchase Orders

### Statuses

| Status | Description |
|--------|-------------|
| `draft` | Being prepared |
| `submitted` | Awaiting approval |
| `approved` | Approved for ordering |
| `partially_received` | Some items received |
| `received` | All items received |
| `cancelled` | Voided |

### Transitions

```
draft → submitted → approved → partially_received → received
draft → submitted → cancelled
submitted → cancelled
approved → cancelled
approved → partially_received
partially_received → received
```

### Approval Roles

| Transition | Required Role |
|------------|---------------|
| `draft → submitted` | Inventory Manager, Branch Manager, Admin |
| `submitted → approved` | Branch Manager, Admin, Super Admin |
| `approved → received` | Inventory Manager, Branch Manager, Admin |

### Side Effects

- **No inventory impact** until goods receiving (purchase record created)
- `partially_received` / `received` triggers purchase creation and inventory increment

---

## Purchases (Goods Receiving)

### Statuses

| Status | Description |
|--------|-------------|
| `draft` | Receiving in progress |
| `received` | Goods received, inventory updated |
| `cancelled` | Voided before receiving |

### Side Effects on `received`

1. Increment inventory per line item
2. Create stock_movement + inventory_transaction
3. Update supplier outstanding_balance
4. Create audit log
5. Update purchase_order received quantities

---

## Returns

### Sale Returns

| Status | Description |
|--------|-------------|
| `draft` | Return being prepared |
| `confirmed` | Return processed |
| `cancelled` | Voided |

**On `confirmed`:** increment inventory, reverse financial impact, create audit log, update sale status to `returned` if full return.

### Purchase Returns

| Status | Description |
|--------|-------------|
| `draft` | Return being prepared |
| `confirmed` | Return processed |
| `cancelled` | Voided |

**On `confirmed`:** decrement inventory, reduce supplier balance, create audit log.

---

## Inventory Adjustments

| Status | Transitions | Side Effects on `confirmed` |
|--------|-------------|----------------------------|
| `draft` | → `confirmed`, → `cancelled` | Adjust inventory quantities, create movements |

---

## Inventory Transfers

| Status | Transitions | Side Effects |
|--------|-------------|--------------|
| `draft` | → `in_transit`, → `cancelled` | None |
| `in_transit` | → `received`, → `cancelled` | On `received`: decrement source, increment destination |
| `received` | Terminal | Movements created |

---

## Document Number Sequences

All document numbers are **unique per branch**:

- Format: `{PREFIX}-{BRANCH_CODE}-{YEAR}-{SEQUENCE}`
- Example: `INV-BR01-2026-000001`
- Sequences stored in `settings` table per branch
- Offline clients use local sequence; reconciled on sync

---

## Status Enum Reference (Implementation)

```python
SALE_STATUS = ["draft", "confirmed", "completed", "partially_paid", "cancelled", "returned"]
QUOTATION_STATUS = ["draft", "sent", "accepted", "expired", "converted", "cancelled"]
INVOICE_STATUS = ["draft", "issued", "paid", "partially_paid", "overdue", "void"]
PO_STATUS = ["draft", "submitted", "approved", "partially_received", "received", "cancelled"]
PURCHASE_STATUS = ["draft", "received", "cancelled"]
RETURN_STATUS = ["draft", "confirmed", "cancelled"]
ADJUSTMENT_STATUS = ["draft", "confirmed", "cancelled"]
TRANSFER_STATUS = ["draft", "in_transit", "received", "cancelled"]
```

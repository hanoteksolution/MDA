# Posting Rules Engine

**Date:** 2026-08-07  
**Service:** `PostingRuleService`  
**Models:** `PostingRule`, `PostingRuleLine` (STEP 35; engine activated STEP 37)

---

## Behavior

```text
Accounting Event
      ↓
PostingRuleService.try_build_lines  (if event is rule-driven)
      ↓ match rule by event_type + conditions
      ↓ resolve mapping_key → AccountMapping → Account
      ↓
Journal lines
      ↓ (if no rule)
Hardcoded AccountingPostingService builders (sales/refunds/splits/tax/COGS)
```

### Rule-driven events (seeded)

| Event | Debit | Credit |
|-------|-------|--------|
| `EXPENSE_APPROVED` | `@expense_mapping` | `DEFAULT_CASH` |
| `PURCHASE_RECEIVED` | `DEFAULT_INVENTORY` | `DEFAULT_PAYABLE` |
| `CUSTOMER_PAYMENT_RECEIVED` | `@payment_mapping` | `DEFAULT_RECEIVABLE` |
| `SUPPLIER_PAYMENT_COMPLETED` | `DEFAULT_PAYABLE` | `@payment_mapping` |
| `FUTSAL_INCOME_RECORDED` | `@payment_mapping` | `FUTSAL_REVENUE` |
| `FUTSAL_EXPENSE_RECORDED` | `FUTSAL_EXPENSE` | `@payment_mapping` |

Special mapping keys:

- `@expense_mapping` — from expense `category`
- `@payment_mapping` — from `payment_method` (cash/bank/mobile/card/on_account)

Memo templates on rule lines:

- `{payment_method}` — payload field
- `{category:Futsal income}` — field with default when empty

### Still builtin (complex)

`SALE_COMPLETED`, `SALE_REFUNDED`, `GYM_MEMBERSHIP_SOLD` — split tenders, tax split, COGS.

---

## Seed

Called automatically on posting (`AccountingPostingService.post`) and cutover prepare.

```python
PostingRuleService.seed_defaults(tenant_id=...)
```

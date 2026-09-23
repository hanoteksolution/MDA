# School Management — Central Accounting Integration

**Date:** 2026-09-01  
**Rule:** School uses the ONE Central Accounting Engine (`apps.finance`). No school-specific ledger.

Reference: `docs/accounting/CENTRAL_ACCOUNTING_ARCHITECTURE.md`, `apps/finance/services/posting_service.py`

---

## Integration Pattern

School fee operations follow the **Gym / Housing** pattern:

```
SchoolFeeService.generate_invoice()
    → creates sales.Invoice + InvoiceItems
    → SchoolFeePostingService.post_invoice()
        → AccountingPostingService.post_event(SCHOOL_FEE_INVOICED)
            → JournalEntry (DR AR / CR Revenue accounts)
```

Payments:

```
sales.Payment recorded
    → SchoolFeePostingService.post_payment()
        → AccountingPostingService.post_event(SCHOOL_FEE_PAYMENT)
            → JournalEntry (DR Cash/Bank / CR AR)
```

---

## New Finance Event Types (Target)

Add to `apps/finance/events/event_types.py`:

| Event | Trigger |
|---|---|
| `SCHOOL_FEE_INVOICED` | Fee invoice issued |
| `SCHOOL_FEE_PAYMENT` | Student payment received |
| `SCHOOL_SCHOLARSHIP_APPLIED` | Discount/scholarship on invoice |
| `SCHOOL_FEE_REFUND` | Refund to student/guardian |
| `SCHOOL_TRANSPORT_FEE_INVOICED` | Transport fee component |
| `SCHOOL_REGISTRATION_FEE` | One-time admission fee |
| `SCHOOL_EXPENSE` | School-context expense (reuses `post_expense` where possible) |
| `SCHOOL_PAYROLL` | When payroll posts (future hrm integration) |

---

## Account Mapping Keys

Configurable per tenant via `AccountMapping` (existing pattern in `apps/finance/models/account_mapping.py`).

| Mapping Key | Default account role | Used when |
|---|---|---|
| `SCHOOL_TUITION_REVENUE` | Revenue | Tuition invoice lines |
| `SCHOOL_REGISTRATION_REVENUE` | Revenue | Registration fees |
| `SCHOOL_TRANSPORT_REVENUE` | Revenue | Transport fees |
| `SCHOOL_UNIFORM_REVENUE` | Revenue | Uniform sales |
| `SCHOOL_BOOK_REVENUE` | Revenue | Book/material fees |
| `SCHOOL_EXAM_REVENUE` | Revenue | Exam fees |
| `SCHOOL_ACTIVITY_REVENUE` | Revenue | Activity/lunch/boarding |
| `SCHOOL_OTHER_REVENUE` | Revenue | Miscellaneous fees |
| `SCHOOL_SCHOLARSHIP_DISCOUNT` | Contra-revenue or discount expense | Per policy config |
| `SCHOOL_ACCOUNTS_RECEIVABLE` | Asset | All student invoices |
| `SCHOOL_CASH` | Asset | Cash payments |
| `SCHOOL_BANK` | Asset | Bank/transfer payments |
| `SCHOOL_PAYROLL_EXPENSE` | Expense | Staff salaries |
| `SCHOOL_OPERATING_EXPENSE` | Expense | School operating costs |

Settings UI: `/school/settings` → Finance tab → mapping picker (reuses finance account list).

---

## Journal Entry Examples

### Tuition fee invoice issued ($400)

```
DR  Accounts Receivable (Student)     400.00
    CR  Tuition Revenue                        400.00
```

### Partial payment received ($200 cash)

```
DR  Cash                               200.00
    CR  Accounts Receivable                     200.00
```

### 25% scholarship applied on invoice

Policy A (contra-revenue):
```
DR  Scholarship Discount               100.00
    CR  Accounts Receivable                     100.00
```

Policy B (net invoice at issue):
```
Invoice issued at $300 net; revenue credited $300
```

*Default: Policy B at invoice generation; Policy A for post-issue adjustments.*

### Transport fee (separate line item)

```
DR  Accounts Receivable                80.00
    CR  Transport Revenue                       80.00
```

### School expense (supplies)

Uses existing `post_expense` with `cost_center` = school branch:

```
DR  School Operating Expense           150.00
    CR  Cash / Accounts Payable                 150.00
```

### Payroll (future / interim)

When staff payroll posts:
```
DR  Salary Expense (by cost center)
    CR  Payroll Payable
```

Interim: manual finance vouchers until `hrm` module provides payroll runs.

---

## Fee Type → GL Mapping

`SchoolFeeType` model includes `account_mapping_key`:

```python
class SchoolFeeType(TenantScopedModel):
    code = models.CharField(max_length=32)  # tuition, transport, etc.
    name = models.CharField(max_length=128)
    account_mapping_key = models.CharField(max_length=64)  # SCHOOL_TUITION_REVENUE
```

Invoice line generation copies mapping key to posting metadata.

---

## Service: `SchoolFeePostingService`

Location: `apps/school/services/fee_posting_service.py`

```python
class SchoolFeePostingService:
    @staticmethod
    def post_invoice(*, invoice: Invoice, user, tenant):
        lines = build_posting_lines_from_invoice(invoice)
        return AccountingPostingService.post_event(
            event_type=SCHOOL_FEE_INVOICED,
            source_type="school.fee_invoice",
            source_id=str(invoice.id),
            lines=lines,
            user=user,
            tenant=tenant,
        )
```

Idempotency: check `AccountingEvent` for existing `source_type` + `source_id` before posting.

---

## School Finance Dashboard (Read-Only Overlay)

`/school/finance` workspace page queries central finance APIs with school context filters:

| Widget | Source |
|---|---|
| Fees collected (month) | `school_fee_payment` events + invoice aggregates |
| Outstanding fees | Open AR on school-tagged invoices |
| Revenue by fee type | Invoice line grouping |
| Expenses | Finance expense report filtered by branch cost center |
| Payroll cost | Future hrm; interim from finance vouchers |
| Student balances | `StudentFeeAssignment` + invoice status |

**No duplicate P&L computation** — delegate to `financeApi` reports with filters.

---

## Cost Centers & Branches

- Each school branch maps to a `finance.CostCenter` (auto-provision on school profile setup)
- Student invoices tagged with `branch_id` + optional `cost_center_id`
- Multi-branch consolidation: finance reports at tenant level with branch breakdown

---

## Cutover & Migration

For schools migrating opening balances:

1. Import opening student balances via `school.fees.import` (validated preview)
2. Generate opening invoices in `draft` → `issued` with `is_opening_balance=True` flag
3. Post via `SCHOOL_FEE_INVOICED` with audit note "Opening balance import"
4. Reconcile AR control account

---

## Testing Requirements

- Invoice → journal balances (debits = credits)
- Payment reduces AR correctly
- Scholarship does not double-count revenue
- Tenant isolation on all postings
- Idempotent re-post prevention
- Branch/cost center on every entry

See `SCHOOL_TEST_MATRIX.md` → Accounting section.

---

## Related Documents

- `docs/accounting/MODULE_INTEGRATION.md`
- `docs/accounting/ACCOUNT_MAPPING.md`
- `SCHOOL_ARCHITECTURE.md`
- `SCHOOL_DATABASE_ERD.md`

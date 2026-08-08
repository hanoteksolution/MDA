# Accounting Equation

**Date:** 2026-08-07  
**Service:** `AccountingEquationService`  
**API:** `GET /api/v1/finance/equation/?as_of=YYYY-MM-DD`  
**Health check id:** `accounting_equation`

---

## Identities

Balance sheet (after incorporating period earnings):

```text
Assets = Liabilities + Equity + (Revenue − Expenses)
```

Expanded identity (always true for double-entry ledgers):

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

---

## Normal balances

| Class | Normal | Increase | Decrease |
|-------|--------|----------|----------|
| Asset | Debit | Debit | Credit |
| Expense | Debit | Debit | Credit |
| Liability | Credit | Credit | Debit |
| Equity | Credit | Credit | Debit |
| Revenue | Credit | Credit | Debit |

Centralized in `apps/finance/domain/account_behavior.py`.

---

## Tolerance

Comparisons use `Decimal` with absolute tolerance `0.01` for report float noise.

---

## Failure

Unbalanced equation → health status **unhealthy** (critical). Never auto-correct.

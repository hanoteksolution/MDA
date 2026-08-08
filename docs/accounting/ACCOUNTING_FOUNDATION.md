# Accounting Foundation — Equation & Double-Entry

**Date:** 2026-08-07  
**Status:** STEP 01–03 audit complete; foundation hardening in progress  
**Stack reality:** Django + DRF + React/Vite (not Next.js). Extend `apps/finance` only.

---

## Audit verdict (STEP 01)

The **Central Accounting Engine (STEP 35 A–P)** already implements most of the mega-prompt spine:

| Capability | Status |
|------------|--------|
| Double-entry journals (D=C) | KEEP |
| CoA five classes | EXTEND (`AccountClass` TextChoices) |
| Account mappings + events | KEEP |
| Periods, reversals, health | KEEP / EXTEND |
| POS/purchase/expense/gym/futsal posting | KEEP |
| TB / P&L / BS / cash flow | KEEP |
| Dedicated equation validator | CREATE → shipped |
| JournalValidationService | CREATE → shipped |
| Line XOR DB constraints | CREATE → shipped |
| PostingRule engine | EXTEND → runtime activated (simple events) |
| Maker-checker / draft workflow | CREATE → shipped (manual journals) |
| Cost centers | CREATE → shipped (optional line dimension) |
| Multi-currency | CREATE later |

**Do not rebuild finance.** Harden integrity, then activate PostingRules.

---

## Classification (prompt Phases 1–20)

See roadmap STEP 37 changelog. Short form:

- **KEEP:** Journal aggregate, events, mappings, reversal, reports, balance-from-ledger
- **EXTEND:** Account behavior, health (+ equation), journal validation, control-account enforcement
- **CREATE (done this slice):** `domain/account_behavior.py`, `equation_service.py`, `journal_validation_service.py`, line CheckConstraints
- **CREATE (done PostingRules):** `posting_rule_service.py` seeds + `try_build_lines` for expense/purchase/AR-AP/futsal
- **CREATE (next):** multi-currency
- **OPS:** Pilot cutover (runbook exists)

---

## Non-negotiables already enforced

1. Total Debit = Total Credit (service + structured `UNBALANCED_JOURNAL`)
2. Line debit XOR credit (service + DB `chk_fin_jl_not_both_sides`)
3. Posted ledger is source of balances (no `account.balance +=`)
4. Tenant-scoped accounts/journals
5. Periods block closed/locked posting
6. Control accounts reject **manual** posts (`JOURNAL_CONTROL_ACCOUNT`)
7. Accounting equation health check

---

## Implementation order (remaining)

```
DONE  PostingRule engine activation (simple events)
DONE  Posted journal immutability guards
DONE  GL ledger API + FE equation badge
DONE  Maker-checker (manual journal drafts)
DONE  Cost centers (optional journal dimension)
LATER Multi-currency
OPS   Pilot cutover (runbook ready)
```

Companion: [ACCOUNTING_EQUATION.md](./ACCOUNTING_EQUATION.md) · [POSTING_RULES.md](./POSTING_RULES.md) · [JOURNAL_IMMUTABILITY.md](./JOURNAL_IMMUTABILITY.md) · [MAKER_CHECKER.md](./MAKER_CHECKER.md) · [COST_CENTERS.md](./COST_CENTERS.md)

# Central Accounting Engine — Documentation Index

**Date:** 2026-08-07  
**Status:** Phases A–P complete (engine through cutover tooling).

---

## Overview

Finance is the **central accounting infrastructure** of the ERP. Cutover is per-tenant via CLI/API; nightly Celery scans alert on integrity failures.

---

## Ops

```bash
python manage.py accounting_cutover --tenant=<slug> --prepare
python manage.py accounting_cutover --tenant=<slug> --activate --date=YYYY-MM-DD
python manage.py accounting_backfill --tenant=<slug> --dry-run
python manage.py accounting_health_scan
```

Runbook: [ACCOUNTING_CUTOVER_RUNBOOK.md](./ACCOUNTING_CUTOVER_RUNBOOK.md)

---

## Documents

| Document | Purpose |
|----------|---------|
| [ACCOUNTING_FOUNDATION.md](./ACCOUNTING_FOUNDATION.md) | Equation + double-entry audit / hardening |
| [ACCOUNTING_EQUATION.md](./ACCOUNTING_EQUATION.md) | Assets = L + E validator |
| [POSTING_RULES.md](./POSTING_RULES.md) | PostingRule engine (STEP 37) |
| [JOURNAL_IMMUTABILITY.md](./JOURNAL_IMMUTABILITY.md) | Posted journals cannot mutate |
| [GENERAL_LEDGER.md](./GENERAL_LEDGER.md) | Account statement / GL drill-down |
| [MAKER_CHECKER.md](./MAKER_CHECKER.md) | Manual journal draft approval |
| [COST_CENTERS.md](./COST_CENTERS.md) | Optional journal-line cost centers |
| [ACCOUNTING_CUTOVER_RUNBOOK.md](./ACCOUNTING_CUTOVER_RUNBOOK.md) | Staging/production cutover steps |
| [ACCOUNTING_MIGRATION_PLAN.md](./ACCOUNTING_MIGRATION_PLAN.md) | Strategy + checklist |
| [CENTRAL_ACCOUNTING_ARCHITECTURE.md](./CENTRAL_ACCOUNTING_ARCHITECTURE.md) | Architecture |

---

## Phases

```
A–O  Engine → futsal → Celery alerts     ✓
P    Cutover tooling + runbook           ✓
```

CAE implementation epic is **complete** for foundation scope. Remaining work is operational (staging pilot, expand tenants).

---

*Architectural rule: No ERP module may create its own independent accounting system.*

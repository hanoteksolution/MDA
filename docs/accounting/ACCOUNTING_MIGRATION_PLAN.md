# Accounting Migration Plan

**Date:** 2026-08-07  
**Status:** Phases A–P complete — cutover tooling + runbook shipped; execute per-tenant on staging

---

## 1. Objectives

Migrate from **operational-only financial truth** to **ledger-authoritative** accounting without:

- Losing historical invoices, payments, expenses, POs
- Double-counting revenue or expenses
- Breaking existing Finance summary dashboard during transition
- Allowing shop clients to push authoritative journals

---

## 2. Current data state

| Data | Table | Has journal today? |
|------|-------|-------------------|
| Operating expenses | `sales_expenses` | Yes (on create, via `post_expense`) |
| Manual journals | `finance_journal_entries` | N/A |
| POS sales | `sales_invoices` + `sales_payments` | **No** |
| Gym memberships | invoices linked to subscriptions | **No** |
| Purchase receipts | inventory movements | **No** |
| Refunds | `sale_refunds` | **No** |
| Futsal entries | `futsal_ledger_entries` | **No** (parallel) |

---

## 3. Migration strategy — phased

### Phase A — Foundation (no business logic change)

1. Add new models: `FinancialPeriod`, `AccountMapping`, `PostingRule`, `AccountingEvent`
2. Add nullable columns to `JournalEntry` (`source_module`, `idempotency_key`, etc.)
3. Seed mappings from `EXPENSE_CATEGORY_ACCOUNT` + default codes
4. Seed open financial period for all active tenants
5. Backfill `source_module='sales'` on existing expense-sourced journals

**Rollback:** Drop new tables; new columns nullable — no data loss.

### Phase B — Engine + expense migration

1. Implement `AccountingPostingService`
2. Route `post_expense` through engine (behavior identical)
3. Add expense update/delete reversal logic
4. Deploy with feature flag `ACCOUNTING_ENGINE_ENABLED=true`

**Rollback:** Flag off → direct `post_expense` path.

### Phase C — Forward posting (POS, gym, purchases)

1. Wire POS checkout → `SALE_COMPLETED` (new sales only)
2. Wire refunds → `SALE_REFUNDED`
3. Wire gym checkout → same handler
4. Wire PO receive → `PURCHASE_RECEIVED`

**No historical backfill yet** — ledger reflects from cutover date forward.

### Phase D — Historical backfill (optional, tenant-by-tenant)

**Implemented:** `AccountingBackfillService` + `manage.py accounting_backfill`

```
# Dry-run (default)
python manage.py accounting_backfill --tenant=acme --dry-run

# Commit journals (marks notes="historical backfill")
python manage.py accounting_backfill --tenant=acme --commit --before=2026-09-01
```

API: `GET/POST /finance/backfill/` (dry-run by default on POST).

Covers missing `SALE_COMPLETED`, `EXPENSE_APPROVED`, and `PURCHASE_RECEIVED` for documents before cutover/`--before`.

Idempotency keys match forward posting so re-runs are safe.

**Risk:** COGS requires historical cost on invoice lines — may need approximation from current product cost if not stored.

### Phase E — Report cutover

1. Trial balance / P&L from selectors
2. Finance summary shows "Ledger mode" badge
3. Deprecate invoice-aggregate P&L in `AnalyticsService`

### Phase F — Futsal migration

**Implemented (Phase N):** Dual-write — `FutsalLedgerEntry` remains the operational record; `AccountingPostingService.post_futsal_ledger` posts `FUTSAL_INCOME_RECORDED` / `FUTSAL_EXPENSE_RECORDED` to the GL (accounts 4100 / 6080).

Optional later: deprecate futsal summary KPIs in favor of GL selectors; historical backfill of pre-cutover futsal rows.

---

## 4. Cutover date convention

Per tenant:

```
TenantSettings.accounting_cutover_date = 2026-09-01
```

- Before cutover: operational reports only; optional backfill journals marked `notes="historical backfill"`
- On/after cutover: forward posting is live; health dual-run compares invoices vs revenue GL from this date

Field shipped on `TenantSettings` (migration `platform.0013_accounting_cutover_date`).

---

## 5. Idempotency during backfill

Backfill idempotency keys:

```
BACKFILL:SALE_COMPLETED:sales:invoice:{invoice_id}
```

Unique constraint prevents duplicate if backfill run twice.

---

## 6. Dual-run period (recommended)

For 30 days after Phase C:

- Post journals on every sale (new path)
- Keep invoice KPIs on dashboard
- **Automated:** `finance.scan_accounting_health` Celery beat (daily) + 6h aggregate scans
- Notifies users with `finance.view` when health status is degraded/unhealthy
- Dedupe key per tenant per day (`accounting_health:{tenant_id}:{date}`)

Manual: `python manage.py accounting_health_scan`

---

## 7. Data validation queries

Pre-migration inventory:

```sql
-- Expenses without journals
SELECT e.id FROM sales_expenses e
LEFT JOIN finance_journal_entries j
  ON j.source_id = e.id AND j.source_type = 'expense' AND j.status = 'posted'
WHERE j.id IS NULL AND e.deleted_at IS NULL;

-- Tenant account completeness
SELECT tenant_id, COUNT(*) FROM finance_accounts GROUP BY tenant_id;
```

Post-migration:

```sql
-- Unbalanced journals (should be zero)
SELECT entry_id, SUM(debit), SUM(credit)
FROM finance_journal_lines
GROUP BY entry_id
HAVING SUM(debit) != SUM(credit);
```

---

## 8. Desktop / sync impact

No change to shop push format. Cloud may optionally post journals when ingesting synced invoices:

```
CloudShopSyncService.receive_push(...)
  → upsert invoice
  → if ACCOUNTING_AUTO_POST_SYNCED_SALES:
       AccountingPostingService.post(SALE_COMPLETED, idempotency_key=...)
```

Idempotency includes `device_id` + invoice `local_id`.

---

## 9. Rollback plan

| Phase | Rollback |
|-------|----------|
| A | Drop new tables/columns |
| B | Feature flag off |
| C | Feature flag `ACCOUNTING_POS_POSTING=false` |
| D | Delete backfill journals where `notes LIKE 'historical backfill%'` |
| E | Re-enable analytics P&L path |

Always backup before Phase D backfill.

---

## 10. Production checklist

See full steps in [ACCOUNTING_CUTOVER_RUNBOOK.md](./ACCOUNTING_CUTOVER_RUNBOOK.md).

- [ ] Backup database (see `docs/deployment/RESTORE_DRILL.md`)
- [ ] Run migrations on staging
- [ ] `python manage.py accounting_cutover --tenant=<pilot> --prepare`
- [ ] Optional backfill dry-run / commit
- [ ] `python manage.py accounting_cutover --tenant=<pilot> --activate --date=…`
- [ ] Monitor accounting health dashboard / notifications 7 days
- [ ] Expand to all tenants
- [ ] Update `CURRENT_SYSTEM_AUDIT.md` finance section

---

## 11. Timeline estimate

| Phase | Effort | Dependency |
|-------|--------|------------|
| A — Foundation models | 1 sprint | Architecture approval |
| B — Engine + expense | 1 sprint | A |
| C — POS/gym/purchase forward | 2 sprints | B |
| D — Historical backfill | 1 sprint (optional) | C |
| E — Report cutover | 1 sprint | C |
| F — Futsal | 0.5 sprint | B |

Total: ~6–7 sprints for full CAE excluding fixed assets, budgets, bank rec.

---

*See also: [CURRENT_FINANCE_AUDIT.md](./CURRENT_FINANCE_AUDIT.md), [ACCOUNTING_TESTING.md](./ACCOUNTING_TESTING.md)*

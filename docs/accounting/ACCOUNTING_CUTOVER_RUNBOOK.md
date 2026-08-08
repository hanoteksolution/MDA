# Accounting Cutover Runbook

**Date:** 2026-08-07  
**Audience:** Ops / platform admin  
**Depends on:** CAE Phases A–O, `docs/deployment/RESTORE_DRILL.md`

---

## 1. Goal

Make the general ledger **authoritative** for a tenant from a chosen cutover date, without double-counting or breaking POS.

---

## 2. Flags

| Flag | Scope | Default | Meaning |
|------|-------|---------|---------|
| `ACCOUNTING_ENGINE_ENABLED` | Global env | `true` | Master kill switch |
| `ACCOUNTING_STRICT_AFTER_CUTOVER` | Global env | `true` | Require journals on/after cutover |
| `TenantSettings.accounting_posting_enabled` | Per tenant | `true` | Pilot enable/disable |
| `TenantSettings.accounting_cutover_date` | Per tenant | `null` | Ledger-authoritative from this date |

---

## 3. Staging checklist (pilot tenant)

1. **Backup** — follow [RESTORE_DRILL.md](../deployment/RESTORE_DRILL.md).
2. **Migrate**
   ```bash
   docker compose exec api python manage.py migrate
   ```
3. **Prepare tenant**
   ```bash
   docker compose exec api python manage.py accounting_cutover --tenant=<slug> --prepare
   ```
   Expect `ready: True` (no critical health errors). Soft warnings (inventory variance) are OK.
4. **Optional backfill** (history before cutover)
   ```bash
   docker compose exec api python manage.py accounting_backfill --tenant=<slug> --dry-run
   docker compose exec api python manage.py accounting_backfill --tenant=<slug> --commit --before=YYYY-MM-DD
   ```
5. **Activate cutover**
   ```bash
   docker compose exec api python manage.py accounting_cutover --tenant=<slug> --activate --date=YYYY-MM-DD
   ```
6. **Smoke test** — one cash POS sale, one expense, open Finance → Health (should stay healthy/degraded without new critical errors).
7. **Confirm Celery**
   ```bash
   docker compose ps celery celery-beat
   docker compose exec api python manage.py accounting_health_scan
   ```
8. **Monitor 7 days** — Finance Health + `accounting_health` notifications.

---

## 4. Rollback (pilot)

```bash
# Stop posting journals for this tenant (POS continues operationally)
docker compose exec api python manage.py accounting_cutover --tenant=<slug> --disable-posting

# Global emergency stop
# Set ACCOUNTING_ENGINE_ENABLED=false and restart api/celery
```

Backfill journals are tagged `notes` containing `historical backfill` and can be soft-deleted if needed.

---

## 5. Expand to all tenants

1. Repeat prepare → (optional backfill) → activate per slug.
2. Or script:
   ```bash
   for slug in tenant-a tenant-b; do
     python manage.py accounting_cutover --tenant=$slug --prepare
     python manage.py accounting_cutover --tenant=$slug --activate --date=$(date -I)
   done
   ```

---

## 6. Status API / CLI

```bash
python manage.py accounting_cutover --tenant=<slug> --status
```

API: `GET /finance/cutover/` (status), `POST /finance/cutover/` with `{"action":"prepare"|"activate"|"disable_posting","date":"..."}`.

---

*See also: [ACCOUNTING_MIGRATION_PLAN.md](./ACCOUNTING_MIGRATION_PLAN.md)*

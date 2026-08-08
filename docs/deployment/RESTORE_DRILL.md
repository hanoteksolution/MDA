# Backup & Restore Drill Checklist

**Purpose:** Verify backups are restorable before you need them.  
**Frequency:** Quarterly (minimum), after major schema migrations, after VPS changes.  
**Owner:** Ops / platform admin  
**STEP:** 34 — Monitoring & Backup

---

## Pre-requisites

- [ ] Latest backup exists (`make restore-list` shows archive < 24h old on production)
- [ ] Staging environment or isolated machine available (never drill on production without a maintenance window)
- [ ] PostgreSQL client tools installed if using Postgres (`pg_restore`, `pg_dump`)
- [ ] Team notified; production write traffic stopped on drill target if using prod clone

---

## Drill steps

### 1. Create a fresh backup

```bash
make backup
```

- [ ] Command exits 0
- [ ] New `.zip` appears in `backups/` with today's timestamp
- [ ] If configured: copy appears in `GOOGLE_DRIVE_BACKUP_DIR`

### 2. Record baseline

On the **drill target** (staging):

- [ ] Note current product count or a known SKU
- [ ] Note a sample media file path under `backend/media/`
- [ ] Export `GET /api/v1/health/ready/` — expect `status: ok`

### 3. Restore backup

```bash
make restore-list
make restore --yes   # or: python infrastructure/scripts/restore.py path/to/archive.zip --yes
```

- [ ] Restore completes without error
- [ ] Database engine matches manifest (`sqlite` dev / `postgresql` prod)

### 4. Post-restore verification

```bash
docker compose exec api python manage.py migrate   # if Postgres staging
./scripts/smoke_deploy.sh http://127.0.0.1:8010
./scripts/check_health.sh http://127.0.0.1:8010
```

- [ ] Health liveness: `GET /api/v1/health/` → `ok`
- [ ] Health database: `GET /api/v1/health/database/` → `ok`
- [ ] Health cache: `GET /api/v1/health/cache/` → `ok` (requires Redis)
- [ ] Login works on restored data
- [ ] Sample product / media file from step 2 is present
- [ ] POS smoke: one test sale or `pytest -m critical` against staging API

### 5. Rollback drill target (optional)

- [ ] Restore pre-drill snapshot or rebuild staging from scratch
- [ ] Confirm staging healthy again

---

## Sign-off

| Field | Value |
|-------|--------|
| Date | |
| Environment | staging / local |
| Backup file tested | `mda_erp_backup_YYYYMMDD_HHMMSS.zip` |
| Restore duration | |
| Issues found | none / (describe) |
| Signed off by | |

---

## Failure actions

| Symptom | Action |
|---------|--------|
| `pg_dump` / backup fails | Check DB credentials, disk space, run manually with verbose |
| Restore missing media | Confirm `media/` was non-empty at backup time |
| Health cache 503 after restore | Start Redis; check `REDIS_URL` in `.env.cloud` |
| Migrations fail post-restore | Run `migrate`; if broken, restore older backup and investigate schema drift |

---

## Automation hooks

```bash
# Nightly backup (production VPS crontab)
0 2 * * * cd /home/ubuntu/projects/mda && make backup >> /var/log/mda-backup.log 2>&1

# Hourly readiness
0 * * * * /home/ubuntu/projects/mda/scripts/check_health.sh https://erp.safaritechno.com
```

See also: [GOOGLE_DRIVE_BACKUP.md](../../infrastructure/scripts/GOOGLE_DRIVE_BACKUP.md), [DEPLOYMENT.md](../architecture/DEPLOYMENT.md).

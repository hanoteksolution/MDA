# Monitoring (STEP 34)

Lightweight observability for MDA ERP deployments.

## Health endpoints

| Endpoint | Type | HTTP | Purpose |
|----------|------|------|---------|
| `GET /api/v1/health/` | Liveness | 200 | Process up |
| `GET /api/v1/health/database/` | Dependency | 200 / 503 | Postgres/SQLite ping |
| `GET /api/v1/health/cache/` | Dependency | 200 / 503 | Redis ping |
| `GET /api/v1/health/ready/` | Readiness | 200 / 503 | All dependencies |

Use **readiness** for load balancer / Docker health checks. Use **liveness** only to detect hung processes.

## Cron / uptime check

```bash
# Exit 0 when ready, 1 when degraded (for cron + alerting)
./scripts/check_health.sh http://127.0.0.1:8010
```

Example crontab (daily backup + hourly health):

```cron
0 2 * * * cd /home/ubuntu/projects/mda && make backup >> /var/log/mda-backup.log 2>&1
0 * * * * /home/ubuntu/projects/mda/scripts/check_health.sh https://erp.safaritechno.com || mail -s "MDA health fail" ops@example.com
```

## Prometheus + Grafana (optional)

```bash
docker compose \
  -f docker-compose.yml \
  -f infrastructure/monitoring/docker-compose.monitoring.yml \
  up -d
```

- Prometheus UI: http://127.0.0.1:9090
- Grafana UI: http://127.0.0.1:3000 (default admin / changeme — change immediately)

Health endpoints return JSON (not Prometheus text format). Use `check_health.sh` for alerting, or add `blackbox_exporter` later for HTTP probe metrics.

## Logging

Production (`config.settings.production`) emits **JSON logs** to stdout:

```json
{"ts":"2026-08-07T12:00:00+00:00","level":"WARNING","logger":"django.request","message":"Not Found: /api/v1/foo/"}
```

Set `LOG_LEVEL=INFO` (default) or `DEBUG` in `backend/.env.cloud`.

Docker:

```bash
docker compose logs -f api celery
```

## Backup monitoring

- Daily: `make backup` (see [RESTORE_DRILL.md](../../docs/deployment/RESTORE_DRILL.md))
- Verify latest archive exists: `make restore-list`
- Alert if backup age > 26 hours (manual or cron wrapper)

## Related

- [DEPLOYMENT.md](../../docs/architecture/DEPLOYMENT.md)
- [RESTORE_DRILL.md](../../docs/deployment/RESTORE_DRILL.md)
- [GOOGLE_DRIVE_BACKUP.md](../scripts/GOOGLE_DRIVE_BACKUP.md)

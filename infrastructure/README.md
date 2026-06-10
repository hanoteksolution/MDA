# Infrastructure

Deployment and operations configuration.

## Contents

- `docker/` — Dockerfiles and Compose stacks (dev, prod)
- `nginx/` — Reverse proxy configuration
- `scripts/` — Backup and restore (`backup.py`, `restore.py`); see [GOOGLE_DRIVE_BACKUP.md](scripts/GOOGLE_DRIVE_BACKUP.md)
- `monitoring/` — Observability setup (planned)

## Requirements (from SYSTEM_ARCHITECTURE.md)

- PostgreSQL daily backup, 30-day retention
- Redis for cache and Celery broker
- Celery workers for reports, alerts, sync, backups

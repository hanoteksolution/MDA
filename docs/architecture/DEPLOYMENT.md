# Deployment Architecture

**Status:** STEP 33 complete — Docker Compose production stack documented  
**Last updated:** 2026-08-07

---

## Overview

MDA ERP deploys as a **Docker Compose stack** on a VPS (Hostinger or similar):

| Service | Image / build | Role |
|---------|---------------|------|
| `db` | `postgres:16-alpine` | Primary database (shared schema + `tenant_id`) |
| `redis` | `redis:7-alpine` | Cache + Celery broker |
| `api` | `infrastructure/docker/Dockerfile` | Django + Gunicorn |
| `celery` | same as API | Background tasks (notifications, scans) |
| `celery-beat` | same as API | Scheduled jobs (STEP 23) |
| `web` | `infrastructure/docker/Dockerfile.web` | Nginx: React SPA + `/api/` reverse proxy |

Host-level Nginx (optional) terminates TLS and proxies to `web` on port **8010**.

---

## Compose files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full production stack (default) |
| `docker-compose.staging.yml` | Local/staging: expose DB `5432`, API `8000`, web `8010` |
| `docker-compose.vps.yml` | Hostinger: Postgres `127.0.0.1:5437`, web `8010` |
| `docker-compose.volumes.yml` | Attach legacy external volumes on existing VPS |

### Commands

```bash
# Staging (build + run)
cp backend/.env.cloud.example backend/.env.cloud   # edit secrets first
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build

# Existing VPS with legacy volumes (REQUIRED on Hostinger — keeps docker_mda_pgdata)
# Do NOT run bare `docker compose up -d` on this host; it creates empty mda_mda_pgdata.
docker compose -f docker-compose.yml -f docker-compose.vps.yml -f docker-compose.volumes.yml up -d
```

Always include `docker-compose.volumes.yml` on the production VPS so Postgres mounts **`docker_mda_pgdata`** (and media **`docker_mda_media`**), not a new empty volume.
# Production VPS
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d --build

# With existing volumes
docker compose -f docker-compose.yml -f docker-compose.vps.yml -f docker-compose.volumes.yml up -d
```

Makefile shortcuts: `make docker-build`, `make docker-up`, `make docker-smoke`.

---

## First-time bootstrap

After containers are healthy:

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py bootstrap_system
docker compose exec api python manage.py bootstrap_platform   # SaaS control plane
# Optional demo data (non-production):
# docker compose exec api python manage.py seed_data --with-admin --demo
```

Verify:

```bash
./scripts/smoke_deploy.sh http://127.0.0.1:8010
```

Smoke checks: health, mobile meta, SPA index, OpenAPI schema.

---

## Environment variables

Copy `backend/.env.cloud.example` → `backend/.env.cloud`.

| Variable | Required | Notes |
|----------|----------|-------|
| `SECRET_KEY` | Yes | Long random string |
| `ALLOWED_HOSTS` | Yes | Include `.erp.safaritechno.com` for wildcard tenants |
| `TENANT_BASE_DOMAIN` | Yes | e.g. `erp.safaritechno.com` |
| `DB_*` | Yes | `DB_HOST=db` inside Compose |
| `REDIS_URL` | Yes | `redis://redis:6379/0` inside Compose |
| `CORS_ALLOWED_ORIGINS` | Yes | HTTPS apex + dev origins |
| `SECURE_SSL_REDIRECT` | When TLS | Set `True` only when HTTPS is guaranteed end-to-end |

See also `backend/.env.example` for local development.

---

## Wildcard DNS + TLS runbook

Tenant shops resolve at `{slug}.erp.safaritechno.com`. Platform apex hosts: `erp`, `api`, `admin`, `app`, `platform`.

### 1. DNS records

| Type | Name | Value |
|------|------|-------|
| A | `erp.safaritechno.com` | VPS public IP |
| A | `*.erp.safaritechno.com` | VPS public IP |

Verify:

```bash
dig +short arabica.erp.safaritechno.com
dig +short erp.safaritechno.com
```

### 2. Docker stack

Ensure `web` listens on `127.0.0.1:8010` (default with `docker-compose.vps.yml`).

### 3. Host Nginx + TLS

Template: `infrastructure/nginx/wildcard-erp.safaritechno.com.conf`

**Option A — DNS wildcard certificate (recommended):**

```bash
sudo certbot certonly --manual --preferred-challenges dns \
  -d erp.safaritechno.com -d '*.erp.safaritechno.com'
# Add _acme-challenge TXT records when prompted, then:
sudo cp infrastructure/nginx/wildcard-erp.safaritechno.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/wildcard-erp.safaritechno.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**Option B — HTTP only (staging):** use `infrastructure/nginx/erp.safaritechno.com.conf` (single host, certbot `--nginx`).

### 4. Django production settings

When TLS is active on host nginx:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CORS_ALLOWED_ORIGINS=https://erp.safaritechno.com,https://*.erp.safaritechno.com
```

(`ALLOWED_HOSTS` with leading dot covers subdomains.)

---

## Static frontend build pipeline

The `web` image uses a **multi-stage Dockerfile**:

1. `node:20-alpine` — `npm ci && npm run build`
2. `nginx:1.27-alpine` — serves `frontend/dist`, proxies `/api/` → `api:8000`

Build args:

```bash
docker compose build web \
  --build-arg VITE_TENANT_BASE_DOMAIN=erp.safaritechno.com
```

Default API base in the SPA is `/api/v1` (same-origin via Nginx).

---

## Service topology

```
Internet
    │
    ▼
Host Nginx (:443 TLS, wildcard)
    │
    ▼
Docker web (:8010) ──► /api/* ──► api:8000 (Gunicorn)
    │                              │
    │                              ├──► db:5432 (Postgres)
    │                              └──► redis:6379
    │
    └──► /* SPA static (Vite build)

celery / celery-beat ──► redis + db
```

---

## Upgrades

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.vps.yml build
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d
docker compose exec api python manage.py migrate
./scripts/smoke_deploy.sh http://127.0.0.1:8010
```

Remote deploy scripts: `scripts/deploy_vps.py`, `scripts/deploy_vps_update.py`.

Detailed Hostinger walkthrough: [deployment/HOSTINGER_VPS.md](../deployment/HOSTINGER_VPS.md).

---

## Health checks

| Endpoint | Auth | HTTP | Purpose |
|----------|------|------|---------|
| `GET /api/v1/health/` | Public | 200 | Liveness |
| `GET /api/v1/health/database/` | Public | 200 / 503 | Database connectivity |
| `GET /api/v1/health/cache/` | Public | 200 / 503 | Redis connectivity |
| `GET /api/v1/health/celery/` | Public | 200 / 503 | Beat schedule + broker; `?require_workers=1` requires live workers |
| `GET /api/v1/health/ready/` | Public | 200 / 503 | Readiness (db + Redis) |
| `GET /api/v1/mobile/meta/` | Public | 200 | API contract smoke |

Celery foundation check:

```bash
docker compose ps celery celery-beat
docker compose exec api python manage.py celery_status --require-workers
curl -s "$BASE/api/v1/health/celery/?require_workers=1"
REQUIRE_CELERY_WORKERS=1 ./scripts/smoke_deploy.sh "$BASE"
```

Scheduled jobs: `notifications.run_all_scheduled_scans` (6h), `finance.scan_accounting_health` (daily).

Cron / uptime: `./scripts/check_health.sh https://erp.safaritechno.com`

Monitoring overlay: `infrastructure/monitoring/` (Prometheus + Grafana optional).

Backup drill: [deployment/RESTORE_DRILL.md](../deployment/RESTORE_DRILL.md).

---

## Related docs

- [DOMAIN_MANAGEMENT.md](../DOMAIN_MANAGEMENT.md) — tenant host resolution
- [HOSTINGER_VPS.md](../deployment/HOSTINGER_VPS.md) — step-by-step VPS guide
- [TESTING.md](../TESTING.md) — pytest + smoke before release

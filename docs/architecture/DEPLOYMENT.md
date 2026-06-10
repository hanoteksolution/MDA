# Deployment Architecture

> **Status:** Planned — placeholder created during structure phase.  
> See [MISSING_REQUIREMENTS.md](./MISSING_REQUIREMENTS.md) for gaps to resolve before implementation.

## Target Environments

| Environment | Purpose |
|-------------|---------|
| Development | Local Docker Compose |
| Staging | Pre-production validation |
| Production | On-prem or cloud deployment |

## Services

| Service | Technology |
|---------|------------|
| API | Django + Gunicorn/Uvicorn |
| Database | PostgreSQL 16+ |
| Cache / Broker | Redis 7+ |
| Workers | Celery |
| Reverse Proxy | Nginx |
| Desktop Client | Tauri (Windows primary) |

## To Be Defined

- [ ] Environment variable catalog
- [ ] Docker Compose service definitions
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] SSL/TLS configuration
- [ ] Backup and restore procedures
- [ ] Log aggregation
- [ ] Health check endpoints
- [ ] Desktop auto-update strategy

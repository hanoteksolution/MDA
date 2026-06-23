# Retail ERP & POS Desktop Application

Enterprise-grade retail management system: ERP + POS, offline-first, built with Django, React, and Tauri.

## Status

**Planning phase complete.** Project structure scaffolded. Implementation follows `docs/product/FEATURE_ROADMAP.md`.

## Documentation

| Document | Purpose |
|----------|---------|
| [agent.md](agent.md) | AI agent and development rules |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Complete repository layout |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) | System design |
| [docs/architecture/MISSING_REQUIREMENTS.md](docs/architecture/MISSING_REQUIREMENTS.md) | Gap analysis |
| [docs/product/FEATURE_ROADMAP.md](docs/product/FEATURE_ROADMAP.md) | Implementation phases |

## Stack

- **Backend:** Django, DRF, PostgreSQL, Redis, Celery
- **Frontend:** React 19, TypeScript, Shadcn UI, Tailwind, Zustand
- **Desktop:** Tauri
- **Offline:** SQLite + sync engine

## Repository Layout

```
backend/          Django REST API
frontend/         React UI
desktop/          Tauri shell + offline sync
infrastructure/   Docker, deployment, scripts
shared/           Cross-cutting constants and schemas
docs/             Source-of-truth documentation
```

## Next Steps

1. Resolve remaining gaps in [MISSING_REQUIREMENTS.md](docs/architecture/MISSING_REQUIREMENTS.md) (TAX_AND_PRICING, OFFLINE_SYNC, DEPLOYMENT)
2. Phase 2: Categories, brands, products, warehouses, inventory tracking

## Quick Start

Requires [GNU Make](https://www.gnu.org/software/make/) (included with Git for Windows), Python 3.11+, and Node 18+.

```bash
make setup    # install deps, create .env, migrate, bootstrap
make dev        # API :8000 + UI :5173 (parallel)
```

On first launch, complete the **setup wizard** to create your company and administrator account.

For dev demo data: `make seed-demo` (admin / admin12345 + sample catalog).

### Makefile commands

| Command | Description |
|---------|-------------|
| `make help` | List all commands |
| `make setup` | First-time install + migrate + bootstrap |
| `make install` | Install backend and frontend dependencies |
| `make migrate` | Run Django migrations |
| `make bootstrap` | Bootstrap roles and permissions only |
| `make seed-demo` | Dev demo data + admin user |
| `make run-backend` | Start Django API |
| `make run-frontend` | Start Vite dev server |
| `make dev` | Start both servers |
| `make build` | Build frontend for production |
| `make build-desktop` | Build Windows desktop installer (Tauri) |
| `make dev-desktop` | Run Tauri desktop app in dev mode |
| `make install-desktop` | Install Tauri CLI dependencies |
| `make test` | Run backend pytest |

### Manual setup (without Make)

#### Backend

```bash
cd backend
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py bootstrap_system
python manage.py runserver
```

Open the app and complete the setup wizard, or run `python manage.py seed_data --with-admin --demo` for dev demo data.

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Desktop app (Tauri) — fully portable offline

**Target PCs do not need Python.** Build the installer on a dev machine:

```bash
pip install -r backend/requirements/bundle.txt
make install-desktop
make build-desktop    # bundles mda-api.exe + Windows installer
```

For development (uses local Python): `make dev-desktop`

Installers: `desktop/src-tauri/target/release/bundle/`

Data is stored locally in SQLite at `%APPDATA%\com.mda.erp\`. The API starts automatically — no `make run-backend`.

See [desktop/README.md](desktop/README.md).

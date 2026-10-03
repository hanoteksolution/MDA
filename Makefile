# MDA ERP — production operations (top) and local development commands (bottom).
# Production targets drive the EXISTING Docker Compose project "mda" through systemd units and
# scripts/ops/mda-ops.sh. See docs/deployment/SYSTEMD_OPERATIONS.md.
#
#   RESTART = existing deployed image, no build      (make restart-frontend)
#   BUILD   = image creation only, nothing restarted (make build-frontend)
#   REBUILD = build + recreate, no migrations        (make rebuild-frontend)
#   DEPLOY  = controlled production release          (make deploy-frontend)

BACKEND_DIR  := backend
FRONTEND_DIR := frontend
DESKTOP_DIR  := desktop
PYTHON       ?= python
PIP          ?= pip
NPM          ?= npm
MANAGE       = cd $(BACKEND_DIR) && $(PYTHON) manage.py
OPS          := ./scripts/ops/mda-ops.sh
SYSTEMD_SRC  := deploy/systemd
SYSTEMD_DST  := /etc/systemd/system
MDA_UNITS    := mda-backend.service mda-frontend.service mda-celery.service mda-celery-beat.service mda-workers.target
TAIL         ?= 200
FOLLOW       ?= 1
export TAIL FOLLOW

# Ensure Rust/Cargo is on PATH (common Windows issue: CMD opened before rustup install)
ifeq ($(OS),Windows_NT)
  NULL      := nul
  CARGO_BIN := $(USERPROFILE)/.cargo/bin
  export PATH := $(CARGO_BIN);$(PATH)
else
  NULL      := /dev/null
  CARGO_BIN := $(HOME)/.cargo/bin
  export PATH := $(CARGO_BIN):$(PATH)
endif

.DEFAULT_GOAL := help

.PHONY: help status health logs logs-frontend logs-backend logs-celery logs-beat \
        restart restart-frontend restart-backend restart-celery restart-beat restart-workers \
        build build-frontend build-backend rebuild rebuild-frontend rebuild-backend \
        deploy deploy-frontend deploy-backend rollback rollback-frontend rollback-backend \
        migrate bootstrap preflight install-systemd verify-systemd \
        install install-backend install-frontend install-desktop setup env local-migrate local-bootstrap seed-demo reset-data \
        run-backend run-frontend dev dev-desktop local-build build-desktop bundle-desktop-api check-rust \
        test test-unit test-integration test-critical test-isolation \
        docker-smoke check-health clean shell createsuperuser backup restore restore-list

## help — Show available commands
help:
	@echo "MDA ERP — production operations (Compose project 'mda', via systemd)"
	@echo ""
	@echo "  RESTART = existing deployed image, no build   BUILD = image only, nothing restarted"
	@echo "  REBUILD = build + recreate (no migrations)      DEPLOY = preflight, rollback tag, build, migrate, health"
	@echo ""
	@echo "  make status | health | logs              Overview, health checks, all app logs (FOLLOW=0 TAIL=200)"
	@echo "  make restart-frontend | restart-backend  Restart ONE service on its current image"
	@echo "  make restart-celery | restart-beat | restart-workers"
	@echo "  make restart                             Restart API, workers and frontend (no build)"
	@echo "  make build-frontend | build-backend | build        Build image(s) only"
	@echo "  make rebuild-frontend | rebuild-backend | rebuild  Build + recreate (refuses pending migrations)"
	@echo "  make deploy-frontend | deploy-backend | deploy     Controlled release (backend first)"
	@echo "  make rollback-frontend | rollback-backend | rollback  Return to the recorded previous image"
	@echo "  make migrate [CONFIRM=yes]   Show plan / apply migrations with the deployed API image"
	@echo "  make bootstrap CONFIRM=yes   Additive roles/permissions bootstrap"
	@echo "  make logs-frontend | logs-backend | logs-celery | logs-beat"
	@echo "  make install-systemd | verify-systemd   Install / check the systemd units"
	@echo ""
	@echo "Local development"
	@echo "  make setup | install | env | local-migrate | local-bootstrap | seed-demo | reset-data"
	@echo "  make run-backend | run-frontend | dev | local-build | test | test-unit | test-integration"
	@echo "  make dev-desktop | build-desktop | bundle-desktop-api | install-desktop"
	@echo "  make shell | createsuperuser | clean | backup | restore-list | restore | docker-smoke | check-health"

# ---------------------------------------------------------------- production: observe
status:
	@$(OPS) status

health:
	@$(OPS) health

preflight:
	@$(OPS) preflight backend && $(OPS) preflight frontend

logs:
	@$(OPS) logs api web celery celery-beat

logs-frontend:
	@$(OPS) logs web

logs-backend:
	@$(OPS) logs api

logs-celery:
	@$(OPS) logs celery

logs-beat:
	@$(OPS) logs celery-beat

# ---------------------------------------------------------------- production: restart (no build)
restart-frontend:
	@$(OPS) restart frontend

restart-backend:
	@$(OPS) restart backend

restart-celery:
	@$(OPS) restart celery

restart-beat:
	@$(OPS) restart beat

restart-workers:
	@$(OPS) restart workers

restart:
	@$(OPS) restart all

# ---------------------------------------------------------------- production: build / rebuild / deploy
build-frontend:
	@$(OPS) build frontend

build-backend:
	@$(OPS) build backend

build:
	@$(OPS) build all

rebuild-frontend:
	@$(OPS) rebuild frontend

rebuild-backend:
	@$(OPS) rebuild backend

rebuild:
	@$(OPS) rebuild backend && $(OPS) rebuild frontend

deploy-frontend:
	@$(OPS) deploy frontend

deploy-backend:
	@$(OPS) deploy backend

deploy:
	@$(OPS) deploy all

rollback-frontend:
	@$(OPS) rollback frontend

rollback-backend:
	@$(OPS) rollback backend

rollback:
	@$(OPS) rollback all

migrate:
	@$(OPS) migrate

bootstrap:
	@$(OPS) bootstrap

# ---------------------------------------------------------------- production: systemd units
install-systemd:
	@for u in $(MDA_UNITS); do systemd-analyze verify $(SYSTEMD_SRC)/$$u || exit 1; done
	install -m 0644 $(addprefix $(SYSTEMD_SRC)/,$(MDA_UNITS)) $(SYSTEMD_DST)/
	systemctl daemon-reload
	@echo "Installed. Enable with: systemctl enable $(MDA_UNITS)"

verify-systemd:
	@for u in $(MDA_UNITS); do cmp -s $(SYSTEMD_SRC)/$$u $(SYSTEMD_DST)/$$u && echo "in sync  $$u" || echo "DIFFERS  $$u"; done
	@systemctl is-enabled $(MDA_UNITS) || true

# ================================================================ local development
## install — Install all dependencies
install: install-backend install-frontend

## install-all — Install backend, frontend, and desktop dependencies
install-all: install-backend install-frontend install-desktop

## install-desktop — npm install Tauri CLI
install-desktop:
	cd $(DESKTOP_DIR) && $(NPM) install

## install-backend — pip install backend requirements
install-backend:
	$(PIP) install -r $(BACKEND_DIR)/requirements/dev.txt

## install-frontend — npm install frontend packages
install-frontend:
	cd $(FRONTEND_DIR) && $(NPM) install

## setup — Full first-time project setup
setup: install env local-migrate local-bootstrap
	@echo Setup complete. Run: make dev — then complete the setup wizard in the browser.

## env — Create backend/.env from .env.example if missing
env:
	@$(PYTHON) -c "import shutil, pathlib; d=pathlib.Path('$(BACKEND_DIR)'); env=d/'.env'; ex=d/'.env.example'; \
		(shutil.copy2(ex, env), print(f'Created {env}')) if not env.exists() else print(f'{env} already exists')"

## local-migrate — Apply migrations to the LOCAL dev database
local-migrate:
	$(MANAGE) migrate

## local-bootstrap — Roles and permissions only, LOCAL dev database
local-bootstrap:
	$(MANAGE) bootstrap_system

## seed-demo — Dev admin user + sample catalog/sales data
seed-demo:
	$(MANAGE) seed_data --with-admin --demo

## reset-data — Remove dev + desktop SQLite (shows setup wizard again)
reset-data:
	$(PYTHON) $(BACKEND_DIR)/scripts/reset_local_data.py

## run-backend — Django development server
run-backend:
	$(MANAGE) runserver

## run-frontend — Vite development server
run-frontend:
	cd $(FRONTEND_DIR) && $(NPM) run dev

## dev — Run API and UI together (requires GNU make -j)
dev:
	$(MAKE) -j2 run-backend run-frontend

## check-rust — Verify Rust/Cargo is available (required for Tauri)
ifeq ($(OS),Windows_NT)
check-rust:
	@cargo --version >nul 2>&1 || ( \
		echo. & \
		echo ERROR: Rust/Cargo not found. Tauri desktop builds require Rust. & \
		echo. & \
		echo   Install:  winget install Rustlang.Rustup & \
		echo   Then run: rustup default stable & \
		echo   Reopen your terminal and run: make build-desktop & \
		echo. & \
		exit /b 1 \
	)
else
check-rust:
	@cargo --version >/dev/null 2>&1 || ( \
		echo ""; \
		echo "ERROR: Rust/Cargo not found. Tauri desktop builds require Rust."; \
		echo ""; \
		echo "  Install: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"; \
		echo "  Then run: rustup default stable"; \
		echo ""; \
		exit 1 \
	)
endif

## dev-desktop — Tauri desktop development (uses system Python for API)
dev-desktop: check-rust
	cd $(DESKTOP_DIR) && $(NPM) run dev

## local-build — Local frontend build into frontend/dist (not a production deploy)
local-build:
	cd $(FRONTEND_DIR) && $(NPM) run build

## bundle-desktop-api — PyInstaller standalone API (bundled into installer)
bundle-desktop-api:
	$(PIP) install -r $(BACKEND_DIR)/requirements/bundle.txt
	$(PYTHON) $(BACKEND_DIR)/scripts/build_desktop_api.py

## build-desktop — Portable Windows installer (no Python required on target PCs)
build-desktop: check-rust bundle-desktop-api
	cd $(DESKTOP_DIR) && $(NPM) run build

## test — Backend test suite
test:
	cd $(BACKEND_DIR) && pytest

## test-unit — Unit tests only
test-unit:
	cd $(BACKEND_DIR) && pytest tests/unit/

## test-integration — Integration tests only
test-integration:
	cd $(BACKEND_DIR) && pytest tests/integration/ -m integration

## test-critical — Critical business-path tests
test-critical:
	cd $(BACKEND_DIR) && pytest -m critical

## test-isolation — Tenant isolation tests
test-isolation:
	cd $(BACKEND_DIR) && pytest -m isolation

# docker-build / docker-up / docker-down were removed: without -p they targeted Compose project
# "mda" (production) and fixed container names, so docker-down would stop production.

## docker-smoke — HTTP smoke checks against running stack
docker-smoke:
	./scripts/smoke_deploy.sh http://127.0.0.1:8010

## check-health — Readiness probe for cron / monitoring
check-health:
	./scripts/check_health.sh http://127.0.0.1:8010

## shell — Django interactive shell
shell:
	$(MANAGE) shell

## createsuperuser — Django admin user wizard
createsuperuser:
	$(MANAGE) createsuperuser

## backup — Export DB + media; copy to GOOGLE_DRIVE_BACKUP_DIR
backup:
	$(PYTHON) infrastructure/scripts/backup.py

## restore-list — Show local and Google Drive backups
restore-list:
	$(PYTHON) infrastructure/scripts/restore.py --list

## restore — Restore latest backup (interactive confirm)
restore:
	$(PYTHON) infrastructure/scripts/restore.py

## clean — Remove caches and frontend dist
clean:
	-$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('$(BACKEND_DIR)').rglob('__pycache__')]"
	-$(PYTHON) -c "import shutil; shutil.rmtree('$(FRONTEND_DIR)/dist', ignore_errors=True)"
	-$(PYTHON) -c "import shutil; shutil.rmtree('$(DESKTOP_DIR)/src-tauri/target', ignore_errors=True)"
	@echo Cleaned Python caches, frontend dist, and desktop target

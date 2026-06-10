# MDA Retail ERP & POS — development commands
# Requires: GNU Make, Python 3.11+, Node 18+ (Windows / macOS / Linux)

BACKEND_DIR  := backend
FRONTEND_DIR := frontend
DESKTOP_DIR  := desktop
PYTHON       ?= python
PIP          ?= pip
NPM          ?= npm
MANAGE       = cd $(BACKEND_DIR) && $(PYTHON) manage.py

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

.PHONY: help install install-backend install-frontend install-desktop setup env migrate seed \
        run-backend run-frontend dev dev-desktop build build-desktop check-rust test clean shell \
        createsuperuser backup restore restore-list

## help — Show available commands
help:
	@echo MDA Retail ERP — Makefile commands
	@echo.
	@echo   make setup            First-time setup (install, env, migrate, seed)
	@echo   make install          Install backend + frontend dependencies
	@echo   make env              Copy backend/.env.example to backend/.env
	@echo   make migrate          Run Django migrations
	@echo   make seed             Load default roles, admin user, sample data
	@echo   make run-backend      Start Django API on http://127.0.0.1:8000
	@echo   make run-frontend     Start Vite dev server on http://localhost:5173
	@echo   make dev              Start backend and frontend (parallel)
	@echo   make dev-desktop      Start Tauri desktop app (dev)
	@echo   make build            Build frontend for production
	@echo   make build-desktop    Build Windows desktop installer
	@echo   make install-desktop  Install Tauri CLI dependencies
	@echo   make test             Run backend tests (pytest)
	@echo   make shell            Django shell
	@echo   make createsuperuser  Create Django superuser
	@echo   make clean            Remove build artifacts and caches
	@echo   make backup           Backup database + media to Google Drive folder
	@echo   make restore-list     List available backups
	@echo   make restore          Restore latest backup
	@echo.
	@echo   Default login after seed: admin / admin12345

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
setup: install env migrate seed
	@echo Setup complete. Run: make dev

## env — Create backend/.env from .env.example if missing
env:
	@$(PYTHON) -c "import shutil, pathlib; d=pathlib.Path('$(BACKEND_DIR)'); env=d/'.env'; ex=d/'.env.example'; \
		(shutil.copy2(ex, env), print(f'Created {env}')) if not env.exists() else print(f'{env} already exists')"

## migrate — Apply database migrations
migrate:
	$(MANAGE) migrate

## seed — Seed roles, permissions, company, admin, sample data
seed:
	$(MANAGE) seed_data

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

## dev-desktop — Tauri desktop development mode
dev-desktop: check-rust
	cd $(DESKTOP_DIR) && $(NPM) run dev

## build — Production frontend build
build:
	cd $(FRONTEND_DIR) && $(NPM) run build

## build-desktop — Build Tauri Windows installer (requires Rust)
build-desktop: check-rust
	cd $(DESKTOP_DIR) && $(NPM) run build

## test — Backend test suite
test:
	cd $(BACKEND_DIR) && pytest

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

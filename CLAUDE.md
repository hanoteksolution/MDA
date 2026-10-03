# Project Instructions

Session handoff state lives in `.claude/progress.md`; context workflow in `.claude/context-guide.md`.

## Session Resume Protocol (read before acting on any prompt)

Sessions expire mid-task. `.claude/progress.md` opens with an **ACTIVE TASK** block — read it before doing anything else, then inspect the working tree only where the task requires.

- If `Status: IN_PROGRESS`, continue from `Exact next step`. Do not restart the task, redo completed tests or analysis, undo existing changes, or start a later phase on your own.
- Update the ACTIVE TASK block after every meaningful step. Keep it short; it is read by every new session.
- **If a command or session was interrupted, verify whether it actually completed before rerunning it.** Never blindly rerun migrations, deployments, payments, service restarts, or production data operations.
- **This VPS is live production: never assume an interrupted operation failed.** Check real DB / container / service / migration state first, then decide.

## Project Overview

MDA / "Safari ERP": a multi-tenant, modular ERP + POS. Backend is a Django modular monolith with per-industry apps (retail/inventory/sales/purchases/finance core, plus pharmacy, restaurant/cafeteria, gym, hotel, school, futsal, property/housing/office rental, project management, travel agency). A React web UI and a Tauri desktop shell consume the API; `mobile/` currently holds only a README (mobile API endpoints exist in the backend).

`README.md` and `PROJECT_STRUCTURE.md` are partly stale (README still says "planning phase"). The code is authoritative.

## Technology Stack (confirmed in repo)

- Backend: Django 5.2, DRF, SimpleJWT, Celery (+ beat), Redis, PostgreSQL (SQLite for dev/desktop and in-memory for tests). Python 3.10 in this environment.
- Frontend: React 19, TypeScript, Vite 6, React Router 7, Zustand, Tailwind 3, Radix UI, Recharts, Vitest.
- Desktop: Tauri 2 shell bundling a local Django API (`desktop/`).
- Deploy: `docker-compose*.yml` (services: db, redis, api, celery, celery-beat, web), nginx/monitoring under `infrastructure/`, VPS scripts under `scripts/`.

## Repository Structure

- `backend/apps/<module>/` — one Django app per domain (`models/`, `services/`, `serializers/`, `migrations/`). Business logic lives in `services/`.
- `backend/api/v1/<module>/` — DRF views and URLs, mounted from `backend/api/v1/urls.py`.
- `backend/core/` — tenancy (`core/tenancy.py`, `core/models/tenant.py`), auth, responses, exceptions, pagination, security.
- `backend/config/settings/` — `base`, `development`, `production`, `test`, `desktop`, `school_verification`; `config/celery.py`.
- `backend/tests/{unit,integration,verification}/` — pytest suites.
- `frontend/src/` — `modules/<module>/` (screens), `services/api/` (API clients), `app/` (routes), `navigation/`, `store/`, `components/`.
- `docs/` — extensive design docs (see below). `docs/school/` and `docs/branches/` hold the current work streams.

Key conventions: tenant-owned models use `TenantScopedModel`; query scoping goes through `apply_tenant_scope` / `resolve_acting_tenant` (`core/tenancy.py`); permissions are codenames checked with `user.has_permission()` / `HasPermission` (`backend/permissions/base.py`); mutations write audit rows via `apps/audit/services/audit_write.py`.

## Development Workflow

Commands come from the `Makefile` (run `make help`):

- Local dev: `make local-migrate`, `make local-bootstrap`, `make seed-demo`, `make run-backend` (:8000), `make run-frontend` (:5173), `make dev`, `make local-build`
- Production ops (`make status|health|restart-*|build-*|rebuild-*|deploy-*|rollback-*|migrate|bootstrap`) act on the LIVE Compose project via systemd units — see `docs/deployment/SYSTEMD_OPERATIONS.md`. Never run build/rebuild/deploy/migrate without explicit authorization.
- Frontend: `cd frontend && npm run dev | build | test` (`build` = `tsc -b && vite build`, `test` = `vitest run`)
- Backend env template: `backend/.env.example`. Environment has no `python` alias; use `python3`.

## Testing

- Backend: `cd backend && python3 -m pytest <path>::<test>` (settings `config.settings.test`, in-memory SQLite, Celery eager). Markers: `unit`, `integration`, `isolation`, `critical`. `make test-unit | test-integration | test-critical | test-isolation`.
- SQLite ignores `select_for_update`; concurrency/locking claims need PostgreSQL (see `tests/unit/test_school_postgresql.py`).
- Run targeted tests first. A full `pytest tests` takes >10 minutes.
- Baseline on 2026-09-19 (dirty tree): the full suite already had ~12 failed / 9 errors (school_sis, pharmacy_rx_fefo, performance_step31, tenant_isolation_api, and a few others). Compare against this, and re-measure rather than trust it.
- Frontend: `vitest` (a few `src/**/*.test.ts` files plus `frontend/tests/school`). No browser-test runner is configured in `package.json`.

## Context Efficiency

- Search narrowly before reading large files; read only the relevant range.
- Do not re-inspect unchanged files or repeat repo-wide searches without reason.
- Do not load generated, data, or binary files, and do not dump large logs — redirect long output to a file and read the tail/grep.
- Reuse existing docs (below) instead of restating them. The repository state is the source of truth.
- Avoid: `node_modules/`, `frontend/dist/`, `frontend/tsconfig.tsbuildinfo`, `backend/db.sqlite3` / `mda_erp.sqlite3` / `media/`, `**/__pycache__/`, `desktop/src-tauri/target/`, `backups/`, `*.dump`, `*.log`, `package-lock.json`. Existing `migrations/` are large; read only the one you need.

## Investigation Rules

For bugs: gather evidence → reproduce when safe → trace the real execution path → read the relevant code → state the evidence-supported root cause → propose the smallest safe fix → implement only when asked → run targeted tests → confirm unrelated behavior is unchanged. Never claim a root cause from speculation.

## Scope Control

Do not refactor unrelated code, touch unrelated files, add unrequested features or abstractions, create needless temp files, or rewrite working architecture without evidence. Put scratch files in the session scratchpad, not the repo.

## Production Safety

Production may be live (VPS deploy scripts exist). Without explicit authorization do NOT delete production data, run destructive migrations, reset databases (`make reset-data` wipes the local DB), force push, kill or restart production services, change production config, or run the `scripts/*vps*` scripts. Prefer read-only diagnostics.

## Git Safety

- The working tree is routinely dirty with unrelated in-progress work (School, cafeteria, branch work). Run `git status` before broad edits.
- Never discard, revert, stash, or stage changes you did not make. Stage by explicit path.
- Do not assume uncommitted changes belong to the current task.
- Do not commit or push unless asked. Commit messages/PRs: follow the attribution the harness specifies.

## Existing Documentation (reference, don't duplicate)

- `agent.md` — original agent/architecture rules (Clean Architecture layers; partly aspirational — verify against code).
- `docs/CURRENT_SYSTEM_AUDIT.md` (dated 2026-08-07, partly outdated), `docs/architecture/`, `docs/api/API_SPECIFICATION.md`, `docs/erp-transformation/`, `docs/modular-erp/`, `docs/workspace-architecture/`, `docs/deployment/`, `docs/accounting/`.
- School: `docs/school/README.md`. Multi-branch: `docs/branches/MULTI_BRANCH_ARCHITECTURE.md`.

## Long-Running Session Management

When context grows large, keep only: current objective, completed work, files changed, important decisions, tests/results, unresolved issues, next action. Drop repeated tool output, big logs, re-read file contents, and obsolete investigation. Checkpoint into `.claude/progress.md` (see `.claude/context-guide.md`), then `/compact` or start fresh.


## Token / Context Efficiency

- Existing docs are the source of truth; never restate them unless necessary.
- Read only files directly relevant to the current task.
- Never recursively inspect the whole repository unless explicitly requested.
- Do not repeatedly reread unchanged files.
- Prefer targeted search over opening large files.
- Keep tool output and explanations minimal.
- Do not paste large diffs/files into chat.
- Run targeted tests during development.
- Run the full regression suite only at the final phase gate.
- Do not rewrite documentation already containing the required information.
- Reuse existing models/services/tests before creating new abstractions.
- After completing a phase, return only: PASS/FAIL, tests, blockers, important files changed, and readiness for next phase.
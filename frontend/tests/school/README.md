# School Phase 2 browser verification

These scripts create synthetic records in the isolated `school_verify` database. Never point them at production. They use real JWT login, real API requests, the production build, Chromium and axe. Deliberate error injection is limited to the UX retry check.

1. Initialize a temporary PostgreSQL cluster with UTF8; use localhost port 55439, role postgres and database school_verify. Configure another isolated port/user with SCHOOL_VERIFY_PG_PORT / SCHOOL_VERIFY_PG_USER if needed.
2. From backend run `DEBUG=False python3 manage.py migrate --settings=config.settings.school_verification` and `DEBUG=False python3 manage.py shell --settings=config.settings.school_verification < tests/verification/seed_school_browser.py`.
3. Start Django on localhost:8000 using those settings. From frontend build with `npm run build`, then `npm run preview -- --host 127.0.0.1 --port 5174` (the existing proxy forwards /api and /media).
4. Install external test tooling in `/tmp/school25-tooling`: `npm install --prefix /tmp/school25-tooling @playwright/test @axe-core/playwright`; install Chromium and its system dependencies with Playwright. Set SCHOOL_PLAYWRIGHT if using another module path.
5. From repository root run `node frontend/tests/school/verify.mjs`, then `node frontend/tests/school/ux.mjs`. Do not run them simultaneously against the same actor/rate-limit bucket. The scripts pace page transitions to respect normal API throttles.

Reports/screenshots are written under `/tmp/school25-browser` and `/tmp/school25-ux`. Fixture JWTs stay in `/tmp`; the scripts obtain fresh login sessions. Verification credentials are intentionally disposable and must not be reused elsewhere. The seed asserts the disposable database name.

Backend gates: from backend run `DEBUG=False python3 -m pytest --ds=config.settings.school_verification --reuse-db tests/unit/test_school_foundation.py tests/unit/test_school_postgresql.py tests/unit/test_school_migrations.py tests/unit/test_rbac_bootstrap.py`.

Query probe: `DEBUG=False python3 manage.py shell --settings=config.settings.school_verification < tests/verification/school_query_probe.py`. This seeds separate synthetic tenants and emits PostgreSQL EXPLAIN ANALYZE/buffer evidence.

Verification versions used: PostgreSQL 14.24, Playwright 1.63.0 / Chromium 153.0.8010.12. See docs/school/SCHOOL_PHASE_2_VERIFICATION.md for scope, measured results and rollback limitations.

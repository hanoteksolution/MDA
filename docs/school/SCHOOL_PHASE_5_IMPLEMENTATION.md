# School Phase 5 — assignments, results and promotion

Date: 2026-09-21. Scope: Phase 1 audit §N row 5 and exams/results gates in §P. Phase 4 is signed off by the user; previous phases, Branch and Integrations remain outside this change. Stop at Phase 5.

## Implementation

- Assignment draft/publish/close, teacher-recorded submissions and bounded scores/feedback. Existing teacher assignments and tenant/campus permissions govern access. Student/guardian self-service and submission attachments remain deferred to their approved phases.
- Grade schemes and continuous, non-overlapping pass/fail bands; configurable disabled/competition/dense ranking. Assessment weights live directly on each assessment, total 100 per subject offering, and use Decimal arithmetic with half-up rounding. Missing marks block submission; absent is zero; exempt is excluded with remaining weights normalized. All-exempt results cannot promote. Overall results use existing subject-offering weights; every assessed subject must pass.
- Exams and dated assessments with invigilator/room schedules and overlapping class, teacher and room checks. Class/year/term/section and enrollment relationships are revalidated server-side.
- Bulk draft mark entry with expected revision, assigned-teacher restrictions, atomic validation and 0..maximum score bounds. Draft → submitted → moderated → published; reason-required reopening produces a new immutable publication/report-card version. Existing versions retain marks, grading policy, attendance totals and student identity snapshots.
- Printable report cards use authenticated, escaped HTML; browser printing supports Save as PDF. No new document generation service or public report URLs.
- Persisted promotion preview checks published passing results, active historical enrollment, destination calendar/class/section and capacity. A fingerprint rejects stale previews. Atomic, idempotent commit preserves the old enrollment, creates linked promotion/repetition placements or graduation history, and audits both actors and changes. Future-dated execution, cross-campus movement and capacity overrides use no new workflow here; existing transfers remain separate.
- Reused SIS schema/list/detail/form/API/permission/audit foundations. Added marks entry and promotion preview screens, publication commands and a readable report-card panel. Browser exits and in-app navigation protect unsaved marks/previews.
- Additive migrations `0007_phase5` and `0008_phase5_ranking`. No backfill and no change to earlier School data. Empty reverse migration is tested; reversing with academic data would delete Phase 5 tables and is not an operational rollback strategy.

## Verification

Gate: **PASS**. **0 new regressions**. Ready for Phase 6 review; Phase 6 has not been started.

Targeted SQLite backend: **22 passed** ([evidence](verification/phase5-targeted.txt)): grading bounds, missing/absent/exempt, Decimal weighting, rank ties, attendance totals, stale drafts, moderation/publication/revision, assignment grading, teacher/tenant/campus scope, schedule conflicts, rollback, promotion/repetition/graduation, capacity and history.
PostgreSQL: **24 passed, 0 skipped** ([evidence](verification/phase5-postgresql.txt)), including those 22 tests, threaded HTTP mark/publish/promotion races, and migration preservation/empty reverse/re-upgrade. Database: disposable `test_school_phase5_verify`.
Frontend: **128 passed** ([evidence](verification/phase5-frontend.txt)). Production build: **PASS**, with the existing bundle-size warning. School migration drift check: no changes.

Chromium against production frontend and live PostgreSQL: **PASS** ([evidence](verification/phase5-chromium.json)). UI created/published an assignment, teacher recorded/graded a submission and saved marks, owner submitted/moderated/published results, opened and printed the report to PDF, and previewed/committed promotion. Both old and new enrollment rows were verified. Published marks were locked; an unassigned teacher received a visible denial with no mark inputs. Marks and promotion pages fit 1366/768/390 px without page overflow. Zero page errors. Browser harness corrections addressed a stale fixture calendar and waiting for the publication response; no application fixes were needed.
Full backend regression: **889 passed, 43 skipped, 7 failed, 9 errors** in 48m43s, run **once** after backend completion. All seven failed and nine error node names exactly match the signed-off Phase 4 final regression; no names added or resolved. **0 new regressions**. [Full output](verification/phase5-full-regression.txt), [exact comparison](verification/phase5-regression-comparison.json). PostgreSQL-only cases skipped by SQLite were covered by the separate required PostgreSQL gate.

Security/isolation: **PASS** — server-side permissions, tenant/campus and teacher assignment scope, immutable publication APIs, relationship validation, revision checks, tenant-row transaction locks, rollback and commit replay checks passed. Earlier School phases passed in the final regression. No Branch/Integrations application changes were made for Phase 5.

Known limits: teacher/administrator-recorded text submissions; printed HTML/PDF via browser; explicit destination selection rather than inferred class ordering; current-date-or-earlier promotion execution; 500 students per preview and 1,000 marks per save. No Phase 6 fees/accounting, portals or other deferred workflows.


Commands (from repository root unless noted):

```sh
PYTHONPATH=/tmp:$PWD/backend DEBUG=False python3 -m pytest -c backend/pytest.ini backend/tests/unit/test_school_learning.py --ds=mda_school_phase5_settings --reuse-db
PYTHONPATH=$PWD/backend DEBUG=False python3 -m pytest -c backend/pytest.ini backend/tests/unit/test_school_learning.py backend/tests/unit/test_school_learning_postgresql.py --ds=config.settings.school_phase5_verification --reuse-db
# From backend/; single final full regression:
PYTHONPATH=/tmp:$PWD DEBUG=False python3 -m pytest --ds=mda_school_phase5_settings --reuse-db -ra
# From frontend/:
npm test
npm run build
```

`mda_school_phase5_settings` imported test settings and set SQLite `TEST.NAME` to `/tmp/mda-school-phase5-tests.sqlite3`; no production database was used. Migration drift: `DEBUG=False python3 backend/manage.py makemigrations school --check --dry-run --settings=config.settings.test`.

**STOP at Phase 5. Phase 6 requires separate authorization.**

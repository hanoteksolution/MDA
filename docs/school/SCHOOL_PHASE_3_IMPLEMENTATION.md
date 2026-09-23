# School Phase 3 — admissions and student administration

Date: 2026-09-21. Resumed by the user's explicit instruction to implement Phase 3 and stop at its gate. Phase 2's verified foundation is retained. Completed Branch work was not changed.

## Scope

The Phase 1 audit §N defines Admission → reusable guardian/family → Student → Enrollment, conversion idempotency and preserved transfer history. The subsequent `SCHOOL_STUDENT_DOMAIN.md` refines these decisions and makes import conditional on a reusable transactional import pipeline. None was found; bulk import remains deferred, with no import endpoint or shortcut added.

The workspace already contained unfinished Phase 3 models, migration 0005, services, API resources and five failing SIS tests. This phase completed that work rather than recreating Phase 1–2. The earlier completion matrix's “not started” entry did not reflect those unfinished files.

## Delivered

- Campus/tenant-scoped applicant, application, guardian/family, relationship, student and enrollment records. Guardians/families are reused rather than copied into separate identities.
- Application submission, document review, assessment/interview outcomes, immutable decisions, acceptance and atomic conversion. Retrying conversion returns the same authorized student without another number, guardian link or enrollment.
- Direct registration with a reason, school household policy, numbering, duplicate-candidate lookup and UI warning. Academic admission/enrollment flags are enforced.
- Enrollment capacity and roll-number guards; transfer requires source/destination access, retains the original placement and closes it the preceding day. Withdrawal and re-enrollment retain history. Source-campus users cannot open the transferred student's current identity.
- Private document upload/download, verification and required-document acceptance gates. Confidential notes have separate permissions and redacted audit content. Workflows roll back if audit recording fails.
- Academic closure/date guards now protect enrollment dependencies. Later promotion/repetition commands are explicitly unavailable.
- Dedicated list/new/detail/edit pages under `/school/sis/:resource`, admissions dashboard at `/school/admissions`, School overview entry links, permission-controlled commands, paginated/searchable lists, bounded CSV exports, related-record links, private attachments and dirty-form protection.

No timetable, attendance, marks, promotion engine, fees, payroll, portals, AI or automation work was started. Assessment/interview records here are admission appointments, not academic examination grading.

## Corrections to unfinished code

Fixed missing SIS model exports, missing admission dates, national-ID fields incorrectly treated as UUID foreign keys, non-idempotent conversion, accepted-section defaults, inactive term enrollment, calendar admission/enrollment flags, audit before snapshots, malformed nested payload handling, historical re-enrollment links and inactive guardian-link visibility. Private attachments now require existing read authorization before relinking, while transfer access follows the authorized attached student rather than the file’s original campus. Added frontend pages/routes and fixed ES2020-incompatible string methods and optional placement payload normalization.

## Verification

- PostgreSQL: **20 passed, zero skipped**. Seventeen SIS tests plus two threaded HTTP concurrency tests and one Phase 3 migration test. Concurrent conversion returns one identity; concurrent registrations competing for one place yield one success and one controlled validation failure.
- Final SQLite SIS suite: **18 passed** after the final attachment authorization hardening. This adds a file-relink permission-bypass test and strengthens transfer coverage for destination photo access and source-campus denial. [Final SIS evidence](verification/phase3-sis-final.txt). The PostgreSQL run above preceded this database-independent authorization refinement.
- Existing foundation checks for year lifecycle, term closure and offerings: **3 passed** in the targeted development run. Phase 1–2 were not repeated.
- Frontend: **11 passed**, comprising five SIS workflow tests and six existing foundation tests.
- TypeScript/Vite production build: passed; existing large-bundle warning remains.
- School migration autodetection: no changes. `git diff --check`: passed.
- Chromium against the production build and live Django/PostgreSQL API: **16 passed**, zero page errors and zero failed School API responses. Created guardians/applicants/applications, completed review/decision/conversion, transferred placement, checked history, withdrew/re-enrolled and checked the dashboard plus student lists at 1366/768/390 pixels. [Browser evidence](verification/phase3-chromium.json). The walkthrough found and resolved untouched nullable placement fields and a premature staff lookup.
- [PostgreSQL test evidence](verification/phase3-postgresql.txt).

Backend command (from `backend/`):

```sh
DEBUG=False python3 -m pytest --ds=config.settings.school_phase3_verification --reuse-db tests/unit/test_school_sis.py tests/unit/test_school_sis_postgresql.py tests/unit/test_school_sis_migration.py --tb=short -ra
```

Frontend commands (from `frontend/`):

```sh
npm test -- --run src/modules/school/sis/workflows.test.ts src/modules/school/foundation.test.ts
npm run build
```

PostgreSQL verification uses only `test_school_phase3_verify` on loopback. No production database or configuration was changed. The full ERP regression suite was not repeated, per the user's targeted-test instruction; existing Branch/full-suite debt is not reclassified as fixed.

## Migration and rollback

Existing additive School migration `0005_admissionapplication_admissiondecision_and_more.py` creates the Phase 3 schema. No applied migration was rewritten and no new migration is needed for the completion fixes. The PostgreSQL test upgrades from School 0004, checks existing year/campus/tenant identity and current-year state, reverses an empty SIS schema, then upgrades again.

Reversing 0005 with real SIS data destroys those new records. For an actual rollout, retain a database backup and matching application version; disabling the new routes is preferable to reversing populated tables. School private files are outside public media and require corresponding private-storage backups. Production deployment was not performed.

## Important files

- Backend: `apps/school/services/{student_creation,enrollment_service,student_lifecycle,sis_common,admission_workflow,integrity}.py`, `services/sis_integrity.py`, `serializers/sis.py`, `repositories/sis.py`, `models/__init__.py`, `api/v1/school/{sis_views,sis_read_views}.py`.
- Frontend: `src/modules/school/sis/`, School overview/navigation, and five additive School routes in `src/app/workspaceRoutes.tsx`.
- Tests: `test_school_sis.py`, `test_school_sis_postgresql.py`, `test_school_sis_migration.py`, `sis/workflows.test.ts`, `frontend/tests/school/phase3.mjs`.
- Verification settings: `backend/config/settings/school_phase3_verification.py`; disposable browser seed: `backend/tests/verification/seed_school_phase3_browser.py`.

## Phase 3 gate

**PASS — implemented scope and targeted verification. STOP.** Ready for the user's Phase 3 review; Phase 4 remains unstarted and needs separate authorization.

Limits: import is deferred as specified above; no production deployment, full ERP regression, new load benchmark or exhaustive accessibility/browser matrix is claimed. The browser smoke uses Chromium and disposable records. CSV exports are bounded to 10,000 authorized rows; student/family/guardian portal flags do not create portal accounts. Existing unrelated repository debt remains outside this phase.

For browser reproduction, first run the PostgreSQL tests, then run `seed_school_phase3_browser.py` through `manage.py shell` with a test-only settings module whose database NAME is `test_school_phase3_verify`. Serve Django on loopback :8016 and proxy `/api` from the built frontend on :5177. Run `node frontend/tests/school/phase3.mjs`; set `SCHOOL_PLAYWRIGHT` if tooling is installed elsewhere. The seed refuses other database names. Do not seed before a reused-database test run, since the browser fixture intentionally persists records until that disposable database is recreated.

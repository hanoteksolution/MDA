# School Phase 4 — teaching staff, timetable and attendance

Date: 2026-09-21. Resumed by the user's explicit instruction to implement Phase 4 and stop at its gate. The scope is Phase 1 audit §N row 4: minimal shared Employee contract, School teacher extension/assignment, conflict-safe timetable, daily/period attendance and correction audit. Phase 3 (SIS/enrollment) is the foundation and was not changed except for the additions below. Branch and Integrations work was not touched.

## Delivered

- **Shared Employee contract** — new `apps/hr` app with a deliberately small `Employee` (tenant, home campus, optional login, code, name, contact, job title, employment type/dates, status). One employee record per login; no leave, payroll or contract data.
- **Teacher extension** — `SchoolStaffProfile` (campus-scoped, one live profile per employee and campus, weekly-period cap) and effective-dated `TeacherAssignment` (subject/class/assistant teacher per year, class and optional section/offering). Rules: subject teachers need an offering that matches year/class/section; duplicate assignments and a second class teacher for the same class and dates are rejected; dates must fall inside an open year.
- **Timetable** — `Classroom`, `TimetablePeriod` (no overlaps per campus/shift, inside its shift), `TimetableVersion` (draft → published → archived; one live version per campus and year) and `TimetableEntry`. Conflict checks: teacher double-booking, room double-booking, class/section overlap (class-wide lessons block every section), time-overlapping periods, weekly-period quota per offering/section, teacher weekly cap, teacher must hold an assignment for the class/subject, teacher scheduled on another campus. Publishing re-checks every lesson and atomically supersedes the previous live version; published versions are immutable and are revised by cloning into a draft.
- **Attendance** — `AttendanceSession` (daily or per-period, one per class/section/date/period), `AttendanceRecord` (one per student, tied to the enrollment that placed them on that date) and `AttendanceCorrection`. Bulk save is an idempotent upsert while the session is open; submission requires every rostered student to be marked and then locks it. Later changes go only through correction requests (reason required, one pending per record) that need `attendance_correction.approve`; approval re-checks the record has not changed, and both actors, old/new status and reason are audited. Wrong-academic-year, future-date, non-enrolled-student and duplicate-student marks are rejected.
- **Teacher scope** — `attendance.take` is limited to the user's own active assignments (daily attendance needs a class-teacher assignment; period attendance must name a subject the teacher is assigned to). `attendance.take_any` covers any accessible campus. Teachers can request but not approve corrections and cannot publish timetables.
- **API/UI** — the ten resources plug into the existing SIS resource endpoints and pages (`/school/sis/<resource>`), with commands `publish`, `clone`, `submit`, `correct`, `approve`, `reject`, a roster endpoint (`/school/sis/attendance-roster/`), and two dedicated pages: `/school/attendance` (class list, mark-all, draft/submit, lock) and `/school/timetable` (weekly grid per version). Navigation links appear only with the matching permissions.
- **Permissions** — `apps/school/ops_permissions.py` is merged into the SIS catalog and role bootstrap; `school_teacher` receives view access plus attendance take/request-correction.

## Verification

- SQLite: `test_school_ops.py` **10 passed** (staff/assignment integrity, every conflict rule, publish/supersede/clone/immutability, cross-campus teacher, bulk attendance/lock/errors, period vs daily, teacher scope, correction workflow and audit, HTTP authorization and cross-campus IDOR).
- PostgreSQL (`test_school_phase3_verify`, loopback, `--create-db` then reuse): **18 passed, 0 skipped** — the 10 above, four threaded HTTP concurrency tests (two lessons racing for one teacher slot yield one 201 and one 400; concurrent attendance saves share one session; concurrent publishes leave exactly one live timetable; concurrent approvals apply once), the Phase 4 migration test (upgrade from School 0005 preserving students, reverse when empty, re-upgrade) and the Phase 3 PostgreSQL/migration tests as a regression. [Evidence](verification/phase4-postgresql.txt).
- Frontend: **124 passed** overall (7 new in `sis/academics.test.ts`); `npm run build` (tsc + vite) passed with the existing large-bundle warning.
- Chromium against the production build and live Django/PostgreSQL: owner created lessons, saw a conflicting lesson rejected with a visible message, published the timetable and viewed the grid; a teacher had no publish command, took attendance (mark-all, one absent, draft, submit → locked), requested a correction that the owner approved; no horizontal overflow for either page at 1366/768/390 px; zero page errors and no failed School API call other than the one deliberate conflict. [Browser evidence](verification/phase4-chromium.json).
- `makemigrations --check` for `school` and `hr`: no changes.

Backend commands (from `backend/`):

```sh
python3 -m pytest tests/unit/test_school_ops.py
DEBUG=False python3 -m pytest --ds=config.settings.school_phase3_verification --reuse-db tests/unit/test_school_ops_postgresql.py tests/unit/test_school_ops_migration.py tests/unit/test_school_ops.py
```

Frontend: `npm test -- --run src/modules/school`, `npm run build`. Browser reproduction: run the PostgreSQL tests, then `tests/verification/seed_school_phase4_browser.py` through `manage.py shell` with a test-only settings module whose database is `test_school_phase3_verify`, serve Django on :8016 and the built frontend on :5177 (proxying `/api`), then `node frontend/tests/school/phase4.mjs` (set `SCHOOL_PLAYWRIGHT` if tooling lives elsewhere). The seed refuses other database names; re-seeding needs `manage.py flush` on that disposable database first.

## Migration and rollback

Additive migrations `hr/0001_phase4` and `school/0006_phase4`; no applied migration was rewritten. Reversing 0006 with real timetable/attendance data destroys it; for a real rollout keep a backup and disable the routes instead. Production deployment was not performed.

## Limits and deferred work

- Not in Phase 4: parent absence notifications and communication, attendance analytics/report packs, HR leave/payroll, substitutions and automatic timetable generation, term-specific timetable versions, promotion/marks/fees/portals/AI (later phases), bulk import.
- The Employee master is exposed through the School API under `school.employee.*` until a full HR module exists; an employee's home campus must be accessible to assign them on a campus.
- Legacy `teacher` user references on class/section/offering remain and are not synchronized with `TeacherAssignment`; period attendance is not linked to a specific timetable lesson; the cross-campus teacher check compares against published timetables only; a user may approve a correction they requested (both actors are audited).
- SQLite ignores `select_for_update`; locking claims rest on the PostgreSQL results above.

## Phase 4 gate

**SIGNED OFF / PASS (2026-09-21).** Two Phase 4 regressions found by the first full regression were fixed and a final full regression shows no new failures or errors. Ready for Phase 5 (not started; it needs separate authorization).

Full backend regression (SQLite, `pytest tests`): **9 failed, 9 errors** in the completed run ([output](verification/phase4-regression.txt), [exact comparison](verification/phase4-regression-comparison.json)). By exact node ID against the recorded pre-Phase-4 baseline, seven failures and all nine errors are known baseline debt; **two failures were new and caused by Phase 4**:

- `test_school_sis.py::test_cross_campus_transfer_preserves_private_identity_and_history` — `{'student_id': 'Related record belongs to another campus.'}`
- `test_school_sis.py::test_file_cannot_be_relinked_to_bypass_its_read_permission` — `{'document_type_id': 'Related record belongs to another campus.'}`

Root cause: the campus-consistency loop in `ops_integrity.validate_ops` ran for every School record, not only Phase 4 models, so Phase 3 rows whose related record has no campus (campus-wide document types) or a different campus by design were rejected. The Phase 4 test runs had not included `test_school_sis.py`. Fix: `validate_ops` now applies that loop only to `Classroom`, `SchoolStaffProfile`, `TeacherAssignment`, `TimetablePeriod`, `TimetableVersion` and `TimetableEntry`.

After the fix, `test_school_sis.py`, `test_school_ops.py` and `test_school_foundation.py` passed together on SQLite (one PostgreSQL-only skip). The remaining baseline debt, unchanged and unrelated to School Phase 4:

- Failed (7): `test_accounting_alerts_step35::test_scan_notifies_on_unbalanced_journal`, `test_backfill_health_step35::test_backfill_commit_posts_invoice_and_expense`, `test_demo_tenant_step39::test_create_demo_async_seed_marks_pending`, `test_pharmacy_rx_fefo_step60` (`test_dispense_fails_when_batch_short`, `test_manual_dispense_deducts_fefo_and_inventory`, `test_pos_fill_without_double_stock_deduct`), `test_tenant_foundation::test_valid_slug_and_hostname`.
- Errors (9): `test_tenant_isolation_api` (3, unknown module `products`) and `test_performance_step31` (6).

**Final verification (after the fix).** Full backend regression once more (SQLite, `pytest tests`, [output](verification/phase4-final-regression.txt)): **7 failed, 9 errors, 0 School failures.** By exact node ID these are the 16 known baseline items listed above: 0 new, 0 missing, and both `test_school_sis.py` regressions are gone. The earlier "9 failed" count above is the first run, before the fix.

PostgreSQL, browser and frontend were not re-run. The only code changed after their verification is `ops_integrity.validate_ops`, whose campus-consistency loop now runs only for the six Phase 4 models, the same rows those runs exercised; the fix only stops the check firing on Phase 3 rows. That is reasoning, not a fresh run. Other gates: Phase 4 targeted 10, PostgreSQL 18 with zero skipped, frontend 124, production build and Chromium (13 checks, zero page errors, only the deliberate timetable-conflict 400). Phase 5 was not started.

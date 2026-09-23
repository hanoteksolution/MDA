# PHASE 2 COMPLETION REPORT

**2026-09-13 update:** The verification gaps recorded below have now been closed. See [Phase 2 verification and hardening](SCHOOL_PHASE_2_VERIFICATION.md) for the current **Ready for Phase 3: YES** decision. This report preserves the earlier implementation-stage evidence.

Date: 2026-09-12. Baseline: [Phase 1 audit](SCHOOL_PHASE_1_AUDIT_2026-09-11.md).

## 1. Summary

School Foundation and Academic Core are implemented in the workspace: profile, shared campuses, access grants, calendar, academic catalogs, classes, sections, shifts and subject offerings, with service-enforced authorization, integrity, lifecycle and audit. Dedicated frontend CRUD routes and real foundation dashboard counts replace the previous limited experience. Existing School URLs remain supported.

Implementation is ready for review; production sign-off is pending the verification gates below. No production migration/deployment was performed. Admissions, students, guardians, enrollment workflows, timetable, attendance, exams, fees, payroll, portals, AI and automation were not started.

## 2. Models created

- `EducationLevel`: tenant catalog of levels, configurable sequence.
- `SchoolClass`: campus grade/class, level, sequence, capacity, room and eligible teacher reference.
- `Section`: campus/class stream, capacity, room, optional teacher and shift.
- `SchoolShift`: configurable campus schedule label and time range.
- `SubjectCategory` and `Subject`: reusable tenant catalogs with subject marks, pass mark, weight and type.
- `SubjectOffering`: campus/year/class/subject configuration with optional term, section and teacher.
- `SchoolCampusAccess`: minimal shared-User-to-Branch grant/revocation extension.

`SchoolMaster` is abstract. There is no duplicate company, employee, student or grade identity model.

## 3. Models extended

`SchoolProfile` gains display/authority/calendar/terminology/grading-reference/attendance/status configuration and overlap policy. Shared Company/Branch owns organizational identity and campus contact/address data; profile owns School-specific settings and leadership. Primary campus uses Branch.is_default. Logo upload reuses the shared validated media utility.

`AcademicYear` gains code, admission/enrollment flags, strict calendar/current constraints and archived state. `AcademicTerm` gains code, publication date, archived state and positive sequence. Parent FKs protect academic history. `Branch` adds tenant/code uniqueness. Shared `User` adds School system-role choices; staff remains the existing shared identity.

## 4. Migrations

| Migration | Purpose |
|---|---|
| `school/0002_foundation_fields.py` | New foundation models/fields/constraints; deterministic code backfill, tenant inference and legacy date/current validation |
| `school/0003_protect_academic_history.py` | Protected parent FKs; removes nonexistent finance module dependency from stored School registration |
| `settings_app/0004_foundation_integrity.py` | Preflight duplicate campus codes, then tenant/code uniqueness |
| `school/0004_foundation_integrity.py` | Required tenant/status checks, term sequence default, preflight legacy tenant/campus/year/date/principal consistency |

Original `school/0001_initial.py` remains unchanged. Invalid legacy data stops migration with a repair error rather than silently deleting or renaming records. Backfill retains UUIDs, names and dates. The migration-upgrade test exercises existing School records. Migrations were exercised on isolated SQLite, not the production database. The existing platform migration dependency must be shipped with the repository's preexisting onboarding work.

## 5. APIs

Base: `/api/v1/school/`. Resources: `campuses`, `campus-access`, `academic-years`, `terms`, `levels`, `classes`, `sections`, `shifts`, `subject-categories`, `subjects`, `subject-offerings`.

Each supports list/create, detail/update and archive via DELETE, plus explicit archive/restore commands. Calendar resources additionally support activate/close; academic years support make-current. List queries allow bounded pagination, search, sort, status/archive and applicable relationship/current filters. Unknown payload fields are rejected.

Additional endpoints: `profile/` GET/PUT/PATCH, `profile/logo/` POST, `summary/`, `capabilities/`, paginated `lookups/<kind>/`, and `<resource>/<id>/activity/`. Missing profiles preserve `data: null`, with form defaults returned separately. Legacy summary/profile/year/term paths and names remain available. See [API matrix](SCHOOL_API_MATRIX.md).

## 6. Frontend pages

- `/school`: authorized campus selection, actual academic counts and calendar summary.
- `/school/settings`: campus School profile, leadership, calendar settings and validated logo upload.
- `/school/academic-years`: retained legacy calendar list.
- `/school/academics/:resource`: lists with paging/search/sort, relevant relationship/status/archive/current filters, column visibility and current-page print/PDF.
- Dedicated `/new`, `/:id` and `/:id/edit` routes: grouped forms, inline errors, Save, Save & new, Cancel, details, confirmed lifecycle actions and related class sections/subjects/activity.

Navigation exposes delivered foundation areas. Shared PageLayout, FormSection, DataTable and Radix controls are reused. Capability responses drive action visibility; API permissions remain authoritative. Loading, empty, error/retry and no-permission states are present. Responsive grid classes and label/error associations are tested; actual browser/mobile/focus behavior still needs verification.

## 7. Campus authorization

`SchoolAccess` requires an active authenticated actor, an explicit valid tenant and enabled School/dependencies. All campus queries and direct-ID mutations are server scoped. Shared User.branch grants default campus access; active SchoolCampusAccess rows grant more campuses; an inactive grant revokes even default-campus access. `school.campus.all` permits all campuses only within the acting tenant. All-campus permission is required for campus creation/main-campus changes. Tenant-global subjects/levels/categories remain reusable and require their own permissions.

Grant administration is separate from academic management. Staff lookup queries also enforce campus scope, preventing other-campus identity disclosure. Cross-campus requests fail without returning protected records.

## 8. Principal validation

Principal and teacher IDs must identify active, nondeleted same-tenant shared Users with appropriate `leadership.assignable` or `teacher.assignable` eligibility and campus access. Unrelated employee roles cannot become academic staff merely by supplying an ID. Shared elevated-administrator policy is honored within the explicit tenant context.

Shared User deactivation/deletion saves clear principal/teacher references and audit the removal. Physical deletion uses SET_NULL. Historical audit snapshots retain prior identity references. Bulk QuerySet.update bypasses Django signals: operational bulk staff changes must use the supported user-save path; read indicators and subsequent write validation provide additional protection.

## 9. Academic integrity rules

- One current, active, nondeleted academic year per tenant/campus; year codes remain tenant-unique after archive.
- Strict start < end; term dates inside year; positive sequence; term code unique within year.
- Terms may not overlap by default, including shared boundary dates. Profile policy can explicitly allow overlap; disabling it validates existing periods.
- Exam dates must be paired, ordered and inside the term; publication cannot precede the exam end or term end when no exams are configured.
- Parent edits validate existing children. Term activation requires an active year. Closed periods cannot be edited/reactivated through normal CRUD.
- Section/class/campus and offering/year/term/class/section relationships must agree. Capacity, marks, pass marks, weights and periods are validated.
- Four partial database uniqueness constraints cover active offerings with nullable term/section combinations.
- Transactions and tenant-row locking serialize foundation writes, including current-year switching. PostgreSQL concurrency test exists but remains unexecuted here.
- Close-year checks require terms to be closed/archived. Archive rejects live dependencies; historical FKs use PROTECT. Restore returns calendars to planning and masters to inactive. No academic hard-delete API is exposed.

## 10. Permissions

Granular resource view/create/update/archive/restore permissions, calendar activate/close, profile view/update, campus.all and staff eligibility are registered in shared RBAC. School owner/admin presets manage the foundation; principal/academic-director/registrar presets remain campus scoped and cannot grant campus access. Teacher is read-oriented with teacher eligibility. Registrar does not receive teacher/principal eligibility by default.

Narrow legacy settings/calendar aliases preserve earlier access. Explicit new permission revocation takes precedence over aliases. Campus scope is enforced independently of resource permission. See [permission matrix](SCHOOL_PERMISSION_MATRIX.md).

## 11. Audit events

Create/update, activate/current switching, close, archive/restore, profile changes and principal assignment use the shared audit store with actor, tenant/campus, entity and before/after snapshots. Clearing another current year/main campus is also audited. User deactivation emits `staff_reference_cleared`. Activity reads require scoped resource visibility. Django School admin is read-only to prevent write bypass of domain services.

## 12. Tests added

`test_school_foundation.py` covers all-resource CRUD/lifecycle, tenant/campus IDOR, grants/revocations, permission and legacy-alias behavior, staff eligibility/deactivation, date/overlap/parent integrity, capacity/marks/offerings, database nullable-scope uniqueness, logo validation, malformed JSON, lookup privacy, paging/query growth and legacy URL names. A PostgreSQL-only threaded current-year activation test checks concurrent writes.

`test_school_migrations.py` verifies upgrade of historical School rows. Frontend `foundation.test.ts` covers payload allowlists, lifecycle actions, immutable relationship inputs, rendered field/error associations and configuration consistency.

## 13. Test results

| Check | Result |
|---|---|
| Final School + migration + RBAC/module/tenancy/journal suite | **74 passed, 1 skipped**, 199.27 seconds |
| PostgreSQL concurrent activation | Skipped explicitly on SQLite |
| Complete frontend Vitest suite | **24 passed**, 4 files |
| Frontend TypeScript + Vite production build | Passed, 11.68 seconds; large-chunk warning |
| School/settings migration autodetection | No changes detected |
| Django system check | No issues |
| Whitespace validation | `git diff --check` passed |

Backend command (from backend, with isolated SQLite test settings):

```sh
PYTHONPATH=/tmp:. DEBUG=False python3 -m pytest --ds=mda_school_test_settings --reuse-db tests/unit/test_school_foundation.py tests/unit/test_school_migrations.py tests/unit/test_rbac_bootstrap.py tests/unit/test_module_system.py tests/unit/test_module_deps_gate_step64.py tests/unit/test_tenancy_context.py tests/unit/test_journal_immutability_step37.py --tb=short
```

`/tmp/mda_school_test_settings.py` imports `config.settings.test` and overrides DATABASES to SQLite with TEST.NAME `/tmp/mda-school-tests.sqlite3`; this session-local file avoids touching application databases. On PostgreSQL staging use approved database settings instead; do not reuse the SQLite override for the concurrency check. Frontend commands, from frontend: `npm test -- --reporter=dot` and `npm run build`.

Session logs: `/tmp/school-verified-tests.log`, `/tmp/school-ui-verified.log`, `/tmp/school-ui-build-verified.log`, `/tmp/school-regression.log`, `/tmp/school-baseline-regression.log`. These temporary logs are supporting session evidence, not committed artifacts.

Full backend regression: **487 passed, 7 failed, 9 errors**. A temporary comparison copy with Phase 2's shared bootstrap/User/Branch/School-registration changes reverted reproduced the same 7 failures and 9 errors (plus one passing case in the selected files). This was not a pristine checkout: additive School code remained to satisfy imports. The comparison supports treating these as existing failures; it is not a claim that the entire repository passes.

Existing failures: posted-journal mutation in accounting alert test; invoice/expense backfill expectation; demo callback missing tenant argument; three pharmacy FEFO/stock expectations; tenant slug expectation. Nine setup errors request nonexistent `products` module in tenant-isolation/performance fixtures. No unrelated accounting, pharmacy or tenancy behavior was changed to suppress them.

The frontend production build succeeds with the existing large-chunk warning. School/settings migration dry-run reports no changes; Django system checks and `git diff --check` pass. Global migration autodetection still identifies preexisting sales model drift; no unrelated sales migration was generated.

## 14. Existing RBAC issue status

Phase 1's role-bootstrap failure came from the shared read_only preset referencing undefined `travel.customers.view`. Removed that stale entry; existing `customers.view` remains. No broad RBAC refactor. Relevant RBAC tests now pass. The nonexistent `finance` School module dependency was separately exposed by executable setup tests: shared finance is not a module seed. School now depends on sales, with school/sales/inventory business defaults, and migration reconciles stored registration. This is the documented correction to the audit's assumption.

## 15. Remaining technical debt

Production PostgreSQL migration/concurrency verification remains pending. Creating the isolated PostgreSQL process required ownership privileges; the user declined the escalation. No alternative privilege path was attempted. Real-browser keyboard/focus, narrow/mobile layout, upload and CRUD smoke tests remain pending because no browser runner was available. These are sign-off gates, not passing tests.

Existing full-suite failures, sales migration drift and large frontend bundles remain separate repository debt. Tenant-wide write locking is intentionally conservative; future load measurements can justify narrower locking. Bulk staff deactivation must honor the signal caveat above. Default grading scheme is a reference/configuration value, not a grading engine. Future student/enrollment/history dependencies must extend archive/close guards before those workflows ship.

## 16. Files created

- `backend/apps/school/migrations/0002_foundation_fields.py`
- `backend/apps/school/migrations/0003_protect_academic_history.py`
- `backend/apps/school/migrations/0004_foundation_integrity.py`
- `backend/apps/school/models/foundation.py`
- `backend/apps/school/permissions.py`
- `backend/apps/school/policies/__init__.py`
- `backend/apps/school/policies/access.py`
- `backend/apps/school/policies/staff.py`
- `backend/apps/school/repositories/__init__.py`
- `backend/apps/school/repositories/foundation.py`
- `backend/apps/school/serializers/__init__.py`
- `backend/apps/school/serializers/foundation.py`
- `backend/apps/school/services/foundation_service.py`
- `backend/apps/school/services/integrity.py`
- `backend/apps/school/signals.py`
- `backend/apps/settings_app/migrations/0004_foundation_integrity.py`
- `backend/tests/unit/test_school_foundation.py`
- `backend/tests/unit/test_school_migrations.py`
- `docs/school/SCHOOL_PHASE_2_IMPLEMENTATION.md`
- `frontend/src/modules/school/components/FoundationFields.tsx`
- `frontend/src/modules/school/components/RelatedRecords.tsx`
- `frontend/src/modules/school/components/RelationField.tsx`
- `frontend/src/modules/school/components/RowActions.tsx`
- `frontend/src/modules/school/components/SchoolAcademicNav.tsx`
- `frontend/src/modules/school/foundation.test.ts`
- `frontend/src/modules/school/foundation.ts`
- `frontend/src/modules/school/hooks/useFoundation.ts`
- `frontend/src/modules/school/pages/FoundationDetailPage.tsx`
- `frontend/src/modules/school/pages/FoundationFormPage.tsx`
- `frontend/src/modules/school/pages/FoundationListPage.tsx`

## 17. Files modified

- `backend/apps/school/admin.py`
- `backend/apps/school/apps.py`
- `backend/apps/school/models/__init__.py`
- `backend/apps/school/models/academic.py`
- `backend/apps/school/models/profile.py`
- `backend/apps/school/services/academic_service.py`
- `backend/apps/school/services/profile_service.py`
- `backend/apps/school/services/summary_service.py`
- `frontend/src/modules/school/pages/AcademicYearsPage.tsx`
- `frontend/src/modules/school/pages/SchoolPage.tsx`
- `frontend/src/modules/school/pages/SchoolSettingsPage.tsx`
- `backend/api/v1/school/views.py`
- `backend/api/v1/school/urls.py`
- `backend/apps/authentication/bootstrap.py`
- `backend/apps/authentication/models/user.py`
- `backend/apps/settings_app/models/setting.py`
- `backend/apps/platform/services/module_service.py`
- `backend/apps/platform/services/platform_service.py`
- `frontend/src/services/api/school.ts`
- `frontend/src/app/workspaceRoutes.tsx`
- `frontend/src/navigation/businessWorkspaces.ts`
- `frontend/src/navigation/moduleWorkspaces.ts`
- `docs/school/README.md`
- `docs/school/SCHOOL_ARCHITECTURE.md`
- `docs/school/SCHOOL_DATABASE_ERD.md`
- `docs/school/SCHOOL_CRUD_MATRIX.md`
- `docs/school/SCHOOL_API_MATRIX.md`
- `docs/school/SCHOOL_PERMISSION_MATRIX.md`
- `docs/school/SCHOOL_TEST_MATRIX.md`
- `docs/school/SCHOOL_COMPLETION_MATRIX.md`

The workspace already contained extensive unrelated changes and untracked Phase 1 School files. This inventory describes this phase's edits relative to the session baseline; it does not imply ownership of every file shown by git status. No commit, reset or deployment was performed.

## 18. Phase 3 prerequisites

1. Run all School migrations and the PostgreSQL-only concurrency test on an approved PostgreSQL staging database, including a representative legacy-data upgrade and backup/restore rehearsal.
2. Complete browser CRUD/lifecycle/permissions and responsive keyboard/focus checks with owner, campus principal and read-only users.
3. Resolve or explicitly track/accept the reproduced repository regression failures and sales migration drift before production release.
4. Review roles, assign actual campus grants/staff eligibility, enable School and its dependencies, then obtain Phase 2 sign-off.
5. Begin later domain work only after the user explicitly says `PROCEED TO PHASE 3`.

## 19. Ready for Phase 3: NO

Foundation implementation and available automated checks are complete; production verification gates remain open. Stop here without starting Phase 3.

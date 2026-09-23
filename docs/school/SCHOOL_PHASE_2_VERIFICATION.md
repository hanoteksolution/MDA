# PHASE 2 VERIFICATION COMPLETION REPORT

Finalized: 2026-09-13. Tests executed: 2026-09-12. Scope: Phase 2 verification and hardening only. This report supplements [Phase 2 implementation](SCHOOL_PHASE_2_IMPLEMENTATION.md). Phase 3 is not started.

## 1. Environment

Disposable local PostgreSQL cluster `/tmp/mda-school-pg25`, loopback port 55439; separate `school_verify` browser/probe database and `test_school_verify` pytest database. No application/production database was used. Ubuntu environment, Python 3.10, Django 5.2, Node 24, React 19/Vite frontend. PostgreSQL process ownership and browser installation were explicitly approved after sandbox restrictions were encountered.

Test settings import `config.settings.test` but override the database engine to PostgreSQL, with explicit UTF8 test charset and template0. Browser verification uses actual Django endpoints and the built frontend on localhost:5174. No School API mocks are used for CRUD or authorization. One deliberately injected 503 response is used solely to exercise the error/retry UI.

## 2. PostgreSQL version

PostgreSQL **14.24**, UTF8, x86_64 Ubuntu. [Server evidence](verification/postgresql-environment.txt). Default READ COMMITTED isolation is asserted by the API concurrency test. The initial test database inherited SQL_ASCII from the temporary cluster, causing two Unicode audit JSON failures. It was recreated as UTF8 and all 59 School gates passed; no application workaround was made for invalid encoding.

## 3. Migration verification

All repository migrations applied to a clean PostgreSQL database. Existing School schema was migrated from school0001 to latest using 3 tenants × 3 campuses with 9 profiles, 9 current years and 9 terms. IDs, ownership, branch/year references, profile names, year dates, current flags and term sequence/code backfill were checked. Backfilled year codes were distinct and no duplicate rows appeared.

On disposable data the test reversed to school0001, confirmed the original 27 School rows survived, then migrated forward again. School0002 introduces new tables and fields: reversing it discards Phase 2-only entities and values. Backfills and School module-registration cleanup are intentionally not semantically undone by RunPython.noop. This is schema reversibility, not lossless production rollback. Production rollback must restore a pre-migration database backup with the matching application version; capture/reconcile writes after that backup. Invalid legacy rows/campus code duplicates intentionally stop migration for repair.

## 4. PostgreSQL-only test results

`test_postgresql_concurrent_activation` changed from skipped-on-SQLite to executed/passing on PostgreSQL. It uses independent connections, threads and a barrier to contend on the tenant row lock and verifies one current year survives. The expanded `test_school_postgresql.py` adds API concurrency, catalog/constraint, atomic rollback and cross-tenant/campus request tests. No PostgreSQL gate was skipped in the PostgreSQL runs.

Final combined School/foundation/PostgreSQL/migration/RBAC suite: **69 passed, zero skipped**, in 428.27 seconds, using committed `config.settings.school_verification`. The earlier expanded School run passed 59 tests; the additional HTTP/workflow security matrix also passed and is included in the final 69.

## 5. Constraints verified

Database introspection confirms the offering unique partial indexes for all four nullable term/section combinations, marks check and foreign keys. Direct database writes exercise marks rejection and parent FK protection, independently of service validation. Existing tests verify current-year uniqueness and all four NULL offering scopes against PostgreSQL. Tenant/code and campus/class-scoped uniqueness are exercised by concurrent create requests. List ordering includes a primary-key tie-breaker and was checked with repeated and adjacent pages.

## 6. Concurrency scenarios

| Scenario | Result |
|---|---|
| Two current-year API commands | Both 200; serialized last writer wins; exactly one current year in campus |
| Same offering scope with different codes | One 201, one controlled 400, exactly one row |
| Same academic-year code | One 201, one 400 |
| Same campus code | One 201, one 400 |
| Same class code | One 201, one 400 |
| Same subject code | One 201, one 400 |
| Same section name with different codes | One 201, one 400 |
| Inject audit failure during current switch, term activation/close, principal assignment, offering creation and archive | Entire transaction rolled back; no partial state |

Conflicts return DRF validation envelopes, not raw IntegrityError. There is no application retry loop: tenant-row serialization permits valid sequential commands; duplicate creates return 400 for the caller to correct. Database constraints remain the final defense.

## 7. Campus isolation scenarios

Tenant A has A1/A2, Tenant B has B1, with owner and campus principals; browser fixtures additionally include teacher/read-only. Unauthorized GET detail, PATCH, DELETE and activate/close/archive/restore calls return 404. Cross-scope term POST is rejected. The Tenant A owner cannot access Tenant B, while campus principals cannot access each other's years. List/lookup scoping, explicit extra grants/default-campus revocation and raw-ID attempts are covered by the existing suite on PostgreSQL.

## 8. Principal validation

Valid eligible same-tenant/same-campus principal succeeds. Wrong campus, wrong tenant, inactive and unrelated staff are rejected. Deactivation clears the stored reference; reassignment of the inactive principal fails. Shared User with explicit School eligibility is the chosen employee/staff architecture; there is no separate Employee requirement or SchoolTeacherProfile to fake in tests. Bulk QuerySet.update bypassing model signals remains an operational caveat.

## 9. Academic integrity

PostgreSQL tests cover term/year containment, overlap policy, ordered dates, class/section/campus coherence, offering uniqueness, foreign tenant subjects, invalid teacher/principal references, unsafe archive, current-year uniqueness and lifecycle guards. Rejected workflow and audit-failure tests assert database state, not only HTTP status.

## 10. Query/performance observations

Synthetic dataset: 3 tenants, 9 campuses, 45 years, 135 terms, 36 education levels, 108 classes, 324 sections, 135 subjects and 3,240 offerings. Tenant/campus filtering and deterministic pagination were tested with tied names.

| Page | SQL queries for 1 / 25 rows | Representative EXPLAIN ANALYZE execution ms |
|---|---|---|
| Years | 16 / 15 | 0.363 |
| Terms | 15 / 15 | 0.328 |
| Classes | 15 / 15 | 0.237 |
| Sections | 15 / 15 | 1.007 |
| Subjects | 12 / 12 | 0.093 |
| Offerings | 15 / 15 | 8.211 |
| Campuses | 15 / 15 | 0.100 |

No per-row query growth. PostgreSQL uses indexed joins/filters and also chooses sequential scans on small catalogs; this is not evidence that every sequential scan requires an index. No speculative performance migration was added. These local synthetic timings are not a production latency SLA. Full plans and buffers: [query evidence](verification/postgresql-query-plans.json). Tenant-wide write locking remains conservative and may need load-driven refinement later.

## 11. Browser matrix

**PASS — Chromium 153.0.8010.12, Playwright 1.63.0.** Real browser, production Vite build, live Django API and PostgreSQL. Firefox/Edge were not installed or claimed. The final CRUD run recorded 49 passing checks and the UX run 21 checks, including eight axe scans. No JavaScript page errors. The CRUD run had no failed API responses. The UX run had only the intentionally expected invalid-marks 400 and injected outage 503; both surfaced correctly and recovered.

Rapid development-mode reloads previously hit the normal 600 requests/minute throttle. The final run used the production build and paced navigation, with no rate-limit failures; production throttle settings were not relaxed. A corrupt test PNG was rejected as expected, then the valid generated PNG upload passed. An old rotated test refresh token was replaced with fresh API logins. These were test-environment/fixture corrections, not hidden product exceptions.

Evidence: [CRUD/network report](verification/chromium-crud.json), [UX/axe report](verification/chromium-ux.json).

## 12. CRUD verification

**PASS.** Mouse/keyboard flows created, opened, edited, archived and restored campuses, academic years, terms, levels, classes, shifts, sections, subject categories, subjects and offerings. Year make-current and term activation/close/year close passed. Restored inactive masters were edited back to active in dependency order. Profile update, same-campus principal selection and actual logo file-input upload passed.

Search, sort, empty results, page-size/next-page requests, column visibility and keyboard row menus passed. Save & new persisted exactly once under a double click and cleared the form; unsaved Cancel and browser Back preserved or discarded edits according to the confirmation. Invalid marks produced readable backend validation. An injected 503 produced an error state and Retry loaded the real list successfully. Profile and generic CRUD routes now resolve without collision.

## 13. Responsive verification

**PASS for the requested smoke matrix.** Overview, offerings list and class form at 1920, 1366, 1024, 768 and 390 CSS pixels: **15/15**, no horizontal document overflow. The sidebar rail, cards, forms and action areas remained within the viewport; wide table content scrolls inside its table container. CRUD clicks exercised scrolling to controls. The detail tab bar wraps at narrow widths. This is Chromium coverage, not a claim of every device/assistive technology combination.

Representative evidence: [mobile overview](verification/390-school.png), [mobile form](verification/390-school-academics-classes-new.png), [desktop offerings](verification/1366-school-academics-subject-offerings.png), [dark form](verification/dark-school-academics-classes-new.png).

## 14. Permission verification

**PASS.** Owner CRUD/workflows pass. A1 principal and A1 teacher selectors expose A1 and exclude A2. Teacher has no Create, Edit or Archive action; a manually constructed teacher POST receives 403. Direct cross-campus/tenant object IDOR and workflow requests are additionally covered by the PostgreSQL HTTP matrix. Capability-load failures are visible and retryable on list/detail pages instead of silently looking like changed permissions.

## 15. Accessibility smoke results

**PASS for the smoke scope.** Axe WCAG 2 A/AA and WCAG 2.1 AA scans of overview, subjects list, class form and profile page in both light and dark mode: **8 scans, zero violations**. The profile scan covers its initial campus selector; profile form interaction/upload is separately exercised by CRUD/UX checks. These automated scans are not a full accessibility conformance certification.

Keyboard tests verify row-menu Escape, confirmation focus trapping across repeated Tab presses, Escape dismissal and focus return. Unsaved Back/Cancel confirmations behave correctly. Fixes include School-specific light-text/primary contrast, dark primary-button foreground, theme/sign-out/page-size accessible names and field-error associations. The initial scan's critical unnamed controls and serious contrast findings are resolved.

## 16. Full-suite comparison

| Run | Result |
|---|---|
| Recorded Phase 2 baseline | 487 passed, 7 failed, 9 errors |
| Phase 2.5 PostgreSQL full suite | 511 passed, 7 failed, 9 errors |
| Phase 2.5 same-engine SQLite comparison | 496 passed, 15 skipped, 7 failed, 9 errors |

Exact failing test IDs were compared: **0 added, 0 resolved**, all 16 match. Extra passes/skips reflect tests added since the earlier full run, including final Phase 2 additions and the 14 PostgreSQL gates. The separately added security matrix passed afterward. Known failures remain accounting-alert immutability, backfill expectation, demo callback argument, three pharmacy stock expectations and tenant slug normalization; nine errors request missing products module in old fixtures. No unrelated code was changed to suppress these failures. [Machine-readable comparison](verification/regression-comparison.json).

## 17. Fixes made

- Removed the generated shared-settings route collision that shadowed the real School profile page.
- Added dirty-form protection for link navigation, browser exits/history and campus changes; added immediate in-flight submit guards.
- Added dialog keyboard focus trapping, Escape dismissal and focus restoration to the shared confirmation host used by School workflows.
- Added accessible names to shared theme/sign-out/page-size controls and corrected School light/dark color contrast; associated School input validation text with fields; wrapped detail tabs at narrow widths.
- Hid Edit for deactivated campuses and made capability fetch errors/retry visible on detail/list pages.
- Expanded PostgreSQL/API/migration/transaction/performance/browser verification artifacts. No Phase 3 models or workflows were added.

## 18. Known issues

No remaining blocker from the tested Phase 2 release gates. Existing unrelated repository failures are unchanged and listed in section 16. Frontend build retains its preexisting large-chunk warning. Real production deployment, additional browser engines and exhaustive accessibility/load testing were not performed. No production configuration or database was changed.

## 19. Remaining technical debt

Existing 7 failures/9 errors, preexisting sales migration drift and frontend bundle-size warning remain tracked repository debt. Full production rollout still needs the deployment environment's backup and change-management process. A local PostgreSQL smoke test does not replace site-specific capacity/security/backup acceptance. Bulk staff deactivation must use supported model-save paths so School reference cleanup signals run.

## 20. Final readiness decision

**Ready for Phase 3: YES**, under the user's Phase 2 verification criteria. PostgreSQL migrations/constraints/concurrency, campus and tenant security, principal/academic integrity, real-browser CRUD, responsive and accessibility smoke, production build and no-new-regressions comparison passed.

Final frontend results: **24 passed**, 4 files; TypeScript/Vite production build passed (11.68 seconds, bundle-size warning only). Backend final targeted suite: **69 passed, zero skipped**. Full-suite existing debt remains explicit; this is not a claim that the entire ERP suite is green.

**STOP.** Phase 3 was not started. Wait for the user's explicit `PROCEED TO PHASE 3`.

### Reproducible artifacts

- `backend/config/settings/school_verification.py`: isolated PostgreSQL settings, explicit UTF8.
- `backend/tests/unit/test_school_postgresql.py`: concurrency, atomicity, catalog and HTTP security gates.
- `backend/tests/unit/test_school_migrations.py`: multi-tenant upgrade/reverse/re-upgrade verification.
- `backend/tests/verification/seed_school_browser.py` and `school_query_probe.py`: guarded disposable fixtures/probe.
- `frontend/tests/school/verify.mjs`, `ux.mjs`, `README.md`: runnable browser checks and setup steps.
- `docs/school/verification/`: durable reports, query plans and representative screenshots. Temporary JWTs are excluded.

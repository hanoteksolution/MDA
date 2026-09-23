# School completion matrix

Updated 2026-09-21. [Phase 4 report](SCHOOL_PHASE_4_IMPLEMENTATION.md) records the current gate; [Phase 3 report](SCHOOL_PHASE_3_IMPLEMENTATION.md) is the SIS baseline; [Phase 2 verification](SCHOOL_PHASE_2_VERIFICATION.md) remains the foundation baseline. The user's Phase 2 scope supersedes the older roadmap numbering. [Full implementation report](SCHOOL_PHASE_2_IMPLEMENTATION.md) records evidence and limitations.

| Area | Implementation | Verification |
|---|---|---|
| Profile and logo | Implemented | API validation and real-browser upload passed |
| Campus architecture and access | Implemented using shared Branch/User | Scoped CRUD, grants/revokes and IDOR tested |
| Principal/teacher references | Implemented | Tenant, eligibility, campus and deactivation tested |
| Academic years/terms | Implemented | PostgreSQL lifecycle/date/current/overlap/concurrency passed |
| Levels/classes/sections/shifts | Implemented | API CRUD, relationships, capacity and lifecycle tested |
| Subjects/categories/offerings | Implemented | CRUD, references and nullable-scope uniqueness tested |
| Permissions and audit | Implemented | Action denial, alias revocation and audit snapshots tested |
| Navigation and dashboard | Implemented for foundation only | Frontend tests/build and Chromium smoke passed |
| Dedicated list/new/detail/edit | Implemented | Component/config and browser CRUD/keyboard checks passed |
| Database migration | Implemented | PostgreSQL multi-tenant upgrade/reverse/re-upgrade passed |
| Shared regression safety | Comparison performed | Same 7 failures/9 errors reproduced with shared changes reverted |
| Phase 2 verification | Passed | PostgreSQL and Chromium release gates passed; production deployment not performed |
| Phase 3 | Implemented | PostgreSQL lifecycle/concurrency/migration, frontend and live-browser gate in Phase 3 report |
| Phase 4 | Implemented | PostgreSQL concurrency/migration, frontend, live-browser and regression gate in Phase 4 report |
| Phase 5 | Assignments, weighted assessments, moderated publication, report versions and promotion implemented | **PASS**: SQLite 22, PostgreSQL 24, frontend 128, build/Chromium passed; full regression 889 passed, same 7 failures/9 errors, **0 new regressions** — [report](SCHOOL_PHASE_5_IMPLEMENTATION.md) |

Phase 6 adds fee structures, discounts and shared non-stock billing with allocation, adjustments and reconciliation. Its targeted, PostgreSQL, frontend/build and browser evidence is saved; the final regression gate is pending. See [Phase 6 report](SCHOOL_PHASE_6_IMPLEMENTATION.md). Payroll, portals, AI/automation and deferred imports remain outside this phase.

**STOP at the Phase 6 gate. Do not start Phase 7.**

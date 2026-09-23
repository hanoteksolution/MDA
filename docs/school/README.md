# School Management — Documentation Index

School Management documentation. The dated Phase 1 audit is the baseline; Phase 2 remains the verified foundation. See the Phase 3 report for the resumed admissions/student work and its gate.

## Documents

| Document | Purpose |
|---|---|
| [Phase 5 implementation and gate](SCHOOL_PHASE_5_IMPLEMENTATION.md) | Assignments, results, report versions and promotion evidence |
| [Phase 6 implementation and gate](SCHOOL_PHASE_6_IMPLEMENTATION.md) | Fees, shared billing and reconciliation evidence |
| [Frontend restructure](SCHOOL_FRONTEND_RESTRUCTURE.md) | Grouped sidebar navigation, canonical DataTable pages, dashboard, backend gaps |
| [Phase 3 implementation and gate](SCHOOL_PHASE_3_IMPLEMENTATION.md) | Admissions, student administration and targeted verification |
| [Phase 2 verification report](SCHOOL_PHASE_2_VERIFICATION.md) | PostgreSQL/Chromium evidence, hardening and current readiness decision |
| [Phase 2 implementation report](SCHOOL_PHASE_2_IMPLEMENTATION.md) | Delivered foundation, test evidence and open release gates |
| [Phase 1 audit](SCHOOL_PHASE_1_AUDIT_2026-09-11.md) | Authoritative baseline |
| [SCHOOL_CURRENT_STATE_AUDIT.md](./SCHOOL_CURRENT_STATE_AUDIT.md) | What exists in the repo today; KEEP/EXTEND/CREATE classification |
| [SCHOOL_ARCHITECTURE.md](./SCHOOL_ARCHITECTURE.md) | Workspace architecture, layer model, integration rules |
| [SCHOOL_DATABASE_ERD.md](./SCHOOL_DATABASE_ERD.md) | Target entity model and relationships |
| [SCHOOL_CRUD_MATRIX.md](./SCHOOL_CRUD_MATRIX.md) | Required CRUD operations per entity |
| [SCHOOL_API_MATRIX.md](./SCHOOL_API_MATRIX.md) | REST API endpoint catalog |
| [SCHOOL_PERMISSION_MATRIX.md](./SCHOOL_PERMISSION_MATRIX.md) | Permissions and role bundles |
| [SCHOOL_ACCOUNTING_INTEGRATION.md](./SCHOOL_ACCOUNTING_INTEGRATION.md) | Central accounting event types and GL mappings |
| [SCHOOL_REPORTING_MATRIX.md](./SCHOOL_REPORTING_MATRIX.md) | Reports and dashboard widgets |
| [SCHOOL_MOBILE_ARCHITECTURE.md](./SCHOOL_MOBILE_ARCHITECTURE.md) | React Native parent/teacher/student apps |
| [SCHOOL_TEST_MATRIX.md](./SCHOOL_TEST_MATRIX.md) | Test cases and E2E workflows |
| [SCHOOL_COMPLETION_MATRIX.md](./SCHOOL_COMPLETION_MATRIX.md) | Current delivery and verification tracking |

## Stack Reality Check

| Spec mentions | Actual in repo |
|---|---|
| Next.js | **React + Vite + TypeScript** (`frontend/`) |
| Django + DRF | ✅ `backend/` |
| PostgreSQL | ✅ |
| React Native | ✅ `mobile/staff`, `mobile/gym-member` |

## Implementation Order

Phase 2 foundation and verification gates passed. Phase 3 (admissions/SIS) and Phase 4 (teaching staff, timetable, attendance) were each authorized on 2026-09-21; see `SCHOOL_PHASE_3_IMPLEMENTATION.md` and `SCHOOL_PHASE_4_IMPLEMENTATION.md` for scope, evidence and limitations. Phase 5 subsequently passed and Phase 6 was authorized; see `SCHOOL_PHASE_6_IMPLEMENTATION.md` for the current gate. Stop at Phase 6; do not start Phase 7. Earlier future-plan sections describe intended scope, not delivered features.

## Reference Modules

- **Gym** — member lifecycle, attendance, plans → invoice, mobile portal
- **Housing** — recurring charges → invoice
- **Projects** — large workspace with many sub-pages
- **Travel** — CRUD factory for many entities

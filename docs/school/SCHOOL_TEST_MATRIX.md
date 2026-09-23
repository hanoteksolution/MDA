## Phase 2 verification completed — 2026-09-13

See [verification report](SCHOOL_PHASE_2_VERIFICATION.md): 69 targeted PostgreSQL/RBAC tests passed with no skips; 24 frontend tests and production build passed; 49 Chromium CRUD and 21 UX checks passed, including 15 responsive cases and eight zero-violation axe scans. Full PostgreSQL regression: 511 passed with the exact same 7 failures/9 errors as baseline. Earlier pending notes below are historical.

## Phase 2 executable verification — 2026-09-12

Current executable tests: `backend/tests/unit/test_school_foundation.py`, `test_school_migrations.py`, and `frontend/src/modules/school/foundation.test.ts`. Final command results and limitations are recorded in [SCHOOL_PHASE_2_IMPLEMENTATION.md](SCHOOL_PHASE_2_IMPLEMENTATION.md).

| Area | Coverage |
|---|---|
| Profile/principal | Same-tenant eligible staff; unrelated tenant/pharmacy rejection; active campus assignment; deactivation clearing; profile restore; currency/timezone/enum validation |
| Campus | CRUD, multi-campus grants, default-campus revocation, tenant/campus IDOR, all-campus policy |
| Calendar | CRUD, strict dates, current uniqueness, separate campus currents, lifecycle, audit snapshots, term/exam bounds, parent-edit containment, overlap policy |
| Academic masters | API list/create/detail/edit/archive/restore for every master, marks/capacity/relationship validation, scoped offerings, duplicate offerings |
| Permissions | Action denial, read-only behavior, explicit revocation versus legacy alias, module disabled, missing context, safe lookup identities |
| API/performance | Search/filter/sort/pagination errors, malformed JSON, bounded lookup paging, no per-row calendar query growth |
| Migration | Upgrade preexisting School rows retaining IDs/name/dates and backfilling code/sequence |
| Frontend | Typed payload allowlist, optional references, lifecycle permission visibility, disabled immutable fields, rendered label/error associations and responsive grid classes |
| Regression | Existing RBAC/module/tenancy/journal tests, broader backend suite and complete frontend test/build runs |

SQLite checks are not PostgreSQL concurrency proof. PostgreSQL test setup requires process ownership unavailable in the sandbox; the escalation request was declined. Real-browser keyboard/focus/mobile checks are a release gate, not claimed by server-rendered component tests.

---

## Historical future test plan (a plan is not executable coverage)

# School Management — Test Matrix

**Date:** 2026-09-01  
**Framework:** Django `pytest` (backend), `vitest` (frontend), manual E2E workflows

Status key: `REQ` = required before phase sign-off

---

## Unit Tests (Backend Services)

### Academic structure

| Test | Phase | REQ |
|---|---|---|
| Create academic year with valid dates | 3 | ✓ |
| Reject overlapping academic years (same branch) | 3 | ✓ |
| Only one `is_current` year per branch | 3 | ✓ |
| Close year prevents new enrollments | 3 | ✓ |
| Term dates within year bounds | 3 | ✓ |

### Admissions

| Test | Phase | REQ |
|---|---|---|
| Create applicant with required fields | 4 | ✓ |
| Valid status transitions (application → accepted) | 4 | ✓ |
| Reject invalid transition (rejected → enrolled) | 4 | ✓ |
| Enroll applicant creates student + enrollment | 4 | ✓ |
| Applicant data copied without duplication | 4 | ✓ |
| Document upload validation (type, size) | 4 | ✓ |

### Students & Guardians

| Test | Phase | REQ |
|---|---|---|
| Unique student_number per tenant | 5 | ✓ |
| Guardian linked to multiple students | 5 | ✓ |
| Student linked to multiple guardians | 5 | ✓ |
| Status change audited | 5 | ✓ |
| Archive student preserves enrollment history | 5 | ✓ |
| Import validates rows before commit | 5 | ✓ |

### Timetable

| Test | Phase | REQ |
|---|---|---|
| Detect teacher double-booking | 7 | ✓ |
| Detect room double-booking | 7 | ✓ |
| Detect class period overlap | 7 | ✓ |
| Allow valid non-overlapping entries | 7 | ✓ |

### Attendance

| Test | Phase | REQ |
|---|---|---|
| Bulk class attendance save | 8 | ✓ |
| Attendance correction workflow | 8 | ✓ |
| Parent notification on absence trigger | 8 | ✓ |
| Cannot record for wrong academic year | 8 | ✓ |

### Examinations & Marks

| Test | Phase | REQ |
|---|---|---|
| Marks within 0..max_marks | 9 | ✓ |
| Grade auto-calculated from scale | 9 | ✓ |
| Draft → submit → lock workflow | 9 | ✓ |
| Locked marks reject edit without reopen perm | 9 | ✓ |
| Bulk import validates student in class | 9 | ✓ |

### Report Cards & Promotion

| Test | Phase | REQ |
|---|---|---|
| Report card aggregates marks + attendance | 10 | ✓ |
| Promotion creates new enrollment, keeps history | 10 | ✓ |
| Bulk promotion preview matches commit | 10 | ✓ |
| Repeat year does not delete old enrollment | 10 | ✓ |

### Fees & Accounting

| Test | Phase | REQ |
|---|---|---|
| Fee structure generates correct assignment amounts | 12 | ✓ |
| Scholarship reduces net amount | 12 | ✓ |
| Invoice creation from assignment | 12 | ✓ |
| `SCHOOL_FEE_INVOICED` journal balances | 12 | ✓ |
| Payment reduces AR | 12 | ✓ |
| Idempotent posting (no duplicate journals) | 12 | ✓ |
| Partial payment supported | 12 | ✓ |
| Refund posts correct reversal | 12 | ✓ |

### Transport & Library

| Test | Phase | REQ |
|---|---|---|
| Student route assignment | 13 | ✓ |
| Transport fee links to fee structure | 13 | ✓ |
| Book borrow/return lifecycle | 13 | ✓ |
| Overdue fine calculation | 13 | ✓ |

---

## API / Integration Tests

| Test | REQ |
|---|---|
| Unauthenticated → 401 | ✓ |
| Missing `school` module → 403 | ✓ |
| Missing permission → 403 | ✓ |
| Tenant A cannot read Tenant B students | ✓ |
| Parent can only read linked children | ✓ |
| Student can only read own record | ✓ |
| Teacher marks scoped to assigned class | ✓ |
| Pagination on list endpoints | ✓ |
| Soft delete excludes from default list | ✓ |
| Restore endpoint works | ✓ |

---

## Permission Tests

| Scenario | Expected | REQ |
|---|---|---|
| Parent lists students | Only linked children | ✓ |
| Parent GET other student by ID | 404 or 403 | ✓ |
| Teacher enters marks for unassigned class | 403 | ✓ |
| Receptionist cannot lock marks | 403 | ✓ |
| Exam officer can lock marks | 200 | ✓ |
| Finance officer generates invoice | 200 | ✓ |
| Teacher cannot receive payment | 403 | ✓ |
| Student views unpublished results | Hidden | ✓ |

---

## Frontend Tests (Vitest + RTL)

| Area | Tests | REQ |
|---|---|---|
| School dashboard renders KPIs | mock API | ○ |
| Student list DataTable search/filter | component | ○ |
| Create student form validation | component | ✓ |
| Admission pipeline status buttons | component | ✓ |
| Marks bulk entry grid | component | ✓ |
| Fee invoice generation flow | integration mock | ✓ |
| Permission-gated action buttons hidden | component | ✓ |

---

## E2E Workflows (Critical Paths)

### Workflow 1: Admission to enrolled student

```
Applicant created
  → documents uploaded
  → status: accepted
  → enroll action
  → Student record exists
  → Enrollment in correct class/section
  → Fee assignment created
```

### Workflow 2: Fee to accounting

```
Fee structure defined
  → bulk assign to class
  → generate invoices
  → journal posted (DR AR / CR Revenue)
  → payment recorded
  → journal posted (DR Cash / CR AR)
  → receipt PDF available
```

### Workflow 3: Academic term cycle

```
Attendance recorded daily
  → Exam scheduled
  → Marks entered (bulk)
  → Marks submitted & locked
  → Report card generated
  → Promotion preview
  → Promotion committed
  → New enrollment for next year
```

### Workflow 4: Teacher daily ops

```
Teacher logs in (mobile)
  → views today's class
  → records bulk attendance
  → enters marks for quiz
  → assigns homework
  → parent receives notification
```

### Workflow 5: Parent portal

```
Parent logs in
  → sees only own children
  → views attendance for child A
  → cannot access child B (not linked)
  → views fee balance
  → views published report card
```

---

## Performance Tests

| Scenario | Target | Phase |
|---|---|---|
| Student list (1000 students) | < 500ms API | 38 |
| Bulk attendance save (40 students) | < 1s | 38 |
| Bulk marks import (200 rows) | < 3s | 38 |
| Report card PDF batch (30 students) | < 30s async | 38 |

---

## Security Tests

| Test | REQ |
|---|---|
| IDOR on student detail | ✓ |
| IDOR on invoice/payment | ✓ |
| Cross-branch access without permission | ✓ |
| SQL injection on search params | ✓ |
| File upload path traversal | ✓ |
| XSS in announcement content | ✓ |

---

## Test File Locations (Target)

```
backend/tests/unit/school/
├── test_academic_service.py
├── test_admission_service.py
├── test_student_service.py
├── test_attendance_service.py
├── test_examination_service.py
├── test_fee_service.py
├── test_fee_posting_service.py
├── test_promotion_service.py
├── test_timetable_service.py
├── test_permissions.py
└── test_tenant_isolation.py

backend/tests/integration/school/
├── test_admission_to_student_e2e.py
├── test_fee_accounting_e2e.py
└── test_parent_portal_scope.py

frontend/src/modules/school/__tests__/
├── StudentList.test.tsx
├── AdmissionForm.test.tsx
└── MarksEntry.test.tsx
```

---

## Related Documents

- `SCHOOL_COMPLETION_MATRIX.md`
- `docs/TESTING.md`
- `SCHOOL_PERMISSION_MATRIX.md`

## Phase 5 implementation evidence (2026-09-21)

The authoritative Phase 1 audit §N numbering applies. Exams/marks and report-card/promotion requirements above are exercised by `test_school_learning.py` (22 tests), `test_school_learning_postgresql.py` (concurrent HTTP commands and migration gate), `sis/learning.test.ts`, and the live Chromium academic cycle. See [Phase 5 evidence](SCHOOL_PHASE_5_IMPLEMENTATION.md) for gate results, exact regression comparison and limitations. Later-phase requirements remain deferred.

## Phase 6 implementation evidence (2026-09-22)

The authoritative Phase 1 audit §N row 6 applies. Fee structures, approved discounts, non-stock invoices, receipts/advances, bounded allocations, credits/refunds/reversals and source-matched AR/GL reconciliation are covered by `test_school_fees.py`; PostgreSQL concurrency and migration preservation by `test_school_fees_postgresql.py`. Frontend contracts are covered by `sis/fees.test.ts`; the production Chromium cycle covers scholarship approval through posted reconciliation, invalid cross-campus selection/amounts, printable receipts, responsive views and teacher denial. Existing finance/POS/Branch/tax tests cover shared-foundation preservation. See [Phase 6 evidence](SCHOOL_PHASE_6_IMPLEMENTATION.md). Gate pending final full regression and exact baseline comparison; no Phase 7 work.

## Phase 2 implemented architecture — 2026-09-12

The current implementation extends the existing School app. See [implementation and validation report](SCHOOL_PHASE_2_IMPLEMENTATION.md) for the authoritative Phase 2 scope and release limits. Content below the historical-plan divider describes future work unless explicitly delivered here.

- Tenant is the security boundary; shared Company/Branch remains the organization/campus hierarchy. No second location or employee identity system was added.
- AcademicYear is campus-owned; one current active year per tenant/campus. Codes are tenant-unique and retained after archive. EducationLevel, Subject and SubjectCategory are reusable tenant catalogs; writes require their explicit resource permissions.
- SchoolClass represents a grade at a campus; Section represents a stream within that class. There is no duplicate Grade entity. Rooms are descriptive references, not a timetable/room-booking engine.
- SubjectOffering links year, optional term, campus, class, optional section, subject and optional eligible shared User. Four partial unique constraints cover nullable term/section combinations.
- Teacher/principal eligibility uses explicit permissions on shared User; no new employee master, full teacher management or HR/payroll implementation is introduced.
- SchoolAccess centralizes validated actor/tenant, module dependency, campus and permission checks. Default User.branch access plus SchoolCampusAccess grants/revokes represent specific campuses; `school.campus.all` grants all campuses within the acting tenant.
- AcademicStructureService validates relationships/dates/references. FoundationService performs atomic writes, tenant-row locking, workflow transitions and before/after audit snapshots. Serializers validate request fields; repositories build scoped optimized queries.
- Frontend uses existing PageLayout/FormSection/DataTable/Radix components, typed resource configuration and dedicated list/new/detail/edit routes. Financial and later-phase features remain outside School navigation.
- The earlier audit described `finance` as a School module dependency. Execution proved that code is absent from MODULE_SEEDS; finance is shared infrastructure. School now depends on `sales`; the School business preset uses school/sales/inventory. No accounting engine was changed.

---

## Historical target plan (not a completion claim)

# School Management — Architecture

**Date:** 2026-09-01  
**Phase:** 1–2  
**Status:** Approved design (pre-implementation)

---

## Vision

School Management is a **complete industry-specific business workspace** inside Safari ERP. It must feel like a standalone premium School ERP while using shared platform services for IAM, accounting, notifications, documents, audit, and multi-tenancy.

```
SCHOOL WORKSPACE (/school/*)
│
├── Admissions ── Students ── Guardians
├── Academics (years, terms, classes, subjects, curriculum)
├── Teachers / Staff (profile extension on User)
├── Timetable ── Attendance
├── Examinations ── Marks ── Grades ── Report Cards ── Promotion
├── Fees ── Invoices ── Payments ── Scholarships
├── Transport ── Library ── Inventory (uniforms/supplies)
├── Events ── Communication ── Documents ── ID Cards ── Certificates
├── Reports ── Dashboard ── Settings
│
▼
SHARED SAFARI ERP PLATFORM
├── IAM (Users, Roles, Permissions)
├── Central Accounting Engine
├── Sales / Invoices / Payments
├── Inventory / Purchases
├── Notifications
├── Documents (shared engine)
├── Audit
├── Branches
└── Multi-Tenancy / Module Entitlements
```

---

## Architectural Rules (Non-Negotiable)

1. **One ledger** — All school money flows through `apps.finance`; no school-specific GL.
2. **One identity system** — Parents, teachers, students use `apps.authentication.User` with roles; no duplicate auth.
3. **Tenant + branch scope** — Every school entity extends `TenantScopedModel`; campus = `Branch`.
4. **Backend authority** — State transitions, fee calculations, mark locking, promotion rules enforced in services.
5. **No placeholder UI** — No "Coming Soon" routes or dead buttons in production paths.
6. **Module gated** — API paths under `/api/v1/school/` require `school` module entitlement.
7. **Audit everything material** — Student status, marks, fees, discipline via `write_audit`.

---

## Layer Model

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend workspace (React + Vite)                               │
│  /school/* — Dashboard, CRUD pages, portals                      │
│  frontend/src/modules/school/                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST /api/v1/school/*
┌────────────────────────────▼────────────────────────────────────┐
│  API layer                                                       │
│  backend/api/v1/school/                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Domain app: apps.school                                         │
│  models · services · serializers · permissions · signals         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Shared engines (composition, not duplication)                   │
│  sales · finance · inventory · notifications · audit · settings  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Django App Structure (Target)

```
backend/apps/school/
├── models/
│   ├── profile.py          # SchoolProfile (settings per tenant/branch)
│   ├── academic.py         # AcademicYear, Term, GradeLevel, Section, Subject
│   ├── enrollment.py       # Student, StudentEnrollment, Guardian, GuardianStudent
│   ├── admission.py        # Applicant, AdmissionDocument
│   ├── staff.py            # SchoolStaffProfile, TeacherAssignment
│   ├── timetable.py        # Period, Timetable, TimetableEntry, Room
│   ├── attendance.py       # StudentAttendance, StaffAttendance (overlay)
│   ├── examination.py      # Exam, ExamSchedule, MarkEntry, GradeScale, ReportCard
│   ├── fees.py             # FeeType, FeeStructure, StudentFeeAssignment, Scholarship
│   ├── homework.py         # Homework, Assignment, Submission
│   ├── discipline.py       # BehaviorRecord, DisciplineIncident
│   ├── transport.py        # Vehicle, Route, Stop, StudentRouteAssignment
│   └── library.py          # Book, BookCopy, Borrowing, Fine
├── services/
│   ├── admission_service.py
│   ├── student_service.py
│   ├── academic_service.py
│   ├── attendance_service.py
│   ├── examination_service.py
│   ├── fee_service.py          # → sales.Invoice
│   ├── fee_posting_service.py  # → finance.AccountingPostingService
│   ├── promotion_service.py
│   ├── timetable_service.py
│   ├── transport_service.py
│   ├── library_service.py
│   └── report_card_service.py
├── serializers/
├── admin.py
└── apps.py
```

---

## Module Registration

### `MODULE_SEEDS` entry (target)

```text
code: school
name: School Management
category: industry
route: /school
dependencies: [sales, finance]
optional_dependencies: [inventory, purchases]
supports_mobile: true
supports_pos: false
display_order: 45
```

### API path gate

```python
("/api/v1/school/", "school")
```

### Business type seed

```text
code: school
name: School / Education
default_modules: [school, sales, finance, inventory]
```

---

## Frontend Workspace Integration

| File | Change |
|---|---|
| `navigation/moduleWorkspaces.ts` | Add `school` workspace card |
| `navigation/businessWorkspaces.ts` | Add to `INDUSTRY_PATH_CODES`, nav order, features |
| `app/router.tsx` | `/school` route + PermissionGuard |
| `app/workspaceRoutes.tsx` | Feature routes + capability routes |
| `modules/school/pages/` | Dashboard + entity pages |
| `services/api/school.ts` | Typed API client |

### Navigation skeleton

```
/school                     Dashboard
/school/admissions          Applicant list
/school/students            Student list
/school/students/:id        Student detail (tabs)
/school/guardians           Guardian list
/school/academics           Academic years / terms / classes
/school/teachers            Staff list
/school/timetable           Timetable views
/school/attendance          Attendance entry
/school/exams               Examination management
/school/fees                Fee structures + invoices
/school/transport           Routes & assignments
/school/library             Books & borrowing
/school/events              Calendar
/school/reports             School reports
/school/settings            School profile & config
/school/finance             → shared FinancePage (scoped)
/school/inventory           → shared InventoryPage (scoped)
```

---

## Key Domain Concepts

### Student vs Applicant

- **Applicant** — pre-enrollment pipeline entity
- **Student** — created on enrollment; retains link to applicant
- **StudentEnrollment** — historical class/section/year assignments (never destroy on promotion)

### Guardian vs Customer

- **Guardian** — school-specific; M2M with students; portal access scoped to linked children
- **Customer** — NOT used for parents

### Teacher vs User

- **User** — authentication identity
- **SchoolStaffProfile** — teacher code, qualifications, employment type
- **TeacherSubjectAssignment** — which subjects/classes a teacher handles
- Future: merge into `hrm.Employee` when HR module ships

### Fees vs Invoices

- **FeeStructure** — defines what to charge (by year/term/class)
- **StudentFeeAssignment** — what a student owes
- **Invoice** (`apps.sales`) — billing document; school adds FK `student_fee_assignment_id`
- **Payment** — standard sales payment → GL via posting service

---

## Academic Year Context

All operational records carry:

- `academic_year_id`
- `term_id` (where applicable)
- `branch_id`

Middleware or service layer validates that writes target the **active** or explicitly selected academic year. Only one `is_current=True` per branch unless configured otherwise.

---

## Portal Architecture

| Portal | Role slugs | Data scope |
|---|---|---|
| Parent | `school_parent` | Linked students only |
| Student | `school_student` | Own record only |
| Teacher | `school_teacher` | Assigned classes/subjects |
| Admin | `school_admin`, `principal` | Branch/tenant per permissions |

Enforcement: queryset filtering in services + permission checks + tests for IDOR.

---

## Service Layer Pattern

Follow gym/housing pattern:

```python
class StudentService:
    @staticmethod
    def create_student(*, data, user, tenant, branch):
        # validate → persist → audit → optional side effects
        write_audit(...)
        return student
```

Fee invoicing:

```python
class SchoolFeeService:
    @staticmethod
    def generate_invoice(*, assignment, user):
        invoice = Invoice.objects.create(...)  # sales app
        FeePostingService.post_fee_invoice(invoice)  # finance app
        return invoice
```

---

## Implementation Phases (Ordered)

| Phase | Deliverable |
|---|---|
| 1 | Audit + architecture docs (this document) |
| 2 | School profile + settings |
| 3 | Academic years, terms, classes, sections, subjects |
| 4 | Admissions + applicant workflow |
| 5 | Students + guardians |
| 6 | Teachers / staff profiles |
| 7 | Timetable |
| 8 | Attendance |
| 9 | Examinations + marks + grading |
| 10 | Report cards + promotion |
| 11 | Homework + discipline |
| 12 | Fee structures + invoicing + payments + GL |
| 13 | Transport + library |
| 14 | Events + communication |
| 15 | Documents + ID cards + certificates |
| 16 | Reports + dashboard |
| 17 | Parent / student / teacher portals |
| 18 | React Native integration |
| 19 | Security hardening + test suite |

---

## Non-Goals (This Module)

- Rebuilding IAM, notifications, or reporting engines
- Independent school accounting subsystem
- Full HRM replacement (defer to future `hrm` module)
- LMS replacement (video courses, SCORM) — homework/assignments only

---

## Related Documents

- `SCHOOL_CURRENT_STATE_AUDIT.md` — what exists today
- `SCHOOL_DATABASE_ERD.md` — entity relationships
- `SCHOOL_ACCOUNTING_INTEGRATION.md` — GL mappings
- `SCHOOL_COMPLETION_MATRIX.md` — delivery tracking

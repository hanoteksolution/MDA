# School Management — Current State Audit

**Date:** 2026-09-01  
**Phase:** 1 — Audit Existing ERP  
**Status:** Complete  
**Repository:** `/home/ubuntu/projects/mda`

---

## Executive Summary

Safari ERP (MDA) has **no School Management module** today. The platform provides mature multi-tenancy, IAM, central accounting, sales/invoicing, branches, notifications, audit, and several industry workspaces (gym, hotel, restaurant, projects, travel, housing) that serve as **reference patterns** for building School as a business workspace.

**Classification:** School is **CREATE** (new vertical) with **EXTEND** on shared engines.

**Stack note:** Production frontend is **React + Vite + TypeScript** (not Next.js). Mobile is **React Native (Expo)** under `mobile/`.

---

## Audit Methodology

Inspected:

- `backend/apps/*` — Django apps, models, services
- `backend/api/v1/*` — REST endpoints
- `frontend/src/modules/*` — industry workspace UIs
- `frontend/src/navigation/*` — workspace registry
- `mobile/staff`, `mobile/gym-member` — React Native apps
- `docs/modular-erp/*`, `docs/accounting/*`, `docs/erp-transformation/*`
- Permission bootstrap, module seeds, finance event types

---

## Existing Shared Platform (KEEP — Do Not Rebuild)

| Capability | Location | School Usage |
|---|---|---|
| Multi-tenancy | `apps.platform`, `core.tenancy` | Tenant = school org; branch = campus |
| IAM / Users / Roles | `apps.authentication` | Teachers, staff, parents as users + roles |
| Permissions | `permissions.base`, `bootstrap.py` | Add `school.*` permission namespace |
| Branches | `apps.settings_app.Branch` | Multi-campus schools |
| Company / Settings | `apps.settings_app` | School profile overlay |
| Central Accounting | `apps.finance` | Fee revenue, payroll, expenses — ONE ledger |
| Sales / Invoices / Payments | `apps.sales` | Student fee invoices, receipts |
| Customers | `apps.customers` | Optional link for corporate sponsors only |
| Notifications | `apps.notifications` | Absence, fees, homework, exams |
| Audit | `apps.audit` | All school mutations |
| Documents (partial) | Vertical-specific + sales print | Extend for certificates, report cards |
| Reporting engine | `apps.reports`, finance reports | School report overlays |
| Module entitlements | `apps.platform` module_service | Register `school` module |
| Mobile bootstrap | `MobileNavService`, `/api/v1/mobile/` | Parent/teacher/student nav |

---

## Existing Vertical Patterns (REFERENCE — Copy Architecture)

| Vertical | Analog for School | Key Pattern |
|---|---|---|
| **Gym** | Students ≈ Members, Plans ≈ Fee structures | Tabbed workspace, member portal, attendance, subscriptions → invoice |
| **Hotel** | Guests ≈ Students (transient) | Reservations, folio charges → settlement invoice |
| **Housing Rental** | Lease charges ≈ Term fees | Recurring charges → invoice → payment → GL |
| **Projects** | Workforce ≈ Site payroll only | Daily wages (NOT org payroll) |
| **Travel** | Many CRUD entities | Dashboard + CRUD factory pages |
| **Restaurant** | Industry workspace composition | Shared POS/sales/inventory under workspace prefix |

---

## Functionality Classification Matrix

| Area | Classification | Notes |
|---|---|---|
| Multi-tenancy | **KEEP** | Use as-is |
| IAM / authentication | **KEEP** | Parent/teacher/student = roles on same User model |
| Branches | **KEEP** | Campus per branch |
| Central accounting | **KEEP** | Add school event types + mappings only |
| Sales invoices / payments | **EXTEND** | Link to `StudentFeeAssignment`, school fee types |
| Notifications | **EXTEND** | Add school event types |
| Audit logging | **KEEP** | Wire school services to `write_audit` |
| HR / Employee master | **CREATE** (future `hrm`) | Teacher = User + `SchoolStaffProfile`; no Employee model yet |
| Org payroll | **CREATE** (future `hrm`) | Reuse project wage pattern as interim; full payroll TBD |
| Staff evaluations | **KEEP** | `StaffEvaluation` in reports — extend for teachers |
| Inventory | **KEEP** | Uniforms, books, supplies via shared inventory |
| Documents | **EXTEND** | Certificates, report cards, admission docs |
| Library (school) | **CREATE** | Not gym exercise library |
| Transport | **CREATE** | No routes/vehicles today |
| Students | **CREATE** | |
| Guardians / parents | **CREATE** | Not `Customer` |
| Admissions | **CREATE** | |
| Academic structure | **CREATE** | Years, terms, classes, sections, subjects |
| Timetable | **CREATE** | |
| Attendance | **CREATE** | Gym attendance is member check-in only |
| Examinations / marks | **CREATE** | |
| Grading / report cards | **CREATE** | |
| Promotion | **CREATE** | |
| Homework / assignments | **CREATE** | |
| Discipline | **CREATE** | |
| Fee structures / scholarships | **CREATE** | Pattern from gym plans + housing charges |
| School module (Django app) | **CREATE** | `apps.school` |
| School API | **CREATE** | `/api/v1/school/` |
| School frontend workspace | **CREATE** | `frontend/src/modules/school/` |
| School mobile | **CREATE** | Parent/teacher/student apps |
| `school` business type | **CREATE** | In platform seeds |
| `school` module seed | **CREATE** | In `MODULE_SEEDS` |
| Customer as parent | **DEPRECATE** | Do not use Customer for guardians |
| Independent school ledger | **DEPRECATE** | Never create |
| Second auth system | **DEPRECATE** | Never create |

---

## What Exists Today (Detailed)

### Backend apps with school relevance

```
apps.authentication     — User, Role, Permission, StaffEvaluation
apps.settings_app       — Company, Branch, Setting
apps.sales              — Invoice, Payment, Expense, DocumentSequence
apps.finance            — GL, journals, posting rules, account mappings
apps.customers          — Customer (retail/wholesale/corporate only)
apps.notifications      — Notification (no school types)
apps.inventory          — Warehouse, Stock, Product
apps.purchases          — PurchaseOrder
apps.reports            — Staff performance, evaluations
apps.audit              — Audit trail
apps.platform           — Tenant, modules, business types, entitlements
apps.gym                — Closest member lifecycle reference
apps.housing_rental     — Closest fee/charge → invoice reference
apps.project_management — Site workforce wages only
```

### Finance integration points (existing)

- `AccountingPostingService` — central posting hub
- Event types: `GYM_MEMBERSHIP_SOLD`, `HOTEL_ROOM_CHARGED`, `PROJECT_INVOICE_ISSUED`, `CUSTOMER_INVOICE_POSTED`
- **No** `SCHOOL_FEE_INVOICED`, `TUITION_PAYMENT`, etc.

### Permissions pattern (existing)

Format: `{module}.{resource}.{action}` e.g. `gym.members.create`  
Enforcement: `HasPermission`, `HasModule`, `ModuleGateMiddleware`

### Frontend workspace pattern (existing)

- Registry: `navigation/moduleWorkspaces.ts`, `businessWorkspaces.ts`
- Routes: `app/workspaceRoutes.tsx`, `app/router.tsx`
- Industry prefix: `/gym/*`, `/hotel/*` — shared engines auto-mounted
- **No** `/school/*`

### Mobile (existing)

- `mobile/staff/` — workspace switcher per module
- `mobile/gym-member/` — member portal (reference for parent portal)
- **No** school screens

---

## Gaps (Must Create)

### Academic domain
- AcademicYear, Term, GradeLevel, Section, Subject, Curriculum
- ClassSubject, TeacherSubjectAssignment, Classroom
- Student, StudentEnrollment (history), Guardian, GuardianStudent link
- Admission / Applicant workflow

### Operations
- Timetable (Period, TimetableEntry, conflict validation)
- Student attendance (daily/class/subject)
- Exam engine (Exam, ExamSchedule, MarkEntry, GradeScale, ReportCard)
- Promotion workflow
- Homework, Assignment, Submission
- Discipline / behavior records

### Financial (school-specific overlay on shared engines)
- FeeType, FeeStructure, FeeStructureItem, StudentFeeAssignment
- Scholarship, Discount policies
- Invoice generation from fee structures (via `apps.sales.Invoice`)
- GL mappings for tuition, transport, uniform, etc.

### Support services
- Transport (Vehicle, Route, Stop, StudentRouteAssignment)
- Library (Book, BookCopy, Borrowing, Fine)
- Events / school calendar
- ID cards, certificates (templates + PDF)

### Portals
- Parent portal (child-scoped access)
- Student portal
- Teacher portal (class/subject scoped)

### HR note
Full HR/Payroll module (`hrm`) is listed as **future** in `MODULE_REGISTRY.md`. School teachers should use:
- **Phase 1:** `User` + `SchoolStaffProfile` extension
- **Phase 2:** Integrate when `hrm` module ships
- **Interim:** Staff attendance → project wage pattern if hourly; salaried via finance vouchers

---

## False Positives (Not School-Related)

| Term | Actual meaning in codebase |
|---|---|
| `library` | Gym exercise library (`Exercise` model) |
| `transport` | Expense category / GL account 6050 |
| `parent` | Finance account hierarchy, WBS tree |
| `fee` | Travel visa `fee_amount` |
| `teacher` | Not found; closest = `Trainer` (gym) |
| `class` | Gym class scheduling, not academic class |
| `student` | Zero matches |
| `HR & Payroll` (frontend nav) | Placeholder only — no backend |

---

## Recommended Reference Implementations

When implementing each school phase, primary code references:

| School feature | Reference code |
|---|---|
| Member/student CRUD + detail | `apps/gym`, `modules/gym/GymMemberFormPage.tsx` |
| Subscription/fee plan | `apps/gym/models/plan.py`, `MembershipPlan` |
| Charge → invoice | `apps/housing_rental`, `LeaseCharge` billing |
| Payment + GL posting | `apps/gym/services/gym_payment_service.py` |
| Tabbed workspace UI | `modules/gym/GymPage.tsx` |
| Many entity CRUD | `modules/travel/TravelCrudPages.tsx` |
| Module registration | `module_service.MODULE_SEEDS` (gym entry) |
| Permissions bootstrap | `authentication/bootstrap.py` (gym block) |
| Mobile member portal | `mobile/gym-member/`, `/api/v1/mobile/gym/` |
| Project completion docs | `docs/project-management/` |

---

## Risks & Constraints

1. **No org-wide HR/payroll** — School staff payroll must integrate with central finance; full payslip engine does not exist.
2. **Frontend is Vite/React** — All UI work uses existing SPA patterns, not Next.js App Router.
3. **Scope size** — 38+ phases; must ship incrementally with completion matrix tracking.
4. **Parent data privacy** — Guardian-child scoping is security-critical; no existing pattern except gym member self-access.
5. **Academic year locking** — Marks/fees/promotion need term/year context on all transactional tables.

---

## Phase 1 Exit Criteria

- [x] Repository audited
- [x] KEEP / EXTEND / CREATE / DEPRECATE classified
- [x] Reference patterns identified
- [x] Gaps documented
- [ ] Architecture sign-off (see `SCHOOL_ARCHITECTURE.md`)
- [ ] Completion matrix baseline (see `SCHOOL_COMPLETION_MATRIX.md`)

**Next phase:** School Profile + Academic Structure (Phases 2–6 per implementation order).

## Phase 2 delivered CRUD — 2026-09-12

| Resource | List/detail | Create | Edit | Archive | Restore | Workflow |
|---|---|---|---|---|---|---|
| Profile | Campus GET + form | Upsert | PUT/PATCH | Not exposed | Upsert preserves original row | Principal validation |
| Campus (Branch) | Yes | Yes | Yes | Deactivate with reference checks | Reactivate | Main campus |
| Academic year | Yes | Yes | Yes while open | Yes, dependency checked | Planning, not current | Activate/make-current, close |
| Term | Yes | Yes | Yes while open | Yes, dependency checked | Planning | Activate, close |
| Education level | Yes | Yes | Yes | Yes, dependency checked | Inactive | — |
| Class/grade | Yes | Yes | Yes | Yes, dependency checked | Inactive | Sections/subjects/activity detail tabs |
| Section | Yes | Yes | Yes | Yes, dependency checked | Inactive | — |
| Shift | Yes | Yes | Yes | Yes, dependency checked | Inactive | — |
| Subject category | Yes | Yes | Yes | Yes, dependency checked | Inactive | — |
| Subject | Yes | Yes | Yes | Yes, dependency checked | Inactive | — |
| Subject offering | Yes | Yes | Yes | Yes | Inactive | Nullable-scope uniqueness |
| Campus access | Yes | Yes | Enable/revoke | Soft archive grant | Restore grant | Explicit permission required |

Each resource has dedicated new/detail/edit screens, action-specific permissions and scoped API access. Profile is an intentionally single-campus settings form. School tables support server pagination, search, sorting, relevant relationship/status filters, column visibility and page-scoped print/PDF. Bulk actions are intentionally omitted where no meaningful safe bulk workflow exists in Phase 2.

---

## Historical future CRUD matrix

# School Management — CRUD Matrix

**Date:** 2026-09-01  
**Status:** Target (pre-implementation)

Legend: `✓` required | `—` N/A | `○` optional | `P` planned phase

---

## Master Data

| Entity | List | Create | Detail | Update | Delete/Archive | Restore | Duplicate | Activate | Import | Export | Bulk | Phase |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| School Profile | ✓ | — | ✓ | ✓ | — | — | — | — | — | — | — | 2 |
| Academic Year | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | — | ✓ set current | ○ | ✓ | — | 3 |
| Academic Term | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | — | — | ○ | ✓ | — | 3 |
| Grade Level / Class | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | ✓ | — | ✓ | ✓ | ✓ | 3 |
| Section | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | ✓ | — | ✓ | ✓ | ✓ | 3 |
| Subject | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | ✓ | — | ✓ | ✓ | ✓ | 3 |
| Curriculum | ✓ | ✓ | ✓ | ✓ | ✓ archive | — | ✓ | — | — | ✓ | — | 3 |
| Class Subject | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ | 3 |
| Classroom | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | — | — | ○ | ✓ | — | 3 |

---

## Admissions & Students

| Entity | List | Create | Detail | Update | Delete/Archive | Restore | Workflow | Import | Export | Bulk | Phase |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Applicant | ✓ | ✓ | ✓ | ✓ | ✓ cancel | — | ✓ pipeline | ✓ | ✓ | ✓ status | 4 |
| Admission Documents | — | ✓ upload | ✓ | ✓ verify | ✓ | — | ✓ review | — | — | — | 4 |
| Student | ✓ | ✓ | ✓ tabs | ✓ | ✓ archive | ✓ | ✓ status | ✓ | ✓ | ✓ promote | 5 |
| Student Enrollment | ✓ | ✓ | ✓ | ○ | — | — | ✓ history | — | ✓ | ✓ transfer | 5 |
| Guardian | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ | — | ✓ | ✓ | — | 5 |
| Guardian ↔ Student link | — | ✓ | ✓ | ✓ | ✓ unlink | — | — | ✓ | — | — | 5 |

### Student Detail Tabs (Phase 5+)

| Tab | View | Actions |
|---|---|---|
| Overview | ✓ | Edit, Print, ID card |
| Academic | ✓ | — |
| Attendance | ✓ | — |
| Examinations | ✓ | — |
| Marks | ✓ | — |
| Report Cards | ✓ | Generate PDF |
| Fees | ✓ | Generate invoice |
| Invoices | ✓ | Receive payment |
| Guardians | ✓ | Link/unlink |
| Transport | ✓ | Assign route |
| Library | ✓ | — |
| Discipline | ✓ | Add incident |
| Homework | ✓ | — |
| Documents | ✓ | Upload |
| Activity / Audit | ✓ | — |

---

## Staff & Teachers

| Entity | List | Create | Detail | Update | Delete/Archive | Import | Export | Phase |
|---|---|---|---|---|---|---|---|---|
| School Staff Profile | ✓ | ✓ | ✓ | ✓ | ✓ deactivate | ✓ | ✓ | 6 |
| Teacher Assignment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6 |
| Staff Attendance | ✓ | ✓ bulk | ✓ | ✓ correction | — | ○ | ✓ | 8 |

*Uses existing `User` for identity; no duplicate employee table until `hrm` module.*

---

## Timetable

| Entity | List | Create | Detail | Update | Delete | Views | Phase |
|---|---|---|---|---|---|---|---|
| Period | ✓ | ✓ | ✓ | ✓ | ✓ | — | 7 |
| Timetable | ✓ | ✓ | ✓ | ✓ | ✓ | class/teacher/room/school | 7 |
| Timetable Entry | ✓ | ✓ | ✓ | ✓ | ✓ | conflict warnings | 7 |

---

## Attendance

| Entity | List | Create | Detail | Update | Delete | Bulk | Mobile | Phase |
|---|---|---|---|---|---|---|---|---|
| Student Attendance | ✓ | ✓ daily/class | ✓ | ✓ correction | — | ✓ class | ✓ | 8 |
| Attendance Correction Request | ✓ | ✓ | ✓ | ✓ approve/deny | — | — | — | 8 |

---

## Examinations

| Entity | List | Create | Detail | Update | Delete | Workflow | Import | Phase |
|---|---|---|---|---|---|---|---|---|
| Exam Type | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | 9 |
| Exam | ✓ | ✓ | ✓ | ✓ | ✓ archive | ✓ publish | — | 9 |
| Exam Schedule | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | 9 |
| Grade Scale | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | 9 |
| Mark Entry | ✓ | ✓ bulk | ✓ | ✓ | — | draft→submit→lock | ✓ CSV | 9 |
| Report Card | ✓ | ✓ generate | ✓ | — | — | publish | — | 10 |
| Promotion Batch | ✓ | ✓ preview | ✓ | — | — | ✓ commit | — | 10 |

---

## Fees & Finance Overlay

| Entity | List | Create | Detail | Update | Delete | Workflow | Bulk | Phase |
|---|---|---|---|---|---|---|---|---|
| Fee Type | ✓ | ✓ | ✓ | ✓ | ✓ archive | — | — | 12 |
| Fee Structure | ✓ | ✓ | ✓ | ✓ | ✓ archive | — | ✓ duplicate | 12 |
| Student Fee Assignment | ✓ | ✓ auto | ✓ | ✓ | ✓ cancel | ✓ generate | ✓ bulk invoice | 12 |
| Scholarship / Discount | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ approve | ✓ apply | 12 |
| Invoice (shared) | ✓ | ✓ | ✓ | ✓ | ✓ void | draft→issued→paid | ✓ bulk | 12 |
| Payment (shared) | ✓ | ✓ | ✓ | — | ✓ refund | allocate | — | 12 |

---

## Homework & Discipline

| Entity | List | Create | Detail | Update | Delete | Phase |
|---|---|---|---|---|---|---|
| Homework | ✓ | ✓ | ✓ | ✓ | ✓ | 11 |
| Submission | ✓ | ✓ student | ✓ | ✓ grade | — | 11 |
| Discipline Incident | ✓ | ✓ | ✓ | ✓ | ✓ archive | 11 |

---

## Transport & Library

| Entity | List | Create | Detail | Update | Delete | Phase |
|---|---|---|---|---|---|---|
| Vehicle | ✓ | ✓ | ✓ | ✓ | ✓ archive | 13 |
| Route | ✓ | ✓ | ✓ | ✓ | ✓ archive | 13 |
| Route Stop | ✓ | ✓ | ✓ | ✓ | ✓ | 13 |
| Student Route Assignment | ✓ | ✓ | ✓ | ✓ | ✓ | 13 |
| Book | ✓ | ✓ | ✓ | ✓ | ✓ archive | 13 |
| Book Copy | ✓ | ✓ | ✓ | ✓ | ✓ | 13 |
| Borrowing | ✓ | ✓ borrow | ✓ | ✓ return/renew | — | 13 |

---

## Events & Documents

| Entity | List | Create | Detail | Update | Delete | Phase |
|---|---|---|---|---|---|---|
| School Event | ✓ | ✓ | ✓ | ✓ | ✓ | 14 |
| Announcement | ✓ | ✓ | ✓ | ✓ | ✓ | 14 |
| Certificate | ✓ | ✓ generate | ✓ | — | ✓ | 15 |
| ID Card | ✓ | ✓ generate | ✓ | — | — | 15 |
| Document (shared) | ✓ | ✓ upload | ✓ | ✓ | ✓ | 15 |

---

## UI Page Standards Checklist

Every Create page must include:

- [ ] Breadcrumb, title, description
- [ ] Form sections with required indicators
- [ ] Client + server validation
- [ ] Save / Save & New / Save & Close / Cancel
- [ ] Unsaved changes warning
- [ ] Loading, success, error feedback

Every List page must use `DataTable` with:

- [ ] Search, filters, sort, pagination
- [ ] Column visibility, export CSV/Excel, print
- [ ] Bulk selection + actions
- [ ] Loading shimmer, empty state, error state

---

## Related Documents

- `SCHOOL_API_MATRIX.md`
- `SCHOOL_COMPLETION_MATRIX.md`
- `SCHOOL_PERMISSION_MATRIX.md`

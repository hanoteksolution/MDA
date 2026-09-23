## Phase 2 implemented API — 2026-09-12

Current Phase 3 APIs are under `/api/v1/school/sis/`; see [the Phase 3 report](SCHOOL_PHASE_3_IMPLEMENTATION.md) and `api/v1/school/sis_urls.py`. Older future catalogs below are not a claim that their planned paths are implemented.
Base `/api/v1/school/`. Shared JWT, module/entitlement enforcement and response envelope remain in use.

| Path | Methods / purpose |
|---|---|
| `summary/` | GET real permission/campus-scoped foundation metrics |
| `capabilities/` | GET effective action permissions for frontend (including legacy alias/revoke rules) |
| `profile/?branch_id=UUID` | GET profile or null plus defaults; PUT/PATCH campus profile |
| `{resource}/` | GET paginated list, POST create |
| `{resource}/{id}/` | GET, PATCH/PUT, DELETE (archive only) |
| `{resource}/{id}/archive/` | POST archive |
| `{resource}/{id}/restore/` | POST restore |
| `academic-years/{id}/activate/`, `make-current/`, `close/` | POST controlled lifecycle |
| `terms/{id}/activate/`, `close/` | POST controlled lifecycle |
| `{resource}/{id}/activity/` | GET scoped paginated audit history |
| `lookups/campuses/`, `lookups/companies/` | GET authorized, paginated selectors |
| `lookups/teachers/`, `lookups/principals/`, `lookups/users/` | GET paginated same-tenant selectors; branch_id required; eligibility/campus scoped for staff; users requires campus-access permission |

Resources: campuses, academic-years, terms, levels, classes, sections, shifts, subjects, subject-categories, subject-offerings, campus-access. Calendar URL paths and legacy route names remain available. Unsupported resource/actions return 404 or validation errors; no arbitrary model access.

Query parameters: page >=1, page_size 1–100, bounded search, allowlisted ordering, archived=true, applicable status/is_current/is_active, branch_id, academic_year_id, education_level_id, school_class_id, section_id, subject_id, category_id, user_id. Campus restrictions always apply regardless of supplied filters. Empty foreign scope reads return no rows; unauthorized detail IDs return 404. Invalid fields, IDs and values return field-oriented 400 responses; denied actions return 403.

`POST /api/v1/school/profile/logo/?branch_id=<id>` validates and uploads a School logo through the shared media utility; requires profile.update and campus access.

---

## Historical proposed APIs (not implemented unless listed above)

# School Management — API Matrix

**Date:** 2026-09-01  
**Base path:** `/api/v1/school/`  
**Auth:** JWT + tenant context  
**Gate:** `school` module enabled

---

## Conventions

- List endpoints: `GET /resource/` — paginated (`page`, `page_size`, `search`, filters)
- Detail: `GET /resource/{id}/`
- Create: `POST /resource/`
- Update: `PATCH /resource/{id}/`
- Archive: `DELETE /resource/{id}/` (soft delete)
- Restore: `POST /resource/{id}/restore/`
- Actions: `POST /resource/{id}/{action}/`

Response envelope: `success_response` / `error_response` (existing pattern).

---

## Dashboard & Summary

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/school/summary/` | `school.view` | KPIs for dashboard |
| GET | `/school/quick-stats/` | `school.view` | Today's attendance, payments, alerts |

---

## School Profile & Settings

| Method | Path | Permission |
|---|---|---|
| GET | `/school/profile/` | `school.settings.view` |
| PATCH | `/school/profile/` | `school.settings.update` |
| GET | `/school/settings/{section}/` | `school.settings.view` |
| PATCH | `/school/settings/{section}/` | `school.settings.update` |

Sections: `general`, `academic`, `admissions`, `attendance`, `exams`, `grading`, `fees`, `invoice`, `receipt`, `report_card`, `id_card`, `transport`, `library`, `notifications`, `portals`

---

## Academic Structure

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET/POST | `/school/academic-years/` | view / create | |
| GET/PATCH/DELETE | `/school/academic-years/{id}/` | view / update / archive | |
| POST | `/school/academic-years/{id}/activate/` | `school.academic.activate` | Set current year |
| POST | `/school/academic-years/{id}/close/` | `school.academic.close` | |
| GET/POST | `/school/terms/` | view / create | Filter by year |
| GET/PATCH/DELETE | `/school/terms/{id}/` | view / update / archive | |
| GET/POST | `/school/grade-levels/` | view / create | |
| GET/PATCH/DELETE | `/school/grade-levels/{id}/` | view / update / archive | |
| GET/POST | `/school/sections/` | view / create | |
| GET/PATCH/DELETE | `/school/sections/{id}/` | view / update / archive | |
| GET/POST | `/school/subjects/` | view / create | |
| GET/PATCH/DELETE | `/school/subjects/{id}/` | view / update / archive | |
| GET/POST | `/school/class-subjects/` | view / create | |
| GET/POST | `/school/classrooms/` | view / create | |

---

## Admissions

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET/POST | `/school/applicants/` | view / create | |
| GET/PATCH | `/school/applicants/{id}/` | view / update | |
| POST | `/school/applicants/{id}/status/` | `school.admissions.approve` | Workflow transition |
| POST | `/school/applicants/{id}/enroll/` | `school.admissions.enroll` | Creates student |
| GET/POST | `/school/applicants/{id}/documents/` | view / create | Secure upload |
| POST | `/school/applicants/import/` | `school.admissions.import` | CSV import |
| GET | `/school/applicants/export/` | `school.admissions.view` | CSV export |

---

## Students & Guardians

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET/POST | `/school/students/` | view / create | |
| GET/PATCH/DELETE | `/school/students/{id}/` | view / update / archive | |
| POST | `/school/students/{id}/restore/` | update | |
| POST | `/school/students/{id}/transfer/` | `school.students.transfer` | |
| POST | `/school/students/{id}/suspend/` | `school.students.update` | |
| GET | `/school/students/{id}/overview/` | view | Detail aggregate |
| GET | `/school/students/{id}/enrollments/` | view | History |
| GET | `/school/students/{id}/attendance/` | `school.attendance.view` | |
| GET | `/school/students/{id}/marks/` | `school.marks.view` | |
| GET | `/school/students/{id}/fees/` | `school.fees.view` | |
| GET/POST | `/school/guardians/` | view / create | |
| GET/PATCH/DELETE | `/school/guardians/{id}/` | view / update / archive | |
| POST | `/school/guardians/{id}/link-student/` | update | |
| DELETE | `/school/guardians/{id}/students/{student_id}/` | update | Unlink |

---

## Staff & Teachers

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/staff/` | view / create |
| GET/PATCH/DELETE | `/school/staff/{id}/` | view / update / archive |
| GET/POST | `/school/teacher-assignments/` | view / create |
| GET/PATCH/DELETE | `/school/teacher-assignments/{id}/` | view / update / delete |
| GET | `/school/staff/{id}/timetable/` | view |
| GET | `/school/staff/{id}/classes/` | view |

---

## Timetable

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/periods/` | view / create |
| GET/POST | `/school/timetables/` | view / create |
| GET/PATCH/DELETE | `/school/timetables/{id}/` | view / update / delete |
| GET/POST | `/school/timetables/{id}/entries/` | view / create |
| POST | `/school/timetables/validate/` | create | Conflict check |
| GET | `/school/timetables/class/{section_id}/` | view |
| GET | `/school/timetables/teacher/{staff_id}/` | view |
| GET | `/school/timetables/room/{room_id}/` | view |

---

## Attendance

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/attendance/` | view / record |
| GET/PATCH | `/school/attendance/{id}/` | view / update |
| POST | `/school/attendance/bulk/` | `school.attendance.record` |
| POST | `/school/attendance/class/{section_id}/` | record | Class roll call |
| POST | `/school/attendance/{id}/correction/` | `school.attendance.correct` |

---

## Examinations

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/exams/` | view / create |
| GET/PATCH/DELETE | `/school/exams/{id}/` | view / update / archive |
| GET/POST | `/school/exam-schedules/` | view / create |
| GET/POST | `/school/grade-scales/` | view / create |
| GET/POST | `/school/marks/` | view / enter |
| POST | `/school/marks/bulk/` | `school.marks.enter` |
| POST | `/school/marks/submit/` | `school.marks.submit` |
| POST | `/school/marks/lock/` | `school.marks.lock` |
| POST | `/school/marks/reopen/` | `school.marks.reopen` |
| POST | `/school/marks/import/` | `school.marks.enter` |
| GET/POST | `/school/report-cards/` | view / generate |
| GET | `/school/report-cards/{id}/pdf/` | view |
| POST | `/school/promotions/preview/` | `school.promotion.manage` |
| POST | `/school/promotions/commit/` | `school.promotion.manage` |

---

## Fees & Payments (School + Shared)

| Method | Path | Permission | Engine |
|---|---|---|---|
| GET/POST | `/school/fee-types/` | view / create | school |
| GET/POST | `/school/fee-structures/` | view / create | school |
| GET/POST | `/school/fee-assignments/` | view / create | school |
| POST | `/school/fee-assignments/bulk-generate/` | `school.fees.invoice` | school |
| POST | `/school/fee-assignments/{id}/invoice/` | `school.fees.invoice` | → sales |
| GET/POST | `/school/scholarships/` | view / create | school |
| GET | `/school/invoices/` | `school.fees.view` | sales (filtered) |
| POST | `/school/invoices/{id}/payment/` | `school.fees.receive_payment` | sales + finance |
| GET | `/school/invoices/{id}/receipt/` | view | sales PDF |

---

## Homework & Discipline

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/homework/` | view / create |
| GET/PATCH/DELETE | `/school/homework/{id}/` | view / update / delete |
| POST | `/school/homework/{id}/submissions/` | student/parent submit |
| GET/POST | `/school/discipline/` | `school.discipline.view` / create |

---

## Transport & Library

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/vehicles/` | `school.transport.manage` |
| GET/POST | `/school/routes/` | `school.transport.manage` |
| GET/POST | `/school/student-routes/` | view / manage |
| GET/POST | `/school/books/` | `school.library.manage` |
| GET/POST | `/school/borrowings/` | view / manage |
| POST | `/school/borrowings/{id}/return/` | manage |

---

## Events & Communication

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/events/` | view / create |
| GET/POST | `/school/announcements/` | view / create |
| POST | `/school/announcements/{id}/publish/` | create |

---

## Documents & Certificates

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/school/students/{id}/documents/` | view / upload |
| POST | `/school/students/{id}/id-card/` | `school.id_cards.generate` |
| POST | `/school/certificates/generate/` | `school.certificates.generate` |
| GET | `/school/certificates/{id}/pdf/` | view |

---

## Reports

| Method | Path | Permission |
|---|---|---|
| GET | `/school/reports/enrollment/` | `school.reports.view` |
| GET | `/school/reports/attendance/` | view |
| GET | `/school/reports/fees/` | view |
| GET | `/school/reports/academic/` | view |
| GET | `/school/reports/transport/` | view |
| GET | `/school/reports/library/` | view |

---

## Mobile API (`/api/v1/mobile/school/`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/mobile/school/bootstrap/` | all | Nav + entitlements |
| GET | `/mobile/school/parent/home/` | parent | Children summary |
| GET | `/mobile/school/parent/children/{id}/attendance/` | parent | Scoped |
| GET | `/mobile/school/parent/children/{id}/fees/` | parent | Scoped |
| GET | `/mobile/school/student/home/` | student | Own dashboard |
| GET | `/mobile/school/teacher/classes/` | teacher | Assigned classes |
| POST | `/mobile/school/teacher/attendance/bulk/` | teacher | Class attendance |
| POST | `/mobile/school/teacher/marks/bulk/` | teacher | Marks entry |

---

## Shared Engine APIs (Reused, Not Duplicated)

| Capability | Existing path | School context |
|---|---|---|
| Finance GL | `/api/v1/finance/` | Scoped reports |
| Inventory | `/api/v1/inventory/` | Uniforms, supplies |
| Notifications | `/api/v1/notifications/` | School event types |
| Users | `/api/v1/users/` | Teacher/parent accounts |
| Branches | `/api/v1/settings/branches/` | Campuses |

---

## Related Documents

- `SCHOOL_PERMISSION_MATRIX.md`
- `SCHOOL_ARCHITECTURE.md`
- `SCHOOL_MOBILE_ARCHITECTURE.md`

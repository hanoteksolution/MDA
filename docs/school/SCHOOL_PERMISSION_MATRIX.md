## Phase 2 effective permissions — 2026-09-12

Backend catalog: `backend/apps/school/permissions.py`. Authorization never compares ordinary role names in domain services.

- Resources: campus, academic_year, term, level, class, section, shift, subject, subject_category, subject_offering, campus_access. Each uses `school.{resource}.{view|create|update|archive|restore}`.
- Academic year and term additionally use `activate` and `close`. `make-current` maps to academic_year.activate.
- Profile uses school.profile.view/update. Campus-wide access requires school.campus.all; this does not itself grant create/edit rights.
- Shared-user eligibility requires school.teacher.assignable or school.leadership.assignable plus active same-tenant user and access to the target campus.
- Specific campus access combines User.branch and SchoolCampusAccess grants. A nondeleted grant record with is_active=false revokes that campus, including default branch. All-campus permission overrides individual restrictions within the selected tenant.
- Legacy school.settings.view/update and school.academic.view/create/update/archive/activate remain narrow aliases only for existing profile/year/term operations. Explicit new-code revocation takes precedence over an alias. school.manage does not unlock all new resources.
- Presets: School Owner/Admin (all foundation capabilities/campuses); Principal/Academic Director/Registrar (academic/profile management in permitted campuses); Teacher (foundation read permissions and teacher eligibility). Existing ERP roles are not silently granted new School master privileges.
- Elevated platform users retain shared platform policy but must resolve an explicit tenant before School service use. Tenant/user/branch checks still apply to referenced records.
- Campus-access writes need separate permission and target-campus access; only all-campus actors may create campuses or change the main campus.

The Phase 1 RBAC failure was a stale `travel.customers.view` entry in the read_only default list. It never existed in the permission catalog; customer views use existing customers.view. Removing the dead default entry changes no effective grant and passes the catalog test. No unrelated role refactor or new travel access was introduced.

---

## Historical future role/permission plan

# School Management — Permission Matrix

**Date:** 2026-09-01  
**Pattern:** `{module}.{resource}.{action}` (matches existing `gym.*`, `projects.*`)

Permissions registered in `apps.authentication.bootstrap` under `module="school"`.

---

## Permission Namespace

### Workspace access

| Code | Description | Default roles |
|---|---|---|
| `school.view` | Enter school workspace | All school roles |
| `school.manage` | Full school admin (superset) | school_admin, principal |

### Settings

| Code | Description |
|---|---|
| `school.settings.view` | View school profile & config |
| `school.settings.update` | Edit school settings |

### Academic structure

| Code | Description |
|---|---|
| `school.academic.view` | View years, terms, classes |
| `school.academic.create` | Create academic entities |
| `school.academic.update` | Edit academic entities |
| `school.academic.archive` | Archive academic entities |
| `school.academic.activate` | Set current academic year |

### Admissions

| Code | Description |
|---|---|
| `school.admissions.view` | View applicants |
| `school.admissions.create` | Create applications |
| `school.admissions.update` | Edit applications |
| `school.admissions.approve` | Move through pipeline / reject |
| `school.admissions.enroll` | Convert to student |
| `school.admissions.import` | Bulk import applicants |

### Students

| Code | Description |
|---|---|
| `school.students.view` | View student list & detail |
| `school.students.create` | Enroll / create students |
| `school.students.update` | Edit student records |
| `school.students.archive` | Archive / withdraw |
| `school.students.transfer` | Transfer between branches/classes |
| `school.students.import` | Bulk import |
| `school.students.export` | Export student data |

### Guardians

| Code | Description |
|---|---|
| `school.guardians.view` | View guardians |
| `school.guardians.create` | Create guardian records |
| `school.guardians.update` | Edit guardians |
| `school.guardians.archive` | Archive guardians |

### Staff & Teachers

| Code | Description |
|---|---|
| `school.staff.view` | View staff profiles |
| `school.staff.create` | Add staff |
| `school.staff.update` | Edit staff |
| `school.staff.archive` | Deactivate staff |
| `school.teachers.assign` | Assign subjects/classes |

### Timetable

| Code | Description |
|---|---|
| `school.timetable.view` | View timetables |
| `school.timetable.manage` | Create/edit timetables |

### Attendance

| Code | Description |
|---|---|
| `school.attendance.view` | View attendance records |
| `school.attendance.record` | Record attendance |
| `school.attendance.update` | Edit attendance |
| `school.attendance.correct` | Approve corrections |

### Examinations & Marks

| Code | Description |
|---|---|
| `school.exams.view` | View exams & schedules |
| `school.exams.create` | Create exams |
| `school.exams.schedule` | Manage exam schedules |
| `school.marks.view` | View marks |
| `school.marks.enter` | Enter marks |
| `school.marks.submit` | Submit mark sheets |
| `school.marks.lock` | Lock results |
| `school.marks.reopen` | Reopen locked results (elevated) |
| `school.report_cards.view` | View report cards |
| `school.report_cards.generate` | Generate / publish report cards |
| `school.promotion.manage` | Run promotion workflow |

### Fees & Finance

| Code | Description |
|---|---|
| `school.fees.view` | View fee structures & balances |
| `school.fees.create` | Create fee structures |
| `school.fees.update` | Edit fee structures |
| `school.fees.invoice` | Generate invoices |
| `school.fees.receive_payment` | Record payments |
| `school.fees.discount` | Apply discounts / scholarships |
| `school.fees.refund` | Process refunds |

### Homework & Discipline

| Code | Description |
|---|---|
| `school.homework.view` | View homework |
| `school.homework.create` | Assign homework |
| `school.homework.grade` | Grade submissions |
| `school.discipline.view` | View discipline records |
| `school.discipline.create` | Create incidents |
| `school.discipline.manage` | Edit sensitive discipline data |

### Transport & Library

| Code | Description |
|---|---|
| `school.transport.view` | View routes & assignments |
| `school.transport.manage` | Manage transport |
| `school.library.view` | View library |
| `school.library.manage` | Manage books & borrowing |

### Documents & IDs

| Code | Description |
|---|---|
| `school.documents.view` | View student/staff documents |
| `school.documents.upload` | Upload documents |
| `school.id_cards.generate` | Generate ID cards |
| `school.certificates.generate` | Generate certificates |

### Reports & Communication

| Code | Description |
|---|---|
| `school.reports.view` | View school reports |
| `school.announcements.view` | View announcements |
| `school.announcements.create` | Publish announcements |

---

## Role Bundles (System Seeds)

| Role slug | Name | Key permissions |
|---|---|---|
| `school_owner` | School Owner | `school.manage` + all `school.*` |
| `school_admin` | School Admin | All except `school.marks.reopen` |
| `principal` | Principal | view all + approve admissions + promotion + reports |
| `vice_principal` | Vice Principal | principal minus fee refunds |
| `teacher` | Teacher | attendance.record, homework.*, marks.enter (scoped), timetable.view |
| `class_teacher` | Class Teacher | teacher + class-scoped student view |
| `exam_officer` | Exam Officer | exams.*, marks.*, report_cards.* |
| `finance_officer` | Finance Officer | fees.*, shared finance.view |
| `accountant` | Accountant | fees.* + finance.* (shared) |
| `admission_officer` | Admission Officer | admissions.* |
| `receptionist` | Receptionist | admissions.view/create, students.view |
| `librarian` | Librarian | library.* |
| `transport_manager` | Transport Manager | transport.* |
| `driver` | Driver | transport.view (own route) |
| `parent` | Parent | portal: own children only |
| `student` | Student | portal: own record only |
| `hr_officer` | HR Officer | staff.* (when hrm ships: extend) |
| `payroll_officer` | Payroll Officer | shared payroll perms |

---

## Scoped Access Rules

| Actor | Scope enforcement |
|---|---|
| Parent | `GuardianStudent` link → student IDs only |
| Student | `student.portal_user_id == request.user.id` |
| Teacher | `TeacherAssignment` → class/subject IDs only |
| Class teacher | Section-level student queryset filter |
| Branch staff | `branch_id` from user.branch or explicit assignment |
| Platform admin | Bypass via `is_platform_admin` (existing pattern) |

### Backend enforcement layers

1. `HasPermission("school.students.view")` on view
2. `HasModule("school")` on module gate middleware
3. Service-layer queryset scoping by role
4. Object-level check on detail mutations (IDOR prevention)

### Sensitive data

| Data | Minimum permission |
|---|---|
| Discipline records | `school.discipline.view` + class scope |
| Medical/emergency notes | `school.students.update` + feature flag |
| Financial balances (parent) | own children only via portal service |
| Mark sheets (pre-publish) | `school.marks.view` + assignment scope |
| Locked marks | `school.marks.reopen` to edit |

---

## Frontend Guards

```tsx
<PermissionGuard permission="school.view" module="school">
  <WorkspaceGate workspace="school">
    <SchoolPage />
  </WorkspaceGate>
</PermissionGuard>
```

Row-level actions use `usePermissions().hasPermission()` + server enforcement.

---

## Bootstrap Registration (Target)

Add to `authentication/bootstrap.py`:

```python
SCHOOL_PERMISSIONS = [
    ("school.view", "View school workspace", "school"),
    ("school.students.view", "View students", "school"),
    # ... full list from above
]
```

Assign to roles in `SYSTEM_ROLES` seed block.

---

## Related Documents

- `SCHOOL_API_MATRIX.md`
- `SCHOOL_ARCHITECTURE.md`
- `SCHOOL_TEST_MATRIX.md` (permission test cases)

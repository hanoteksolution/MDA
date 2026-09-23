# School Management — Mobile Architecture

**Date:** 2026-09-01  
**Stack:** React Native (Expo) — existing apps under `mobile/`  
**API:** Same Django REST API as web (`/api/v1/school/`, `/api/v1/mobile/school/`)

---

## Principles

1. **One backend** — Mobile consumes same services; no duplicated business rules.
2. **Role-based navigation** — Backend `MobileNavService` drives available screens.
3. **Shared codebase** — Single app with role-based workspace switcher where possible.
4. **Offline-aware** — Attendance/marks entry queues when offline (follow gym-member pattern).

---

## Existing Mobile Infrastructure (KEEP)

| Component | Path | Reuse |
|---|---|---|
| Staff app shell | `mobile/staff/` | Workspace switcher, auth, API client |
| Gym member app | `mobile/gym-member/` | Portal pattern for parent/student |
| Mobile bootstrap API | `/api/v1/mobile/bootstrap/` | Nav catalog per user role |
| Mobile nav service | `apps/platform/services/mobile_nav_service.py` | Add school entries |
| API client | `mobile/staff/api/client.ts` | Extend for school endpoints |

---

## Target App Strategy

### Option A (Recommended): Extend Staff App + Parent/Student Portal App

| App | Audience | New workspace |
|---|---|---|
| `mobile/staff` | Teachers, admin, finance, transport | `school_staff` workspace screen |
| `mobile/school-portal` (new) | Parents + students | Role-split home after login |

Alternative: single `mobile/school` app with role routing (if bundle size acceptable).

### Reference: Gym member portal

Copy architecture from `mobile/gym-member/`:
- Bootstrap → home dashboard
- Profile, notifications, QR (student ID)
- Module registry for screen IDs

---

## Backend Mobile Catalog (Target)

Add to `MOBILE_NAV_CATALOG` in `mobile_nav_service.py`:

```python
"school_parent": [
    {"id": "home", "label": "Home", "icon": "home"},
    {"id": "children", "label": "My Children", "icon": "users"},
    {"id": "attendance", "label": "Attendance", "icon": "calendar-check"},
    {"id": "homework", "label": "Homework", "icon": "book-open"},
    {"id": "results", "label": "Results", "icon": "award"},
    {"id": "fees", "label": "Fees", "icon": "wallet"},
    {"id": "transport", "label": "Transport", "icon": "bus"},
    {"id": "announcements", "label": "Announcements", "icon": "bell"},
    {"id": "messages", "label": "Messages", "icon": "message-circle"},
],
"school_student": [
    {"id": "home", "label": "Home", "icon": "home"},
    {"id": "timetable", "label": "Timetable", "icon": "calendar"},
    {"id": "attendance", "label": "Attendance", "icon": "calendar-check"},
    {"id": "homework", "label": "Homework", "icon": "book-open"},
    {"id": "exams", "label": "Exams", "icon": "file-text"},
    {"id": "results", "label": "Results", "icon": "award"},
    {"id": "fees", "label": "Fees", "icon": "wallet"},
    {"id": "library", "label": "Library", "icon": "library"},
],
"school_teacher": [
    {"id": "home", "label": "Dashboard", "icon": "layout-dashboard"},
    {"id": "classes", "label": "My Classes", "icon": "users"},
    {"id": "attendance", "label": "Attendance", "icon": "calendar-check"},
    {"id": "marks", "label": "Marks", "icon": "edit"},
    {"id": "homework", "label": "Homework", "icon": "book-open"},
    {"id": "timetable", "label": "Timetable", "icon": "calendar"},
],
"school_admin": [
    {"id": "dashboard", "label": "Dashboard", "icon": "layout-dashboard"},
    {"id": "admissions", "label": "Admissions", "icon": "user-plus"},
    {"id": "students", "label": "Students", "icon": "graduation-cap"},
    {"id": "payments", "label": "Payments", "icon": "credit-card"},
    {"id": "alerts", "label": "Alerts", "icon": "bell"},
],
```

---

## Mobile API Surface

Base: `/api/v1/mobile/school/`

### Parent endpoints

| Endpoint | Description | Scope |
|---|---|---|
| `GET /parent/home/` | Children cards + alerts | linked students |
| `GET /parent/children/` | List children | guardian link |
| `GET /parent/children/{id}/attendance/` | Attendance history | child scope |
| `GET /parent/children/{id}/homework/` | Pending homework | child scope |
| `GET /parent/children/{id}/results/` | Published results | child scope |
| `GET /parent/children/{id}/fees/` | Balance + invoices | child scope |
| `POST /parent/children/{id}/payments/report/` | Report payment (if enabled) | child scope |
| `GET /parent/announcements/` | School announcements | tenant |
| `GET /parent/timetable/{student_id}/` | Child timetable | child scope |

### Student endpoints

| Endpoint | Description |
|---|---|
| `GET /student/home/` | Own dashboard |
| `GET /student/timetable/` | Own timetable |
| `GET /student/attendance/` | Own attendance |
| `GET /student/homework/` | Assignments |
| `GET /student/exams/` | Upcoming exams |
| `GET /student/results/` | Published marks |
| `GET /student/fees/` | Own fee balance |
| `GET /student/library/` | Borrowings |

### Teacher endpoints

| Endpoint | Description |
|---|---|
| `GET /teacher/home/` | Today's classes + tasks |
| `GET /teacher/classes/` | Assigned classes |
| `GET /teacher/timetable/` | Own timetable |
| `POST /teacher/attendance/bulk/` | Class roll call |
| `POST /teacher/marks/bulk/` | Marks entry |
| `GET /teacher/students/{section_id}/` | Class roster |
| `POST /teacher/homework/` | Assign homework |

### Admin mobile endpoints

| Endpoint | Description |
|---|---|
| `GET /admin/dashboard/` | KPIs |
| `GET /admin/admissions/pending/` | Pending applications |
| `GET /admin/alerts/` | Fee overdue, absences |

---

## Screen Map (React Native)

```
mobile/school-portal/
├── App.tsx
├── navigation/
│   ├── ParentNavigator.tsx
│   ├── StudentNavigator.tsx
│   └── AuthNavigator.tsx
├── screens/
│   ├── parent/
│   │   ├── HomeScreen.tsx
│   │   ├── ChildAttendanceScreen.tsx
│   │   ├── ChildFeesScreen.tsx
│   │   └── ...
│   ├── student/
│   │   ├── HomeScreen.tsx
│   │   ├── TimetableScreen.tsx
│   │   └── ...
│   └── shared/
│       ├── AnnouncementsScreen.tsx
│       └── ProfileScreen.tsx
└── api/
    └── school.ts
```

```
mobile/staff/screens/
└── SchoolWorkspaceScreen.tsx   # Admin/teacher quick actions
```

---

## Security (Mobile-Specific)

| Threat | Mitigation |
|---|---|
| Parent accesses wrong child | Server filters by `GuardianStudent`; never trust client student_id alone |
| Student edits marks | Read-only results API; no mark write permission on student role |
| Teacher marks wrong class | `TeacherAssignment` scope on bulk endpoints |
| Token leakage | Short-lived JWT + refresh (existing auth) |
| Offline tampering | Queue with server-side validation on sync |

---

## Push Notifications

Use existing notification infrastructure:

| Event | Push to |
|---|---|
| Student absent | Parent |
| Homework assigned | Student + parent |
| Fee invoice created | Parent |
| Fee overdue | Parent |
| Result published | Student + parent |
| Library overdue | Student |
| School announcement | All (segmented) |

Register device tokens via existing mobile auth flow.

---

## Implementation Phases

| Phase | Deliverable |
|---|---|
| 34a | Mobile API endpoints + nav catalog |
| 34b | Parent portal screens (fees, attendance, results) |
| 34c | Student portal screens |
| 34d | Teacher attendance + marks mobile |
| 34e | Admin dashboard mobile |
| 34f | Push notification wiring |

---

## Related Documents

- `docs/MOBILE_ARCHITECTURE.md`
- `docs/modular-erp/MOBILE_ARCHITECTURE.md`
- `SCHOOL_API_MATRIX.md`
- `SCHOOL_PERMISSION_MATRIX.md`

# School Frontend Restructure

Date: 2026-09-23. Scope: the frontend only. There were no backend changes and no new APIs, and no new School phase was started. This builds on the Phase 1–6 School implementation already in the working tree.

## 1. Functionality discovered

The backend already exposes three API families (`backend/api/v1/school/`):

| Family | Base | What it covers |
|---|---|---|
| Foundation | `/school/<resource>/` | academic-years, terms, levels, classes, sections, shifts, subjects, subject-categories, subject-offerings, campuses, campus-access. Also covers lifecycle actions (activate/close/archive/restore), `/summary/`, `/profile/`, `/capabilities/` (a map from resource to actions) and `/lookups/<kind>/`. |
| SIS | `/school/sis/<resource>/` | 58 resources (see `frontend/src/modules/school/sis/config.ts`): admissions, students, guardians and families, enrollment, transitions, documents, staff, timetable, attendance, assignments and submissions, exams and marks, results, report cards, promotions, fees and billing. Also `/schema/`, `/export/`, `/activity/`, workflow actions, `/dashboard/`, `/capabilities/` (a list of permission codes), `/attendance-roster/`, `/marks-roster/`, `/finance-summary/`, and printable receipts and report cards. |
| Shared ERP | `/api/v1/finance`, `/reports` | The central ledger and reports. They are not School-specific (see §5). |

Workflows the frontend already supported, with their pages: application submit → review → decide → enroll; the student transfer, withdraw, suspend, reactivate and re-enroll actions; document verification; timetable publish and clone; attendance take, submit, correct and approve; assignment publish and close; submission grading; exam submit → moderate → publish → reopen; promotion preview → commit; fee structure activate and close; discount approval; fee batch preview → issue; receipts, allocations, credits and refunds, with reversals.

## 2. Old UI gaps

- The sidebar showed only Dashboard, Academics and School profile (`WORKSPACE_NAV_ORDER.school`). Every other feature could only be reached from a row of underlined text links on `/school`, or from `<select>` "area pickers" inside pages (`SisNav`, `SchoolAcademicNav`).
- The SIS list page was a hand-built `<table>` with a free-text status box, a single "View" link and Previous/Next buttons. It had no DataTable, no status badges, no row actions and no page header copy.
- SIS detail and form pages had no breadcrumbs or description. They used underlined links for actions, native `window.confirm` for business actions, and unstyled error paragraphs.
- The dashboard showed four foundation counters, a large campus `RelationField` block and a grid of cards that duplicated navigation. It had no student, admissions, attendance or teaching data.
- Read-only lists whose records are created by workflows (attendance history, fee batches, receipts…) gave no way to reach the page that creates them.
- The hub card advertised "Reports", which has no School implementation.

## 3. New navigation map

The map is defined in `frontend/src/navigation/schoolNavigation.ts` and plugged into the shared `industryNavSections("school")`. Each entry needs the same `school.<resource>.view` code the API enforces (plus the backend's legacy `school.academic.view` and `school.settings.view` aliases). An entry is shown only when its code is present and the `school` module is enabled, and a group with no visible entries is omitted.

```
School ─ Dashboard                               /school
Admissions      Admissions overview (/school/admissions) · Applications · Applicants · Enrollment
Students        Students · Guardians · Families · Transfers & history (transitions)
Academics       Academic years · Terms · Campuses · Classes · Sections · Subjects · Subject offerings
Teaching        Teaching staff · Teacher assignments · Employees · Timetable (/school/timetable)
                · Timetable versions · Take attendance (/school/attendance) · Attendance history
                · Attendance corrections
Assessments     Assignments · Submissions & grading · Exams & results · Marks entry (/school/marks)
                · Grading scales · Report cards · Promotions (/school/promotions) · Promotion history
Finance         Student billing (/school/finance/fees) · Fee structures · Scholarships & discounts
                · Generate fees (/school/finance/generate) · Fee invoices
                · Record payment (/school/finance/transactions) · Receipts & advances · Billing customers
School settings School profile · Education levels · Subject categories · Shifts · Timetable periods · Rooms
                · Campus access · Document requirements · Admission policies · Relationship types
                · Fee categories · Finance mappings · Payment methods
Platform        All workspaces
```

**Sidebar behaviour.** The shared `layouts/Sidebar/Sidebar.tsx` now renders sections through `SidebarSection.tsx`, and sections can opt in to `collapsible` and `icon`. Existing workspaces are unchanged because they don't set the flag.

- Expanded sidebar: each group is a disclosure button with `aria-expanded`/`aria-controls` and an indented `role="group"` list. The group containing the current route opens automatically, and a group the user toggles keeps its state.
- Icon rail (the shell collapses the sidebar at ≤1440 px, which covers laptops, tablets and phones): each group shows as one labelled icon that links to the active entry or the group's first entry. The existing toggle expands it back to the full groups. The ERP shell has no off-canvas drawer, so School follows the same rail behaviour.

## 4. Pages completed

| Area | Page | What changed |
|---|---|---|
| Dashboard | `pages/SchoolPage.tsx` | Replaced with a real dashboard. KPIs (active students, open admissions, teaching staff, classes, sections, campuses, today's attendance registers, submissions to grade) appear only when the user may read the source. The page also has an academic calendar, today's attendance, recent admissions, academic activity (published assignments, submissions awaiting grading, exams awaiting moderation, active terms, offerings, teacher assignments) and permission-gated quick actions. The campus filter is a compact select in the header toolbar and appears only when more than one campus is accessible. Each source fails independently and a retry banner names what failed. No fabricated values: absent data hides the card. |
| Admissions | `sis/DashboardPage.tsx` | KPI pipeline, recent applications, missing documents, upcoming interviews and applications by class. All values come from `/sis/dashboard/`. |
| All SIS lists (58 resources) | `sis/ListPage.tsx` | PageLayout (title, description, breadcrumbs, "+ New …" or a workflow action) with the canonical `DataTable`. It uses server pagination (25 per page), debounced search, and toolbar filters for status (choices from `/schema/`), campus (when there is more than one), class (students, enrollments, applications) and sort. Other features: status badges, ⋮ row menu (View / Edit / Archive or Restore, with an `appDialog` confirmation), an Archived toggle, CSV export where the API supports it, Print/PDF of the current page, a "filtered by parent record" banner with Clear, and permission-denied, error-with-retry and empty states. Filter state stays in the URL. |
| All SIS details | `sis/DetailPage.tsx` | Back link and breadcrumbs, header actions (Edit, Archive/Restore, print receipt or report card, download attachment), a status badge, and sections for Workflow (the existing domain actions), Details and Related records. It also has a loading skeleton and a permission-denied state. |
| All SIS forms | `sis/FormPage.tsx` | FormSections (Student identity, Initial enrollment, Guardian and Registration reason for direct registration), a sticky Cancel/Save bar, a field-error summary, the unsaved-change guard (kept) and `appDialog` for the duplicate-student check. |
| Workflow pages | Attendance, Timetable, Marks, Promotions, Fees & reconciliation, Generate fees, Payments | Canonical header and breadcrumbs, ContentSection, ErrorBanner, a permission gate that waits for capabilities, ERP table styling and timetable lesson chips. Business confirmations (submit attendance, commit promotion, issue fees, post transaction) now use `appDialog`. The "discard unsaved changes" prompts stay native to match `useUnsavedChanges`. |
| Academics / settings (foundation) | `pages/Foundation*Page.tsx`, `SchoolSettingsPage.tsx` | The in-page area picker is removed in favour of the sidebar. Relation, status and sort filters and the archived/current/visible-columns toggles moved into the DataTable toolbar. Other changes: shared status badge and ⋮ menu, breadcrumbs from the navigation map, back links, a Details section, a permission-denied state, and an empty state on the profile page. |
| Hub card | `navigation/moduleWorkspaces.ts` | Description and pages reflect the real feature set. "Reports" is removed. |

**CRUD verification (list → view → create → edit → domain action).** Foundation resources support all of these, plus activate, close, archive and restore. SIS master data (students, guardians, families, applicants, applications, staff, rooms, periods, timetable versions and lessons, assignments, exams, academic assessments, grade schemes and bands, fee structures, lines, categories and discounts, billing customers and methods, settings resources) supports list, view, schema-driven create and edit, archive and restore, plus the workflow actions in `sis/workflows.ts`. Workflow-owned records (decisions, transitions, attendance, marks, publications, report cards, promotions, fee batches and invoices, receipts, allocations, credits, refunds) are read-only in the generic UI by design. Their lists now offer the workflow page that creates them (`WORKFLOW_ENTRY` in `sis/meta.ts`), and generic Edit/Archive is never shown for them.

## 5. Backend gaps discovered (not built, no APIs invented)

1. **Transfers:** `/sis/transitions/` has no `outcome` filter (`apps/school/repositories/sis_filters.py`), so "Transfers & history" shows all lifecycle history and can't list transfers on their own.
2. **Grade bands:** `scheme_id` is not in the SIS filter allow-list, so a grade scheme's detail page can't link to its own bands.
3. **School reports:** there is no School reporting API. `SCHOOL_REPORTING_MATRIX.md` is a plan. What exists: CSV export for students, applicants, guardians, families and enrollments; `/finance-summary/`; printable receipts and report cards. `/school/reports` and `/school/finance` resolve to the central ERP pages. For that reason the School sidebar has no Reports item.
4. **Upcoming lessons:** there is no "today's timetable" endpoint. Entries need a version id, so the dashboard can't show upcoming classes without per-version N+1 calls. The dashboard doesn't show them.
5. **Sorting:** SIS ordering is limited to an allow-list (`created_at`, `name`, `number`, `status`, some dates, intersected with the model's fields), so lists offer Newest and Oldest only.
6. **Page size:** the maximum is 100. Toolbar filter options (campuses, classes) are capped at 100, and today's attendance KPI counts submitted registers among the first 100 sessions.
7. **Capabilities:** SIS capabilities are global permission codes. Campus scope is enforced server-side only, so an action can still return 403 for a campus the user can't access. The UI shows the API error.

## 6. Routes

These are unchanged, so existing links and bookmarks still work: `/school`, `/school/admissions`, `/school/sis/:resource`, `/school/sis/:resource/new`, `/school/sis/:resource/:id`, `/school/sis/:resource/:id/edit`, `/school/academics/:resource`, `…/new`, `…/:id`, `…/:id/edit`, `/school/academic-years`, `/school/settings`, `/school/attendance`, `/school/timetable`, `/school/marks`, `/school/promotions`, `/school/finance/fees|generate|transactions`.

## 7. Reusable components used

These are existing ERP components, not a second design system: `PageLayout`/`PageHeader` (breadcrumbs, back link, actions), `ContentSection`, `DataTable` + `FilterBar` + `Pagination`, `KpiCard`/`KpiGrid`, `EmptyState`, `LoadingState`, `Badge`, `Button`, `ui/select`, `FormSection`, `appDialog`, the Radix dropdown and the shared `Sidebar`.

The small School-local helpers are in `modules/school/components/SchoolUi.tsx`: `SchoolStatusBadge`/`statusTone` (one status vocabulary), `ErrorBanner`, `PermissionDenied`/`Denied`, `RecordMenu` (the ⋮ row menu) and `DetailGrid`. There are also `hooks/useLookupOptions.ts` (toolbar filter options from existing lookups) and `sis/meta.ts` (page copy, immutability, workflow entry points).

Two small additive fixes were made to shared code. The shared `FilterBar` search input now has an `aria-label`. `WorkspaceNavSection` gained the optional `icon` and `collapsible` fields.

Removed: `sis/Nav.tsx` and `components/SchoolAcademicNav.tsx`, whose job the sidebar now does.

## 8. Tests and evidence

- `npx vitest run`: **176 passed / 17 files** (baseline 145; 31 new).
  - `navigation/schoolNavigation.test.ts` (10): every entry maps to an existing route or resource, permissions equal the API codes, groups follow the target IA, permission and module filtering, legacy aliases, elevated users, and breadcrumbs.
  - `layouts/Sidebar/SidebarSection.test.tsx` (5): the accessible disclosure, the closed state, the collapsed icon rail, unchanged flat sections, and active-group matching.
  - `modules/school/restructure.test.tsx` (16): the DataTable list (search label, detail link, status badge, row-menu label, pagination), archived links, the empty state, parent filters, header copy for every resource, immutability, workflow entry targets, related-link permissions, detail-field hygiene, the status vocabulary, the error and permission states, dashboard loading, no fabricated KPIs, dashboard sections and the hidden attendance panel, and the Admissions overview.
- `npm run build` (`tsc -b && vite build`): **PASS**. The only warning is the existing chunk-size notice.
- Browser smoke check: Chromium via playwright-core 1.63.0 against the production build (`vite preview`), with a mocked API for a limited-permission registrar. The script is in the session scratchpad, not the repo. It passed these checks:
  - Desktop 1600 px: exactly 4 permitted groups, the active group expanded, the toggle works, and Finance is hidden.
  - Students list: header action, search, filters, badges, and the row menu showing View details / Edit / Archive.
  - Detail page has an Edit action. Form: the unsaved-change guard fires on Cancel.
  - Dashboard: only permitted KPIs, and the old text-link row is gone. Every visible control has an accessible name.
  - Tablet 1024 px: one labelled icon per group, and expanding the sidebar restores the groups.
  - Phone 390 px: no horizontal overflow on the dashboard, list or detail pages.
  - No page errors.
- Backend: unchanged, so no backend suites were run.

## 9. Remaining School work

- `frontend/tests/school/phase3.mjs` and `phase4.mjs` accept native dialogs. Workflow confirmations are now in-app `appDialog` dialogs, so those scripts need to click the dialog's confirm button before they are re-run. `verify.mjs` and `ux.mjs` already use in-app dialogs for archive. None of the four was re-run against the seeded PostgreSQL database in this change.
- The Attendance roster, Marks, Promotion, Fee generation and Payments pages are restyled but keep their existing form mechanics. A deeper UX pass (for example, sticky roster headers or bulk marks entry) is future work.
- `BillingTransactionsPage` doesn't read a transaction mode from the URL, so workflow links from the allocation, credit and refund lists open on the receipts mode.
- The backend gaps in §5 (transition outcome filter, grade-band scheme filter, School reports, today's lessons, sort fields).
- The header global search is not School-aware.

# School ERP — Phase 1 repository audit

Date: 2026-09-11. Scope: audit and design only, covering deliverables A–R in the attached master prompt. No Phase 2 implementation is authorized by this report.

## Evidence and limits

This assessment examines the working tree, including existing uncommitted changes. The School app, API, frontend pages, migration and earlier School documents are currently untracked; numerous shared files also have existing modifications. Their presence is implementation evidence, not proof of deployment or production readiness. No application data, migrations, shared code or existing documents were changed for this audit.

Reviewed the repository architecture/business/design instructions in `agent.md`, the ten required architecture/product/API/workflow documents, School code and planning documents, and integration paths through authentication, tenancy, platform modules, sales, finance, inventory, reports, notifications, audit, media, desktop sync and mobile navigation. UI findings are source-based; no screenshot references were supplied and no browser accessibility or responsive audit was performed. Production database contents, migration history, deployed worker health and production query timings were not inspected.

Earlier `SCHOOL_CURRENT_STATE_AUDIT.md` says School does not exist; that is now obsolete. `SCHOOL_COMPLETION_MATRIX.md` acknowledges years/terms in its header but still marks their entities and route registration missing. Its 37-phase sequence differs from the new prompt's 12 phases. This dated assessment is the current planning baseline; earlier documents remain historical proposals, not completed-feature evidence.

Paths below are relative to the repository root. “Exists” means code exists; “missing” means no implementation found in the inspected module and repository searches.

## A. Current architecture

| Area | Observed implementation | Consequence for School |
|---|---|---|
| Backend | Django 5 / DRF modular monolith; `backend/apps`, `api/v1`, shared `core` and `permissions`; service classes plus repositories/selectors | Extend `apps.school`; domain rules in services, queries in repositories/selectors, request validation in serializers |
| Frontend | React 19, TypeScript, Vite, React Router 7, Zustand, Tailwind, Radix primitives, Recharts | Reuse current workspace and component architecture; no Next.js conversion |
| Storage | PostgreSQL 16 in Compose; development/test SQLite; UUID, timestamp, actor and soft-delete base classes | Add migrations compatible with both; validate concurrency on PostgreSQL |
| Tenant/company/campus | `platform.Tenant`, `settings_app.Company`, `Branch`; nullable tenant FK mixin; explicit `apply_tenant_scope` | Tenant is organization boundary, Branch is campus; no second campus/tenant master |
| Authentication | Shared JWT and `core/authentication.py` tenant-host mismatch checks | Portal users remain shared users; require separate object-access policy |
| Authorization | Role permissions plus direct grants minus revokes; elevated roles bypass; `permissions/base.py` | Use existing namespace and enforce actions, campus membership and relationships server-side |
| Entitlements | `ModuleGateMiddleware`, subscription write gate, module dependencies and business presets | School already registered with sales/finance dependencies; business type also enables inventory |
| Requests | `/api/v1`, `{success,message,data}` envelope, shared pagination and HTTP client | Preserve contracts and trailing slashes; add typed validation and consistent field errors |
| State/cache | Zustand auth/UI stores; School uses local effects/state; catalog cache utilities; Redis/Celery configuration | No School query cache/invalidation yet; tenant, campus, permissions and filters must enter cache keys |
| Jobs | Celery worker/beat; scheduled notification scans and accounting-health tasks | Reuse worker infrastructure; add durable School jobs and explicit tenant context |
| Documents/reporting | Shared frontend print/PDF templates and report catalog/vertical runners; backend CSV export | Extend templates/catalog; secure stored documents and asynchronous exports are additional work |
| Desktop/mobile | Tauri local API/SQLite with sync services; Expo staff and gym-member apps | Existing clients are reusable shells, not School offline/portal implementation |

The architecture documents describe desired clean layers, but School currently queries models directly in services and serializes dictionaries there. It has no dedicated repository or serializer layer. School routes are statically imported through the route barrel; School-specific route splitting is not present.

## B. Existing School Management functionality

| Capability | Evidence | Actual scope |
|---|---|---|
| Campus profile | `backend/apps/school/models/profile.py`, `services/profile_service.py` | One profile per Branch; identity/contact/location, timezone/currency/language, principal user/name, calendar type and JSON settings |
| Academic years | `models/academic.py`, `services/academic_service.py` | List/detail/create/update/archive/activate; branch, dates, status, current flag and description |
| Terms | Same academic files | Year/branch membership, dates, optional exam dates, status, sort order; CRUD with soft archive |
| Schema | `migrations/0001_initial.py` | Three concrete models: SchoolProfile, AcademicYear, AcademicTerm |
| API | `backend/api/v1/school/urls.py`, `views.py` | Seven URL patterns, authenticated permissions, paginated year/term lists |
| Dashboard | `services/summary_service.py` | Real year/term/profile queries; student/teacher/class/fee values hard-coded zero; attendance null |
| UI | `frontend/src/modules/school/pages/` | SchoolPage, AcademicYearsPage, SchoolSettingsPage; years and terms share a page |
| Registration | `config/settings/base.py`, `api/v1/urls.py`, platform module/business seeds | App installed in configuration, API included, module prefix gated, school business type seeded by code |
| Navigation | `app/workspaceRoutes.tsx`, `navigation/{moduleWorkspaces,businessWorkspaces}.ts` | `/school`, `/school/academic-years`, `/school/settings` plus shared workspace composition |
| Permissions/audit | `apps/authentication/bootstrap.py`, School service calls to `write_audit` | Nine School codenames and mutation audit calls; not the requested complete role/action matrix |

Frontend can create and archive years/terms and activate years; year/term PATCH APIs exist without corresponding edit forms. Profile form exposes only part of model settings. No complete admission-to-report-card or fee-to-ledger workflow exists.

## C. Reusable ERP functionality

| Reuse | Source | Extension needed / limitation |
|---|---|---|
| Identity and RBAC | `apps/authentication/models/user.py`, permission helpers | School roles, guardian/student links, employee linkage, campus and teacher assignment policies |
| Tenant, branch, module/preset system | `apps/platform`, `apps/settings_app` | Reuse IDs and module gates; validate allowed campuses rather than trusting branch filters |
| Accounting | `apps/finance/models`, `services`, `selectors` | Accounts, journal validation, periods, posting, mappings, reversal, maker/checker, reconciliation, business units and cost centers exist |
| Billing | `apps/sales/models/sales.py`, `services/sales_service.py`, `pos_service.py` | Invoice, InvoiceItem, Payment, Expense, refund and numbering exist; school billing adapter and broader allocation lifecycle needed |
| Billing counterparties | `apps/customers/models/customer.py` | Reuse Customer as financial counterparty linked to family/sponsor; do not model guardian relationships in Customer |
| Inventory/procurement | `apps/products`, `inventory`, `purchases`, `suppliers` | Reuse catalog, warehouses, stock movements, purchases; add school issue/return context and shared asset lifecycle where missing |
| Staff identity/evaluation | User and `authentication/models/staff_evaluation.py` | Neither is an employee master; no shared Employee, Leave or Payroll implementation found |
| Notifications | `apps/notifications/services/notification_service.py`, model and tasks | User-targeted in-app notifications, read state, links and recent-duplicate checks; no complete multichannel campaign/delivery engine |
| Audit | `apps/audit/services/audit_write.py` | Actor, entity, old/new values, request IP and user agent; School must supply meaningful before/after values and reasons |
| Media | `core/utils/media.py` | Validated images and storage backend; not a private, versioned student-document service |
| Reports | `apps/reports/services/report_service.py`, finance selectors | Module-aware catalog, vertical report runners and CSV; add School report permissions, filters, saved configurations and jobs |
| UI | `components/layout`, `data`, `forms`, `feedback`, `ui`, `documents`, `design-system` | Page headers, cards, charts, table server pagination, forms, dialogs, badges, loading/empty patterns, PDF/print branding |
| Command search | `pages/modules/hub/HubCommandSearch.tsx` | Existing entity/workspace/action search; extend with authorized School entities rather than a competing palette |
| Sync/mobile | `platform/services/sync_*`, `mobile_nav_service.py`, `mobile/` | Reuse infrastructure and finance authority policy; no School entities/screens found in current sync/mobile catalogs |

Do not treat project site wages as organizational payroll, property assets as a complete school equipment register, or vertical document records as a universal private file service.

## D. Missing functionality against the master prompt

| Prompt scope | Gap / disposition | Target phase |
|---|---|---|
| 2–4: command center, configuration, academic hierarchy | Profile/year/term partial; levels, classes, sections, subjects, offerings, rooms and campus policy missing | 2, 9 |
| 5–8: admissions, SIS, households, enrollment/promotion | All domain workflows missing, including duplicate review and historical transfers | 3; promotion completion 5 |
| 9–12: scheduling, attendance, teachers, leave | School scheduling/attendance missing; shared HR prerequisite missing | 4, 7 |
| 13–16: assignments, exams, grading, documents | Missing grading/publication/revision workflows and report-card generation | 5 |
| 17–22: fees, invoicing, payments, expenses, payroll, finance dashboard | Shared finance exists; School mappings, fee overlay, allocation/advance lifecycle and school financial reporting missing | 6, 7, 9 |
| 23–32: communication, notices, discipline, library, transport, assets, health, clubs, meetings, documents | School workflows missing; notification/inventory/media patterns only | 7–8 |
| 33–35: guardian/student/teacher portals | Missing role experiences and relationship access policies | 11, with policies designed earlier |
| 36–41: copilot, analytics, prepared actions, insights, automation | No implemented AI provider/tool gateway or general rule/run engine found | 10 |
| 42–45: notifications, report center, core reports, global search | Shared UI/services partial; School data providers and report definitions missing | 7, 9–10 |
| 46–47: permissions and audit | Coarse academic/settings permissions and event-only School audits; fine-grained/object-level policies missing | Every phase |
| 48–53, 60: UX, navigation, list/detail/forms, responsiveness, states | Existing design primitives; School lacks the requested complete screen patterns | Every phase |
| 54–59: performance, integrity, security, AI safety, accounting, imports | Shared foundations require School-specific enforcement, query work and operational controls | Every phase; hardening 12 |
| 61–62: demo data and tests | Shared test/seed infrastructure exists; no School demo seeder or executable School-specific tests found | Incremental; final validation 12 |

## E. Database gap analysis

Current constraints cover active year names per tenant/branch and active term names per tenant/year. They do not enforce one current year, valid date intervals or valid status/current combinations. Tenant columns remain nullable, and base managers are ordinary Django managers; tenant isolation depends on explicit scopes. Foreign keys alone do not establish equal tenants across related rows.

1. Extend existing years with code and admissions/enrollment flags; terms with publication date and explicit calendar rules. Preserve UUIDs, branch ownership and current API names.
2. Add one-current-year conditional uniqueness for active records per tenant/campus, date-order checks, status checks and stable branch-level locking during activation. Resolve existing conflicting rows before enforcing constraints.
3. Validate that term and exam dates remain inside their parent calendar. A year date edit must validate existing terms. Define overlap policy explicitly; do not prohibit overlapping calendars without considering shifts/programs.
4. Separate “closed”, “archived business status” and “soft deleted”. Current DELETE hides the parent year but does not hide its terms from term queries. Published academic history needs protected references and explicit visibility rules.
5. Profile OneToOne on Branch remains unique even when soft deleted; upsert searches only active profiles, so a deleted profile can block recreation. Prefer restore/update semantics over duplicate profile creation.
6. New School-owned tables should require tenant IDs; harden existing nullable rows through staged backfill. Validate tenant and campus coherence in all creation, updates, import and background paths.
7. Financial source records, published result versions and enrollment transitions should be immutable or versioned. Derived balances and academic summaries must not become independent editable truth.
8. Add targeted indexes for student identifier/search, tenant/campus/year/class enrollment, attendance date/session, scheduled exams, invoice due/status and automation execution. Test real plans and volume before adding speculative indexes.

## F. API gap analysis

Existing paths below are relative to `/api/v1/school/`:

| Path | Methods | Existing contract / gap |
|---|---|---|
| `summary/` | GET | Optional branch; foundation counts only, no period/role-aware metrics |
| `profile/` | GET, PUT | Requires branch; missing typed validation and principal-user tenant/campus validation |
| `academic-years/` | GET, POST | Search/status/branch and pagination; ordering fixed in service |
| `academic-years/{id}/` | GET, PATCH, DELETE | Scoped lookup; state/date/history validation incomplete |
| `academic-years/{id}/activate/` | POST | Dedicated permission; forces active/current without using transition table |
| `terms/` | GET, POST | Branch/year/search/pagination; no richer calendar filtering |
| `terms/{id}/` | GET, PATCH, DELETE | Parent interval validation on update; exam/status validation incomplete |

APIViews accept raw request dictionaries and catch only domain errors. Invalid dates/UUIDs, null dates on PATCH, invalid integer ordering, duplicate names and invalid pagination can raise errors outside those handlers. Shared pagination accepts zero/negative/non-integer page sizes incorrectly. Add serializer-level field validation and bounded parameters, translate constraint conflicts, and retain the response envelope.

Future APIs need server-side ordering allowlists, bounded search, authorized lookups, version/concurrency tokens for drafts, idempotent command endpoints, bulk preview/confirm, import row errors, asynchronous job status/download and action-specific authorization. No student/admission/exam/fees/portal/copilot APIs exist yet.

## G. UI/UX gap analysis

The current pages already reuse typography, borders, cards, form sections, status badges, table exports and responsive grids. Build on those components.

| Finding | User impact | Recommended change |
|---|---|---|
| Dashboard catches errors as null and renders default counts; student KPI is placeholder zero | Failure and unavailable features can look like real zero activity | Explicit unavailable/error/retry states; expose only backed metrics |
| Profile load errors reset to a blank/default form | A failed read can look like a new profile and encourage overwriting data | Preserve data, show load error, block save until successful read |
| Years request first 100; terms first default page; DataTable then paginates locally | Records outside fetched pages cannot be reached/exported | Connect server page/count/filter state and explicit full export jobs |
| One `canManage` based on create/manage controls archive and activate buttons | Actions shown/hidden inconsistently with backend permission checks | Match each action's exact permission |
| Selected-year reload fetches terms for current/first year while preserving previous selected ID | Rows can disagree with selected year after mutation | Single selected-year query, cancellation/version protection |
| User branch is fixed source of campus context | Multi-campus managers cannot use a complete campus workspace | Authorized campus selector with optional authorized aggregate view |
| Large inline calendar page and partial settings form | Limited maintainability and progressive disclosure | Split hooks/components; use existing form layouts, drawers and grouped settings |
| No detail profile, admissions board, timetable grid, marks grid or portals | Core daily tasks unavailable | Implement complete workflow-specific experiences in dependency order |

Use consistent list toolbar, summary, server table, bulk preview and detail tabs; retain dark mode. Test keyboard focus, labels, dialogs, status contrast, reduced motion, tablet marks/attendance and mobile navigation. No visual compliance is claimed from source inspection alone. Remove implementation-phase copy from product screens when implementing.

## H. Permission/security gap analysis

**High-priority findings from code:**

| ID | Finding and source | Required resolution |
|---|---|---|
| SEC-1 | `ProfileService.upsert` directly assigns `principal_user_id` without scoped lookup | Reject unrelated tenant users and unauthorized campus assignments; test cross-tenant FK injection |
| SEC-2 | Academic/profile services scope tenant but never restrict permitted branches; detail lookup has no actor-campus predicate | Central campus-access policy for list/detail/write/summary/export, with explicit all-campus permission |
| SEC-3 | Helpers allow unscoped access for elevated users without tenant and for calls without authenticated actor; `BaseModel.objects` is unscoped | School service/tool/job entry points require explicit validated tenant context; elevated access should be deliberate and audited |
| SEC-4 | Create accepts arbitrary year status; current flag writes can bypass activation permission; activate bypasses transition table | Single lifecycle command service; dedicated permission for activation and reopening; atomic constraint-backed invariants |
| SEC-5 | School audit calls omit `old_values`/`new_values`; bulk clearing current flags bypasses individual audit detail | Capture changed entities and before/after values; reasons for corrections, status changes and later financial/result actions |
| SEC-6 | No guardian/student/teacher relationship policy exists | Query-scoped access to linked children, self or assigned class/subject/year; deny direct-ID and export bypasses |
| SEC-7 | Image URLs/storage are not private document authorization | Private object storage/access checks, validated content, restricted downloads and retention policy before sensitive uploads |

Module gating **does exist** through `ModuleGateMiddleware` and `/api/v1/school/` registration even though School APIViews do not declare `HasModule`. Keep and test this middleware path; internal task/tool calls must also check entitlements. JWT host checks and explicit tenant filters are useful existing controls, not proof of complete isolation.

Retain existing `school.*` names. Add resource/action codes such as `school.students.view/create/update/archive`, `school.attendance.take/correct`, `school.exams.enter_marks/approve/publish/reopen`, `school.fees.generate`, `school.payments.collect/reverse`, `school.reports.finance.view`, `school.health.view`, and `school.ai.finance.query/student.query/action.prepare`. Shared accounting/HR permissions remain required when executing their capabilities. New privileges must not flow automatically to every current holder of `school.manage`.

Seed least-privilege School administrator, principal, registrar, teacher, accountant/cashier, librarian, transport, student and guardian bundles through existing RBAC. Global Role records are not tenant-owned; do not mutate a shared role to implement a single school's custom policy. Reuse supported user grants/revokes and design tenant-local role customization separately if required.

## I. Accounting integration plan

The central engine already has Decimal validation, balanced journals, periods, account mappings, posting rules, event idempotency, reversal services and posted-ledger selectors. School must extend these paths and reconcile its operational receivables to the general ledger.

1. Represent fee schedules, scholarship approvals and student charge assignments in School. Link issued charges to shared Invoice/InvoiceItem, a shared Customer billing counterparty, and the student's enrollment/family. Guardian identity and authorization remain distinct from billing identity.
2. Resolve shared billing limitations before fees go live: InvoiceItem requires Product; current `InvoiceService.create` invokes inventory movement. Add a tested shared non-stock service-line path or reuse a proven billing adapter after validating it. Tuition must never decrement inventory or generate COGS. Uniform/book sales may legitimately use inventory.
3. Extend shared collection capabilities for receipts, allocations across invoices, configurable methods, advances, credits, refunds and reversals. Current Payment is a single-invoice tender row with fixed method choices. Do not add a second School Payment table or editable family balance. Preserve compatibility for existing POS tender rows through additive links/backfill.
4. Add School posting adapters using the actual `AccountingPostingService.post(...)` interface. Earlier documents mention `post_event`, which is not the observed entry point. Introduce only events/mappings needed by real workflows, with one owner of posting to avoid duplicate generic and School journal entries.
5. On invoice recognition: debit AR and credit configured revenue, or deferred revenue when policy requires later recognition. On collection against that invoice: debit cash/bank/mobile money and credit AR; do not credit revenue again. Advances credit a liability until allocated. Discounts, credit notes, refunds and opening balances use explicitly approved shared posting policy; never import opening AR as fresh tuition revenue by default.
6. All issuance/allocation/posting must be transactional and idempotent. Lock relevant invoices/receipts; reject excess allocation and stale previews. If accounting is disabled or its period/mapping invalid, return a clear blocked/pending state, never false successful posting.
7. Reuse `Branch`, `BusinessUnit`, `CostCenter` dimensions for campus/program reporting. Preserve dimensions on every posting and reversal: current `reversal_service.py` copies accounts/debit/credit/memo but not line business-unit/cost-center fields. Extend and test before school dimension reports rely on it.
8. Financial statements derive from posted journal selectors, not dashboard placeholder fields or conversational calculations. Operational fee expectations are separately labeled. `ProfitLossSelector` has business-unit/cost-center filters but no branch filter; add validated campus scoping. `ReceivablesAgingSelector` currently reads current invoice balances and all rows, not historical allocations as of a date; improve historical semantics, pagination and dimension reconciliation.

Validate tenant/campus/source scope consistently: reconciling only School invoices to a tenant-wide AR account containing retail receivables is invalid. Retain immutable posted entries and use reversing/adjusting entries, with approval and reason. Existing model guards do not by themselves prove protection against every bulk update or database writer.

## J. AI and automation integration plan

Implement a shared authorized tool gateway with School tool registrations in Phase 10. No AI framework/provider is implemented in the inspected app. Provider choice is deferred; this audit requires no external service or model calls.

Each tool receives server-resolved actor, tenant and permitted campuses; checks entitlement, permission and object policy; validates typed filters; calls deterministic School/finance selectors; bounds output; and logs the invocation. Tools return structured facts with period, filters, source module, generated timestamp and authorized drill-down links. Financial calculations happen in finance services. Reports with no data or insufficient access must say so.

Read tools: school financial summary, attendance summary, outstanding fees, class/subject performance and expense/revenue breakdown. Never expose unrestricted SQL, raw ORM or whole-tenant dumps to a model. Treat retrieved notes/files as untrusted data. Exclude unnecessary child/health information, redact logs and include user/campus/permission context in cache isolation.

Prepared actions: persist a tenant/actor-bound proposal with canonical inputs, eligible IDs, totals, exceptions, version/hash and expiry. Show a deterministic preview. Explicit confirmation invokes the ordinary service, rechecks permissions/current data and applies an idempotency key. Reversals, payroll payments, grade changes, result publication and journal posting additionally retain ordinary approval requirements. Model text cannot confer authorization.

Automation: add shared event/outbox, rule, delivery/run and retry records; publish after successful transactions, execute with explicit tenant context, deduplicate by event/rule/recipient, record attempts/failures, and recheck recipient relationship before delivery. Reuse Celery and NotificationService. Existing notification recent-duplicate checks are not an exactly-once delivery guarantee. Add external channel adapters/preferences/consent only as configured. Begin with absence, overdue fees and result-publication rules; show trigger, target, condition, action and execution history.

## K. Recommended entities and ownership

These are proposed domain groups, not new models created in this audit. Split implementation into the prescribed phases.

| Owner / phase | Entities or extensions | Relationships and key invariants |
|---|---|---|
| Existing shared | Tenant, Company, Branch, User, Role, Customer, Invoice, Payment, Account, Journal, Inventory, Notification, AuditLog | Reuse IDs and lifecycle; no duplicate school masters |
| School / 2 | Extend SchoolProfile, AcademicYear, AcademicTerm; EducationLevel, Class, Section, Subject, Classroom, SubjectOffering | Class/section campus; offering links subject, year/term and class/section; unique scoped codes and valid dates/capacities |
| School / 3 | AdmissionApplication, AdmissionEvent, Family, Guardian, FamilyGuardian, Student, StudentGuardian, Enrollment, EnrollmentTransition | Sibling-safe guardian reuse; relationship/emergency/access flags on links; one conversion per application; protected enrollment history |
| Shared HR + School / 4, 7 | Shared Employee with optional User; SchoolStaffProfile, TeacherAssignment; shared attendance/leave/payroll entities in HR | No mandatory login for all employees; teacher extension references Employee; assignments effective-dated and scoped |
| School / 4 | Period, TimetableVersion, TimetableEntry, AttendanceSession, AttendanceRecord, AttendanceCorrection | Teacher/room/class conflict checks; unique student per session; distinguish daily/period attendance |
| School / 5 | Assignment, Submission, Assessment, Exam, ExamSchedule, GradeScheme, GradeBand, AssessmentWeight, Mark, ResultPublication, ReportCardVersion, PromotionBatch/Item | Decimal grading, non-overlapping bands, valid weights, draft/moderate/publish/revise, immutable published versions and preserved enrollment |
| School / 6 | FeeCategory, FeeStructure/Line, StudentFeeAssignment, Scholarship/DiscountApproval, SchoolInvoiceLink | Link shared invoice lines and billing customer; stable unique charge-period keys; no parallel ledger |
| Shared billing / 6 | Extend receipt/payment allocation, credit/refund, method configuration and non-stock line support | One economic receipt, allocations bounded by available funds and invoice balance; legacy POS compatibility |
| Shared / 7–8 | Employee, LeaveRequest/Approval, PayrollRun/Line, Payslip; communication template/campaign/delivery; private Document/Version/Link | Shared lifecycle, audit and permissions; School adds audience and entity links |
| School / 8 | Announcement/Acknowledgement, DisciplineIncident/Action, HealthIncident/Authorization, Activity/Membership, Meeting/ActionItem | Strong sensitive-record policies; effective dates, responsible actor and follow-up |
| School / 8 | LibraryTitle/Copy/Loan, TransportVehicle/Route/Stop/Assignment | Barcode/copy uniqueness, transactional lending/capacity; employee driver and shared fee links |
| Shared + School / 8 | Shared asset/issue/return extension with school room/borrower links | Reuse product/warehouse/employee records; no duplicate stock truth |
| Shared + School / 9–10 | SavedReport, ExportJob; AutomationRule/Event/Run; AIInvocation/PreparedAction | Owner/tenant/campus scope, expiring downloads/proposals, durable execution and audit |

Model organization as Tenant → Company → Branch, retaining the existing profile per Branch. Common School defaults may be added to shared company settings with campus overrides. Keep current branch-owned academic-year records; do not silently collapse same-named years across campuses. A future organization calendar template can link them without changing historical ownership.

Bring a minimal shared Employee contract forward before teacher integration in Phase 4; expand it into leave/payroll in Phase 7. This resolves the prompt's dependency ordering without making School own an employee master.

## L. Recommended routes and commands

Preserve existing URLs. Add API resource groups under `/api/v1/school/`; maintain existing shared routes for accounting, users, inventory and future HR.

| Area | Proposed browser routes | API groups / commands |
|---|---|---|
| Foundation | `/school`, existing `/school/academic-years`, `/school/settings`; `/school/academics/{classes,sections,subjects,offerings,timetable}` | Existing years/terms; classes, sections, subjects, offerings; authorized campus lookups through Branch |
| Admissions/SIS | `/school/admissions`, `/school/admissions/:id`, `/school/students`, `/school/students/:id` | admissions, students, enrollments; `admissions/{id}/convert`, transfer/withdraw commands |
| Families/teachers | `/school/people/{guardians,families,teachers}`, detail routes | guardian/family relationships, teacher assignments; shared employee references |
| Daily academics | `/school/attendance`, `/school/assignments`, `/school/exams`, `/school/results` | attendance sessions/bulk corrections; submissions, exams, marks draft/submit/approve/publish; report-card revisions |
| Promotion | `/school/academics/promotions` | preview and confirm commands with persisted batch/version |
| Finance | `/school/finance/{overview,fee-structures,invoices,payments,outstanding}` | fee generation preview/confirm, invoice links; authorized shared receipt/allocation commands |
| Operations | `/school/{communication,discipline,library,transport,activities,meetings,documents}` | Corresponding domain resources; health behind a distinct permission |
| Reports/search | `/school/reports`, report detail | School runner in shared report catalog; scoped search providers; shared export jobs |
| AI/automation | Copilot panel, `/school/settings/automation` | Typed tools, prepared actions/confirm, rule/run history via shared gateway |
| Portals | `/school/portal/{guardian,student,teacher}` | Self/children/assignments APIs with relationship policies, not unrestricted admin endpoints |

Keep REST reads separate from audited commands. Existing `/school/academic-years` remains valid even if Academics becomes a grouped destination; introduce aliases/redirects without breaking bookmarks.

## M. Recommended navigation

Keep School as one industry workspace. Top-level groups: Overview, Admissions, Students, Academics, Attendance, Assignments, Exams & Results, Finance, People, Communication, Operations, Reports, Settings. Academics contains calendar/classes/sections/subjects/assignments/timetable; Operations groups library, transport, discipline, activities, meetings and documents. Sensitive health views are contextual and separately authorized.

Link to shared HR/Payroll, Accounting, Inventory and Users using the existing workspace routing conventions; do not duplicate their pages. Hide undelivered destinations rather than creating placeholder pages. Filter navigation and command results by entitlements and permissions, while backend checks remain authoritative. Portal navigation shows only the user's daily tasks and authorized child/self context.

## N. Implementation sequence and phase gates

| Phase | Scope and required exit evidence |
|---|---|
| 1 — this report | Architecture/gaps/integration plan; preserve existing work; stop |
| 2 | Harden profile/year/term validation, tenant/campus policy and lifecycle; add levels/classes/sections/subjects/offerings as foundation; additive migrations and exact-action UI permissions; negative isolation and concurrency tests |
| 3 | Admission → reusable guardian/family → Student → Enrollment; validated import preview, conversion idempotency and preserved transfer history |
| 4 | Minimal shared Employee contract, School teacher extension/assignment, conflict-safe timetable, daily/period attendance and correction audit |
| 5 | Assignments/submissions, assessment weighting, marks moderation/publication, report-card versions and promotion preview/commit; validate complete academic cycle |
| 6 | Shared non-stock billing and allocation gaps first, then fee structures/discounts → invoice → receipt → posted ledger → reconciliation; financial regression suite |
| 7 | Shared HR leave/payroll expansion; School workload/absence integration; communication templates/audiences/delivery and announcements |
| 8 | Library, transport, activities, discipline/health, meetings/actions, private documents and shared asset issue/return integration |
| 9 | Real role-aware command center, searchable report center, saved filters, asynchronous exports and documented metric definitions |
| 10 | Authorized read tools, evidence-based insights, explicit-confirmation prepared actions and durable automation; adversarial authorization tests |
| 11 | Guardian/student/teacher portals on previously tested object policies; responsive/tablet flows, mobile navigation integration |
| 12 | PostgreSQL/load/accessibility/security/offline hardening, realistic tenant demo seed, operational documentation and full regression acceptance |

Security, audit, tests, loading/error states and performance are part of every phase, not deferred entirely to Phase 12. Produce a reviewable diff, migration notes and exit-test evidence for each phase. Do not count planned tables/routes or placeholder metrics as delivered workflows.

## O. Risks and backward compatibility

| Priority | Risk | Mitigation |
|---|---|---|
| Critical | Current worktree contains many unrelated modifications and untracked School files | Preserve baseline; keep future changes scoped; no blanket reset, staging or migration regeneration |
| Critical | Cross-tenant principal link and missing campus policy | Resolve and test before expanding sensitive data |
| High | School initial migration depends on untracked platform migration `0018_alter_agreementacceptance_created_by_and_more` | Verify complete migration graph and delivery order; do not ship School migration alone or rewrite applied migrations |
| High | Current-year race, validation bypasses, soft-archive inconsistencies | Add constraints after conflict inspection and transaction locking; explicit lifecycle commands |
| High | Shared sales path can move inventory for fee items | Tested shared non-stock billing semantics and regression checks for retail/restaurant/gym |
| High | Current shared payment/AR semantics do not cover requested family/advance/historical accounting | Additive allocation model and reconciliation; preserve existing tenders; no balance import shortcuts |
| High | Shared finance, tenancy and routing already being edited for other verticals | Small compatible extensions and regression tests across affected consumers |
| High | Existing roles global/elevated; portals introduce child-related data | No broad new role grants; explicit object and campus access; audit elevated access |
| High | Shared HR/secure documents/automation are absent or partial | Treat as shared prerequisites with clear owners, not fictional available integrations |
| Medium | Branch/profile currency and timezone differ from finance/current date helpers | Define company currency authority and campus timezone policy; avoid silently changing accounting currency |
| Medium | New portal/web data incorrectly assumed to sync offline | Register scoped sync entities deliberately; honor shared finance authority and conflict policy |
| Medium | Reports/exports aggregate all rows and some selectors seed defaults on read | Move provisioning out of read-only tools; bounded selectors/background exports; permission-aware caching |
| Medium | Earlier School plans conflict with actual implementation | Reconcile matrices as implementation begins; this report records current baseline |

Migration strategy: add tables/nullable transitional fields, backfill deterministically with tenant/campus consistency reports, quarantine ambiguous records, then enforce constraints. Preserve existing UUIDs, routes, codenames and financial source identifiers. Preview destructive/merging data corrections separately. Do not run migrations on production during Phase 1. Rollback should disable new capabilities without deleting academic/financial history.

## P. Files/modules expected to change later

| Scope | Files/directories | Reason |
|---|---|---|
| Phase 2 primary | `backend/apps/school/models/{academic,profile}.py`, services, new serializers/repositories/policies, additive migrations | Harden existing foundation and add academic entities |
| Phase 2 API | `backend/api/v1/school/{urls,views}.py` (split by resource as it grows) | Validation, permission/campus enforcement, resource endpoints |
| Phase 2 UI | `frontend/src/modules/school/`, `services/api/school.ts` | Typed contracts, academic pages, real server pagination and states |
| Phase 2 registration | `apps/authentication/bootstrap.py`, `app/workspaceRoutes.tsx`, `app/routes/modules.tsx`, `navigation/{moduleWorkspaces,businessWorkspaces}.ts` | Incremental permissions/routes/navigation; preserve existing registration |
| Shared fix candidate | `backend/core/utils/pagination.py` | Validate pagination centrally with shared contract regressions |
| Future billing/accounting | `apps/sales/models/sales.py`, sales services, `apps/finance/events/event_types.py`, posting/mapping/rule/reversal services and relevant selectors | Non-stock billing, allocations, mappings, dimension-safe posting and reconciliation |
| Future shared services | `apps/notifications`, `apps/reports/services/packs/school.py` (new), shared HR/documents/automation/tool gateway modules (new) | Add missing shared capabilities once their phases are authorized |
| Future clients | Shared command search, document templates, mobile nav, `mobile/staff`, portal pages; sync catalog/policy only for supported entities | Integrate School in existing clients without duplicating engines |
| Verification/docs | New School unit/integration/frontend tests; `docs/school`; future `apps/platform/demo/school.py` | Executable acceptance and truthful capability tracking |

Registration in `config/settings/base.py`, `api/v1/urls.py` and module/business seeds already exists; do not recreate it. Modify only if a new shared capability actually needs installation or changed dependency metadata.

## Q. Files/modules that should not be modified for Phase 2

Preserve POS checkout/cart/receipt behavior, pharmacy fulfillment, restaurant/cafeteria operations, gym billing, hotel/rental/travel/project workflows, and their existing migrations. Reference their patterns without refactoring them as part of School foundation.

Do not replace shared User, Role, Tenant, Company, Branch, Account, JournalEntry, Invoice, Payment, Warehouse, Supplier, Notification or AuditLog; extend their existing services only when a concrete later-phase gap requires it. Do not globally switch tenant manager behavior to solve a local School issue without a separately tested cross-module change.

Leave production databases/media, secrets/environment files, `.git`, `.agents`, `.codex`, deployment volumes, Nginx/TLS and infrastructure settings untouched. Do not rewrite the existing School initial migration because it is untracked; deployment/application status must first be established. No shared engine or client rewrite belongs in Phase 2.

## R. Test strategy and audit validation

No executable School-specific tests were found in `backend/tests`, the School app or frontend School directory. Earlier `SCHOOL_TEST_MATRIX.md` is a plan, not test evidence.

| Suite | Required cases |
|---|---|
| Foundation/security | Two tenants and two campuses in one tenant; unauthorized lists/details/writes/summary/exports; principal FK injection; no-tenant calls; module disabled/dependency missing; host/JWT mismatch; direct-grant/revoke and action permissions |
| Academic integrity | Duplicate/current-year races, invalid/null dates/status/page sizes, exam bounds, child-term checks on year edits, close/archive/activate transitions, profile restoration, audit snapshots |
| SIS/admissions | Duplicate conversion retries, shared guardian siblings, import validation/preview, transaction rollback, historical transfer/promotion/repetition/graduation, guardian access revocation |
| Scheduling/attendance | Teacher/room/class overlap, inactive/wrong assignment, uniqueness by session, correction reason/audit, local date boundaries, bulk atomicity and absence trigger deduplication |
| Exams/results | Decimal weighted calculations, missing/absent/exempt policy, pass bands/rank configuration, draft autosave conflict, publication lock, authorized revision, immutable report-card version |
| Finance | Fee/discount rounding, non-stock tuition, single issuance under retries, partial/multiple allocations, advance/credit/overpayment, refund/reversal, closed period, unbalanced rejection, posting failure rollback, GL/AR and dimension reconciliation |
| HR/operations | Employee reuse without forced login, payroll approve/post/pay controls, leave/workload integration, private documents, library concurrent lending and transport capacity/effective periods |
| AI/automation | Tool permission and tenant/campus/object checks, malicious retrieved instructions, no raw SQL, stale/replayed/foreign confirmation, permission revocation before execution, worker retry and recipient authorization |
| UI/accessibility | Backend-aligned actions, real pagination/search, load/empty/error/forbidden/offline distinction, stale request cancellation, keyboard grids/dialog focus and mobile/tablet layouts |
| Regression/performance | Existing affected shared tests; full PostgreSQL migrations and locking tests; SQLite desktop compatibility; bounded query counts and data-volume tests; secure exports and sync replay |

Use existing pytest/DRF integration patterns and frontend Vitest. Add PostgreSQL CI coverage for concurrency and database semantics that SQLite cannot prove. Confirm API performance against the repository's general <200ms target for ordinary endpoints and <2s dashboard target using representative data; define separate batch/job budgets. Generate realistic, repeatable demo data through the same validated services, including two campuses and a second tenant for isolation scenarios.

Focused baseline command, run from `backend/`:

```bash
DEBUG=False python3 -m pytest tests/unit/test_module_system.py tests/unit/test_tenancy_context.py tests/unit/test_journal_immutability_step37.py tests/unit/test_rbac_bootstrap.py
```

Result: **22 passed, 1 failed** in 157.66 seconds. The existing failure is `test_role_permissions_dict_only_references_known_codenames`: role `read_only` references undefined permission `travel.customers.view`. No application code was changed to address it. Resolve this baseline catalog inconsistency when permission bootstrap changes are authorized; do not silently drop the travel permission or broaden grants.

The shell has no `python` alias; the initial `python3` attempt was blocked by an inherited `DEBUG=release` value that Django's configuration parser rejects. The successful test run used a command-local `DEBUG=False` override and the repository's in-memory SQLite test configuration. No environment file was edited. These are shared-dependency checks, not proof of School-specific correctness, PostgreSQL concurrency, production deployment or full regression success.

`git diff --check` passed for existing tracked changes. The new audit document was separately checked for trailing whitespace and A–R coverage. Only this new document was intentionally added in Phase 1.

## PHASE 1 STATUS

- **Existing capabilities:** School campus profile, academic years/terms, basic dashboard, seven API patterns, three frontend pages, module registration, coarse permissions and audit calls.
- **Reusable capabilities:** Tenant/branch/IAM, workspace design system, billing records, central accounting, inventory/procurement, notifications, audit, reporting, jobs, print/PDF and client/sync infrastructure.
- **Missing capabilities:** Complete academic/SIS/finance/operations workflows, employee/payroll foundation, relationship/campus policy, private documents, School reports/portals, AI and durable automation.
- **Critical risks:** Cross-tenant principal assignment; missing campus restrictions; activation/integrity gaps; uncommitted migration dependencies; fee billing stock side effects and incomplete shared allocation semantics.
- **Recommended implementation:** Extend the existing School foundation, resolve validation/security/lifecycle gaps first, then follow the user's 12-phase sequence with shared prerequisites and tested end-to-end gates.
- **Estimated affected modules:** Phase 2: School backend/API/frontend, authentication permission bootstrap and workspace routing/navigation, plus a focused shared pagination fix if selected. Later phases additionally touch sales/customers, finance, shared HR, inventory, notifications, reports, documents, automation/AI, mobile and sync.
- **Ready for Phase 2: YES — planning readiness only.** The next bounded foundation scope and prerequisites are identified. Existing School functionality is not production-certified. Start only when the user explicitly says **PROCEED TO PHASE 2**.

Phase 1 stops here. No Phase 2 code or schema changes have been made.

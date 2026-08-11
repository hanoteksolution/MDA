# Project Management Architecture

## Purpose

Project Management is a **business workspace** inside Safari ERP. It reuses shared engines (Sales, Purchasing, Inventory, Finance, HR, Customers, Suppliers) and adds project-specific dimensions, workflows, and reporting.

Construction is an **industry profile** within the same workspace (`project_type=construction`), not a separate ERP.

## Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend workspace (/project/*)                            │
│  Dashboard · Projects · Budget · WBS · Tasks · Workforce…   │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST /api/v1/projects/*
┌───────────────────────────▼─────────────────────────────────┐
│  apps.project_management                                      │
│  Models · Services · Serializers · Audit                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Shared engines                                               │
│  finance · purchases · inventory · sales · customers · hr   │
└─────────────────────────────────────────────────────────────┘
```

## Module Boundaries

| Layer | Location | Responsibility |
|---|---|---|
| Platform registration | `apps.platform` | Module catalog, tenant enablement, API path gates |
| Permissions | `apps.authentication.bootstrap` | `projects.*`, `project.budget.*`, workforce, travel |
| Domain models | `apps.project_management.models` | Tenant-scoped project entities |
| Business logic | `apps.project_management.services` | Validation, workflows, audit, code generation |
| API | `api/v1/projects` | DRF views, pagination, permission checks |
| UI | `frontend/src/modules/projects` | Workspace pages, CRUD, dashboard KPIs |

## Phase 2–3 Deliverables (Projects)

### Data model: `Project`

- Tenant + branch scoped (`TenantScopedModel`, `BaseModel`)
- Unique `(tenant, branch, project_code)`
- Lifecycle status graph: draft → planning → approved → active → … → closed
- Financial baseline fields (budget, contract, revenue, cost, profit)
- Optional links: `client`, `project_manager`, `cost_center`
- Archive via `is_archived` + soft delete

### Service: `ProjectService`

- `summary`, `list_projects`, `get_project`, `create_project`, `update_project`
- `update_status` with guarded transitions
- `soft_delete_project`, `restore_project`, `duplicate_project`
- Audit on all mutations via `write_audit`

### API endpoints

| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/projects/summary/` | `projects.view` |
| GET/POST | `/api/v1/projects/` | view / create |
| GET/PATCH/DELETE | `/api/v1/projects/{id}/` | view / update / archive |
| POST | `/api/v1/projects/{id}/status/` | update or approve |
| POST | `/api/v1/projects/{id}/restore/` | update |
| POST | `/api/v1/projects/{id}/duplicate/` | create |

### Frontend routes

| Route | Page |
|---|---|
| `/project` | Dashboard (KPI summary) |
| `/project/projects` | Project list |
| `/project/projects/new` | Create form |
| `/project/projects/:id` | Detail + workflow |
| `/project/projects/:id/edit` | Edit form |

## Future Phases (Planned Attach Points)

| Phase | Entity | Attach to Project |
|---|---|---|
| 5 | Budget | `ProjectBudget` FK → `Project` |
| 6 | WBS | `WbsNode` tree FK → `Project` |
| 7 | Tasks | `ProjectTask` FK → WBS node |
| 9 | Construction | Site → Building → Floor → Unit hierarchy |
| 11+ | Workforce | Worker types, attendance, daily wage with rate history |
| 24+ | Accounting | Journal postings dimensioned by `project_id` + cost center |

## Workforce Cost Chain (Later)

```
Project → Building → Floor/Unit → WBS → Task → Worker
  → Attendance → Daily Wage (historical rate) → Project Cost → Central Accounting
```

Daily wage rate changes apply **forward only**; past attendance rows retain the rate at time of work.

## Construction Hierarchy (Phase 9)

```
Project → Site → Building → Floor → Unit/Apartment → Rooms
  → Work Packages → Tasks / Materials / Labor / Costs
```

## Integration Rules

1. **Never duplicate** purchasing, inventory, or GL logic — call shared services with project dimensions.
2. **All mutations** write audit logs (`module=project_management`).
3. **Permissions** are fine-grained per entity action; API checks match UI gates.
4. **Tenant isolation** via `apply_tenant_scope` on every query.
5. Feature is complete only when DB + model + migration + service + API + permissions + full CRUD UI + workflow + audit + tests exist.

## Current Status

### Project Management
- ✅ Phases 1–25 domain entities (Projects through Billing + accounting preview)
- ✅ Frontend workspace routes for core + operations domains
- ✅ Unit API tests (`test_project_management_crud.py`)
- 🟡 Shared PO/GRN/Documents project-dimensioning; full GL posting; mobile

### Travel Agency
- ✅ Destinations, Packages, Travelers, Bookings, Flights, Hotel stays, Visas, Commissions
- ✅ Dashboard summary + FE CRUD pages
- ✅ Unit API tests (`test_travel_agency_crud.py`)
- 🟡 Shared finance contextualization; deferred insurance/transport/quotations/itineraries

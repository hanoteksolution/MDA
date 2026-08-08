# Implementation Roadmap

**Date:** 2026-08-08  
**Stack:** Django + Vite React (not Next.js)

Status: `done` · `in_progress` · `next` · `later`

| Phase | Name | Status | Notes |
|---|---|---|---|
| 1 | Existing system audit | **done** | This folder + prior `docs/CURRENT_SYSTEM_AUDIT.md` |
| 2 | Architecture & domain | **done** | Target + shared engines + CAE docs |
| 3 | Workspace registry | **done** | FE `businessWorkspaces.ts` + hub |
| 4 | Shared capability registry | **done** | Documented; engines KEEP |
| 5 | Tenant workspace config | **later** | Derive from TenantModule; table deferred |
| 6 | Dynamic navigation | **done** | Switcher + sidebar + URL→tab sync |
| 7 | Workspace dashboards | **next** | Use existing summary APIs; dedicated headers |
| 8 | CRUD audit | **done** | `CRUD_COMPLETION_MATRIX.md` |
| 9 | Create pages | **done** | Warehouse, journal, pharmacy batch + gym/hotel/property `/new` |
| 10 | Update pages | **done** | Vertical PATCH APIs + dedicated edit routes |
| 11 | Detail pages | **in_progress** | Gym member, hotel reservation, property unit shells |
| 12 | Delete / archive / restore | **in_progress** | Soft delete on vertical masters; journal reverse (never mutate posted) |
| 13 | Bulk actions | **later** | After list standard |
| 14 | Forms & validation | **later** | Unsaved guard, Save & New |
| 15–21 | Restaurant → Retail depth | **in_progress** | Kitchen + housekeeping + guests tabs; master U/D APIs shipped |
| 22 | CAE integration | **KEEP** + **in_progress** | Journal reverse API + CoA write shipped; BU map gaps remain |
| 23 | Reporting | **KEEP** / **EXTEND** | Bind packs to workspace |
| 24 | Demo tenant | **KEEP** / **EXTEND** | Futsal seeder; finance/pos stubs |
| 25 | Subscription entitlements | **KEEP** | |
| 26 | React Native | **later** | Same workspace model |
| 27 | Security | **KEEP** / **EXTEND** | Audit writes on vertical + finance mutations; isolation tests remain |
| 28 | Performance | **later** | |
| 29 | Automated FE/E2E tests | **in_progress** | Vitest unit tests; Playwright E2E later |
| 30 | Production hardening | **later** | |

## This delivery (Phase 9–12 + 22 + 29 slice)

1. Vertical master PATCH/DELETE APIs (menu, table, room, guest, property, tenants).
2. Dedicated `/new` + `/:id` + `/:id/edit` for gym members, hotel reservations, property units.
3. CoA write + journal reverse (`POST /finance/journal/:id/reverse/`).
4. Audit writes on mutations + fine-grained perms (`gym.members.create`, …).
5. Vitest unit tests; Playwright E2E later.

## Non-goals now

Rewrite POS/Sales/Finance. Next.js migration. Schema-per-tenant. Per-industry accounting apps.

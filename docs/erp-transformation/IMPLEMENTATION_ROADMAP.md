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
| 9 | Create pages | **in_progress** | Warehouse, journal, pharmacy batch FE shipped; dedicated `/new` routes next |
| 10 | Update pages | **next** | Vertical PATCH APIs + FE |
| 11 | Detail pages | **later** | Master data `:id` shells |
| 12 | Delete / archive / restore | **later** | Soft delete + accounting void |
| 13 | Bulk actions | **later** | After list standard |
| 14 | Forms & validation | **later** | Unsaved guard, Save & New |
| 15–21 | Restaurant → Retail depth | **in_progress** | Kitchen + housekeeping + guests tabs live; master U/D APIs next |
| 22 | CAE integration | **KEEP** + **next** | Reverse API, BU map gaps, expense BU |
| 23 | Reporting | **KEEP** / **EXTEND** | Bind packs to workspace |
| 24 | Demo tenant | **KEEP** / **EXTEND** | Futsal seeder; finance/pos stubs |
| 25 | Subscription entitlements | **KEEP** | |
| 26 | React Native | **later** | Same workspace model |
| 27 | Security | **KEEP** / **EXTEND** | Audit writes + isolation tests |
| 28 | Performance | **later** | |
| 29 | Automated FE/E2E tests | **later** | |
| 30 | Production hardening | **later** | |

## This delivery (Phase 1–9 slice)

1. Transformation docs (this directory).
2. Workspace URL ↔ mega-page tab sync (gym, hotel, restaurant, pharmacy, property, futsal).
3. Create CTAs using **existing** APIs: warehouses, pharmacy batches, manual journals.
4. Restaurant **Kitchen** tab + Hotel **Housekeeping** tab (real filtered UI, not dead aliases).

## Non-goals now

Rewrite POS/Sales/Finance. Next.js migration. Schema-per-tenant. Per-industry accounting apps.

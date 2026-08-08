# Dashboard Architecture

**Date:** 2026-08-07  
**Status:** PHASE 08 — widget registry + module cards + finance KPIs

---

## Current

| Dashboard | State |
|-----------|-------|
| Main `/dashboard` | Retail/POS KPIs — **KEEP** |
| Finance KPI strip | **DONE** — `DashboardFinanceStrip` (`finance.view`, ledger when authoritative) |
| Widget registry | **DONE** — `DashboardWidgetService` + `GET /dashboard/widgets/` |
| Module cards | **DONE** — `DashboardModuleCards` composes from registry + loaders |
| Finance page | Embedded detail — **KEEP** |
| Reports packs | Gym/Pharmacy + Hotel / Restaurant / Property (module-gated) |

---

## Composition rule

Widgets register against **module codes** (`gym`, `pharmacy`, …) or empty module + permission (finance).  
Main dashboard / RN query enabled TenantModule set + permissions.

**BusinessType must not drive widget selection.**

### Backend
`apps/platform/services/dashboard_widget_service.py` — catalog + `list_for_actor`  
API: `GET /api/v1/dashboard/widgets/`  
Catalog includes `finance_ledger_kpis` (permission `finance.view`, no TenantModule required yet).

### Frontend
`modules/dashboard/widgets/registry.tsx` — vertical loaders + `filterDashboardWidgets`  
`DashboardModuleCards` — module overview cards  
`DashboardFinanceStrip` — revenue / expenses / net profit / cash from `GET /finance/summary/`

---

## Target (later)

Optional user-layout preferences; optional dedicated `finance` TenantModule seed.

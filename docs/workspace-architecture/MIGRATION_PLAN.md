# Migration Plan

**Date:** 2026-08-08  
**Status:** Incremental — do not rewrite working modules

---

## Classification of current implementation

| Area | Verdict | Action |
|---|---|---|
| POS / Sales / Inventory / Purchases / Customers / Suppliers | **KEEP** | Shared engines; alias into workspaces |
| Finance CAE + `BusinessUnit` | **KEEP** | One books; optional BU filter later |
| Gym / Pharmacy / Restaurant / Hotel apps | **EXTEND** | Become workspace packs |
| Property + housing + office apps | **REFACTOR** | One Property workspace; housing/office = features |
| Futsal app | **EXTEND** / billing **MIGRATE** | Keep venue; fold ledger into sales |
| Retail business types (no app) | **KEEP** | Retail workspace over engines |
| `Tenant` / presets / `TenantModule` / entitlements | **KEEP** / **EXTEND** | Activation source |
| `Module` industry seeds | **REFACTOR** (compat) | Treat as workspace activation codes |
| RBAC `HasPermission` | **KEEP** | |
| Hub chrome (HubShell, KPIs, search) | **KEEP** | Re-key cards to industries |
| `MODULE_WORKSPACES` flat catalog | **REFACTOR** | `businessWorkspaces.ts` |
| Sidebar hard-coded `navSections` | **REFACTOR** | Generate from workspace map |
| `workspaceFromPath` / switcher | **REFACTOR** | Industry prefix wins |
| `postLogin` | **EXTEND** | Count industry workspaces |
| Industry tab-shell pages | **KEEP** then **MIGRATE** tabs → URLs | Phase 2 |
| Flat `/pos` `/sales` hub cards | **DEPRECATE** as top-level hub | Remain as capability routes |
| Housing / office hub peers | **MIGRATE** under Property | |
| Mobile staff nav catalog | **EXTEND** later | Same split |
| `TenantAwareManager` unused flag | **DEPRECATE** or finish | Unrelated |
| New Workspace Django tables | **DEFER** | Increment 1 derives from TenantModule |

---

## Increments

### Increment 1 (this change) — UX + registry, no engine rewrite

1. Docs in `docs/workspace-architecture/`.
2. FE `businessWorkspaces.ts` registry (workspaces, capabilities, features, nav).
3. Hub `/modules` shows **Your Business Workspaces** (Restaurant, Gym, Pharmacy, Hotel, Property, Retail, Futsal) + Finance/Admin.
4. Switcher lists industries, not POS/Sales/Inventory peers.
5. Sidebar generated from focused workspace capabilities; links `/restaurant/pos` etc.
6. Alias routes: same page components, `WorkspaceGate` sets brand + focus.
7. Keep `/pos`, `/sales`, `/inventory`, `/housing`, `/office` working.
8. `postLogin` uses industry card count.
9. Brand color follows industry workspace (already via `activeWorkspace`).

### Increment 2 — URL IA inside industry homes

- `/gym/members`, `/hotel/reservations`, `/pharmacy/batches` as tab deep-links on existing pages.
- `/restaurant/dashboard` alias.
- Dashboard aggregate strip by workspace.

### Increment 3 — backend serializer

- `GET /platform/workspaces/` derived from TenantModule (still no new tables unless needed).
- Optional `finance` engine module in `MODULE_SEEDS`.

### Increment 4 — persistence (only if required)

- `TenantWorkspace` / capability / feature tables.
- Property: collapse housing/office TenantModules into features.
- Futsal billing onto Invoice.

### Increment 5 — mobile staff

- Same industry-first catalog as web.

---

## Non-goals (do not do now)

- Rewrite PosPage / SalesPage / FinancePage.
- Duplicate models per industry.
- Schema-per-tenant or schema-per-workspace.
- New permission system.
- Blocking on cafeteria as a separate Django app (use restaurant engine + POS profile).

---

## Rollback

Increment 1 is additive: old routes remain. Revert FE registry + hub + alias routes if needed; engines untouched.

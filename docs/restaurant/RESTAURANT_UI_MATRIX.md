# RESTAURANT_UI_MATRIX

Frontend stack in repo: React + TypeScript + Vite (not Next.js).

## Existing Restaurant UI

| UI Area | Path | Status | Notes |
|---|---|---|---|
| Restaurant workspace page | `/restaurant` | PARTIAL | Single mega-page with tabs |
| Kitchen tab | `/restaurant/kitchen` | PARTIAL | Reuses same page, no station workflow |
| Menu tab | `/restaurant/menu` | PARTIAL | Inline create, no dedicated forms |
| Tables tab | `/restaurant/tables` | PARTIAL | Inline create, no floor plan |
| Cafeteria alias | `/cafeteria*` | PARTIAL | Same component as restaurant |
| Shared POS alias | `/restaurant/pos` | PARTIAL | Uses shared POS page |

## Missing Dedicated Pages

| Entity | `/new` | `/:id` | `/:id/edit` | Status |
|---|---|---|---|---|
| Menu Category | MISSING | MISSING | MISSING | MISSING |
| Menu Item | COMPLETE | COMPLETE | COMPLETE | PARTIAL |
| Table | MISSING | MISSING | MISSING | MISSING |
| Order | MISSING | MISSING | MISSING | MISSING |
| Modifier Group/Modifier | MISSING | MISSING | MISSING | MISSING |
| Recipe/Ingredient | MISSING | MISSING | MISSING | MISSING |
| Floor/Table Group | MISSING | MISSING | MISSING | MISSING |
| Kitchen Station | MISSING | MISSING | MISSING | MISSING |

## UX Quality Assessment

- DataTable is used for list rendering: **COMPLETE**
- Inline forms are functional but non-enterprise for scale: **NEEDS_REFACTOR**
- No robust empty/error/loading strategy per resource section: **PARTIAL**
- No deep actions row (view/edit/archive/duplicate/export) for key entities: **MISSING**
- No audit/timeline panel for order detail: **MISSING**

## Mobile (RN) Snapshot

- `RestaurantWorkspaceScreen.tsx` shows KPI cards only.
- No mobile order/menu/table/kitchen workflows yet.
- Status: **PARTIAL**

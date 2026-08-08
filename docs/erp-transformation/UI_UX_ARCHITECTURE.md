# UI / UX Architecture

## Reality

Vite SPA + existing design tokens (`--primary` per workspace tone). Hub is glass + KPIs (Linear/Stripe-inspired, original Safari language). Do not add neon noise.

## Shells

| Shell | Route | Role |
|---|---|---|
| HubShell | `/modules` | Enterprise workspace hub |
| AppShell | industry + engines | Sidebar from workspace map + ModuleSwitcher |

## Page types (target design system)

Reuse what exists: `PageLayout`, `DataTable`, `EmptyState`, `FormPageLayout`, `FormSection`, `KpiCard`, `TabNav`, `appDialog`.

Add when implementing Detail/Create standards:

- `EntityDetailLayout` (header + tabs + audit)
- `ConfirmArchiveDialog` (context, not naked `window.confirm`)
- `UnsavedChangesGuard`
- Global Create (`N` / `+`) — permission filtered, workspace-aware

## List standard

Search · filters · sort · pagination · export · refresh · **primary + Create** top-right · empty state with CTA.

## Create / Edit standard

Breadcrumbs · back · title · sections · validation · Save / Save & New / Save & Close / Cancel · loading · errors.

Industry product forms = base ProductForm + profile fields (pharmacy/restaurant/gym), not three apps.

## Workspace dashboards

Today: industry mega-page KPIs + `/dashboard` aggregate. Target: `/restaurant/dashboard` dedicated strip (revenue, orders, tables, kitchen, low stock) using existing summary APIs.

## Dark / light

KEEP via `uiStore` + workspace brand tokens.

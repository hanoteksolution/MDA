# Dynamic Navigation

**Date:** 2026-08-07  
**Status:** Implemented (PHASE 07) — see also [NAVIGATION_SWITCHER.md](./NAVIGATION_SWITCHER.md)

---

## Current (KEEP / EXTEND)

`frontend/src/layouts/Sidebar/Sidebar.tsx` — static section list filtered by:

```text
user.permissions AND enabled_modules (useModules) AND activeWorkspace (soft focus)
```

Header **ModuleSwitcher** lists workspaces from enabled modules (`moduleWorkspaces.ts`).

---

## Target (remaining)

```text
navigation =
  ModuleRegistry.forTenant(enabled)
    .filterByFeatures(tenant features)
    .filterByPermission(user)
    .sort(display_order)
```

Nav item metadata from API `Module.route` / catalog — FE map is interim.

### Module switcher (CREATE) ✓

Header: `[ Workspace ▼ ]`

```text
Overview → /dashboard
Gym → /gym
POS → /pos
Inventory → /inventory
Finance → /finance
…
```

Built from enabled modules, not BusinessType.

### Route guards (EXTEND)

Already: middleware `MODULE_DISABLED` / `MODULE_DEPENDENCY`. FE: `PermissionGuard module=` + `useModules` (usable set) hide + redirect deep links.

---

## Multi-module example

Gym + Cafeteria enabled → sidebar shows both trees + shared POS/Inventory/Finance. Sidebar must not hardcode “this is a gym+cafeteria business.”

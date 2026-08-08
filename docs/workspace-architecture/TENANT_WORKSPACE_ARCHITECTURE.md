# Tenant Workspace Architecture

**Date:** 2026-08-08  
**Status:** Target — no new DB tables in increment 1

---

## Tenant may enable many workspaces

Example: Lifestyle Center

```
Enabled TenantModules: gym, restaurant, pos, sales, inventory, purchases
→ User sees: Gym · Cafeteria/Restaurant · Finance · Administration
```

Example: Somfutsal

```
Enabled: futsal, pos, sales, inventory, …
→ User sees: Futsal · Retail (if engines used standalone) · Finance
```

---

## Live building blocks (KEEP)

| Piece | Role |
|---|---|
| `Tenant` + `TenantDomain` | SaaS shop + host |
| `BusinessType` / `BusinessPreset` | Default industry pack on onboard |
| `TenantModule` | Enabled engines + industry codes |
| `TenantModule.configuration.features` | Feature flags |
| `PlanModule` + entitlements | Subscription caps |
| `User.role` / permissions / branch | RBAC + location |
| `enabled_modules` / `module_features` on `/me` | FE hydration |

There is **no** `Workspace` Django model today. Increment 1 **does not add one**. Activation = existing `TenantModule` industry codes + engine deps.

---

## Conceptual entities (later, not increment 1)

When we need first-class persistence:

| Entity | Purpose |
|---|---|
| `BusinessWorkspace` | Catalog row (restaurant, gym, …) |
| `BusinessWorkspaceCapability` | Default engines embedded |
| `BusinessWorkspaceFeature` | Default industry features |
| `TenantWorkspace` | Tenant activation + label + config |
| `TenantWorkspaceCapability` | Override engines |
| `TenantWorkspaceFeature` | Override features |
| `WorkspaceNavigationItem` | Optional server-driven nav |
| `WorkspaceConfiguration` | POS profile pin, default warehouse, … |

Until then: derive `TenantWorkspace` **in memory** on FE (and later a small backend serializer) from `enabled_modules` + `module_features` + `BusinessType`.

---

## Entitlements

`EntitlementService` already: starter = core engines; business/enterprise = industry modules; trial uses preset.

**KEEP.** Workspace UI only shows industries the tenant can actually use (`usable_module_codes`).

---

## RBAC

**KEEP** `HasPermission` + module gates. Do not invent workspace-scoped roles in increment 1.

A user with `gym.view` + `pos.access` sees Gym workspace and its POS capability. A user with only `gym.view` sees Gym without POS.

---

## Multi-tenancy

Shared PostgreSQL schema + `tenant_id`. Workspaces are **not** schemas. **KEEP** `TenantScopedModel` + `apply_tenant_scope`.

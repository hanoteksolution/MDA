# Module Architecture

**Date:** 2026-08-07  
**Status:** Design — extend `Module` / `TenantModule` / `PlanModule`

---

## Separation rules

| Concept | Answers | Authoritative store |
|---------|---------|---------------------|
| Business Type | What kind of org? | `BusinessType` |
| Business Preset | What to recommend at signup? | `BusinessPreset` (**CREATE**) |
| Subscription | What is entitled/paid? | `PlanModule` |
| Module | What capability exists in product? | `Module` |
| Feature | What inside the module? | `ModuleFeature` (**CREATE**) |
| Tenant config | What is enabled now? | `TenantModule` (+ features) |
| Branch | Where? | `Branch` |
| Business Unit | Which P&L slice? | `BusinessUnit` (**KEEP**, PHASE 09) |

Never create modules named `GYM_CAFETERIA` or `HOTEL_RESTAURANT`. Those are **presets**.

---

## Existing models (KEEP)

### `Module`
Catalog row: `code`, `name`, `description`, `category` (core/industry/addon), `is_active`, `sort_order`.

### `TenantModule`
`UNIQUE(tenant, module)` + `enabled`.

### `PlanModule`
Plan entitlement set.

### Services
`module_service.sync_tenant_modules`, `enabled_module_codes`, `ModuleGateMiddleware`, `EntitlementService`.

---

## EXTEND Module metadata

Add fields (or JSON `metadata`) without breaking seeds:

```text
route, dashboard_route
icon
dependencies[]          # required module codes
optional_dependencies[]
is_core
supports_mobile
supports_pos
supports_inventory
supports_finance
display_order           # alias sort_order
```

---

## CREATE ModuleFeature / TenantModuleFeature

```text
ModuleFeature(module, code, name, is_default, is_required)
TenantModuleFeature(tenant, module_feature, is_enabled, configuration)
```

Example Gym features: `members`, `classes`, `attendance` (lockers later).

**Interim (STEP 37 / 68):** pharmacy + gym features live on `TenantModule.configuration["features"]` via `ModuleFeatureService` (catalog in code). Promote to tables if querying/reporting needs it.

---

## Activation security (KEEP + harden)

Frontend must not be sole gate. Enable path:

```text
Module exists?
  → Plan entitled?
  → Dependencies satisfied?
  → Platform/tenant admin permission?
  → Write TenantModule
  → Seed default features
  → Seed account mappings if needed
  → Audit log
```

---

## Finance module

Today finance is permission-gated, not in module catalog. Target: add optional catalog code `finance` as **core-ish** always entitled on business/enterprise plans, still overridable for edge tenants.

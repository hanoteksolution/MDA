# Module Entitlement Architecture

## Existing authority

The current architecture correctly separates:

- `BusinessType`: organization classification and defaults.
- `BusinessPreset`: recommended module configuration.
- `Module`: canonical capability definition and dependency metadata.
- `TenantModule`: tenant-selected enabled state.
- `PlanModule`: commercial plan inclusion.
- Role/user permissions: what an individual may do.

Effective access is the intersection of active tenant, usable subscription, plan inclusion, enabled tenant module, satisfied dependencies and user permission.

## Provisioning rules

1. Public catalogs expose active module definitions, capabilities, dependencies and plan inclusion without internal configuration.
2. Preset selection proposes defaults; it never becomes runtime authorization.
3. Submission sends explicit selected codes.
4. Backend validates codes, expands required dependencies, applies plan constraints and rejects an invalid combination with field-level errors.
5. Provisioning writes `TenantModule` rows using existing `sync_tenant_modules()` and records the selected snapshot.
6. Module defaults are idempotently seeded.

Core/shared engines should remain canonical modules where they already exist. Do not invent duplicate “supermarket” or “construction” engines if those are presets/profiles over retail/project modules.

## Runtime enforcement

Retain `ModuleGateMiddleware` and `TenantAwareJWTAuthentication`, but close coverage gaps:

- Maintain one audited API-prefix registry and test every module route.
- Add service-level entitlement checks for sensitive operations invoked outside HTTP (Celery, management commands, sync, direct service calls).
- Apply module and permission checks independently.
- Return stable `403 MODULE_DISABLED`, `MODULE_NOT_IN_PLAN` or `MODULE_DEPENDENCY` envelopes.
- Filter navigation and routes from the same backend entitlement response for UX only.

The current path map does not cover general finance, reports, dashboard, notifications or admin as commercial modules. Decide whether these are always-core capabilities or explicitly gated modules before pricing is published.

## Catalog consistency risk

Module codes exist in backend seed data and frontend workspace definitions. Backend remains authoritative; frontend definitions should become presentation metadata keyed by backend code. Tests must fail when an API route references an unknown module or a preset contains a code absent from the module catalog.

## Plan changes

Enabling a module requires plan inclusion and dependencies. Disabling must reject dependent enabled modules unless the caller confirms an atomic cascade. Downgrades should calculate impact before mutation and preserve data in read-only state rather than deleting module data.

## Existing tenant migration

- Backfill missing `TenantModule` rows from the existing explicit `provisioned_modules` snapshot, preset or business-type defaults in that priority order.
- Compare rather than overwrite existing explicit configurations.
- Produce a dry-run discrepancy report.
- Preserve platform-admin access semantics while preventing tenant admins from changing commercial plan inclusion.


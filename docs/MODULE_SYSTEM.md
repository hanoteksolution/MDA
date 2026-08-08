# Module System (STEP 08)

Shared-schema feature modules control which capabilities a tenant may use.

## Models

- `Module` — catalog (`pos`, `inventory`, `sales`, `purchases`, `pharmacy`, `restaurant`, `gym`, `futsal`)
- `TenantModule` — per-tenant `enabled` flag (unique on tenant+module)

Defaults come from `BusinessType.default_modules` when a shop is provisioned (`sync_tenant_modules`).

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/platform/modules/` | Catalog |
| GET/PUT | `/api/v1/platform/tenants/:id/modules/` | List / set `enabled_modules` |

Auth `/me` and login payloads include `enabled_modules: string[]`.

## Gating

`ModuleGateMiddleware` maps path prefixes (e.g. `/api/v1/futsal/` → `futsal`) and returns:

```json
{ "success": false, "code": "MODULE_DISABLED", "details": { "module": "futsal" } }
```

If the module is enabled but a required dependency is off (orphan TenantModule row):

```json
{ "success": false, "code": "MODULE_DEPENDENCY", "details": { "module": "pharmacy", "missing": ["inventory", "pos"] } }
```

`/me` `enabled_modules` is the **usable** set (enabled + deps). Platform admins bypass. Plan entitlements remain STEP 24.

## Frontend

`useModules()` + Sidebar `module` field on nav items (permission AND module must pass).  
`PermissionGuard` optional `module` prop redirects deep links when the module is not usable.

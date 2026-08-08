# Domain Management

**Status:** STEP 05 complete — host resolution + JWT host match  
**Date:** 2026-08-07

---

## Request flow

```
Request
  → Host / X-Forwarded-Host
  → TenantResolutionMiddleware
  → resolve_tenant_from_hostname()
  → request.tenant + core.tenancy context
  → TenantAwareJWTAuthentication (mismatch → 401 TENANT_HOST_MISMATCH)
  → Application
```

Never trust a client-supplied `tenant_id` as the sole authority.

---

## Base domain

```
TENANT_BASE_DOMAIN=erp.safaritechno.com
PLATFORM_HOSTS=          # optional extra apex hosts
TENANT_HOST_ENFORCEMENT=True
```

Tenant primary hostname:

```
{slug}.{TENANT_BASE_DOMAIN}
# example: arabica.erp.safaritechno.com
```

Platform hosts (no shop tenant bound): apex base, `www`/`api`/`admin`/`app`/`platform` prefixes, `localhost`, `127.0.0.1`, `tauri.localhost`.

---

## Resolution modes

| Mode | Meaning |
|------|---------|
| `platform` | SaaS control plane host |
| `tenant` | Matched `TenantDomain` or `{slug}.base` |
| `unknown` | Unrecognized host / missing subdomain tenant |

---

## Models

| Model | Role |
|-------|------|
| `TenantDomain` | Maps hostname → tenant |
| `Tenant.slug` | Subdomain key |
| `TenantSettings` | Branding used by public resolve |

---

## APIs

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/v1/platform/resolve-host/` | Public | Branding payload for login UI |
| `GET /api/v1/platform/business-types/` | Platform | Types + reserved slugs |
| `GET /api/v1/platform/slug-check/?slug=` | Platform | Availability |
| `GET/POST .../tenants/<id>/domains/` | Platform | Domain list/add |
| `GET/PUT .../tenants/<id>/settings/` | Platform | Settings |

Response headers (when resolved): `X-Tenant-Mode`, `X-Tenant-Slug`.

---

## Enforcement

- Login on a tenant host rejects users who cannot access that tenant (`403 TENANT_HOST_MISMATCH`)
- Authenticated API calls on a tenant host use `TenantAwareJWTAuthentication`
- Platform admins may access tenant hosts
- Shop-group managers may access tenants in their group

---

## Frontend

- `frontend/src/config/tenantHost.ts` — parse host + `resolveTenantHost()`
- Login page loads resolve-host for tenant-aware branding

---

## Ops notes

- Wildcard DNS + TLS: `*.erp.safaritechno.com`
- `ALLOWED_HOSTS` must include `.erp.safaritechno.com` (or explicit hosts) in production

---

## Next

**STEP 22 done** — Central ReportService, gym/pharmacy packs, catalog + CSV export.

**STEP 23 done** — Celery/Redis, notification model, scheduled scans, in-app drawer.

**STEP 24 done** — Plan modules, entitlement middleware, limits, paywall banner.

**STEP 25 done** — Self-serve onboarding wizard (catalog, slug, provision).

**STEP 26 done** — Density tokens, denser tables, empty/loading, module nav, POS touch.

**STEP 27 done** — OpenAPI, throttling, `X-Tenant-Slug` header, mobile meta/bootstrap endpoints.

**STEP 28 done** — Gym member portal API + Expo app (`mobile/gym-member/`).

**STEP 29 done** — Sync outbox, idempotent cloud ingest, finance sync rules, queue UX.

**STEP 30 done** — Login lockout, security headers, upload validation, production secret checks.

**STEP 12b done** — Cashier sessions (open/close, variance) + sale refunds (partial return, stock restore). API + `pos.ts` client; tests `test_pos_step12b.py`.

**STEP 34 done** — Health probes (database/cache/ready), JSON production logging, monitoring overlay, restore drill checklist.

Foundation roadmap steps **03–34** complete; STEP 12 deferred items (sessions/refunds) closed. Remaining foundation DoD: desktop sync tenant auth, Celery verify on staging. Additional tracks: restaurant/KDS, import/export, CRM.

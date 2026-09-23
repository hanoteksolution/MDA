# Current Architecture Audit

## Scope and evidence

This is a read-only Phase A/B audit performed on 2026-09-01. No DNS, TLS, proxy, database, or production application change is part of this phase.

The repository is an existing shared-schema multi-tenant ERP:

- Frontend: React 19, TypeScript, Vite, React Router, Tailwind, Zustand. It is not Next.js.
- Backend: Django/DRF, SimpleJWT, PostgreSQL, Redis, Celery.
- Runtime: Docker Compose; host Nginx terminates TLS and proxies to the Docker Nginx SPA on port 8010.
- Tenant namespace: `{slug}.erp.safaritechno.com`.

## Existing tenant and organization model

| Existing component | Current responsibility | Reuse decision |
|---|---|---|
| `Tenant` | Organization/workspace identity, slug, lifecycle, locale, demo state | Reuse; extend lifecycle only if required |
| `TenantDomain` | Unique hostname-to-tenant mapping | Reuse; add normalized status metadata only if needed |
| `Company` / `Branch` | Legal/operating company and branches | Reuse |
| `TenantSettings` | Branding, locale, fiscal and module snapshots | Reuse; avoid making JSON the source of durable workflow state |
| `User`, `Role`, `Permission` | Existing IAM and tenant membership | Reuse; tenant owner maps to a tenant admin role, never platform admin |
| `BusinessType` | Broad industry profile | Reuse; do not treat as entitlement |
| `BusinessPreset` / `BusinessPresetModule` | Recommended module packs | Reuse |
| `Module` / `TenantModule` | Module catalog and tenant enablement | Reuse as entitlement source |
| `SubscriptionPlan`, `PlanModule`, `TenantSubscription` | Plan limits, included modules and trial/active state | Reuse |

There is no separate `Shop` model; “shop” is terminology used around `Tenant` plus `Company` and `Branch`. Creating a second shop/tenant system would be harmful.

## Existing provisioning paths

1. `OnboardingService.provision()` validates a small public payload and calls `PlatformService.create_shop()` inside an atomic transaction.
2. `PlatformService.create_shop()` creates tenant, domain/settings defaults, company, branch, warehouse, owner, subscription and module links.
3. `DemoTenantService` also delegates foundation creation to `PlatformService.create_shop()` and then performs demo seeding, partially satisfying the desired shared engine.
4. `PlatformService.provision_tenant_defaults()` creates default settings/domain and applies preset/module defaults.

Reusable strengths:

- Atomic database provisioning already exists.
- Tenant slug and domain uniqueness exist in PostgreSQL.
- Passwords use Django `create_user()` hashing.
- Module dependencies are backend-authoritative.
- API path module gates and JWT host/tenant mismatch checks exist.
- Plan entitlements and subscription write blocking exist.
- Demo seeding is already asynchronous-capable through Celery.
- Image verification and size/type limits exist for company logos.
- Explicit audit infrastructure and idempotent accounting bootstrap exist.

## Current onboarding limitations

- Public UI has five steps: business, type, subdomain, plan, owner. Preset and module information is returned but not fully exposed in the wizard.
- No complete company profile, logo step, review, agreements, provisioning status or success workflow.
- Registration immediately creates an active trial tenant and returns JWTs. Email ownership is not verified.
- Idempotency is based on replaying the same slug, username and plaintext password supplied again. There is no client idempotency key or durable registration record.
- Slug availability uses only `Tenant.slug`; final domain collision and custom-domain semantics are not expressed by a reservation object.
- `slugify()` silently transforms unsafe input instead of strictly rejecting dots, schemes, Unicode lookalikes and other invalid syntax.
- Public onboarding endpoints use only global anonymous throttling; no registration/slug-specific rate scopes exist.
- No terms/privacy acceptance model, version, timestamp or evidence.
- No `ProvisioningJob`/stage model, retry classification or operator recovery view.
- No verification/welcome email configuration or templates were found.
- `PlatformService.create_shop()` does not explicitly initialize the chart of accounts during registration; finance currently initializes lazily when accessed.
- Provisioning does not emit the required structured stage/audit events.

## Routing and application behavior

- `/` redirects unauthenticated users to `/login`; no public landing page exists.
- `/onboard` hosts the existing self-service wizard.
- The same Vite SPA is served on public and tenant hosts.
- Tenant route visibility uses frontend permission/module guards, while backend `ModuleGateMiddleware` enforces mapped API prefixes.
- Unknown subdomains still receive the SPA from Nginx. The API resolves them as `unknown`, but a dedicated workspace-not-found route is absent.

## Security/configuration findings

- Production `ALLOWED_HOSTS` supports the tenant suffix through a leading-dot entry.
- Host tenant resolution trusts `Host`/`X-Forwarded-Host`; live host Nginx forwards `Host` but not `X-Forwarded-Host`, which avoids one ambiguity.
- `TenantResolutionMiddleware` binds context but deliberately leaves manager-level enforcement disabled. Isolation therefore depends on explicit queryset scoping plus authentication/middleware.
- CORS is an explicit static list. The example does not include tenant origins; same-origin SPA API calls do not need CORS, which is preferable.
- JWTs are stored in browser local storage. Cookies are not the primary web authentication mechanism.
- Baseline headers exist, but no Content-Security-Policy is configured.
- Production HSTS defaults to one year with `includeSubDomains=True` even though the current certificate does not cover arbitrary tenant hosts. This is unsafe until wildcard TLS is complete.
- `SECURE_SSL_REDIRECT` defaults false; host Nginx currently performs HTTP-to-HTTPS redirect.

## Compatibility and migration risk

Existing tenants, domain rows, module snapshots, users and subscriptions must remain authoritative. The design must be additive, backfill existing rows without changing hostnames, and preserve `/api/v1/onboarding/*` during a compatibility window.


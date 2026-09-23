# Implementation Plan

## Gate

This document is a design only. Implementation begins only after explicit `PROCEED`, DNS-provider decisions and a tested backup/rollback path.

## Work sequence

### 1. Infrastructure readiness

- Confirm DNS provider and issue an apex + wildcard DNS-01 certificate in staging.
- Add default reject hosts, TLS 1.2/1.3 policy, safe proxy headers and HTTPS redirects.
- Centralize public/tenant URL settings and remove HTTP production fallbacks.
- Verify certificate renewal before enabling public registration.

### 2. Additive data model

- Add registration, verification, agreement and provisioning job models.
- Add required unique constraints and indexes.
- Add any missing company profile fields and domain status without replacing existing models.
- Provide migrations, rollback SQL/steps and legacy backfill commands with dry-run mode.

### 3. Provisioning service

- Introduce `TenantProvisioningService` modes and stage API.
- Wrap existing `PlatformService.create_shop()`, preset/module, subscription and finance bootstrap services.
- Add durable idempotency and safe retry classification.
- Route demo creation through the same foundation while retaining seeders.
- Add structured events and explicit audit writes.

### 4. Public APIs

- Versioned public catalogs for types, presets, modules and plans.
- Strict subdomain check with suggestions and scoped throttle.
- Registration create/status, email verify/resend and logo workflow.
- Consistent response fields including request ID, status, data and field errors.
- Preserve old onboarding endpoints as adapters during migration.

### 5. Frontend public experience

- Add host-aware public route shell and landing routes to the existing React/Vite app.
- Build catalog/pricing/solution pages from API data.
- Replace the current five-step wizard with the designed flow, review, verification, real provisioning status and success.
- Add unknown-workspace and suspended/billing-safe experiences.
- Add accessible responsive behavior and tests.

### 6. Platform administration

- Extend existing tenant pages with domain, module, subscription, provisioning, security and audit tabs.
- Add failed-registration/job queues and safe retry actions.
- Never expose or reset passwords directly; use established reset/invitation workflows.

### 7. QA and release

- Run backend, frontend, integration, E2E, isolation, security and TLS matrices.
- Back up database/media and record current images/config/certificate.
- Deploy additive migrations, infrastructure, backend and frontend in staged order.
- Create one staging registration, then limited production canary.
- Monitor errors, provisioning latency, email and certificate health.

## Likely files to modify

Backend:

- `backend/apps/platform/models/*`, migrations and admin exports
- `backend/apps/platform/services/onboarding_service.py`, `platform_service.py`, `demo_tenant_service.py`, domain/module/entitlement services
- new provisioning, registration, verification and agreement services
- `backend/api/v1/onboarding/*` or a new compatible public API package
- `backend/config/settings/base.py`, `production.py`, `backend/.env.cloud.example`
- audit, email, throttling and tests

Frontend:

- `frontend/src/app/router.tsx`
- public layout/pages/components and registration feature package
- `frontend/src/services/api/onboarding.ts`
- `frontend/src/config/tenantHost.ts`, `publicCloudUrl.ts`
- auth routing, workspace-not-found, onboarding checklist and tests

Infrastructure/docs:

- `infrastructure/nginx/erp.safaritechno.com.conf`
- replace/retire `sync-erp-cert.sh` and update `TLS_AUTOSYNC.md`
- Docker build arguments/environment examples, smoke scripts and deployment runbooks

## Blockers requiring decisions

1. DNS provider and supported DNS-01 automation/plugin.
2. Product policy: verify email before tenant creation or create pending tenant first.
3. Email delivery provider, sender domain and templates.
4. Legal Terms/Privacy URLs, versions and retention requirements.
5. Owner identity policy: globally unique username vs email-based/multi-workspace membership.
6. Which modules are always-core versus commercially selectable.
7. Trial duration and payment/manual activation policy.
8. Logo/object storage target for multi-node scale.
9. Whether public contact/analytics/anti-bot providers are approved.


# Rollback Plan

## Principles

All rollout changes are additive and backward compatible. Existing tenant hostnames and records are never deleted/recreated. Separate application rollback from DNS/TLS rollback; a valid wildcard certificate should normally remain even if the new registration feature is disabled.

## Pre-release capture

- Verified PostgreSQL backup and restore drill; media/object-storage backup.
- Current Docker image digests, Git revision, Compose files and environment variable inventory.
- `nginx -T`, active site links, certificate lineage/SAN/expiry and renewal configuration.
- Export counts/checksums for tenants, domains, users, subscriptions and tenant modules.
- Feature flag defaults public registration off until smoke gates pass.

## Deployment order

1. Backup and readiness check.
2. Additive database migrations.
3. TLS/DNS ingress validation in staging, then production wildcard certificate without removing the old lineage until verified.
4. Backend with compatibility endpoints and registration disabled.
5. Frontend public routes.
6. Enable internal/canary registration, then limited public release.

## Rollback triggers

- Any cross-tenant access or owner privilege escalation.
- Certificate mismatch, renewal failure, redirect loop or widespread HTTPS failure.
- Existing tenant login/module regression.
- Partial/duplicate tenant creation or accounting corruption.
- Elevated 5xx/provisioning failure rate beyond agreed threshold.

## Application rollback

1. Disable registration feature flag and keep existing tenant application online.
2. Revert API/frontend to recorded image digests using the production volume overlays.
3. Do not reverse additive migrations immediately; old code must ignore new tables/nullable fields.
4. Mark in-flight registrations paused/failed and prevent automated retries.
5. Validate existing tenant login, module APIs, finance and health endpoints.

## TLS/ingress rollback

- Before reload, retain a tested copy of the current Nginx config and certificate lineage.
- If the new vhost fails syntax or routing checks, restore the prior config and reload.
- If wildcard issuance fails before activation, retain the existing SAN certificate and keep public registration disabled.
- If activation causes trust/routing problems, switch certificate paths back to the recorded valid lineage. Do not fall back to HTTP or self-signed certificates.
- Keep wildcard DNS unless it is proven to route incorrectly; DNS rollback has propagation delay and does not by itself correct certificate problems.

## Data recovery

Failed atomic provisioning should leave no tenant foundation. For committed external-side-effect failures, keep a non-ready registration/job and retry idempotently. Never automatically delete an existing tenant based solely on a failed job. Any cleanup command must require an explicit registration ID, verify no business activity, produce a dry run and write an audit event.

## Migration reversal

New workflow tables can remain dormant after application rollback. Destructive schema reversal occurs only in a maintenance window after confirming no retained registration evidence is legally or operationally required. Existing `Tenant`, `TenantDomain`, company, user, module and subscription data is not rolled back or rewritten.

## Post-rollback verification

- Apex and representative existing tenant HTTPS/browser tests.
- Health/readiness, login, module gate and cross-tenant isolation.
- Celery and email queues stopped or compatible with the reverted version.
- No registration endpoints create new state.
- Incident timeline, affected registrations and recovery decisions recorded.


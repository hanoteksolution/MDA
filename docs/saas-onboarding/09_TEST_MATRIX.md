# Test Matrix

## Backend

| Area | Required cases |
|---|---|
| Catalogs | Active-only data, stable codes, preset/type distinction, no internal leakage |
| Slug | Strict syntax, reserved list, normalization, length, Unicode, dots/schemes/ports, suggestions |
| Race/idempotency | Concurrent same slug, same key replay, changed payload conflict, double click/network retry |
| Registration | Required fields, plan/module constraints, terms versions, logo validation, no plaintext persistence |
| Verification | Expiry, single use, resend rate, wrong token, already consumed, safe responses |
| Provisioning | Tenant/company/branch/warehouse/owner/subscription/modules/accounting/audit, atomic rollback |
| IAM | Tenant owner not platform admin, password validators/hashing, permission assignment |
| Entitlements | Hidden and direct API denial, dependencies, plan exclusion, downgrade behavior |
| Lifecycle | Pending, trial, active, past-due/read-only, suspended, cancelled, archived |
| Isolation | Host mismatch, IDOR, queryset isolation, task/service context, platform exceptions |
| Abuse/security | Scoped throttles, host attacks, mass assignment, upload polyglots, error redaction |
| Recovery | Retryable/final failures, stage replay, email failure after commit, operator retry |
| Compatibility | Existing tenant/domain/demo/subscription login and APIs remain unchanged |

## Frontend

- Public and tenant root routing, navigation, CTA paths and authenticated redirects.
- Every wizard step, back/edit, validation, autosave excluding passwords, preset/module dependency UX.
- Logo preview/replace/remove and server error handling.
- Availability debounce, stale result handling and submit-time conflict.
- Password show/hide, strength and accessible confirmation.
- Review/agreements, double-submit prevention and idempotency.
- Verification, actual provisioning stages, success, retry and manual-intervention states.
- Workspace-not-found and suspended experiences.
- Desktop, tablet and mobile layouts; keyboard, focus, screen reader, contrast and reduced motion.

## E2E canary

Run the requested hospitality scenario from public landing through verified registration, secure tenant login, Restaurant/Cafeteria visibility, unauthorized Pharmacy denial, finance initialization, audit verification and cross-tenant isolation. Add a second concurrent browser competing for the same slug.

## DNS/TLS/ingress

| Check | Hosts |
|---|---|
| DNS A/AAAA consistency | apex, known tenant, random wildcard label |
| Certificate trust/SAN/chain/expiry | apex, existing tenant, new staging tenant, random wildcard label |
| HTTP→HTTPS and no loop | apex and tenant |
| Unknown host safety | unknown tenant and unrelated Host header |
| TLS negotiation | TLS 1.2/1.3 accepted; obsolete protocols rejected |
| Browser matrix | Chrome, Edge, Firefox, Safari, Android, iOS |
| Content | no HTTP assets/API/email links; CSP report clean |

## Operational acceptance

- Wildcard renewal dry run succeeds.
- External expiry and health monitoring alerts are tested.
- Backup restore and application rollback are rehearsed.
- Metrics expose attempts, conflicts, verification, success, failure and latency.
- Fresh logs contain request IDs and no secrets.

## Current baseline gaps discovered

Existing onboarding tests cover catalog, reserved slug, creation, password-based replay and basic API flow. They do not cover concurrency, strict label rejection, module customization, agreements, verification, durable jobs, scoped throttles, TLS, full rollback or E2E. A separate existing integration fixture currently references an unknown `products` module code; catalog/test consistency must be repaired before using the entire integration suite as a release gate.


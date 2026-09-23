# Security Threat Model

## Assets and trust boundaries

Critical assets are tenant data, credentials, JWTs, subscription/module entitlements, domains, audit evidence, finance configuration, uploaded branding and platform-admin authority. Trust boundaries exist at public browser→host Nginx, Nginx→Docker web/API, anonymous registration→provisioning, Celery→database, and platform operator→tenant controls.

## Principal threats and controls

| Threat | Current exposure | Required control |
|---|---|---|
| Host-header tenant confusion | Resolver consumes forwarded/host values | Ingress allowlist, trusted proxy chain, strict one-label parser, unknown-host default server |
| Cross-tenant access/IDOR | Explicit scoping is required; manager enforcement is disabled | Mandatory service/query scoping, host/JWT match, isolation tests, consider enforced request context |
| Module bypass | Path middleware covers many routes, not all execution paths | Complete route registry plus service/task-level checks |
| Privilege escalation | Owner role is payload-normalized to admin today | Server-fixed tenant-owner/admin role; reject elevated flags and role IDs |
| Registration abuse | Global anonymous rate only | Scoped throttles, email verification, honeypot, optional Turnstile, monitoring |
| Subdomain enumeration/race | Availability endpoint and pre-check | Generic responses/suggestions, rate limit, atomic DB constraints, idempotency |
| Password/token leakage | Password accepted by public API; no verification workflow | Never log/persist plaintext, Django validators, short-lived hashed verification tokens, log redaction |
| Duplicate provisioning | Password-based replay | Durable idempotency key and payload fingerprint |
| Upload attacks | Existing MIME/size/Pillow checks | Reuse validation, strip metadata/re-encode where appropriate, safe storage names, SVG prohibited |
| XSS/mixed content | No CSP; frontend has an HTTP IP fallback | HTTPS-only URL generation, CSP report-only rollout, output encoding |
| CSRF/CORS | JWT header auth, CSRF middleware, static CORS | Keep same-origin web API; do not wildcard CORS; audit any cookie-auth endpoints |
| JWT theft | Tokens stored in local storage | Evaluate in-memory/access + secure host-only refresh cookie; never share auth cookie across tenant suffix |
| Open redirect | Future success/workspace URLs | Generate server-side from normalized domain; allowlist relative redirects |
| TLS name mismatch | Finite SAN certificate on wildcard ingress | Apex + wildcard DNS-01 certificate before self-service release |
| Sensitive error leakage | Generic API envelope now exists | Request IDs, safe categories, server-only traces |

## Cookie/session decision

Current web authentication is JWT/local-storage based. If cookies are introduced, they should be host-only by default, `Secure`, `HttpOnly` for refresh/session tokens, and appropriately `SameSite`. Do not set `Domain=.erp.safaritechno.com`; that would expose a credential to every tenant subdomain and increase cross-tenant compromise impact.

## Public endpoint controls

Use dedicated DRF scoped throttles for catalog, slug check, registration, verification and resend, with stricter limits on mutating endpoints. Add maximum payload/body sizes, uniform timing where practical, idempotency, safe email responses and abuse metrics. CAPTCHA remains configurable and risk-triggered rather than mandatory.

## Browser security

Retain nosniff, frame denial, referrer and permissions policies. Design a CSP from actual build assets and API/image requirements, deploy report-only, resolve violations, then enforce. Do not add `unsafe-eval`. HSTS rollout follows the TLS document.

## Data/privacy

Agreement evidence should store policy version and minimum defensible request metadata. Logs must exclude passwords, tokens, secrets and full documents. Define retention/deletion for failed registrations and verification records. Audit all platform actions affecting domains, owners, modules, subscriptions and lifecycle.

## Security release gates

Threat-focused tests must include concurrent slug registration, malformed/Unicode slugs, Host/X-Forwarded-Host attacks, cross-tenant JWT use, unauthorized direct module APIs, elevated-role injection, replay mismatch, upload polyglots, throttling and unknown host behavior.


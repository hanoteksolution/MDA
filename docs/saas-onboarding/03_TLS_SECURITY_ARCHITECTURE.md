# TLS Security Architecture

## Confirmed root cause

The current certificate is trusted but is not a wildcard certificate. The live certificate SAN list contains the apex plus a finite list of tenant hosts. It does not contain `*.erp.safaritechno.com`; for example, `demo-ambakaaro.erp.safaritechno.com` is routed by wildcard DNS/Nginx but is absent from the certificate.

This creates the observed behavior:

1. Wildcard DNS immediately sends every new subdomain to the VPS.
2. Nginx immediately accepts it because `server_name` includes `*.erp.safaritechno.com`.
3. TLS is negotiated before Django can resolve the tenant.
4. Nginx presents the finite SAN certificate.
5. Browsers reject any hostname not already in its SAN list with a name mismatch.

The `sync-erp-cert.sh` workaround polls tenant domains every 15 minutes and expands the certificate using HTTP-01. It has an unavoidable insecure interval, is limited to 100 SANs, couples certificate issuance to database contents, risks Let's Encrypt rate limits, and cannot scale to 10,000 tenants. Browser differences are timing/cache symptoms, not application behavior.

## Target certificate

Use one publicly trusted certificate containing both:

- `erp.safaritechno.com`
- `*.erp.safaritechno.com`

The wildcard covers exactly one label and intentionally does not cover `branch.tenant.erp.safaritechno.com`. Tenant URLs must remain one label deep.

## Issuance and renewal

Wildcard issuance requires DNS-01. Preferred order:

1. Certbot DNS plugin for the actual DNS provider using a narrowly scoped credential file outside the repository.
2. Provider-neutral delegated `_acme-challenge` automation if supported.
3. Manual DNS-01 only as a temporary bootstrap, not a sustainable renewal design.

The current per-tenant SAN sync job should be retired only after the wildcard certificate is installed, verified and automatically renewable. Renewal must run unattended, validate with a dry run, and reload Nginx only after success.

## Ingress TLS policy

- TLS 1.2 and 1.3 only; remove global TLS 1.0/1.1 support.
- Serve the full chain and matching private key.
- HTTP port 80 redirects valid Safari ERP hosts to the same host over HTTPS.
- Reject other hostnames through a default server rather than reflecting an arbitrary `$host` into redirects.
- Preserve `Host`, set `X-Forwarded-Proto=https`, and configure trusted proxy behavior in Django.
- Add certificate-expiry monitoring and an external probe for apex plus a synthetic wildcard tenant.

## HSTS rollout

Current Django defaults enable a one-year HSTS policy with `includeSubDomains`. Do not rely on that setting until all intended subdomains have valid HTTPS. Roll out in stages after wildcard validation: short max-age without preload, observe, then extend; enable `includeSubDomains` only when the entire relevant namespace is ready. Preload requires separate organizational approval because rollback is slow.

## Verification gate

Before enabling production self-registration, verify apex, existing tenants, a newly created staging tenant and an unknown tenant with `openssl`, `curl`, SSL Labs or equivalent, Chrome, Edge, Firefox, Safari and mobile. Validate SAN coverage, chain, expiry, SNI, redirect behavior, TLS versions, mixed content and proxy loops.


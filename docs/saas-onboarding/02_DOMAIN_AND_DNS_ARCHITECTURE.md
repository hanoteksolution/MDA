# Domain and DNS Architecture

## Canonical strategy

Use exactly one production namespace:

- Public/control-plane host: `erp.safaritechno.com`
- Tenant host: `{slug}.erp.safaritechno.com`
- Example: `arabica.erp.safaritechno.com`

Do not create new tenants at `{slug}.safaritechno.com`. Existing unrelated products on that namespace remain outside Safari ERP.

## Central configuration

Introduce or formalize these settings and consume them in backend, frontend, emails and operations:

| Setting | Production value |
|---|---|
| `PUBLIC_APP_URL` | `https://erp.safaritechno.com` |
| `TENANT_BASE_DOMAIN` | `erp.safaritechno.com` |
| `TENANT_URL_SCHEME` | `https` |
| `PLATFORM_HOSTS` | explicit control-plane host set |
| `VITE_TENANT_BASE_DOMAIN` | `erp.safaritechno.com` |
| `VITE_PUBLIC_APP_URL` | `https://erp.safaritechno.com` |

Remove the frontend fallback to `http://88.222.220.238:8010` for production builds. Domain construction must use a single backend domain service and a matching frontend configuration helper.

## DNS records

The live read-only audit confirms both public and arbitrary tenant labels resolve to `88.222.220.238`, so wildcard A resolution is currently working.

Required provider records:

| Type | Name | Value | Purpose |
|---|---|---|---|
| A | `erp` | `88.222.220.238` | Public host |
| A | `*.erp` | `88.222.220.238` | All one-label tenants |
| TXT | `_acme-challenge.erp` | DNS-01 value/provider-managed | Wildcard certificate issuance |

Avoid individual A records per tenant. Remove conflicting tenant-specific A/AAAA records only after a reviewed inventory. No AAAA response was observed in this audit; if IPv6 is introduced, both apex and wildcard AAAA must reach the same TLS ingress.

## Host validation and resolution

Ingress accepts only `erp.safaritechno.com` and one-label `*.erp.safaritechno.com`. Django then classifies:

1. Explicit platform host → public/control plane.
2. Exact active `TenantDomain` → tenant.
3. Valid one-label suffix and matching `Tenant.slug` → compatibility fallback.
4. Otherwise → unknown host, with no tenant context.

Target state should make verified `TenantDomain` authoritative and retain slug fallback temporarily for legacy rows. Unknown subdomains should render a generic workspace-not-found page; they must not fall through to another tenant or disclose tenant records.

## Slug policy

Strictly accept ASCII labels matching `^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$`, with a product-specific length range such as 2–50. Reject rather than silently transliterate input containing schemes, dots, ports, slashes, whitespace, underscores, wildcard characters or unsafe Unicode.

The reserved-name registry remains centralized and should be expanded with `auth`, `login`, `register`, `signup`, `payments`, `dashboard`, `root`, `system`, `demo`, `ftp`, `smtp` and every actual infrastructure name.

Final uniqueness is enforced by `Tenant.slug` and normalized `TenantDomain.domain` database constraints inside the provisioning transaction. Availability checks are advisory only.

## Provider/API blocker

The DNS provider and availability of a scoped DNS API token cannot be determined from the repository. Wildcard DNS already resolves, but automated DNS-01 renewal requires either a supported Certbot DNS plugin/provider API or a deliberately operated RFC2136/acme-dns mechanism. Credentials must live outside Git with least privilege limited to `_acme-challenge.erp.safaritechno.com` where the provider permits.


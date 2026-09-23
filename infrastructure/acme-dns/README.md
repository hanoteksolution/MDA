# acme-dns — automatic wildcard TLS without a DNS provider API

This gives `erp.safaritechno.com` + `*.erp.safaritechno.com` a Let's Encrypt
wildcard that renews itself forever, so **every tenant subdomain is valid HTTPS
the moment it resolves** — nothing per shop, no insecure window, no 100-SAN cap.

## Why not just use the Hostinger DNS API

`safaritechno.com` is managed through **collaborator access**, not ownership.
Hostinger tokens inherit the permissions of the account that created them, and
collaborator rights do not carry into the API. Verified against the live API:

| Call | Result |
| --- | --- |
| `GET /api/domains/v1/portfolio` | `200` — lists `safaritechno.com` |
| `GET /api/domains/v1/portfolio/safaritechno.com` | `404 [Domains:2006] Domain is not registered at Hostinger` |
| `GET /api/dns/v1/zones/safaritechno.com` | `403 [DNS:4002] Customer does not own` |

RDAP confirms the registrar really is Hostinger, so the domain is fine — the
*token's account* simply is not the registrant. Visible in list endpoints,
rejected by every ownership check. No token generated from this account will
ever pass.

## Why the public acme-dns instance

The original plan was to self-host acme-dns on this VPS. That requires
delegating a zone with an `NS` record, and **Hostinger's DNS editor has no `NS`
record type** — only `A`, `MX`, `AAAA`, `CNAME`, `SRV`, `TXT`, `CAA`. So the
zone must live somewhere already delegated, which means the public instance at
`auth.acme-dns.io`.

The risk of a third-party challenge host is that whoever runs it could satisfy
DNS-01 for our domain. That is closed off with a **CAA `accounturi` pin**
(RFC 8657), which Let's Encrypt enforces: issuance is restricted to our specific
ACME account, so a compromised acme-dns instance still cannot obtain a
certificate.

`config.cfg` and `docker-compose.yml` here are the **self-hosting migration
path**, kept for the day a domain with `NS` support is available. They are not
in use.

## How it works

`_acme-challenge.erp.safaritechno.com` is CNAMEd, once, into an acme-dns
account. acme.sh writes the TXT record there over the acme-dns API; Let's
Encrypt follows the CNAME and validates. Hostinger is never touched again.

Only `_acme-challenge` lookups leave Hostinger. Tenant subdomains keep resolving
from Hostinger, so an acme-dns outage delays renewal (30 days of slack) and
never affects the live ERP.

## Setup

```bash
# 1. Register an acme-dns account (credentials are secrets — mode 0600)
curl -s -X POST https://auth.acme-dns.io/register | sudo tee /root/.acmedns-account.json
sudo chmod 600 /root/.acmedns-account.json

# 2. Register the Let's Encrypt account whose URI the CAA record will pin
/root/.acme.sh/acme.sh --register-account --server letsencrypt \
  --config-home /root/.acme.sh/data
grep ACCOUNT_URL /root/.acme.sh/data/ca/acme-v02.api.letsencrypt.org/directory/ca.conf
```

## DNS records in hPanel

**Add the CNAME first**, using the `fulldomain` from the register response:

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| `CNAME` | `_acme-challenge.erp` | `<fulldomain>.auth.acme-dns.io` | 3600 |

One CNAME covers **both** `erp.safaritechno.com` and `*.erp.safaritechno.com`,
because both validate against the same `_acme-challenge.erp` name.

**Add the CAA only after the production certificate is issued.** A staging
rehearsal uses a different ACME account and would be blocked by the pin:

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| `CAA` | `erp` | `0 issue "letsencrypt.org; accounturi=<ACCOUNT_URL>"` | 3600 |
| `CAA` | `erp` | `0 issuewild "letsencrypt.org; accounturi=<ACCOUNT_URL>"` | 3600 |

Both are live as of 2026-09-22 and verified on `ns1`/`ns2` and public resolvers.

Scope the CAA to `erp`, never the apex: other subdomains (`cafeteria`, `ecomm`,
`myvat`, …) are issued by **certbot under a different ACME account**, and an
apex CAA pin would break their renewals.

## Issue the certificate

See [../nginx/WILDCARD_TLS.md](../nginx/WILDCARD_TLS.md).

## Maintenance

- `/root/.acmedns-account.json` holds the acme-dns credentials. Losing it means
  re-registering and updating the CNAME once. Back it up.
- Rotating the acme.sh ACME account means updating the CAA `accounturi`, or
  issuance will start failing.

## Live values (deployed 2026-09-22)

- acme-dns fulldomain: `b10adab0-c892-4180-a24a-6b9378ca60b6.auth.acme-dns.io`
- ACME account URI: `https://acme-v02.api.letsencrypt.org/acme/acct/3777948196`
- Certificate: `/etc/ssl/mda/erp-wildcard/` — SANs `*.erp.safaritechno.com`, `erp.safaritechno.com`, expires 2026-12-21
- Renewal: acme.sh cron `22 4,10,16,22 * * *`, ARI window 2026-11-21
- Rollback: old SAN cert retained at `/etc/letsencrypt/live/erp.safaritechno.com/`; nginx backup `/root/nginx-erp-conf.bak.20260922-135754`
- CAA: `issue` + `issuewild` live on `erp.safaritechno.com` only; apex and all other
  subdomains carry no CAA, so certbot renewals for `cafeteria`/`ecomm`/`myvat`/
  `amelectronics` are unaffected.

**Rollout status: COMPLETE — wildcard TLS, auto-renewal and CAA pinning all verified.**

# ERP Wildcard TLS

One certificate covers `erp.safaritechno.com` and `*.erp.safaritechno.com`, so
**every tenant subdomain is valid HTTPS the moment it resolves**. Nothing is
provisioned per shop, there is no insecure window after a workspace is created,
and there is no Let's Encrypt 100-SAN ceiling.

This replaces [TLS_AUTOSYNC.md](TLS_AUTOSYNC.md) (per-tenant SAN expansion),
which only secured a hostname *after* a `TenantDomain` row existed and the cron
had re-issued the shared certificate.

## How it works

- Let's Encrypt issues wildcards over **DNS-01 only**.
- The Hostinger DNS API is unavailable to us: `safaritechno.com` is held via
  collaborator access, and Hostinger tokens inherit the creating account's
  ownership, which collaboration does not confer. See
  [../acme-dns/README.md](../acme-dns/README.md) for the verified API responses.
- So validation is delegated to **acme-dns** (public instance, pinned with a
  CAA `accounturi` record) via a one-time
  `_acme-challenge.erp` CNAME. acme.sh writes the TXT record there over the
  acme-dns API; Hostinger is never touched again.
- Installed to `/etc/ssl/mda/erp-wildcard/{fullchain,privkey}.pem`, deliberately
  outside `/etc/letsencrypt/` so certbot's own renewals never collide with it.
- `acme.sh` renews on its daily cron (~60 days) and reloads nginx via the
  `--reloadcmd` recorded at install time.

## Prerequisites

1. DNS: wildcard `A` record `*.erp.safaritechno.com` → VPS, plus the apex `A`.
   (Both already exist.)
2. An acme-dns account and the one-time CNAME — follow
   [../acme-dns/README.md](../acme-dns/README.md) **first**. Nothing below works
   until `dig +short CNAME _acme-challenge.erp.safaritechno.com` returns the
   acme-dns `fulldomain`.
3. `acme.sh` **>= 3.1.5** installed at `/root/.acme.sh`.

## Install acme.sh (once)

```bash
curl -fsSL -o /tmp/acme.tar.gz \
  https://github.com/acmesh-official/acme.sh/archive/refs/tags/3.1.6.tar.gz
tar xzf /tmp/acme.tar.gz -C /tmp
cd /tmp/acme.sh-3.1.6 && ./acme.sh --install \
  --home /root/.acme.sh --config-home /root/.acme.sh/data --nocron
/root/.acme.sh/acme.sh --set-default-ca --server letsencrypt \
  --config-home /root/.acme.sh/data

sudo install -m 0755 infrastructure/nginx/issue-wildcard-cert.sh \
  /usr/local/sbin/issue-erp-wildcard
```

## Issue

```bash
sudo /usr/local/sbin/issue-erp-wildcard --staging   # rehearse against LE staging
sudo /usr/local/sbin/issue-erp-wildcard             # real certificate
```

The script refuses to start if the `_acme-challenge` CNAME is missing, so a
misconfigured delegation fails fast instead of burning an ACME round trip.

Add the CAA `accounturi` pin **after** the production certificate exists — see
[../acme-dns/README.md](../acme-dns/README.md). Adding it earlier blocks the
staging rehearsal, which runs under a different ACME account.

## Cut nginx over

`erp.safaritechno.com.conf` already points at the wildcard paths. Deploy it
**only after** the certificate exists, or nginx will fail to start:

```bash
sudo cp infrastructure/nginx/erp.safaritechno.com.conf /etc/nginx/sites-available/
sudo nginx -t && sudo systemctl reload nginx
```

## Renewal

This repo installs acme.sh with `--nocron`, so add the renewal job explicitly:

```bash
sudo /root/.acme.sh/acme.sh --install-cronjob --config-home /root/.acme.sh/data
```

Verify: `sudo /root/.acme.sh/acme.sh --list --config-home /root/.acme.sh/data`

## Retire the old SAN job

Once the wildcard serves correctly, the per-tenant expansion job is redundant
and will keep re-issuing a certificate nginx no longer reads:

```bash
sudo crontab -l | grep -v sync-erp-cert | sudo crontab -   # drop the cron entry
sudo certbot delete --cert-name erp.safaritechno.com       # only after verifying
```

## Verify

```bash
# any subdomain, including one that does not exist as a tenant
echo | openssl s_client -connect erp.safaritechno.com:443 \
  -servername anything.erp.safaritechno.com 2>/dev/null \
  | openssl x509 -noout -subject -dates -ext subjectAltName
```

Expect `DNS:*.erp.safaritechno.com, DNS:erp.safaritechno.com` and no others.

## Note on missing workspaces

A wildcard makes every subdomain *cryptographically* valid, but the tenant still
has to exist for the app to resolve it. `TenantDomain` hostnames come from the
tenant slug via `build_tenant_hostname`, and slugs are uniquified on collision
(e.g. a workspace named "Baarista" became `baariste19072`), so the live hostname
is not always the name typed at signup. Read the workspace URL from the
registration payload (`RegistrationService.payload` → `workspace_url`), never by
guessing the slug.

## Status

Rollout **complete and verified 2026-09-22**: wildcard issued, nginx cut over,
acme.sh renewal cron active (next window 2026-11-21), and CAA `accounturi`
pinning live on `erp.safaritechno.com` only. Every tenant subdomain — existing
or created in future — is valid HTTPS on first request, with no per-shop step.

Rollback assets retained until the next successful renewal: old SAN cert at
`/etc/letsencrypt/live/erp.safaritechno.com/`, nginx config backup at
`/root/nginx-erp-conf.bak.20260922-135754`.

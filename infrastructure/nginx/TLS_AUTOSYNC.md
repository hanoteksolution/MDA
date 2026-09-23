# ERP TLS Auto-Sync (DEPRECATED)

> **Superseded by [WILDCARD_TLS.md](WILDCARD_TLS.md).** The DNS-01 wildcard
> secures every tenant subdomain immediately, with no per-shop step. This
> HTTP-01 SAN expansion only covered a hostname *after* its `TenantDomain` row
> existed and the cron had re-issued the shared certificate — a new workspace
> was served an invalid certificate until then. Disable the `sync-erp-cert`
> cron once the wildcard is live. Keep this document only as the fallback for
> environments with no DNS API access.

Keeps the `erp.safaritechno.com` certificate SAN list aligned with current
`TenantDomain` hostnames so newly registered shops get HTTPS automatically.

> Long-term preferred: one DNS-01 certificate for `erp.safaritechno.com` +
> `*.erp.safaritechno.com`. Until that is issued, this HTTP-01 expand job is required.

## Install

```bash
sudo install -m 0755 infrastructure/nginx/sync-erp-cert.sh /usr/local/sbin/sync-erp-cert
sudo mkdir -p /var/lib/mda/tls-sync /var/www/html/.well-known/acme-challenge
sudo touch /var/log/sync-erp-cert.log
```

## Run once

```bash
sudo /usr/local/sbin/sync-erp-cert
```

Dry-run:

```bash
sudo /usr/local/sbin/sync-erp-cert --dry-run
```

## Schedule (every minute)

New workspaces need the cert expanded before the first HTTPS redirect. A 15-minute
cron leaves a long insecure window — use every minute (no-op when already covered):

```cron
* * * * * /usr/local/sbin/sync-erp-cert >> /var/log/sync-erp-cert.log 2>&1
```

Registration also writes `/var/lib/mda/tls-sync/request` (and
`media/.system/tls-sync-request`) so the next cron pass picks up the new hostname
immediately after provision.

## Notes

- Script reads domains from `TenantDomain` via `docker compose exec api`.
- Uses `grep -E` (no `rg` dependency).
- Skips renewal when the live cert already contains every required SAN.
- Reloads nginx only after a successful certificate update.
- Let's Encrypt SAN limit is 100 names per certificate — migrate to wildcard before you approach that.

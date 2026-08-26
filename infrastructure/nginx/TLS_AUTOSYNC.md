# ERP TLS Auto-Sync

This keeps the ERP certificate SAN list aligned with current tenant hostnames
(`*.erp.safaritechno.com`) so newly created shop/demo domains become HTTPS
without manual `certbot --expand` each time.

## Install

```bash
sudo install -m 0755 infrastructure/nginx/sync-erp-cert.sh /usr/local/sbin/sync-erp-cert
```

## Run once

```bash
sudo /usr/local/sbin/sync-erp-cert
```

Dry-run (Let's Encrypt staging check):

```bash
sudo /usr/local/sbin/sync-erp-cert --dry-run
```

## Schedule

```bash
crontab -e
```

Add:

```cron
*/15 * * * * /usr/local/sbin/sync-erp-cert >> /var/log/sync-erp-cert.log 2>&1
```

## Notes

- Script reads domains from `TenantDomain` via `docker compose exec api`.
- It only includes names ending in `.erp.safaritechno.com`.
- It skips renewal if the current cert already contains all required SANs.
- It reloads nginx only after a successful certificate update.
- Let's Encrypt SAN limit is 100 names per certificate.

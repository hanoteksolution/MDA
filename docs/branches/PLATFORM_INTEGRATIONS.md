# Platform Admin → Integrations

Date: 2026-09-23. This builds on `BRANCH_SMS_FRAMEWORK.md` and `BRANCH_PAYMENT_FRAMEWORK.md`. The SMS and payment architecture is unchanged: provider, credential, webhook and reconciliation rows are still tenant-scoped, credentials are still Fernet-encrypted, and secrets are still write-only and masked.

## What changed

SMS and payment **provider configuration is platform infrastructure**. Only a global platform administrator can manage it. The check is `PlatformService.is_global_platform_admin`, which covers Super Admin, Platform Admin and superusers. Other platform staff and tenant users are refused, including tenant admins who hold `integrations.manage`, `integrations.payments.reconcile` or `platform.view`.

| Area | Endpoint (under `/api/v1/`) | Who |
|---|---|---|
| Credentials, SMS providers, payment providers | `platform/integrations/{credentials,sms-providers,payment-providers}/[<id>/]` | Global platform admin |
| Webhook events, reconciliation run/list/resolve | `platform/integrations/payments/{webhook-events,reconcile,reconciliation[/<id>/resolve]}/` | Global platform admin |
| Branches of the managed tenant (for binding a provider to a branch) | `platform/integrations/branches/` | Global platform admin |
| SMS templates, message logs, send | `integrations/{sms-templates,sms-logs,sms/send}/` | Tenant users with the existing `integrations.*` permissions (unchanged) |
| Payment intents | `integrations/payments/intents/[<id>/]` | Tenant users with `integrations.payments.*` (unchanged) |
| Provider webhook callback | `integrations/payments/webhooks/<provider_id>/` | Public, HMAC-verified (unchanged) |

- Every platform call must include `tenant_id` (query string, or body on writes). A missing `tenant_id` returns 400. An unknown tenant, or one the admin cannot access, returns 404.
- Credential and branch references must belong to that tenant, or the call returns 400. A provider addressed through the wrong tenant returns 404.
- The old tenant routes `/api/v1/integrations/{credentials,sms-providers,payment-providers,payments/webhook-events,payments/reconcile,payments/reconciliation}` no longer exist.
- The guard and tenant selection are in `backend/api/v1/integrations/platform_access.py`, and the routes are in `platform_urls.py`.

## UI

- **Platform → Integrations** (`/platform/integrations`) has a tenant selector, an overview, SMS providers, payment providers and merchants, webhook events and reconciliation. It reuses the existing integrations views and forms, and the credential flow stays write-only. The route uses `PermissionGuard elevatedOnly`, and the sidebar entry is shown only to elevated users.
- **Settings → Integrations** (tenant) covers operations only: SMS templates, message logs, test SMS, payment transactions and intents. It shows no providers, credentials, webhooks or reconciliation.

## Notes

- The `integrations.manage` permission now only covers creating SMS templates. `integrations.payments.reconcile` no longer grants anything, because reconciliation is platform-only. The permission codes were kept to avoid RBAC churn.
- Reseller or package-level SMS provisioning is not implemented.

## Tests

- Backend: `tests/unit/test_platform_integrations.py` (new) covers the role matrix on every endpoint, the tenant selection rules, cross-tenant references, masked secrets, and the tenant operations that must keep working. `test_integration_secrets.py`, `test_payment_framework.py` (reconciliation is now platform-only) and `tests/integration/test_branch_isolation_sweep.py` were updated to use the platform routes.
- Frontend: the integrations `lib` and `views` tests, plus `navigation/platformIntegrationsNav.test.ts`.

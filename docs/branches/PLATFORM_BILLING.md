# Platform Admin → Billing

Date: 2026-09-23. This builds on `SUBSCRIPTION_AUTO_PAYMENT.md`, `PLATFORM_INTEGRATIONS.md` and `BRANCH_PAYMENT_FRAMEWORK.md`. It adds no models and no migrations.

## What it is

A cross-tenant billing console for platform operators. It is a set of read models over the existing billing rows, plus one audited recovery action.

| Source | Used for |
|---|---|
| `TenantSubscription` | Subscriptions, status, expiry, next billing (the expiry date, following the existing renewal policy) |
| `SubscriptionPayment` | Payments: online checkouts (`intent` set) and manual/legacy requests |
| House-tenant sales `Invoice` (via `SubscriptionPayment.invoice`) | Invoices (checkouts only; legacy requests have none) |
| `ReconciliationRecord` whose intent belongs to a subscription payment | Reconciliation issues |
| `AuditLog` for the tenant, subscription and payment ids | Activation/renewal history and audit |

**Revenue.** Only ledger-backed amounts count: `amount_paid` on paid checkout invoices, which are posted by the central engine. Manually confirmed legacy payments are listed separately as "not posted", because they never reached the books. Nothing is estimated or projected.

**Billing status** is derived per subscription, never stored. In priority order: `review`, `pending` (the latest payment), `overdue` (past expiry), `due_soon` (the existing `needs_payment_alert`), `failed`, `current`, `no_billing`. The table can also filter by `expiring_soon`, meaning active or trial and expiring within `max(warning_days, 7)` days.

## API — `/api/v1/platform/billing/`

These routes are for elevated users only (`IsPlatformBillingAdmin` → `PlatformService.is_global_platform_admin`). Tenant users get 403, including tenant admins holding `platform.view` or `subscriptions.manage`.

| Route | Notes |
|---|---|
| `GET overview/` | Counts, revenue, and `can_recover` |
| `GET subscriptions/` | Params: `search`, `status`, `billing_status`, `plan`, `page`, `page_size` (max 100) |
| `GET tenants/<tenant_id>/` | Plan, timeline, invoices, payments, renewal history, reconciliation, audit |
| `GET payments/` | Params: `search`, `status`, `kind=checkout\|manual` |
| `GET invoices/` | Params: `search`, `status` |
| `GET reconciliation/` | Params: `search`, `status`, `kind` (read-only; resolve in Platform → Integrations) |
| `GET plans/` | Existing plan payload plus subscription count; includes inactive plans |
| `POST subscriptions/<id>/recover/` | Super Admin only; see below |

Paged responses have the shape `{count, page, page_size, results}`. Money values are decimal strings, and responses contain no provider configuration or credentials.

**Plans.** Plans are listed here and created through the existing `POST /platform/plans/`. The backend has no plan update or retire endpoint, so the UI doesn't offer one. That is a known gap.

## Manual subscription recovery (exceptional)

`PlatformBillingService.recover`:

- **Super Admin only.** The caller must have the `super_admin` role, or be a Django superuser without the `platform_admin` role. A Platform Admin can view billing but cannot recover (403).
- **Reason and confirmation.** The body must include a reason of at least 10 characters and `confirm: true`; the value must be the literal boolean `true`.
- **Effect.** It extends the subscription by one billing period, using the same rule as `renew_subscription` (`max(expiry, today) + period`), and sets the status to active. The subscription row is locked while this happens.
- **What it does not do.** It **never** creates or confirms a `SubscriptionPayment`, `Invoice`, `PaymentIntent` or sales `Payment`, and it leaves `last_paid_at` untouched.
- **Audit.** Every recovery writes an audit row with `event=subscription_manual_recovery`, the reason, the before and after values, and `payment_created=false`.

The existing endpoints are unchanged: manual renewal (`subscriptions/<id>/renew/`) and legacy manual payment confirmation (`payments/<id>/confirm/`, which refuses checkout rows).

## UI

- **Routes:** `/platform/billing`, with tabs Overview · Subscriptions · Payments · Invoices · Reconciliation · Plans, and `/platform/billing/tenants/:tenantId`.
- **Access:** both routes use `PermissionGuard elevatedOnly`. The nav item "Billing" appears only for elevated users.
- **Components:** the pages reuse `PageLayout`, `TabNav`, `KpiCard`, the canonical `DataTable` (server paging, search and filters kept in the URL) and `Badge`.
- **Recovery dialog:** it uses `PlatformConfirmDialog`, which gained optional `children` and `confirmDisabled` props. It requires the reason and an acknowledgement checkbox.

## Tests

- **Backend:** `tests/unit/test_platform_billing.py` (12 tests). They cover tenant and anonymous refusal on every endpoint, overview counts and ledger-backed revenue, table search, filters and paging, the payments, invoices, reconciliation and plans tables, tenant detail, a Platform Admin being refused recovery, and the recovery checks: reason and confirmation required, audited, and creating no payment, invoice, intent or receipt.
- **Frontend:** `modules/platform/pages/billing/platformBilling.test.tsx` and the nav visibility cases in `navigation/platformIntegrationsNav.test.ts`.
- **PostgreSQL:** recovery row locking was not run on PostgreSQL. It uses `select_for_update(of=("self",))`, the same pattern as the existing PostgreSQL-verified billing code.

## Not done

- Hormuud/Waafi adapter (MOCK is the only adapter; the production MOCK guard is unchanged).
- Plan edit/retire API.
- Proration.
- Resolving reconciliation from this screen (resolution stays in Integrations).

## Deferred technical debt

- **Repeated manual recovery extends twice.** `recover` locks the subscription (`select_for_update`), so concurrent calls are serialised with no lost update (PostgreSQL-verified in `tests/unit/test_platform_billing_postgresql.py`). But the action is not idempotent: repeating it, for example with a double submit or a retry, extends the subscription by one more billing period each time, with one audit row per call. Not fixed yet. A future fix could use an idempotency key or a "recovered within N minutes" guard.

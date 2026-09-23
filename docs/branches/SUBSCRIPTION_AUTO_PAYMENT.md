# ERP Subscription Checkout & Verified Activation

Date: 2026-09-23. This builds on `BRANCH_PAYMENT_FRAMEWORK.md`, `PLATFORM_INTEGRATIONS.md` and `SMS_RESELLER_BILLING.md`.

**Scope.** Automatic *confirmation*: a subscription activates or renews as soon as a verified provider payment settles. This is **not** recurring auto-debit. The only adapter is MOCK, and no real provider (such as Hormuud/Waafi) has an adapter, because we don't have its API documentation yet.

## Flow (reuses existing architecture; no parallel payment system)

```
Tenant: Billing & Subscription → choose plan → POST /api/v1/billing/subscription/checkout/ (idempotency key)
  → SubscriptionPayment (existing model, extended)  = the subscription invoice / payment request
  → sales Invoice in Safari's house tenant (billing provider's tenant; customer "SUB-<tenant id>")
  → PaymentIntent via PaymentService.create_intent (MOCK / configured provider)
Customer pays → provider webhook /api/v1/integrations/payments/webhooks/<provider_id>/
  → HMAC signature + timestamp window + event-id dedupe      (existing)
  → PaymentService._settle under the intent row lock          (existing: Payment row, invoice PAID,
                                                                Dr Cash / Cr AR journal)
  → SubscriptionBillingService.on_intent_settled              (new hook, same transaction)
       verify → Dr AR / Cr Revenue (post_sale on_account) → plan applied → renew_subscription
       → payment confirmed → audit → tenant notification
```

- **Before activation, the hook checks all of the following** (`_verify`):
  - the payment is still pending;
  - the event came through the configured subscription billing provider;
  - the intent belongs to the provider's (house) tenant;
  - the intent is settled and has a Payment row;
  - the intent's invoice is the payment's invoice;
  - the invoice customer is the subscribing tenant;
  - the intent amount and invoice total equal the price exactly;
  - the currency matches;
  - the subscription is not suspended.

  If any check fails, nothing is activated: the payment goes to `review`, and a `ReconciliationRecord` (unapplied_payment) plus an audit row are written.
- **Handled by the existing flow, with no activation:**

  | Case | What happens |
  |---|---|
  | Forged or stale webhook | Rejected. |
  | Unknown reference | Ignored. |
  | Wrong amount | Reconciliation `amount_mismatch`; not settled. |
  | Failed payment | The intent is marked failed. |
  | Expired intent that later succeeds | Reconciliation `late_success`. |
  | A superseded checkout (its invoice is cancelled) that later succeeds | Reconciliation `unapplied_payment`. |
- **Idempotency.**
  - The intent state machine under its row lock, plus event-id dedupe, means an intent is settled once.
  - The `SubscriptionPayment` row is locked and applied only while pending.
  - `intent` is one-to-one with the payment.
  - Accounting uses the posting idempotency keys (`SALE_COMPLETED:sales:invoice:<id>` and `CUSTOMER_PAYMENT_RECEIVED:sales:payment:<id>`).
  - The subscription row is locked while its expiry is extended.
  - Checkout is idempotent on `(subscription, idempotency_key)`. There is one open checkout per subscription; a newer one supersedes the older one, expiring its intent and cancelling its invoice.
- **Renewal.** Unchanged existing policy (`PlatformService.renew_subscription`): the new expiry is `max(current expiry, today) + billing_period_days`, so a renewal never shortens a subscription. Paying during a trial extends from the trial's end date.
- **Plan change.** There were no upgrade/downgrade rules to reuse, and no proration exists.
  - While a paid period is active, only the current plan can be renewed.
  - When the subscription is in trial or expired, the tenant can switch to another plan, provided current users and branches fit that plan's existing entitlement limits (`max_users` / `max_branches`).
  - A new plan uses its list price, and its negotiated fee is cleared. The current plan keeps `effective_monthly_fee`.
  - **Gaps:** proration, mid-period upgrades, yearly pricing (plans have only `monthly_price`, so billing is monthly only), and refunds.
- **Accounting.** Everything lands in Safari's house-tenant books through the central engine. Nothing is posted until a verified payment arrives, so unpaid or cancelled checkouts never touch the ledger. The receipt is the sales `Payment` row on the paid invoice.

## Security & recovery

- **Tenant API** (`/api/v1/billing/subscription/`): overview, checkout, and `payments/<id>/` (read-only, for polling). Permissions are `billing.subscription.view` and `billing.subscription.pay`, both new and granted to the admin role.
  - These routes and the provider webhook path are exempt from the subscription write-lock, so an expired tenant can still pay.
  - No endpoint lets a client mark a payment paid, and responses contain no provider data.
- **Retired:** `POST /api/v1/platform/payments/waafi-callback/` now returns 410. It was public and unsigned, so anyone could renew any subscription.
- **Manual confirmation** (`/platform/payments/<id>/confirm/`, platform subscriptions users) is now an exceptional recovery path. It requires a reason, is audited (`subscription_payment_manual_confirm`), and **refuses online checkout rows**, which use the verified webhook or reconciliation instead. Manual renewal is audited too.
- **Billing provider.** Setting `payment_provider_id` or `currency` in the subscription payment config is Super Admin only and audited. The provider is a Safari house-tenant provider configured in Platform → Integrations.
- The Superadmin subscription bypass is unchanged, and its tests pass.

## Found and fixed during this work

- The unsigned Waafi callback (see *Retired* above).
- The legacy `ensure_pending_payment` alert flow reused, and re-priced, online checkout rows. It is now limited to legacy rows.
- `select_for_update` combined with a nullable `select_related` fails on PostgreSQL. The fix is `of=("self",)`; SQLite never showed the error.

## UI

- **Tenant:** `/billing` (linked from Settings → "Billing & Subscription" and from the payment notification). It shows the current plan, status, expiry, next billing amount, plan cards (Renew, Pay now, or Switch where valid, with the server's reason otherwise), the pending, success or failed state with read-only polling, and the invoice/payment history.
- **Platform console:** the "Confirm & renew" button is hidden for online checkouts, and manual confirmation asks for a reason.

## Tests

- SQLite: `tests/unit/test_subscription_checkout.py` (15 tests).
- PostgreSQL 14 (`config.settings.branch_verification`): `tests/unit/test_billing_postgresql.py` (6 tests). It covers concurrent duplicate and distinct-event webhooks (one activation, one Payment, one of each journal), concurrent checkouts with one idempotency key, SMS reservations racing (3 credits and 10 sends: 3 sent, 7 refused, balance 0, never negative), debit adjustments racing sends, and SMS purchase confirmations racing (credited once).
- Frontend: `modules/billing/billing.test.tsx`.

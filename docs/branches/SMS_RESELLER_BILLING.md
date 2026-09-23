# SMS Reseller Packages & Credits

Date: 2026-09-23. This builds on `PLATFORM_INTEGRATIONS.md`, `BRANCH_SMS_FRAMEWORK.md` and `BRANCH_PAYMENT_FRAMEWORK.md`, and adds no new provider adapters.

**Business model.** Safari Technology owns the SMS providers; they are configured in Platform Admin only. Tenants buy SMS packages from Safari, and every message segment they send uses one credit. Tenants never see provider credentials or configuration.

## Data model (`apps/integrations/models/sms_billing.py`, migration `0003_sms_billing`)

| Model | Purpose |
|---|---|
| `SmsPackage` | Platform-wide package: name, code (unique), SMS quantity (>0), price (≥0), currency, validity days (empty = no expiry), description, active flag. |
| `SmsBillingSettings` | Singleton: the payment provider Safari collects package payments through. It is one of Safari's own house-tenant `PaymentProviderConfig` rows, configured in Platform → Integrations. |
| `SmsPackagePurchase` | Tenant purchase that snapshots the package (name, quantity, price, currency, validity). Status is one of pending, credited, failed, expired or review. It is unique on `(tenant, idempotency_key)` and on `(provider, provider_reference)`. |
| `SmsCreditLot` | A grant of units with one expiry. It has `units_remaining ≥ 0` and a one-to-one link to its purchase, so a purchase can be credited only once at the DB level. |
| `SmsCreditEntry` | The **immutable** ledger: purchase, adjust_credit, adjust_debit, reserve, release and expire. Each entry records signed units, `balance_after` and lot allocations. `save()` on an existing row and `delete()` both raise. DB-unique constraints allow one purchase entry per purchase and one reserve/release per SMS log. |
| `SmsCreditAccount` | One per tenant. Its row lock serialises every credit movement. |
| `SmsLog.credit_units` / `credit_state` | Records what a message reserved and whether it ended charged or released. |

Balance is the remaining units in lots that have not expired. Expired units never count, even before the expiry sweep runs.

## Credit engine (`services/sms_credit_service.py`)

- **Consumption** is hooked into the existing `SmsService`, whose contract is otherwise unchanged:
  - When a message is accepted (queued), it **reserves** its segment count. Segments are GSM-7 160/153 characters, otherwise UCS-2 70/67. Credits are drawn from the lots expiring soonest.
  - Insufficient credit marks the log FAILED with "Insufficient SMS credits." before any provider call, so the balance can never go negative.
  - When the message reaches SENT, the reserve becomes **charged**. When it reaches FAILED (permanent error or retries exhausted), a **release** returns the units to the same lots. While a message is RETRYING, its units stay reserved.
- **Purchases.** `POST /api/v1/integrations/sms-billing/purchases/` with `package_id` and `idempotency_key` creates a pending purchase and calls the billing provider's `create_payment`. Replaying the same key returns the same purchase.
- **Crediting happens only through the existing verified-webhook path.** `PaymentService.process_event` handles the HMAC signature, the timestamp window and event-id dedupe. When a verified event matches no payment intent, it hands the event to `SmsPurchaseService.apply_event`, which:
  - credits a pending purchase whose amount matches exactly;
  - treats a credited purchase as a no-op;
  - flags a mismatched amount, or a success arriving after failure or expiry, as `review` (no automatic credit);
  - marks the purchase `failed` when the provider reports failure.

  No API endpoint, frontend callback or redirect can credit a purchase.
- **Expiry.** The beat task `integrations.expire_sms_credits` runs every 30 minutes. It writes expire entries for lapsed lots and marks purchases still pending after 24 hours as `expired`.
- **Manual adjustments** (Platform Admin only) require a reason, can never take the balance below zero, and are written to both the ledger and `AuditLog` (`event=sms_credit_adjustment`).
- **Enforcement setting.** `SMS_CREDITS_ENFORCED` defaults to True. Test settings turn it off so older SMS suites keep working without credits; the reseller tests turn it on.

## API

- **Tenant** (`/api/v1/integrations/sms-billing/`): `packages/` (active only), `summary/` (balance, reserved, usage, purchased, next expiry, whether payments are available), `ledger/` (message entries are scoped to the user's branches), `purchases/` (GET and POST), and `purchases/<id>/` (read-only, for polling).
  - Permissions: `integrations.sms.billing.view` and `integrations.sms.billing.purchase`. Both are new and granted to the admin role.
  - No response contains a provider id, configuration or secret.
- **Platform** (`/api/v1/platform/integrations/sms-billing/`, global platform admin only): `packages/` (GET and POST), `packages/<id>/` (PATCH, covering edit and activate/deactivate), `settings/` (GET and PUT the billing provider), `balances/` (all tenants), `ledger/?tenant_id=`, and `adjustments/?tenant_id=`.

## UI

- **Tenant:** Settings → Integrations → SMS → **Packages & billing**. It shows balance cards, package cards with a Buy button (behind a confirmation, and reusing the idempotency key when a purchase is retried), purchase history and credit activity. It polls a pending purchase until it is credited or fails.
- **Platform:** Platform → Integrations → **SMS billing**. Tabs: Packages (create, edit, activate or deactivate), Tenant balances, Tenant ledger (balance, audited adjustment form, purchases and ledger) and Billing provider.

## Not in scope

- ERP subscription auto-payment and renewal.
- Real provider adapters (only MOCK exists).
- Refunds of package payments. A `review` purchase is resolved with a manual adjustment.

## Tests

- Backend: `tests/unit/test_sms_reseller.py`.
- Frontend: `modules/settings/integrations/__tests__/smsBilling.test.tsx`.

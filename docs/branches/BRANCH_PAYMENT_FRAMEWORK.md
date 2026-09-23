# Payment Framework — Phase 8

Companion to `MULTI_BRANCH_ARCHITECTURE.md` (D6, D7) and `BRANCH_TEST_MATRIX.md` §8. Lives in
`apps/integrations` next to the SMS framework; migration `integrations/0002_payments`. It reuses the Phase 7
credential store and the same "provider trouble is a result, never an exception" contract.

## The one rule
An invoice is settled (a `sales.Payment` row, `amount_paid`/`PAID`, and the `CUSTOMER_PAYMENT_RECEIVED`
journal entry) **only** by `PaymentService._settle`, and `_settle` runs only from a webhook whose HMAC
signature and timestamp verified on the server. There is no confirm endpoint: `GET /payments/intents/<id>/`
is read-only and the frontend polls it. Creating an intent never touches the invoice.

## Models
| Model | Purpose |
|---|---|
| `PaymentProviderConfig` | Gateway config (`MOCK` only — D7). Two credential refs: `credential` (outbound API key) and `webhook_credential` (HMAC signing key). Optional branch (branch provider wins over tenant-wide). |
| `PaymentIntent` | One attempt to collect `amount` on an invoice. Branch is **stamped from the invoice**, never from the caller. Unique `(tenant, idempotency_key)`; unique `(provider, provider_reference)`. Optional 1:1 `payment` once settled. |
| `PaymentWebhookEvent` | Every inbound webhook, raw, before anything acts on it. `event_id` is set only for signature-verified events. |
| `ReconciliationRecord` | A provider-vs-ledger discrepancy for a human. One open row per `(intent, kind)`. |

## Intent lifecycle (B8-2)
`created → pending → succeeded | failed | expired` (also `created → failed | expired`). `succeeded`, `failed`
and `expired` are terminal; `PaymentService._transition` is the only writer and refuses anything else.
Provider trouble at creation (timeout, 5xx, rejection, unusable credential) yields a `failed` intent with a
reason — the caller never sees an exception. `expires_at` = now + `config.intent_ttl_minutes` (default 30);
Celery `integrations.expire_payment_intents` (5-min beat) expires overdue ones.

## Idempotency (B8-3)
* **Intent:** replaying a key returns the original intent (`created=False`, HTTP 200). Reusing a key for a
  different invoice or amount is refused. A concurrent insert race is decided by the unique constraint.
* **Webhook:** deduplicated on the provider `event_id` (unique constraint) *and* on intent state under the
  intent row lock, so a provider re-sending one payment under a **new** event id still settles once. The
  journal entry is additionally keyed on the payment id by the existing posting idempotency key.

## Webhook security (B8-5, B8-6)
`POST /integrations/payments/webhooks/<provider_id>/` is public (no JWT); the unguessable provider id picks the
tenant. Signature = `hex(HMAC-SHA256(webhook_secret, "<timestamp>." + raw_body))` in `X-Payment-Signature`,
timestamp (unix seconds) in `X-Payment-Timestamp`, compared in constant time. The timestamp must be within
±5 min (stale = replay, far-future rejected). Order of operations: verify → store → parse → dedupe → process.
* Unsigned / bad / stale / tampered / no-secret / undecryptable-secret → stored `rejected` with the raw body, no
  `event_id`, no financial effect, HTTP 401 with a generic body (no reason leaked).
* A forged event carrying a real `event_id` cannot burn it: only verified events get an `event_id`.
* Signed but unparseable → `invalid` (400). Unknown reference or unhandled type → `ignored` (200).
* Settlement failure (e.g. ledger error) rolls the whole settlement back, marks the event `error` and returns
  500 so the provider redelivers; a redelivery of an `error`/`received` event is retried, not skipped.
* Body cap 64 KB (413). The event list API omits `raw_body` and signatures.

## Things that are flagged, not fixed (B8-7)
Late success (intent already expired/failed), amount mismatch (intent stays pending), money the invoice can
no longer absorb (cancelled, or paid meanwhile → intent `succeeded`, no `Payment`, kind `unapplied_payment`),
"failed" for an already-settled intent. `ReconciliationService.run` (API `POST /payments/reconcile/`) also
compares each intent with the provider's own status (`adapter.fetch_status`) and with the ledger (payment row
present, amounts equal, journal entry present). It **only writes `ReconciliationRecord`s**; an unreachable
provider is counted, not flagged. `resolve` needs a note and changes no money.

## Branch (B8-8) and access
Intent, payment and journal lines carry the invoice's branch. Endpoints are branch-scoped like the rest of the
module: a foreign-branch invoice is a 404 on create, lists and resolves filter by the caller's branches.
Permissions: `integrations.payments.view|collect|reconcile` (added to `admin`; `integrations.manage` for
providers).

## API (`/api/v1/integrations/`)
`payment-providers/` (+`<id>/`), `payments/intents/` (POST needs `idempotency_key` or `Idempotency-Key` header),
`payments/intents/<id>/`, `payments/webhook-events/`, `payments/webhooks/<provider_id>/`, `payments/reconcile/`,
`payments/reconciliation/`, `payments/reconciliation/<id>/resolve/`.

## Known limits
* Only `MOCK` exists (D7); a real provider needs an adapter (`create_payment`, `fetch_status`,
  `parse_webhook`) and, if its signature scheme differs, an override of the shared HMAC check.
* Idempotency keys are unique per tenant, not per invoice/user; the caller owns key generation.
* Full refunds/chargebacks from a provider are not modelled (`payment.refunded` is `ignored`).
* No POS-terminal UI yet; the frontend must poll the intent and must not treat a redirect/callback as success.
* Intents are collected on the invoice's own branch only; a payment settles at most the invoice balance.

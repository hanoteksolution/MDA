# Provider Adapter Implementation Guide (internal)

For our developers. Describes how a real SMS or payment provider is added to the **existing** Phase 7 (SMS) and
Phase 8 (payments) framework **without modifying any business module** (sales, POS, finance, school …).
Everything named here exists in the code today; where the framework has a gap it is listed in §7 rather than
worked around. Companion docs: `docs/branches/BRANCH_SMS_FRAMEWORK.md`, `docs/branches/BRANCH_PAYMENT_FRAMEWORK.md`.

> **Do not write an adapter from assumptions.** Start from the provider's written API documentation and sandbox
> (see the external requirement documents in this folder). Decision D7: no invented provider endpoints.

## 1. Architecture contract

```
ERP business module ──▶ Integration service ──▶ Provider adapter ──▶ External provider
```

| Layer | Code | Knows about |
|-------|------|-------------|
| Business module | `apps/sales`, `apps/finance`, … | Calls `SmsService.enqueue/…` or `PaymentService.create_intent`. Never imports an adapter or provider name. |
| Integration service | `apps/integrations/services/sms_service.py` (`SmsService`), `payment_service.py` (`PaymentService`, `ReconciliationService`), `credential_service.py` (`CredentialService`) | Queueing, retries, idempotency, state machines, audit, settlement. Resolves the provider for a branch and instantiates the adapter. |
| Adapter | `apps/integrations/providers/` | One provider's wire protocol only. Receives `config` (non-secret dict) and `secret` (one decrypted string). |
| Provider | external | — |

**Payment path:** Invoice/POS → `PaymentIntent` → adapter `create_payment` → provider → **HMAC-verified webhook**
(`PaymentService.receive_webhook`) → `PaymentService.process_event` → `_settle` (the only code that pays an invoice)
→ accounting posting → receipt/notification.

**SMS path:** business event → `SmsService` (`SmsLog` row, template rendering) → adapter `send` → provider →
`SmsLog` status.

Invariants an adapter must not break:

- The browser/frontend is never authoritative for payment success. There is no confirm endpoint and none may be
  added. Only `PaymentService._settle` settles, only from a verified webhook.
- Adapters **never raise for provider-side trouble** (timeouts, 5xx, garbage bodies). They return a result with
  `outcome` `OK`, `TRANSIENT` (retry) or `PERMANENT` (stop). The services also catch adapter crashes, but a crash
  is a bug.
- Error strings returned by an adapter are stored and shown to users. They must never contain the URL, headers,
  request body or secret (`custom_http.py` drops exception text for exactly this reason).
- Business modules gain no provider-specific branches. If you find yourself editing `apps/sales` for a provider,
  stop.

## 2. Existing interfaces

### 2.1 SMS — `apps/integrations/providers/base.py`

```python
OK, TRANSIENT, PERMANENT = "OK", "TRANSIENT", "PERMANENT"

@dataclass
class OutboundSms:  to: str; body: str; sender_id: str = ""
@dataclass
class SendResult:   outcome: str; reference: str = ""; error: str = ""

class SmsProviderAdapter:
    type_code = ""
    def __init__(self, *, config: dict, secret: str | None): ...
    def send(self, message: OutboundSms) -> SendResult: ...      # required
    def validate_config(self) -> list[str]: ...                   # optional; human-readable problems
```

`SendResult.reference` is the provider's message ID and is stored in `SmsLog.provider_reference`.
`SmsService` retries `TRANSIENT` results up to `MAX_ATTEMPTS` (4) with `BACKOFF` (1 / 5 / 30 minutes) and marks
`PERMANENT` results `FAILED`. Reference implementations: `mock.py` (`MockProvider`) and `custom_http.py`
(`CustomHttpProvider`).

### 2.2 Payments — `apps/integrations/providers/payment_base.py`

```python
@dataclass
class CreateResult:  outcome: str; reference: str = ""; error: str = ""
@dataclass
class RemoteStatus:  outcome: str; status: str = ""; amount: Decimal | None = None; error: str = ""
                     # status: "pending" | "succeeded" | "failed"
@dataclass
class ParsedEvent:   event_id: str; kind: str; reference: str; amount: Decimal | None = None
                     # kind: "succeeded" | "failed" | "other"

class PaymentProviderAdapter:
    type_code = ""
    def __init__(self, *, config: dict, secret: str | None): ...
    def create_payment(self, *, amount: Decimal, currency: str, reference: str) -> CreateResult: ...
    def fetch_status(self, reference: str) -> RemoteStatus: ...
    def parse_webhook(self, payload: dict) -> ParsedEvent | None: ...
    def validate_config(self) -> list[str]: ...
```

Facts the implementation must respect (from `PaymentService`):

- `create_payment` is called with `reference=str(intent.pk)` (our UUID) — send it to the provider as the merchant
  reference / idempotency key. The `reference` you **return** is the *provider's* transaction ID; it becomes
  `PaymentIntent.provider_reference`, is unique per provider, and moves the intent `created → pending`.
- `parse_webhook(payload)` receives the JSON-decoded body of an **already signature-verified** event and must
  return a `ParsedEvent` whose `reference` equals the provider transaction ID returned by `create_payment`
  (that is how the intent is found). Return `None` for an unrecognisable body (event stored as `invalid`, HTTP
  400). `event_id` must be unique per delivered event (dedupe key). `amount` is compared with the intent amount.
- `fetch_status` feeds `ReconciliationService.run`; `TRANSIENT` means "provider unreachable" (counted, not
  flagged). Map provider states to exactly `pending` / `succeeded` / `failed`.
- Currency comes from `PaymentProviderConfig.config["currency"]` (default `USD`); intent expiry from
  `config["intent_ttl_minutes"]` (default 30). Amounts are `Decimal`; convert to the provider's format
  (decimal string or minor units) inside the adapter.
- Webhook authenticity is **not** the adapter's job today: `receive_webhook` verifies
  `HMAC-SHA256(webhook_secret, "<timestamp>." + raw_body)` from headers `X-Payment-Signature` /
  `X-Payment-Timestamp` (`SIGNATURE_HEADER`, `TIMESTAMP_HEADER`, `TOLERANCE_SECONDS = 300`). See §7 if a provider
  signs differently.

### 2.3 Secrets — `CredentialService` / `IntegrationCredential`

Secrets are Fernet-encrypted (`INTEGRATION_ENCRYPTION_KEY`). A provider row references credentials by FK:
`SmsProvider.credential`; `PaymentProviderConfig.credential` (outbound API secret) and
`.webhook_credential` (inbound signing secret). The service decrypts with `CredentialService.reveal` for the
duration of one call and passes the plaintext to the adapter as `secret`. Adapters receive **one string**.

## 3. Choose the smallest path

| Situation | Path |
|-----------|------|
| SMS provider with a plain HTTPS JSON/form API | **No code.** Configure a `CUSTOM_HTTP` provider in *Settings → Integrations → SMS* (URL, method, headers, body template using `{to}`, `{message}`, `{sender}`, `{secret}`, `success_statuses`, `reference_path`). Verify against the sandbox. |
| SMS provider needing signing, multi-step auth, XML/SOAP or special error mapping | New SMS adapter (§4). |
| Any payment provider | New payment adapter (§5). There is no generic payment adapter. |

## 4. Adding an SMS adapter

1. **Create** `apps/integrations/providers/<name>.py` with a class deriving from `SmsProviderAdapter`,
   `type_code = "<NAME>"`. Implement `send` (never raise; classify: network error/timeout/5xx/408/429 →
   `TRANSIENT`, other 4xx and bad config → `PERMANENT`, 2xx → `OK` with the provider message ID) and
   `validate_config`. Reuse `custom_http._blocked_host` for any tenant-supplied URL (SSRF guard).
2. **Register** it in `apps/integrations/providers/registry.py` → `PROVIDER_REGISTRY`.
3. **Expose the type** on the model: add it to `SmsProvider.TYPE_CHOICES` in `apps/integrations/models/sms.py`
   and generate the migration (`makemigrations integrations` — an `AlterField` on `provider_type`; check the
   generated file contains only that change).
4. **No view change.** `api/v1/integrations/views.py::_save_provider` validates `provider_type` against
   `PROVIDER_REGISTRY` and calls `validate_config()` for every non-MOCK type.
5. **Frontend:** add the type to `SmsProviderType` in `frontend/src/services/api/integrations.ts` and to
   `SMS_PROVIDER_TYPES` in `frontend/src/modules/settings/integrations/lib.ts`. If it needs fields beyond the
   existing form, extend `SmsProviderFormView` and `validateSmsProviderForm`/`buildSmsProviderInput`.
6. **Test** in `backend/tests/unit/test_sms_framework.py` style: mock the HTTP layer; cover success (reference
   extracted), each `TRANSIENT` and `PERMANENT` class, malformed reply, and **assert the secret and URL never
   appear in `SendResult.error` or `SmsLog.error`** (see `test_integration_secrets.py`).
7. **Sandbox proof** before enabling in production.

Delivery receipts are not modelled (see §7): `SmsLog.status = SENT` means the provider *accepted* the message.

## 5. Adding a payment adapter

1. **Create** `apps/integrations/providers/payment_<name>.py`; derive from `PaymentProviderAdapter`;
   `type_code = "<NAME>"`. Implement:
   - `create_payment` — call the provider with `reference` as the idempotency/merchant reference; on success
     return `CreateResult(OK, reference=<provider transaction id>)`; on provider failure return `TRANSIENT`/
     `PERMANENT` with a sanitised message. A timeout is **not** a failure of the payment: the provider may have
     accepted it. Prefer `PERMANENT`-only-when-certain, and let reconciliation catch the rest.
   - `fetch_status` — query by provider transaction ID; map to `pending|succeeded|failed`; return the provider's
     amount as `Decimal`.
   - `parse_webhook` — map the provider's event to `ParsedEvent` (§2.2). Unknown event types → `kind="other"`.
   - `validate_config` — required non-secret config (base URL, merchant ID, …). Base URLs must be `https`.
2. **Register** it in `PAYMENT_PROVIDER_REGISTRY` (`registry.py`).
3. **Expose the type:** add to `PaymentProviderConfig.TYPE_CHOICES` (`models/payment.py`) + migration.
4. **View validation:** `api/v1/integrations/payment_views.py::_save_provider` checks the registry but, unlike
   SMS, does **not** call `validate_config()` — add that call (same pattern as SMS) in the same change.
5. **Frontend:** add the type to `PaymentProviderType` (`services/api/integrations.ts`) and
   `PAYMENT_PROVIDER_TYPES` (`lib.ts`). The form's metadata rows already carry non-secret keys such as
   `merchant_id`, `currency`, `intent_ttl_minutes`; the mock-mode selector is MOCK-specific and should be shown
   only for MOCK.
6. **Webhook address:** every provider row already has `POST /api/v1/integrations/payments/webhooks/<provider_id>/`
   (shown in the UI as `webhook_path`). Give that URL and the signing secret to the provider.
7. **Tests** (`backend/tests/unit/test_payment_framework.py`, helpers in `backend/tests/helpers/payment_factory.py`
   — `make_provider`, `start_payment`, `signed`, `deliver`): mock the HTTP layer and cover create success/failure
   /timeout, duplicate initiation (idempotency), verified success webhook settles exactly once, duplicate and
   out-of-order webhooks, forged/stale webhook rejected, amount mismatch flagged (not settled), late success after
   expiry flagged, `fetch_status` mapping, reconciliation, and that no secret appears in errors or events.
8. **Sandbox proof** for the full list in `INTEGRATION_PROVIDER_HANDOFF.md` §4, then live test transactions.

## 6. What must not change

- `PaymentService._settle`, `_transition`, `receive_webhook`'s verify → store → parse → dedupe → process order,
  or the "only a verified webhook settles" rule.
- Any business module. Providers are resolved per branch by `SmsService.resolve_provider` /
  `PaymentService.resolve_provider`; branch-bound providers override tenant-wide ones.
- The credential store contract (write-only secrets; API returns `has_secret` + `masked_tail` only).

## 7. Known framework gaps (change the framework, not the business modules, when needed)

| Gap | Impact | Where it would be fixed |
|-----|--------|-------------------------|
| **Webhook signature scheme is fixed** (shared HMAC over `"<ts>." + body`, fixed header names) | A provider that signs differently (other header/algorithm/signed fields) cannot be verified today. | Give `PaymentProviderAdapter` an optional `verify_webhook(headers, raw_body, secret)` hook used by `PaymentService.receive_webhook`; default = current behaviour. Needs review because it touches the security path. |
| **One secret string per credential** | Providers needing key+secret or client-id+secret pairs need a composite secret the adapter splits, or a framework extension. | `CredentialService` / adapter constructor. |
| **No SMS delivery-receipt ingestion** | `SENT` = accepted by provider, not delivered. | New public signed endpoint + `SmsLog` status extension, modelled on `PaymentWebhookView`. |
| **No SMS status polling** | As above. | Adapter method + Celery task. |
| **`payment.refunded` / chargebacks are `ignored`** | No refund or dispute modelling. | New states + reconciliation kinds; finance design needed. |
| **Payment `validate_config` not invoked by the API** | Bad config surfaces at first payment. | One call in `payment_views._save_provider` (§5.4). |
| **No "test connection" endpoint** | UI can only send a real test SMS; nothing equivalent for payments. | Endpoint calling `validate_config` + a harmless provider ping. |
| **`sms/send` cannot target a specific provider** | Test SMS uses the branch's resolved provider. | Optional `provider_id` in `SmsSendView`. |
| **`CUSTOM_HTTP` has no DNS pinning** | SSRF guard resolves at validate time. | `custom_http._blocked_host`. |

## 8. Checklist before enabling a new provider in production

- [ ] Written API docs and sandbox access obtained (no assumed behaviour)
- [ ] Adapter never raises; every provider error classified `TRANSIENT`/`PERMANENT`
- [ ] Secrets and URLs absent from errors, logs, audit rows and API responses (tests prove it)
- [ ] Idempotent initiation and duplicate-callback tests pass
- [ ] Forged, stale and tampered webhooks rejected
- [ ] Reconciliation run against the provider's report
- [ ] `INTEGRATION_ENCRYPTION_KEY` set in the target environment
- [ ] Migration reviewed (only the `provider_type` choices change)
- [ ] Frontend type lists updated; integrations frontend tests pass
- [ ] Runbook and provider support/escalation contacts recorded

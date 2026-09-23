# SMS Framework — Phase 7

Companion to `MULTI_BRANCH_ARCHITECTURE.md` (D6, D7) and `BRANCH_TEST_MATRIX.md` §7. New app
`apps/integrations` (D1); migration `integrations/0001_initial`. Payments (Phase 8) will reuse the credential
store and the same failure-isolation contract.

## Secrets (D6)
* `IntegrationCredential` holds Fernet ciphertext (`crypto.py`, `cryptography`). `INTEGRATION_ENCRYPTION_KEY`
  may list several keys, comma-separated: the **first** encrypts, all decrypt (rotation via `MultiFernet`;
  `rotate_token` re-encrypts). Only `has_secret` and a masked tail (last 4 chars, and only for secrets ≥ 12
  chars) ever leave the backend (`CredentialService.serialize`).
* **No key = no module.** Any store/use raises `ImproperlyConfigured` (never a plaintext fallback); a send
  with an unusable credential ends `FAILED` "Integration credentials cannot be used". This is enforced at use
  time, not as a Django startup check, so an environment that does not use integrations still boots.
* A provider's `config` must reference the secret only as `{secret}`; the value is injected per call and never
  stored. The config itself is not a secret store — do not paste keys into it (audit rows omit `config`).

## Providers (D7)
Only `MOCK` and generic `CUSTOM_HTTP` (`providers/registry.py`); no vendor adapters were invented.
`CUSTOM_HTTP` is configured entirely by the tenant (url, method, header/body templates with `{to} {message}
{sender} {secret}`, success statuses, `reference_path`). It requires **https**, refuses loopback/private/
link-local hosts (`SMS_ALLOW_PRIVATE_URLS` opts out for dev), never follows redirects, and caps the timeout at
30 s. Known gap: the host check resolves DNS once at send time (no pinning), so a DNS-rebinding attacker
controlling the tenant's own domain could still race it.

## Sending
* Resolution: a **branch** provider (`SmsProvider.branch`) wins, else the tenant-wide default; inactive ones
  are ignored; never across tenants. Sender = provider `sender_id`, else the branch code.
* Templates: `{name}` substitution only (no attribute access/format specs); a missing value fails the message
  instead of sending a broken one.
* `SmsService.send` (sync) / `enqueue` (log now in a savepoint, deliver `on_commit`) / `dispatch_safe`.
  **`enqueue` and `dispatch_safe` never raise** and never touch the caller's transaction state (B7-3).
  Adapters return `OK / TRANSIENT / PERMANENT` results; anything unexpected is contained as transient.
* Retry is bounded (B7-4): `TRANSIENT` (timeout, network, 5xx, 408/429, unreadable 2xx) retries after 1 → 5 →
  30 min up to `MAX_ATTEMPTS = 4`, then ends `FAILED (retries exhausted)`; `PERMANENT` (4xx, bad config,
  rejected, redirect) ends `FAILED` at once. `SENT`/`FAILED` are terminal and never re-dispatched; a row lock
  stops two workers sending one message. Celery: `integrations.dispatch_sms`, and `integrations.retry_due_sms`
  every 5 min (beat). Delivery is at-least-once: a crash after the provider accepted but before the row commits
  can resend once.
* `SmsLog` stores status, provider reference, attempts, next retry and a **scrubbed** error (secret replaced,
  provider bodies and exception text never stored). SEC-2 is tested across API responses, application logs
  (DEBUG, all loggers), audit rows and log rows.

## API (`/api/v1/integrations/`)
`credentials/` (+`<id>/` rotate), `sms-providers/`, `sms-templates/`, `sms-logs/` (branch-scoped; branch-less
logs only for unscoped callers), `sms/send/`. New permissions `integrations.view|manage|sms.send` (granted to
`admin`; platform/super admins have `*`). Branch-bound actions check `has_branch_permission`.

## Not in scope / limits
No frontend, no automatic SMS from business events yet (the framework exposes `enqueue`; wiring receipts,
transfers or shift variances to it is a product decision), no delivery-receipt webhooks, no vendor adapters.

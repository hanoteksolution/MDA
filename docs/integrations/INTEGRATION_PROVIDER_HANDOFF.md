# Integration Provider Handoff

**Prepared by:** [YOUR COMPANY NAME] · **Contact:** [TECHNICAL CONTACT NAME, EMAIL, PHONE]
**Version:** 1.0 · **Date:** [DATE]
**Audience:** Any SMS, telecom, mobile-money, bank or payment provider we are onboarding

## 1. What this pack is

We are integrating external providers into our business platform (ERP and point-of-sale). This handoff explains
**how our integrations are structured, what we expect from a provider, and how onboarding proceeds**. It is sent
together with one or both of:

| Document | Send to |
|----------|---------|
| `SMS_PROVIDER_INTEGRATION_REQUIREMENTS.md` | SMS gateways, telecom operators, messaging-API providers |
| `PAYMENT_PROVIDER_INTEGRATION_REQUIREMENTS.md` | Mobile-money operators, banks, payment gateways |

Each of those documents ends with a checklist titled **"Information we need from your technical team"**.
Please return it completed, with your API documentation.

## 2. Integration boundary

Our business modules (sales, POS, finance, school, and others) never talk to a provider directly. They talk to an
internal integration service, which uses a provider-specific connector. Adding or replacing a provider therefore
changes only its connector and configuration — not our business processes.

**Messaging**

```
Business event (invoice paid, reminder due, low stock …)
  → Notification / SMS service   (queue, template, retry, log)
    → SMS provider connector
      → Provider API
        → Delivery status
```

**Payments**

```
Invoice / POS order
  → Payment intent               (our unique reference, amount, currency, expiry)
    → Payment provider connector
      → Provider API
        → Signed, verified webhook from the provider
          → Backend verification (signature, freshness, amount, duplicates)
            → Settlement against the invoice
              → Accounting entry
                → Receipt / notification
```

### Non-negotiable rules for payments

1. **The browser or mobile app is never authoritative for payment success.** A payment succeeds in our system only
   after a server-side, authenticated confirmation from the provider.
2. **Callbacks must be signed and time-stamped**, and are rejected otherwise.
3. **Requests and callbacks must be idempotent.** Retries and redeliveries must not duplicate money movement.
4. **Mismatches are reported for review**, never silently corrected. We reconcile provider reports against our
   ledger.

### Rules for messaging

1. Provider errors are classified as **temporary** (retry with back-off) or **permanent** (stop) — please document
   which is which.
2. A message is recorded with the provider's message ID so delivery reports can be matched.
3. Sending a message never blocks or fails the business transaction that triggered it.

## 3. Security expectations

| Topic | Our practice | Your part |
|-------|--------------|-----------|
| Transport | HTTPS (TLS 1.2+) only; no redirects followed on outbound calls | Provide HTTPS endpoints and callbacks |
| Credentials | Encrypted at rest; never logged, never shown after entry, never sent to browsers | Issue separate sandbox/production credentials; support rotation |
| Secrets in transit | Never by email or chat | Agree a secure exchange channel |
| Callback authenticity | HMAC signature + timestamp, constant-time comparison | Sign callbacks and document the scheme |
| Replay protection | Timestamp tolerance (5 minutes) and unique event IDs | Include a timestamp and a unique event ID |
| Least privilege | Separate secrets for API access and webhook signing | Allow distinct keys |
| Network | Outbound calls from fixed egress IPs on request | Tell us if allowlisting is required, and your callback IPs |

## 4. Onboarding process

| Step | Owner | Output |
|------|-------|--------|
| 1. Kick-off and contacts | Both | Named technical contacts, support and escalation paths |
| 2. Requirements checklist returned | Provider | Completed checklist and API documentation |
| 3. Fit review | [YOUR COMPANY NAME] | Confirmation, or a list of gaps and questions |
| 4. Sandbox access | Provider | Sandbox URL, credentials, test data, outcome triggers |
| 5. Build and sandbox testing | [YOUR COMPANY NAME] with provider support | Test evidence (see below) |
| 6. Production onboarding | Provider | Production credentials, sender IDs / merchant IDs, allowlisting |
| 7. Controlled go-live | Both | Live test transactions and monitoring |
| 8. Hand-over to support | Both | Runbook, contacts, reconciliation schedule |

### Test evidence we will produce and share

- **SMS:** successful send, invalid number, rejected sender, provider timeout, rate-limited request, delivery
  report for each final status.
- **Payments:** successful payment, declined payment, customer timeout/expiry, duplicate initiation request,
  duplicate callback, out-of-order callback, forged or stale callback (must be rejected), late success after
  expiry, amount mismatch, and a reconciliation run against the provider report.

## 5. What we will not do

- We will not build against assumed API behaviour. We integrate against your **written documentation and
  sandbox**.
- We will not go live without successful sandbox evidence for the cases above.
- We will not accept payment confirmation from any channel other than your authenticated server-to-server
  confirmation.

## 6. Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Technical lead | [NAME] | [EMAIL] | [PHONE] |
| Project / commercial | [NAME] | [EMAIL] | [PHONE] |
| Escalation (out of hours) | [NAME] | [EMAIL] | [PHONE] |

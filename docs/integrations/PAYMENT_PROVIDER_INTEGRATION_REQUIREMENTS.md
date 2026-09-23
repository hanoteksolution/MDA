# Payment Provider Integration Requirements

**Prepared by:** [YOUR COMPANY NAME] · **Contact:** [TECHNICAL CONTACT NAME, EMAIL, PHONE]
**Version:** 1.0 · **Date:** [DATE]
**Audience:** Mobile-money operators, banks, payment gateways and payment-API providers' technical and onboarding teams

## 1. Purpose

We operate a business-management platform (ERP and point-of-sale) used by several businesses. We want to let
customers pay invoices and point-of-sale orders through your service — for example by mobile money, card or bank
transfer — and to have each payment confirmed and reconciled automatically.

This is a **requirements list, not a description of your API**. Please answer each item from your own
documentation and send us your API reference. All JSON below is **illustrative only** (labelled *EXAMPLE*); it is
not an assumed provider contract. Where your API differs, your API wins — tell us how.

## 2. Our integration principles

These principles are why some of the items below matter to us. Please tell us early if any of them cannot be met.

1. **Your confirmation is the source of truth.** A payment is marked successful in our system only after a
   **verified, server-to-server confirmation from you** (an authenticated webhook and/or a status query). We never
   treat a customer's browser redirect, an app return or a screenshot as proof of payment.
2. **Every callback must be verifiable.** We accept callbacks only when we can verify their authenticity and
   freshness (signature + timestamp).
3. **Everything is idempotent.** We may retry a request, and you may redeliver a callback; neither may result in a
   double charge or a double credit.
4. **Differences are reported, never hidden.** We reconcile your records against ours and surface any mismatch
   for human review.
5. **Secrets stay secret.** Credentials are stored encrypted and are never placed in URLs, logs or client apps.

```
Invoice / POS order
  → Payment request (our unique reference, amount, currency)
    → Provider connector
      → Your payment API   (customer approves the payment with you)
        → Your signed callback (webhook) to us      ← authoritative
          → Our verification (signature, timestamp, amount, duplicate check)
            → Payment recorded against the invoice and booked in accounting
              → Receipt / notification to the customer
```

If the callback is late or lost, we ask you for the payment status using your status endpoint (§3.3) before
declaring a payment failed or expired.

## 3. What we need from you

### 3.1 Merchant account and access

| # | Item | Details we need |
|---|------|-----------------|
| 1 | **Merchant account requirements** | Eligibility, documents (business registration, licences, KYC/KYB, bank details), approval time, fees and settlement terms. One account per company or per branch? |
| 2 | **Merchant ID(s)** | Identifier(s) we must send with requests; whether sub-merchants or per-branch/till identifiers are supported. |
| 3 | **API base URL** | Production and sandbox base URLs, HTTPS only. |
| 4 | **Authentication / signing method** | API key, OAuth2 client credentials, Basic, request signing (algorithm, signed fields, canonicalisation). Exact header names and a worked example. |
| 5 | **API credentials** | Issued separately for sandbox and production; expiry, rotation procedure, and a way to hold **two active credentials** during rotation. |
| 6 | **Sandbox / test environment** | URL, test credentials, test accounts/wallets/cards, and how to trigger each outcome (success, pending, declined, timeout, insufficient funds, duplicate). |
| 7 | **Production onboarding** | Steps, go-live checklist, test-transaction requirements, expected timeline. |
| 8 | **IP / domain allowlisting** | Whether you require our servers' outbound IPs: **[EGRESS IP(S) — to be provided by [YOUR COMPANY NAME]]**. Please also list **your** callback source IPs/ranges. |

### 3.2 Initiating a payment

| # | Item | Details we need |
|---|------|-----------------|
| 9 | **Payment initiation endpoint** | Method, path, headers, request and response fields. Whether the customer is prompted on their phone (push/USSD), redirected to a hosted page, or scans a QR code. |
| 10 | **Reference identifiers** | We send a **unique merchant reference** per payment attempt (a UUID, 36 characters). Confirm the maximum length and allowed characters, that it is returned in callbacks and reports, and what **provider transaction ID** you return. |
| 11 | **Amount and currency format** | Decimal string or integer minor units? Number of decimals per currency, supported currencies, minimum/maximum amounts, rounding rules. We use decimal amounts with up to 4 decimal places internally and will convert exactly. |
| 12 | **Customer identifier** | What you need to identify the payer (phone number format, account number, email) and how it is validated. |
| 13 | **Payment expiry** | How long a pending payment stays valid, whether we can set it, and what happens if the customer pays after expiry. |
| 14 | **Idempotency support** | An idempotency key or unique-reference rule so that re-sending the same request never creates a second payment; how long keys are honoured; what response a duplicate receives. |
| 15 | **Partial and over-payments** | Whether the customer can pay less/more than requested, and how that is reported. |

### 3.3 Status, callbacks and verification

| # | Item | Details we need |
|---|------|-----------------|
| 16 | **Status / verification endpoint** | Path and parameters to query a payment by our merchant reference and/or your transaction ID; what it returns; rate limit; how long a transaction remains queryable. |
| 17 | **Payment states** | Complete list with meanings and which are **final**. We map them to: *pending* (awaiting customer), *succeeded*, *failed/declined*, *expired/cancelled*. Please tell us how you represent each, including "unknown/processing" states. |
| 18 | **Webhook / callback URL requirements** | HTTPS? Ports? Number of URLs per account, whether the URL can differ per branch or per request, and the response you expect from us (status code/body). |
| 19 | **Webhook signature verification** | Algorithm, header names, exactly which bytes are signed, encoding of the signature, key rotation. *Our preferred scheme is given in §4; please tell us if yours differs.* |
| 20 | **Timestamp / replay protection** | A timestamp (or nonce) in every callback and the tolerance you recommend. We reject callbacks older than 5 minutes by default. |
| 21 | **Callback event identifier** | A unique ID per event so we can discard duplicates, distinct from the transaction ID. |
| 22 | **Webhook retry policy** | Retry schedule and duration when we do not reply 2xx; whether events can be duplicated or delivered out of order; how we can ask for a replay of missed events. |
| 23 | **Which events you send** | e.g. payment succeeded, failed, expired, refunded, reversed, chargeback opened/closed. |

### 3.4 Money movement after the payment

| # | Item | Details we need |
|---|------|-----------------|
| 24 | **Refunds** | Supported? Full/partial, API endpoint, time limits, fees, resulting states and callbacks. |
| 25 | **Reversals / cancellations** | Ability to cancel or reverse a pending or completed payment; conditions and time windows. |
| 26 | **Chargebacks / disputes** | Applicability, notification method, evidence and deadlines, fees. |
| 27 | **Settlement** | Settlement schedule, currency, fees deducted (gross vs net), settlement reference format and how it links to individual transactions. |
| 28 | **Reconciliation / settlement reports** | Report or API to list transactions and settlements for a date range (format, fields, availability time), used to reconcile against our records daily. |

### 3.5 Limits, reliability and support

| # | Item | Details we need |
|---|------|-----------------|
| 29 | **Rate limits** | Per second/minute for initiation and status queries, and the response when limited. |
| 30 | **Timeout and retry rules** | Recommended client timeouts; how to safely retry an initiation that timed out (we never assume a timed-out request failed); which errors are safe to retry. |
| 31 | **Error codes** | Full list of HTTP and body error codes, each marked **retryable** or **permanent**, with customer-facing meaning. |
| 32 | **Security and compliance** | PCI-DSS scope for card flows (we prefer hosted/tokenised flows so card data never touches our systems), regulatory requirements, data-residency. |
| 33 | **Support** | Technical support contacts and hours, severity levels and response times. |
| 34 | **Escalation process** | Named escalation contacts for outages, stuck payments and disputes. |
| 35 | **Status page / maintenance notices** | Where incidents and planned maintenance are announced. |

## 4. Our preferred webhook verification scheme

If you can, please sign callbacks as follows. If you already use another scheme (for example a different header
name or a signed-fields list), that is fine — describe it and we will adapt.

- **Timestamp header:** Unix time in seconds, e.g. `X-Payment-Timestamp: 1767225600`.
- **Signature header:** `X-Payment-Signature: <lower-case hex>`.
- **Signature value:** `HMAC-SHA256(secret, "<timestamp>" + "." + <raw request body bytes>)`, hex-encoded.
- **Secret:** a webhook-signing secret **separate** from your API credential, exchanged out of band.
- **Freshness:** we reject a callback whose timestamp differs from our clock by more than 5 minutes.
- **Duplicates:** we discard a callback whose event ID we have already processed, and we ignore redeliveries of
  a payment we have already settled.
- **Response:** we reply `2xx` when we have accepted the event, `4xx` when it is rejected (invalid signature or
  malformed body) and `5xx` when we could not process it and want you to retry.

## 5. EXAMPLES (illustrative only — not your contract)

**EXAMPLE — payment initiation request:**

```http
POST /v1/payments HTTP/1.1
Host: api.payment-provider.example
Authorization: Bearer <API_TOKEN>
Idempotency-Key: 3f9a1c1e-6a1d-4f7f-9c2e-0d5a7b1e2c44
Content-Type: application/json

{
  "merchant_id": "M-100234",
  "merchant_reference": "3f9a1c1e-6a1d-4f7f-9c2e-0d5a7b1e2c44",
  "amount": "25.00",
  "currency": "USD",
  "customer": { "msisdn": "+252611234567" },
  "description": "Invoice INV-1042",
  "expires_in_seconds": 1800
}
```

**EXAMPLE — initiation response (payment awaiting customer approval):**

```json
{
  "transaction_id": "tx_9b2e4c",
  "merchant_reference": "3f9a1c1e-6a1d-4f7f-9c2e-0d5a7b1e2c44",
  "status": "PENDING",
  "expires_at": "2026-01-01T00:30:00Z"
}
```

**EXAMPLE — status query response:**

```json
{
  "transaction_id": "tx_9b2e4c",
  "merchant_reference": "3f9a1c1e-6a1d-4f7f-9c2e-0d5a7b1e2c44",
  "status": "SUCCESS",
  "amount": "25.00",
  "currency": "USD",
  "completed_at": "2026-01-01T00:04:31Z"
}
```

**EXAMPLE — webhook callback to our system:**

```http
POST <our callback URL> HTTP/1.1
Content-Type: application/json
X-Payment-Timestamp: 1767225871
X-Payment-Signature: 5d41402abc4b2a76b9719d911017c592e2c1f4d0a2f6b3c8e7d9a1b0c3f4e5d6

{
  "event_id": "evt_5521",
  "type": "payment.succeeded",
  "transaction_id": "tx_9b2e4c",
  "merchant_reference": "3f9a1c1e-6a1d-4f7f-9c2e-0d5a7b1e2c44",
  "amount": "25.00",
  "currency": "USD",
  "occurred_at": "2026-01-01T00:04:31Z"
}
```

**EXAMPLE — error response:**

```json
{ "error": { "code": "INSUFFICIENT_FUNDS", "message": "Customer balance too low", "retryable": false } }
```

## 6. INFORMATION WE NEED FROM YOUR TECHNICAL TEAM

Please return this checklist with your API documentation.

- [ ] Merchant account requirements, fees, documents and approval timeline
- [ ] Merchant ID(s) and whether per-branch identifiers are possible
- [ ] Sandbox **and** production base URLs
- [ ] Authentication / signing method with a worked example
- [ ] Sandbox credentials, test accounts and outcome triggers
- [ ] Production credentials procedure, rotation and dual-credential support
- [ ] Payment initiation endpoint: request/response fields and customer flow (push, redirect, QR)
- [ ] Maximum length/format of our merchant reference; name of your transaction-ID field
- [ ] Amount format (decimal vs minor units), supported currencies, min/max amounts
- [ ] Idempotency behaviour for repeated initiation requests
- [ ] Status / verification endpoint and its rate limit
- [ ] Complete payment-state list, marking the final states
- [ ] Webhook URL requirements, event list and event-ID field
- [ ] Webhook signature scheme with a worked example (or confirmation of §4)
- [ ] Timestamp/replay-protection details
- [ ] Webhook retry policy and duplicate/out-of-order behaviour
- [ ] Refund, reversal and chargeback support (endpoints, states, time limits)
- [ ] Settlement schedule, fees and settlement/reconciliation reports
- [ ] Rate limits, timeout and safe-retry guidance
- [ ] Complete error-code list, marking retryable vs permanent
- [ ] Source IPs for callbacks; whether our IPs must be allowlisted
- [ ] PCI/regulatory requirements relevant to our flow
- [ ] Support contacts, escalation process, SLA and status page

## 7. Next steps

1. You return the checklist and API documentation.
2. We confirm fit and request sandbox credentials.
3. We build and test the connection against your sandbox, including duplicate, delayed, failed and forged-callback
   cases, and a reconciliation run against your report.
4. You complete production onboarding; we run agreed live test transactions and then go live.

*This document contains no credentials. Please never send secrets by email — share them through a channel we agree
in advance.*

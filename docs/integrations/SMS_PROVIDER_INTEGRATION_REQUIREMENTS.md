# SMS Provider Integration Requirements

**Prepared by:** [YOUR COMPANY NAME] · **Contact:** [TECHNICAL CONTACT NAME, EMAIL, PHONE]
**Version:** 1.0 · **Date:** [DATE]
**Audience:** SMS gateway, telecom and messaging-API providers' technical and onboarding teams

## 1. Purpose

We operate a business-management platform (ERP and point-of-sale) used by several businesses. We want to send
transactional SMS messages — receipts, payment confirmations, reminders and alerts — through your network.

This document lists what we need from you to integrate. It is a **requirements list, not a description of your
API**: please answer each item from your own documentation, and send us your API reference where one exists.
All JSON below is **illustrative only** (labelled *EXAMPLE*); it is not an assumption about your contract. If
your API works differently, your API wins — tell us how.

### How we integrate

Our platform sends a message by calling your HTTPS API from our servers. The request is built from a
configurable template (URL, HTTP method, headers, body fields), so **we do not need a proprietary SDK** if your
API is a standard HTTPS/JSON or form-encoded API. Credentials are stored encrypted on our side and are never
placed in message content or logs.

```
Business event (e.g. invoice paid)
  → Our messaging service (queues the message, retries on failure)
    → Provider connector (builds the HTTPS request from configuration)
      → Your SMS API
        → Delivery status  (your callback to us, or our status query to you)
```

Our platform treats the provider as unreliable by design: timeouts, 5xx, 408 and 429 responses are retried
with back-off (up to 4 attempts over roughly 36 minutes); any other 4xx response is treated as a permanent
failure and is **not** retried. Please make sure your status codes follow this convention (see §8).

## 2. What we need from you

### 2.1 Access and environments

| # | Item | Details we need |
|---|------|-----------------|
| 1 | **API base URL** | Production and sandbox base URLs. HTTPS (TLS 1.2+) is mandatory. |
| 2 | **Authentication method** | Bearer token / API key header / Basic auth / query-string key / request signing. Exact header or parameter names. |
| 3 | **API credentials** | Issued separately for sandbox and production. Tell us the expiry and rotation procedure. |
| 4 | **Sandbox / test environment** | URL, test credentials, test phone numbers, and how to trigger each delivery outcome (delivered, failed, rejected). |
| 5 | **Production onboarding** | Steps, documents (KYC, business registration), approval time, and any go-live checklist. |
| 6 | **IP / domain allowlisting** | Whether you require our servers' outbound IPs to be allowlisted. We will supply our egress IPs on request: **[EGRESS IP(S) — to be provided by [YOUR COMPANY NAME]]**. Please also list **your** callback source IPs so we can allowlist them. |

### 2.2 Sending messages

| # | Item | Details we need |
|---|------|-----------------|
| 7 | **Single-SMS endpoint** | Method, path, headers, body fields (recipient, message text, sender ID, optional client reference), content type (JSON or form). |
| 8 | **Bulk-SMS support** | If available: endpoint, maximum recipients per request, and whether recipients get per-message IDs. |
| 9 | **Sender ID requirements** | Alphanumeric vs numeric, length (we can send up to 32 characters), registration/approval process and lead time, per-country rules, whether you assign a default. |
| 10 | **Phone-number format** | E.164 (`+2526…`) or national? With/without `+`? Country-specific validation and prefixes you support. |
| 11 | **Encoding and languages** | GSM-7 / UCS-2 / Unicode support, how Arabic, Somali and other scripts are handled, characters that silently switch encoding. |
| 12 | **Message length and segmentation** | Characters per segment for each encoding, maximum segments per message, how concatenated messages are billed and reported. |
| 13 | **Provider message ID** | The field in the send response that uniquely identifies the accepted message. We store it to correlate delivery reports. |
| 14 | **Idempotency / duplicate protection** | Whether you accept a client reference to prevent double sends when we retry after a timeout, and for how long you deduplicate. |
| 15 | **Scheduling / validity** | Optional: scheduled send, message validity period. |

### 2.3 Delivery status

We would like to know the **final delivery state** of each message, not only that you accepted it.

| # | Item | Details we need |
|---|------|-----------------|
| 16 | **Delivery-status mechanism** | Callback (webhook) to us, and/or a status-query endpoint we can poll. Which do you support? |
| 17 | **Callback URL requirements** | HTTPS only? Ports? Do you need a fixed URL per account, or can each request carry its own callback URL? Expected response from us (status code/body). |
| 18 | **Callback authentication** | How do we verify a callback really came from you: HMAC signature (algorithm, header, signed content), shared token, mutual TLS, source-IP allowlist? Include a worked example with a test secret. |
| 19 | **Replay protection** | Timestamp/nonce in callbacks? Tolerance window? |
| 20 | **Delivery statuses** | Complete list with meanings and which are final (e.g. `ACCEPTED`, `SENT`, `DELIVERED`, `UNDELIVERED`, `EXPIRED`, `REJECTED`). |
| 21 | **Callback retry policy** | How often and how long you retry if we do not answer 2xx; whether callbacks can arrive duplicated or out of order. |
| 22 | **Status-query endpoint** | Path, parameters, rate limit, and how long status remains queryable. |

### 2.4 Errors, limits and reliability

| # | Item | Details we need |
|---|------|-----------------|
| 23 | **Error codes** | Full list of HTTP status codes and body error codes, each marked **temporary (safe to retry)** or **permanent (do not retry)**: invalid number, blocked sender, insufficient balance, content rejected, throttled, etc. |
| 24 | **Rate limits** | Requests per second/minute, messages per second, daily caps, and the response and headers (`Retry-After`) you return when limited. |
| 25 | **Timeouts and retry guidance** | Recommended client timeout, your typical response time, and your advice for retrying after a timeout without double-sending. |
| 26 | **Balance / credit** | How to check remaining balance, low-balance notifications, behaviour at zero balance. |
| 27 | **Opt-out / compliance** | Regulatory requirements (opt-out keywords, quiet hours, template pre-approval, content restrictions) for the countries you serve. |
| 28 | **Reporting and reconciliation** | Delivery reports/CDR exports, billing statements, and how message counts are reconciled. |

### 2.5 Support and operations

| # | Item | Details we need |
|---|------|-----------------|
| 29 | **Support contacts** | Technical support address/phone, hours and time zone, expected response times per severity. |
| 30 | **Escalation path** | Named contacts for outages and for onboarding blockers. |
| 31 | **Status page / maintenance notices** | Where planned maintenance and incidents are published. |
| 32 | **SLA** | Availability and delivery-time commitments, if any. |

## 3. EXAMPLES (illustrative only — not your contract)

**EXAMPLE — send request** (`POST {base_url}/messages`):

```http
POST /v1/messages HTTP/1.1
Host: api.sms-provider.example
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "to": "+252611234567",
  "from": "ACMESHOP",
  "text": "Payment of 25.00 USD received for invoice INV-1042. Thank you.",
  "client_reference": "msg-7f3c1e"
}
```

**EXAMPLE — success response:**

```json
{ "status": "accepted", "data": { "message_id": "m_01HXYZ", "segments": 1 } }
```

**EXAMPLE — error response:**

```json
{ "status": "error", "code": "INVALID_NUMBER", "message": "Recipient is not a valid mobile number" }
```

**EXAMPLE — delivery callback to our system** (the exact callback address and authentication will be agreed once we know which mechanism you offer):

```http
POST <our callback URL> HTTP/1.1
Content-Type: application/json
X-Signature: <hex HMAC-SHA256 of "<timestamp>." + raw body>
X-Timestamp: 1767225600

{
  "message_id": "m_01HXYZ",
  "client_reference": "msg-7f3c1e",
  "status": "DELIVERED",
  "delivered_at": "2026-01-01T00:00:12Z",
  "error_code": null
}
```

## 4. INFORMATION WE NEED FROM YOUR TECHNICAL TEAM

Please return this checklist with your API documentation.

- [ ] Sandbox **and** production base URLs
- [ ] Authentication method with exact header/parameter names, and a worked example
- [ ] Sandbox credentials and test phone numbers (with outcome triggers)
- [ ] Single-SMS endpoint: request and response with field names and types
- [ ] Bulk-SMS endpoint (or confirmation that it is not offered)
- [ ] Sender ID rules, registration process and lead time
- [ ] Accepted phone-number format(s)
- [ ] Supported encodings/languages and segment-length rules
- [ ] Name of the provider message-ID field in the send response
- [ ] Duplicate-send protection (client reference / idempotency) behaviour
- [ ] Delivery-status mechanism: callback and/or query endpoint
- [ ] Callback authentication scheme with a worked signature example
- [ ] Complete list of delivery statuses, marking the final ones
- [ ] Complete list of error codes, marking retryable vs permanent
- [ ] Rate limits and the response when limited
- [ ] Recommended timeout and retry behaviour
- [ ] Source IPs for callbacks and whether our IPs must be allowlisted
- [ ] Production onboarding steps, documents required and expected timeline
- [ ] Balance-check method and low-balance behaviour
- [ ] Regulatory/content restrictions for the target countries
- [ ] Support contacts, escalation path, SLA and status page

## 5. Next steps

1. You return the checklist and API documentation.
2. We confirm fit and request sandbox access.
3. We configure and test against your sandbox together with you.
4. You complete production onboarding; we go live on agreed sender IDs.

*This document contains no credentials. Please never send secrets by email — share them through a channel we agree
in advance.*

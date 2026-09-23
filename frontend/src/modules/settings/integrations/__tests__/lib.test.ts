import { describe, expect, it } from "vitest";
import type { PaymentIntent, SmsProvider } from "@/services/api/integrations";
import {
  REDACTED,
  buildPaymentProviderInput,
  buildSmsProviderInput,
  describeCredential,
  emptyPaymentProviderForm,
  emptySmsProviderForm,
  findLiteralSecrets,
  integrationCaps,
  platformIntegrationCaps,
  intentStatusView,
  paginate,
  redactConfig,
  searchRows,
  settledTransactions,
  smsFormFromProvider,
  validateCredentialForm,
  validatePaymentProviderForm,
  validateSmsProviderForm,
  validateTemplateForm,
  validateTestSms,
} from "../lib";

const validHttp = () => ({
  ...emptySmsProviderForm(),
  name: "Gateway",
  url: "https://api.gateway.example/v1/sms",
  credential_id: "cred-1",
});

describe("permission guards", () => {
  const caps = (...granted: string[]) => integrationCaps((p) => granted.includes(p));

  it("grants nothing without permissions", () => {
    const c = caps();
    expect(c).toMatchObject({ any: false, sms: false, payments: false, manage: false, sendSms: false, reconcile: false });
  });

  it("view alone is read-only SMS operations", () => {
    const c = caps("integrations.view");
    expect(c.sms && c.view && c.operations).toBe(true);
    expect(c.manage || c.sendSms || c.reconcile || c.paymentsView || c.payments).toBe(false);
  });

  it("tenant permissions never expose provider infrastructure", () => {
    const all = caps("integrations.view", "integrations.manage", "integrations.sms.send", "integrations.payments.view", "integrations.payments.reconcile");
    expect(all.providers).toBe(false);
    expect(all.reconcile).toBe(false);
  });

  it("platform caps manage providers but not tenant operations", () => {
    expect(platformIntegrationCaps()).toMatchObject({ providers: true, manage: true, reconcile: true, operations: false, sendSms: false });
  });

  it("payments.view alone opens payments but not SMS or provider config", () => {
    const c = caps("integrations.payments.view");
    expect(c.payments).toBe(true);
    expect(c.sms).toBe(false);
    expect(c.view).toBe(false);
  });

  it("manage, send and reconcile are independent grants", () => {
    expect(caps("integrations.view", "integrations.manage").manage).toBe(true);
    expect(caps("integrations.view").sendSms).toBe(false);
    expect(caps("integrations.view", "integrations.sms.send").sendSms).toBe(true);
  });
});

describe("masked credentials", () => {
  it("shows label and masked tail only", () => {
    const text = describeCredential({ id: "1", label: "Gateway key", has_secret: true, masked_tail: "••••9f2a", rotated_at: null });
    expect(text).toBe("Gateway key · ••••9f2a");
  });

  it("does not invent a tail for short secrets", () => {
    expect(describeCredential({ id: "1", label: "K", has_secret: true, masked_tail: "", rotated_at: null })).toBe("K · secret stored");
  });

  it("reports a missing secret and a missing credential", () => {
    expect(describeCredential({ id: "1", label: "K", has_secret: false, masked_tail: "", rotated_at: null })).toContain("no secret");
    expect(describeCredential(null)).toBe("No credential linked");
  });
});

describe("secret hygiene in provider config", () => {
  it("flags literal secrets but accepts placeholders", () => {
    expect(findLiteralSecrets({ Authorization: "Bearer {secret}", key: "{secret}" })).toEqual([]);
    expect(findLiteralSecrets({ Authorization: "Bearer sk_live_123", api_key: "abc" })).toEqual(["Authorization", "api_key"]);
    expect(findLiteralSecrets({ text: "{message}", from: "ACME" })).toEqual([]);
  });

  it("redacts literal secrets, keeps placeholders and ordinary values", () => {
    const out = redactConfig({ url: "https://x.example", headers: { Authorization: "Bearer {secret}", "X-Api-Key": "live-key" }, body: { token: "abc" } });
    expect(out).toEqual({
      url: "https://x.example",
      headers: { Authorization: "Bearer {secret}", "X-Api-Key": REDACTED },
      body: { token: REDACTED },
    });
  });

  it("a stored literal secret is masked when the edit form loads it", () => {
    const provider: SmsProvider = {
      id: "p1", name: "Legacy", provider_type: "CUSTOM_HTTP", branch_id: null, sender_id: "", credential_id: null,
      is_active: true, is_default: false,
      config: { url: "https://x.example/send", headers: { Authorization: "Bearer topsecretvalue" }, body: { to: "{to}", text: "{message}" } },
    };
    const form = smsFormFromProvider(provider);
    expect(JSON.stringify(form)).not.toContain("topsecretvalue");
    // ...and saving it as-is is refused until the user moves the secret into a credential.
    expect(validateSmsProviderForm({ ...form, credential_id: "c" }).headers).toMatch(/credential/i);
  });
});

describe("SMS provider form validation", () => {
  it("accepts a well-formed custom HTTP provider", () => {
    expect(validateSmsProviderForm(validHttp())).toEqual({});
  });

  it("requires a name", () => {
    expect(validateSmsProviderForm({ ...validHttp(), name: "  " }).name).toBeTruthy();
  });

  it("requires an https URL", () => {
    expect(validateSmsProviderForm({ ...validHttp(), url: "http://api.example/send" }).url).toMatch(/https/);
    expect(validateSmsProviderForm({ ...validHttp(), url: "not a url" }).url).toBeTruthy();
  });

  it.each(["https://localhost/send", "https://127.0.0.1/send", "https://10.0.0.5/send", "https://192.168.1.9/x", "https://172.20.0.1/x", "https://169.254.169.254/x"])(
    "rejects private host %s",
    (url) => expect(validateSmsProviderForm({ ...validHttp(), url }).url).toMatch(/private|internal/)
  );

  it("bounds the timeout to 1–30 seconds", () => {
    expect(validateSmsProviderForm({ ...validHttp(), timeout_seconds: "0" }).timeout_seconds).toBeTruthy();
    expect(validateSmsProviderForm({ ...validHttp(), timeout_seconds: "31" }).timeout_seconds).toBeTruthy();
    expect(validateSmsProviderForm({ ...validHttp(), timeout_seconds: "abc" }).timeout_seconds).toBeTruthy();
  });

  it("validates success status codes", () => {
    expect(validateSmsProviderForm({ ...validHttp(), success_statuses: "200, 201" })).toEqual({});
    expect(validateSmsProviderForm({ ...validHttp(), success_statuses: "ok" }).success_statuses).toBeTruthy();
    expect(validateSmsProviderForm({ ...validHttp(), success_statuses: "99" }).success_statuses).toBeTruthy();
  });

  it("requires the body to carry both {to} and {message}", () => {
    expect(validateSmsProviderForm({ ...validHttp(), body: [] }).body).toBeTruthy();
    expect(validateSmsProviderForm({ ...validHttp(), body: [{ key: "to", value: "{to}" }] }).body).toMatch(/\{message\}/);
  });

  it("refuses a literal secret typed into headers or body", () => {
    const f = { ...validHttp(), headers: [{ key: "Authorization", value: "Bearer abc123" }] };
    expect(validateSmsProviderForm(f).headers).toMatch(/Authorization/);
    const g = { ...validHttp(), body: [...validHttp().body, { key: "api_key", value: "abc123" }] };
    expect(validateSmsProviderForm(g).headers).toMatch(/api_key/);
  });

  it("requires a credential when the template uses {secret}", () => {
    expect(validateSmsProviderForm({ ...validHttp(), credential_id: "" }).credential_id).toBeTruthy();
    const noSecretUse = { ...validHttp(), credential_id: "", headers: [] };
    expect(validateSmsProviderForm(noSecretUse).credential_id).toBeUndefined();
  });

  it("limits the sender ID length", () => {
    expect(validateSmsProviderForm({ ...validHttp(), sender_id: "x".repeat(33) }).sender_id).toBeTruthy();
  });

  it("only needs a name for the mock provider", () => {
    expect(validateSmsProviderForm({ ...emptySmsProviderForm(), provider_type: "MOCK", name: "Mock" })).toEqual({});
  });

  it("builds an API payload with credential ids and no secret material", () => {
    const input = buildSmsProviderInput({ ...validHttp(), success_statuses: "200,201", reference_path: "data.id" });
    expect(input).toMatchObject({
      provider_type: "CUSTOM_HTTP", credential_id: "cred-1", branch_id: null,
      config: { url: "https://api.gateway.example/v1/sms", method: "POST", timeout_seconds: 10, success_statuses: [200, 201], reference_path: "data.id" },
    });
    expect(Object.keys(input)).not.toContain("secret");
  });
});

describe("payment provider form validation", () => {
  const base = { ...emptyPaymentProviderForm(), name: "Merchant" };

  it("accepts a named provider and builds a payload without secrets", () => {
    expect(validatePaymentProviderForm(base)).toEqual({});
    const input = buildPaymentProviderInput({ ...base, credential_id: "a", webhook_credential_id: "b", metadata: [{ key: "merchant_id", value: "M-100" }] });
    expect(input).toMatchObject({ credential_id: "a", webhook_credential_id: "b", config: { merchant_id: "M-100", mode: "success" } });
  });

  it("requires a name", () => {
    expect(validatePaymentProviderForm({ ...base, name: "" }).name).toBeTruthy();
  });

  it("rejects secret-looking metadata keys (metadata is unencrypted)", () => {
    expect(validatePaymentProviderForm({ ...base, metadata: [{ key: "api_key", value: "x" }] }).metadata).toMatch(/api_key/);
    expect(validatePaymentProviderForm({ ...base, metadata: [{ key: "client_secret", value: "x" }] }).metadata).toBeTruthy();
    expect(validatePaymentProviderForm({ ...base, metadata: [{ key: "merchant_id", value: "x" }] })).toEqual({});
  });

  it("requires distinct API and webhook secrets", () => {
    expect(validatePaymentProviderForm({ ...base, credential_id: "same", webhook_credential_id: "same" }).webhook_credential_id).toBeTruthy();
  });
});

describe("template, credential and test-SMS validation", () => {
  it("validates template code and body", () => {
    expect(validateTemplateForm({ code: "", name: "", body: "" })).toMatchObject({ code: expect.any(String), body: expect.any(String) });
    expect(validateTemplateForm({ code: "bad code!", name: "", body: "x" }).code).toBeTruthy();
    expect(validateTemplateForm({ code: "invoice_paid", name: "", body: "Hi {customer}" })).toEqual({});
  });

  it("validates a new credential", () => {
    expect(validateCredentialForm({ label: "", secret: "" })).toMatchObject({ label: expect.any(String), secret: expect.any(String) });
    expect(validateCredentialForm({ label: "K", secret: "s" })).toEqual({});
  });

  it("normalises phone numbers like the backend", () => {
    expect(validateTestSms({ to: "+252 61-555 (1234)", body: "hi" })).toEqual({});
    expect(validateTestSms({ to: "12345", body: "hi" }).to).toBeTruthy();
    expect(validateTestSms({ to: "abc", body: "hi" }).to).toBeTruthy();
    expect(validateTestSms({ to: "+2526155512", body: " " }).body).toBeTruthy();
  });
});

describe("payment status comes from the backend", () => {
  const intent = (over: Partial<PaymentIntent>): PaymentIntent => ({
    id: "i", invoice_id: "inv", branch_id: "b", provider_id: "p", idempotency_key: "k", amount: "10.0000", currency: "USD",
    method: "mobile", status: "pending", provider_reference: "ref", expires_at: null, failure_reason: "", payment_id: null,
    settled_at: null, created_at: "2026-01-01T00:00:00Z", ...over,
  });

  it("maps statuses one-to-one with no upgrade", () => {
    expect(intentStatusView("pending").label).toBe("Pending");
    expect(intentStatusView("succeeded").label).toBe("Succeeded");
    expect(intentStatusView("failed").variant).toBe("destructive");
    expect(intentStatusView("something_new").label).toBe("something_new"); // unknown stays visible, never "success"
  });

  it("counts a transaction only when the backend says succeeded AND linked a payment", () => {
    const rows = [
      intent({ id: "a", status: "succeeded", payment_id: "pay" }),
      intent({ id: "b", status: "succeeded", payment_id: null }),
      intent({ id: "c", status: "pending", payment_id: "pay" }),
      intent({ id: "d", status: "failed" }),
    ];
    expect(settledTransactions(rows).map((r) => r.id)).toEqual(["a"]);
  });
});

describe("search and pagination", () => {
  const rows = Array.from({ length: 25 }, (_, i) => ({ n: `item-${i}` }));
  it("searches case-insensitively", () => {
    expect(searchRows(rows, "ITEM-2", (r) => [r.n]).length).toBe(6); // 2, 20..24
    expect(searchRows(rows, "  ", (r) => [r.n]).length).toBe(25);
  });
  it("paginates and clamps the page", () => {
    expect(paginate(rows, 1, 10)).toMatchObject({ pageCount: 3, total: 25 });
    expect(paginate(rows, 3, 10).rows.length).toBe(5);
    expect(paginate(rows, 99, 10).page).toBe(3);
    expect(paginate([], 1, 10)).toMatchObject({ pageCount: 1, total: 0 });
  });
});

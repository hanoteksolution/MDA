import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type {
  IntegrationCredential,
  PaymentIntent,
  PaymentProvider,
  PaymentWebhookEvent,
  ReconciliationRecord,
  SmsLog,
  SmsProvider,
  SmsTemplate,
} from "@/services/api/integrations";
import { integrationCaps, platformIntegrationCaps, summarize } from "../lib";
import type { IntegrationCaps } from "../lib";
import {
  OverviewView,
  PaymentIntentsView,
  PaymentProvidersView,
  PaymentTransactionsView,
  ReconciliationView,
  SmsLogsView,
  SmsProvidersView,
  SmsTemplatesView,
  WebhookEventsView,
} from "../components/views";
import type { Load } from "../components/views";
import { PaymentProviderFormView, SmsProviderFormView, TestSmsPanel } from "../components/forms";

const caps = (...granted: string[]): IntegrationCaps => integrationCaps((p) => granted.includes(p));
const READ = caps("integrations.view", "integrations.payments.view");
const ADMIN = caps("integrations.view", "integrations.manage", "integrations.sms.send", "integrations.payments.view", "integrations.payments.reconcile");
const branches = { name: (id: string | null | undefined) => (id ? "Hodan" : "—") };
const noop = () => undefined;

const ok = <T,>(data: T[]): Load<T> => ({ data, loading: false, error: null, onRetry: noop });
const loading = <T,>(): Load<T> => ({ data: [], loading: true, error: null });
const failed = <T,>(message: string): Load<T> => ({ data: [], loading: false, error: message, onRetry: noop });
const html = (el: React.ReactElement) => renderToStaticMarkup(el);
const tbody = (out: string) => out.match(/<tbody[^>]*>.*<\/tbody>/s)?.[0] ?? "";

const SECRET = "sk_live_SUPERSECRETVALUE_123456";
const credential: IntegrationCredential = { id: "c1", label: "Gateway key", has_secret: true, masked_tail: "••••3456", rotated_at: null };
const smsProvider: SmsProvider = {
  id: "s1", name: "Primary gateway", provider_type: "CUSTOM_HTTP", branch_id: null, sender_id: "ACME", credential_id: "c1",
  is_active: true, is_default: true,
  config: { url: "https://gw.example/send", headers: { Authorization: "Bearer {secret}" }, body: { to: "{to}", text: "{message}" } },
};
const payProvider: PaymentProvider = {
  id: "p1", name: "Merchant A", provider_type: "MOCK", branch_id: "b1", credential_id: "c1", webhook_credential_id: "c1",
  config: {}, is_active: true, webhook_path: "/api/v1/integrations/payments/webhooks/p1/",
};
const intent = (over: Partial<PaymentIntent> = {}): PaymentIntent => ({
  id: "11111111-aaaa", invoice_id: "22222222-bbbb", branch_id: "b1", provider_id: "p1", idempotency_key: "k", amount: "25.0000",
  currency: "USD", method: "mobile", status: "pending", provider_reference: "ref-1", expires_at: null, failure_reason: "",
  payment_id: null, settled_at: null, created_at: "2026-01-01T10:00:00Z", ...over,
});

describe("loading / error / empty states", () => {
  it("shows a skeleton while loading, without table data", () => {
    const out = html(<SmsProvidersView load={loading()} credentials={[]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(out).toContain('data-state="loading"');
    expect(out).not.toContain("<table");
  });

  it("shows the error and a retry action", () => {
    const out = html(<SmsLogsView load={failed("Network down")} branches={branches} />);
    expect(out).toContain('data-state="error"');
    expect(out).toContain("Network down");
    expect(out).toContain("Try again");
  });

  it("shows an empty state, with a call to action only for managers", () => {
    const manager = html(<SmsProvidersView load={ok([])} credentials={[]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(manager).toContain("No SMS provider configured");
    expect(manager).toContain("Add provider");
    const viewer = html(<SmsProvidersView load={ok([])} credentials={[]} branches={branches} caps={READ} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(viewer).toContain("No SMS provider configured");
    expect(viewer).not.toContain("Add provider");
  });

  it.each([
    ["templates", () => html(<SmsTemplatesView load={ok<SmsTemplate>([])} caps={ADMIN} onAdd={noop} />), "No templates yet"],
    ["sms logs", () => html(<SmsLogsView load={ok<SmsLog>([])} branches={branches} />), "No messages yet"],
    ["intents", () => html(<PaymentIntentsView load={ok<PaymentIntent>([])} providerName={() => "x"} branches={branches} />), "No payment intents"],
    ["transactions", () => html(<PaymentTransactionsView load={ok<PaymentIntent>([intent()])} providerName={() => "x"} branches={branches} />), "No settled transactions"],
    ["webhooks", () => html(<WebhookEventsView load={ok<PaymentWebhookEvent>([])} providerName={() => "x"} />), "No webhook events yet"],
    ["reconciliation", () => html(<ReconciliationView load={ok<ReconciliationRecord>([])} caps={ADMIN} running={false} providerName={() => "x"} branches={branches} onRun={noop} onResolve={noop} />), "No discrepancies"],
  ])("%s has an empty state", (_name, render, text) => {
    expect(render()).toContain(text);
  });

  it("renders rows with search and status filter when data exists", () => {
    const out = html(<SmsProvidersView load={ok([smsProvider])} credentials={[credential]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(out).toContain("Primary gateway");
    expect(out).toContain('aria-label="Search"');
    expect(out).toContain("Default");
    const logs = html(<SmsLogsView load={ok<SmsLog>([{ id: "l1", branch_id: null, provider_id: "s1", to: "+252611", sender_id: "ACME", body: "Hi", status: "FAILED", provider_reference: "", attempts: 4, next_retry_at: null, sent_at: null, error: "Provider rejected the number.", entity_type: "", entity_id: "", created_at: "2026-01-01T00:00:00Z" }])} branches={branches} />);
    expect(logs).toContain('aria-label="Filter by status"');
    expect(logs).toContain("Failed");
    expect(logs).toContain("Provider rejected the number.");
  });

  it("warns when a list may be truncated at the API cap", () => {
    const many = Array.from({ length: 200 }, (_, i) => ({ ...intent(), id: `id-${i}` }));
    expect(html(<PaymentIntentsView load={ok(many)} providerName={() => "x"} branches={branches} />)).toContain("most recent 200");
  });
});

describe("permission-aware actions", () => {
  it("hides create / edit / disable for read-only viewers", () => {
    const out = html(<SmsProvidersView load={ok([smsProvider])} credentials={[credential]} branches={branches} caps={READ} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(out).toContain("Primary gateway");
    expect(out).not.toContain("Add provider");
    expect(out).not.toContain("Edit Primary gateway");
    expect(out).not.toContain("Disable Primary gateway");
  });

  it("shows edit / disable for managers", () => {
    const out = html(<SmsProvidersView load={ok([smsProvider])} credentials={[credential]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(out).toContain('aria-label="Edit Primary gateway"');
    expect(out).toContain('aria-label="Disable Primary gateway"');
  });

  it("offers Enable (not Disable) on a disabled provider", () => {
    const out = html(<PaymentProvidersView load={ok([{ ...payProvider, is_active: false }])} credentials={[credential]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(out).toContain('aria-label="Enable Merchant A"');
    expect(out).toContain("Disabled");
  });

  it("only reconcilers can run reconciliation or resolve records", () => {
    const record: ReconciliationRecord = { id: "r1", branch_id: "b1", provider_id: "p1", intent_id: "33333333", kind: "amount_mismatch", status: "open", provider_status: "succeeded", provider_amount: "10", ledger_status: "succeeded", ledger_amount: "9", detail: "Amounts differ", resolved_at: null, resolution_note: "", created_at: "2026-01-01T00:00:00Z" };
    const viewer = html(<ReconciliationView load={ok([record])} caps={READ} running={false} providerName={() => "Merchant A"} branches={branches} onRun={noop} onResolve={noop} />);
    expect(viewer).toContain("Amount mismatch");
    expect(viewer).not.toContain("Run reconciliation");
    expect(viewer).not.toContain(">Resolve<");
    const admin = html(<ReconciliationView load={ok([record])} caps={platformIntegrationCaps()} running={false} providerName={() => "Merchant A"} branches={branches} onRun={noop} onResolve={noop} />);
    expect(admin).toContain("Run reconciliation");
    expect(admin).toContain(">Resolve<");
  });

  it("does not offer Resolve on an already-resolved record", () => {
    const record: ReconciliationRecord = { id: "r2", branch_id: "b1", provider_id: "p1", intent_id: "33333333", kind: "late_success", status: "resolved", provider_status: "", provider_amount: null, ledger_status: "", ledger_amount: null, detail: "", resolved_at: "2026-01-02T00:00:00Z", resolution_note: "Refunded manually", created_at: "2026-01-01T00:00:00Z" };
    const out = html(<ReconciliationView load={ok([record])} caps={platformIntegrationCaps()} running={false} providerName={() => "x"} branches={branches} onRun={noop} onResolve={noop} />);
    expect(out).toContain("Refunded manually");
    expect(out).not.toContain(">Resolve<");
  });

  it("overview only shows the sections the user can access", () => {
    const summary = summarize({ smsProviders: [smsProvider], smsLogs: [], paymentProviders: [payProvider], intents: [], events: [], records: [] });
    const smsOnly = html(<OverviewView caps={caps("integrations.view")} summary={summary} loading={false} error={null} onOpen={noop} />);
    expect(smsOnly).toContain("SMS needing attention");
    expect(smsOnly).not.toContain("SMS providers");
    expect(smsOnly).not.toContain("Open reconciliation");
    const paymentsOnly = html(<OverviewView caps={caps("integrations.payments.view")} summary={summary} loading={false} error={null} onOpen={noop} />);
    expect(paymentsOnly).toContain("Payments in progress");
    expect(paymentsOnly).not.toContain("Open reconciliation");
    expect(paymentsOnly).not.toContain("Payment providers");
    const platform = html(<OverviewView caps={platformIntegrationCaps()} summary={summary} loading={false} error={null} onOpen={noop} />);
    for (const label of ["SMS providers", "Payment providers", "Webhook problems", "Open reconciliation"]) expect(platform).toContain(label);
    expect(platform).not.toContain("SMS needing attention");
  });
});

describe("secrets never render", () => {
  it("provider lists show only the masked credential", () => {
    const sms = html(<SmsProvidersView load={ok([smsProvider])} credentials={[credential]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    const pay = html(<PaymentProvidersView load={ok([payProvider])} credentials={[credential]} branches={branches} caps={ADMIN} onAdd={noop} onEdit={noop} onToggle={noop} />);
    for (const out of [sms, pay]) {
      expect(out).toContain("Gateway key · ••••3456");
      expect(out).not.toContain(SECRET);
    }
    expect(sms).not.toContain("Bearer");
  });

  it("the SMS edit form never prefills any secret and its secret inputs are password fields", () => {
    const out = html(<SmsProviderFormView initial={smsProvider} credentials={[credential]} branches={[]} canManageCredentials onSave={async () => ({})} onCancel={noop} />);
    expect(out).toContain("Gateway key · ••••3456");
    expect(out).toContain('type="password"'); // the write-only "replace secret" input
    expect(out).toMatch(/id="credential_id-rotate"[^>]*type="password"|type="password"[^>]*id="credential_id-rotate"/);
    expect(out).not.toMatch(/type="password"[^>]*value="[^"]+"/);
    expect(out).not.toContain(SECRET);
  });

  it("the payment form shows two separate write-only secret slots and no values", () => {
    const out = html(<PaymentProviderFormView initial={payProvider} credentials={[credential]} branches={[]} canManageCredentials onSave={async () => ({})} onCancel={noop} />);
    expect(out).toContain("API credential");
    expect(out).toContain("Webhook signing secret");
    expect(out).not.toMatch(/type="password"[^>]*value="[^"]+"/);
    expect(out).toContain("/api/v1/integrations/payments/webhooks/p1/");
  });

  it("users without manage rights cannot rotate a secret from the form", () => {
    const out = html(<SmsProviderFormView initial={smsProvider} credentials={[credential]} branches={[]} canManageCredentials={false} onSave={async () => ({})} onCancel={noop} />);
    expect(out).not.toContain("credential_id-rotate");
    expect(out).not.toContain("Create new credential");
  });

  it("webhook events never expose bodies or signatures", () => {
    const event: PaymentWebhookEvent = { id: "e1", provider_id: "p1", event_id: "evt_1", signature_valid: false, status: "rejected", reason: "Bad signature", intent_id: null, received_at: "2026-01-01T00:00:00Z", processed_at: null };
    const out = html(<WebhookEventsView load={ok([event])} providerName={() => "Merchant A"} />);
    expect(out).toContain("Not verified");
    expect(out).toContain("Rejected");
    expect(out.toLowerCase()).not.toContain("raw_body");
  });
});

describe("payment status is backend-verified", () => {
  it("renders the backend status verbatim and never a pay/confirm control", () => {
    const out = html(<PaymentIntentsView load={ok([intent({ status: "pending" }), intent({ id: "x2", status: "failed", failure_reason: "Declined" })])} providerName={() => "Merchant A"} branches={branches} onRefresh={noop} />);
    expect(tbody(out)).toContain("Pending");
    expect(tbody(out)).toContain("Declined");
    expect(tbody(out)).not.toContain("Succeeded"); // no row is shown as succeeded unless the backend said so
    for (const forbidden of ["Mark as paid", "Mark paid", "Confirm payment", "Pay now", "Approve"]) {
      expect(out).not.toContain(forbidden);
    }
    expect(out).toContain("never from this page or the browser");
  });

  it("lists as a transaction only intents the backend settled with a payment", () => {
    const rows = [
      intent({ id: "i1", invoice_id: "aaaaaaaa-1", status: "succeeded", payment_id: "pay-1", settled_at: "2026-01-01T10:05:00Z" }),
      intent({ id: "i2", invoice_id: "bbbbbbbb-2", status: "pending" }),
      intent({ id: "i3", invoice_id: "cccccccc-3", status: "succeeded", payment_id: null }),
    ];
    const out = html(<PaymentTransactionsView load={ok(rows)} providerName={() => "Merchant A"} branches={branches} />);
    expect(tbody(out).match(/<tr/g)).toHaveLength(1);
    expect(tbody(out)).toContain("Succeeded");
    expect(tbody(out)).toContain("aaaaaaaa");
    expect(tbody(out)).not.toContain("bbbbbbbb");
    expect(tbody(out)).not.toContain("cccccccc");
  });

  it("has no client-side status mutation in the payments client", async () => {
    const { integrationsApi } = await import("@/services/api/integrations");
    const names = Object.keys(integrationsApi.payments);
    expect(names).not.toEqual(expect.arrayContaining(["confirm"]));
    expect(names.filter((n) => /confirm|settle|markPaid|succeed/i.test(n))).toEqual([]);
  });
});

describe("test SMS panel", () => {
  it("renders the form and states there is no dry-run API", () => {
    const out = html(<TestSmsPanel branches={[{ id: "b1", name: "Hodan" }]} onSend={vi.fn()} />);
    expect(out).toContain("Send test");
    expect(out).toContain("no dry-run");
    expect(out).toContain("Hodan");
  });
});

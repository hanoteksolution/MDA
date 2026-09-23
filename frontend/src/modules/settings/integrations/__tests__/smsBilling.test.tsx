import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { SmsBillingSummary, SmsCreditEntry, SmsPackage, SmsPurchase } from "@/services/api/integrations";
import { integrationCaps, platformIntegrationCaps, purchaseStatusView, validatePackageForm, validityLabel } from "../lib";
import { SmsAdjustmentForm, SmsBillingView, SmsPackagesAdminView } from "../components/smsBilling";
import type { Load } from "../components/views";

const noop = () => undefined;
const ok = <T,>(data: T[]): Load<T> => ({ data, loading: false, error: null, onRetry: noop });
const pkg: SmsPackage = { id: "p1", name: "Starter", code: "S100", sms_quantity: 100, price: "5.0000", currency: "USD", validity_days: 30, description: "", is_active: true };
const summary: SmsBillingSummary = { balance: 42, reserved: 1, used_30d: 8, used_total: 58, purchased_total: 100, next_expiry: [], enforced: true, payments_available: true };
const purchase: SmsPurchase = { id: "u1", package_id: "p1", package_name: "Starter", sms_quantity: 100, price: "5.0000", currency: "USD", validity_days: 30, status: "pending", payment_reference: "mockpay-1", failure_reason: "", credited_at: null, created_at: "2026-09-23T10:00:00Z" };
const entry: SmsCreditEntry = { id: "e1", kind: "reserve", units: -1, balance_after: 42, purchase_id: null, sms_log_id: "l1", expires_at: null, reason: "SMS to •••4567", created_at: "2026-09-23T10:00:00Z" };

const view = (over: Partial<Parameters<typeof SmsBillingView>[0]> = {}) =>
  renderToStaticMarkup(
    <SmsBillingView
      summary={{ data: summary, loading: false, error: null }}
      packages={ok([pkg])}
      purchases={ok([purchase])}
      ledger={ok([entry])}
      canPurchase
      buying={null}
      onBuy={noop}
      {...over}
    />
  );

describe("SMS billing permissions", () => {
  it("billing is a separate tenant grant; platform caps never show tenant billing", () => {
    const has = (...g: string[]) => (p: string) => g.includes(p);
    expect(integrationCaps(has("integrations.sms.billing.view"))).toMatchObject({ billingView: true, billingPurchase: false, sms: true, providers: false });
    expect(integrationCaps(has("integrations.sms.billing.view", "integrations.sms.billing.purchase")).billingPurchase).toBe(true);
    expect(integrationCaps(has("integrations.sms.billing.purchase")).billingPurchase).toBe(false);
    expect(platformIntegrationCaps()).toMatchObject({ billingView: false, billingPurchase: false });
  });
});

describe("tenant SMS billing view", () => {
  it("shows balance, packages, history and activity without any provider data", () => {
    const out = view();
    expect(out).toContain(">42<");
    expect(out).toContain("Starter");
    expect(out).toContain("USD 5.00");
    expect(out).toContain("Valid 30 days");
    expect(out).toContain("Awaiting payment");
    expect(out).toContain("SMS sent");
    expect(out).toContain("Buy package");
    expect(out).not.toMatch(/credential|webhook|secret/i);
  });

  it("hides buying without the purchase permission and disables it when payments are off", () => {
    expect(view({ canPurchase: false })).not.toContain("Buy package");
    const off = view({ summary: { data: { ...summary, payments_available: false }, loading: false, error: null } });
    expect(off).toMatch(/<button[^>]*disabled=""[^>]*>Buy package/);
    expect(off).toContain("Package payments are not available yet");
    expect(view({ buying: "p1" })).toContain("Starting payment…");
  });

  it("shows loading, error and empty states", () => {
    expect(view({ summary: { data: null, loading: true, error: null } })).toContain('aria-label="Loading"');
    expect(view({ packages: { ...ok<SmsPackage>([]), error: "Boom" } })).toContain("Boom");
    expect(view({ packages: ok([]) })).toContain("No packages available");
  });
});

describe("platform SMS billing", () => {
  it("lists packages with edit and activation actions", () => {
    const out = renderToStaticMarkup(<SmsPackagesAdminView load={ok([pkg, { ...pkg, id: "p2", code: "OLD", is_active: false }])} onAdd={noop} onEdit={noop} onToggle={noop} />);
    expect(out).toContain("Deactivate");
    expect(out).toContain("Activate");
    expect(out).toContain("Add package");
  });

  it("adjustments require a reason field", () => {
    const out = renderToStaticMarkup(<SmsAdjustmentForm onSubmit={async () => null} />);
    expect(out).toContain('aria-label="Reason"');
    expect(out).toContain("Remove credits");
  });

  it("validates package input like the backend", () => {
    expect(validatePackageForm({ name: "", code: "", sms_quantity: "0", price: "-1", validity_days: "x" })).toEqual({
      name: expect.any(String), code: expect.any(String), sms_quantity: expect.any(String), price: expect.any(String), validity_days: expect.any(String),
    });
    expect(validatePackageForm({ name: "A", code: "A", sms_quantity: "10", price: "0", validity_days: "" })).toEqual({});
    expect(validityLabel(null)).toBe("No expiry");
    expect(purchaseStatusView("credited").variant).toBe("success");
  });
});

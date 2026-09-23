import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { BillingOverview, BillingPlan, SubscriptionPaymentItem } from "@/services/api/billing";
import { PaymentHistory, PendingPaymentNotice, PlanCards, planAction } from "./BillingViews";

const plan = (over: Partial<BillingPlan>): BillingPlan => ({
  id: "p1", code: "starter", name: "Starter", description: "", monthly_price: "29.0000", max_users: 5, max_branches: 1,
  is_current: true, action: "renew", available: true, reason: "", ...over,
});
const payment = (over: Partial<SubscriptionPaymentItem>): SubscriptionPaymentItem => ({
  id: "x", reference: "SUB-1", kind: "renew", plan_id: "p1", plan_name: "Starter", amount: "29.0000", currency: "USD",
  status: "pending", failure_reason: "", invoice_number: "INV-000001", payment_reference: "mockpay-1",
  payment_expires_at: null, confirmed_at: null, created_at: "2026-09-23T10:00:00Z", ...over,
});
const overview = (over: Partial<BillingOverview> = {}): BillingOverview => ({
  subscription: {
    reference: "SUB-1", plan_id: "p1", plan_name: "Starter", status: "active", started_at: null, expires_at: "2026-10-23",
    next_billing_date: "2026-10-23", days_until_expiry: 30, grace_period_days: 5, billing_period_days: 30, is_usable: true,
    last_paid_at: null, monthly_fee: "29.0000", currency: "USD",
  },
  plans: [plan({}), plan({ id: "p2", code: "business", name: "Business", is_current: false, action: "change", available: false, reason: "Plan changes take effect at renewal: proration of an active paid period is not supported." })],
  payments: [],
  online_payment: true,
  ...over,
});

describe("subscription plan actions", () => {
  it("offers renew/pay on the current plan and switching only where the server allows it", () => {
    expect(planAction(plan({}), "active")).toBe("Renew");
    expect(planAction(plan({}), "expired")).toBe("Pay now");
    expect(planAction(plan({ is_current: false }), "expired")).toBe("Switch to this plan");
    expect(planAction(plan({ available: false }), "active")).toBe("");
  });

  it("renders plans with the server's reason and no buy action without permission or provider", () => {
    const out = renderToStaticMarkup(<PlanCards overview={overview()} busyPlan={null} canPay onPay={() => undefined} />);
    expect(out).toContain("USD 29.00");
    expect(out).toContain(">Renew<");
    expect(out).toContain("proration of an active paid period is not supported");
    expect(out).not.toContain("Switch to this plan");
    expect(renderToStaticMarkup(<PlanCards overview={overview()} busyPlan={null} canPay={false} onPay={() => undefined} />)).not.toContain(">Renew<");
    const offline = renderToStaticMarkup(<PlanCards overview={overview({ online_payment: false })} busyPlan={null} canPay onPay={() => undefined} />);
    expect(offline).toMatch(/<button[^>]*disabled=""[^>]*>Renew/);
    expect(offline).toContain("contact support");
  });
});

describe("payment states", () => {
  it("pending explains that activation waits for the provider's confirmation", () => {
    const out = renderToStaticMarkup(<PendingPaymentNotice payment={payment({})} />);
    expect(out).toContain("Awaiting payment");
    expect(out).toContain("activates automatically once the provider confirms");
  });

  it("shows success and failure without implying activation on failure", () => {
    expect(renderToStaticMarkup(<PendingPaymentNotice payment={payment({ status: "confirmed" })} />)).toContain("Starter is active");
    const failed = renderToStaticMarkup(<PendingPaymentNotice payment={payment({ status: "review", failure_reason: "Paid amount does not match the subscription price." })} />);
    expect(failed).toContain("Under review");
    expect(failed).toContain("does not match");
  });

  it("lists invoices and payments without provider data", () => {
    const out = renderToStaticMarkup(<PaymentHistory payments={[payment({ status: "confirmed", confirmed_at: "2026-09-23T11:00:00Z" })]} />);
    expect(out).toContain("INV-000001");
    expect(out).toContain("Paid");
    expect(out).not.toMatch(/credential|secret|webhook/i);
  });
});

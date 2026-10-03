import { describe, expect, it, vi } from "vitest";

// Page modules import the auth store, which reads localStorage at import time.
vi.hoisted(() => {
  const values = new Map<string, string>();
  Object.assign(globalThis, { localStorage: { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => void values.set(k, v), removeItem: (k: string) => void values.delete(k), clear: () => values.clear() } });
});
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { PageMetaProvider } from "@/contexts/PageMetaContext";
import { BillingBadge, RecoveryDialog, humanize, money } from "./billingUi";
import { PlatformBillingPage } from "./PlatformBillingPage";

const html = (el: React.ReactElement, path = "/platform/billing") => renderToStaticMarkup(<MemoryRouter initialEntries={[path]}><PageMetaProvider>{el}</PageMetaProvider></MemoryRouter>);

describe("Platform billing UI helpers", () => {
  it("shows decimal strings verbatim and never invents missing amounts", () => {
    expect(money("29.00", "USD")).toBe("USD 29.00");
    expect(money(null, "USD")).toBe("—");
    expect(humanize("due_soon")).toBe("Due soon");
  });

  it("renders status badges with tones", () => {
    expect(html(<BillingBadge status="overdue" />)).toContain("Overdue");
    expect(html(<BillingBadge status="overdue" />)).toContain("text-destructive");
    expect(html(<BillingBadge status={null} />)).toContain("—");
  });
});

describe("Manual subscription recovery dialog", () => {
  it("requires a reason and acknowledgement and states no payment is recorded", () => {
    const out = html(<RecoveryDialog target={{ id: "s1", label: "Acme" }} onClose={() => undefined} onDone={() => undefined} />);
    expect(out).toContain("Manual subscription recovery");
    expect(out).toContain("does not record a payment");
    expect(out).toContain("<textarea");
    expect(out).toContain('type="checkbox"');
    expect(out).toMatch(/<button[^>]*disabled[^>]*>.*Apply recovery/s);
  });

  it("renders nothing when closed", () => {
    expect(html(<RecoveryDialog target={null} onClose={() => undefined} onDone={() => undefined} />)).not.toContain("Manual subscription recovery");
  });
});

describe("Platform Admin → Billing page", () => {
  it("renders the section tabs inside the platform page layout", () => {
    const out = html(<PlatformBillingPage />);
    for (const tab of ["Overview", "Subscriptions", "Payments", "Invoices", "Reconciliation", "Plans"]) expect(out).toContain(tab);
    expect(out).toContain("Billing");
  });

  it("renders the subscriptions table toolbar with search and filters", () => {
    const out = html(<PlatformBillingPage />, "/platform/billing?section=subscriptions");
    expect(out).toContain("Search company, workspace, reference or plan…");
    for (const header of ["Company / workspace", "Subscription", "Billing", "Next billing", "Last payment"]) expect(out).toContain(`>${header}<`);
  });
});

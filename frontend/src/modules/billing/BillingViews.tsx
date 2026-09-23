import { CalendarClock, CreditCard, RefreshCw, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ContentSection } from "@/components/layout/ContentSection";
import { EmptyState } from "@/components/layout/EmptyState";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import type { BillingOverview, BillingPlan, SubscriptionPaymentItem, SubscriptionPaymentStatus, SubscriptionStatus } from "@/services/api/billing";

type Variant = "default" | "secondary" | "success" | "warning" | "destructive" | "outline";

const SUB_STATUS: Record<SubscriptionStatus, [string, Variant]> = {
  trial: ["Trial", "warning"],
  active: ["Active", "success"],
  expired: ["Expired", "destructive"],
  suspended: ["Suspended", "destructive"],
};
const PAY_STATUS: Record<SubscriptionPaymentStatus, [string, Variant]> = {
  pending: ["Awaiting payment", "warning"],
  confirmed: ["Paid", "success"],
  failed: ["Failed", "destructive"],
  expired: ["Expired", "secondary"],
  review: ["Under review", "warning"],
};

export const subscriptionStatus = (s: SubscriptionStatus) => SUB_STATUS[s] ?? [s, "outline" as Variant];
export const paymentStatus = (s: SubscriptionPaymentStatus) => PAY_STATUS[s] ?? [s, "outline" as Variant];
export const money = (amount: string, currency: string) => `${currency} ${Number(amount).toFixed(2)}`;
const date = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString() : "—");

/** Which action a plan card offers — the server re-checks every rule at checkout. */
export function planAction(plan: BillingPlan, status: SubscriptionStatus | undefined): string {
  if (!plan.available) return "";
  if (plan.is_current) return status === "active" ? "Renew" : "Pay now";
  return "Switch to this plan";
}

export function CurrentPlanCards({ overview }: { overview: BillingOverview }) {
  const sub = overview.subscription!;
  const [label] = subscriptionStatus(sub.status);
  const days = sub.days_until_expiry;
  return (
    <KpiGrid columns={4}>
      <KpiCard index={0} title="Current plan" value={sub.plan_name} icon={<CreditCard className="h-5 w-5" />} />
      <KpiCard index={1} title="Status" value={label} icon={<ShieldCheck className="h-5 w-5" />} accent={sub.status === "active" ? "success" : "warning"} />
      <KpiCard index={2} title="Expires" value={date(sub.expires_at)} icon={<CalendarClock className="h-5 w-5" />} accent={days !== null && days < 0 ? "warning" : undefined} />
      <KpiCard index={3} title="Next billing" value={money(sub.monthly_fee, sub.currency)} icon={<RefreshCw className="h-5 w-5" />} />
    </KpiGrid>
  );
}

export function PlanCards({
  overview,
  busyPlan,
  canPay,
  onPay,
}: {
  overview: BillingOverview;
  busyPlan: string | null;
  canPay: boolean;
  onPay: (plan: BillingPlan) => void;
}) {
  const status = overview.subscription?.status;
  const currency = overview.subscription?.currency ?? "USD";
  return (
    <ContentSection title="Plans" description={overview.online_payment ? "Monthly billing. Payment is confirmed automatically by the payment provider." : "Online payment is not available yet — contact support to renew."}>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {overview.plans.map((plan) => {
          const action = planAction(plan, status);
          return (
            <article key={plan.id} aria-label={`${plan.name} plan`} className={`flex flex-col rounded-2xl border p-4 ${plan.is_current ? "border-primary/50 bg-primary/5" : "border-border"}`}>
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-semibold">{plan.name}</h3>
                {plan.is_current && <Badge>Current</Badge>}
              </div>
              <p className="mt-2 text-2xl font-semibold">{money(plan.monthly_price, currency)}<span className="text-sm font-normal text-muted-foreground"> / month</span></p>
              <p className="mt-1 text-xs text-muted-foreground">Up to {plan.max_users} users · {plan.max_branches} branches</p>
              {plan.description && <p className="mt-2 text-xs text-muted-foreground">{plan.description}</p>}
              {!plan.available && plan.reason && <p className="mt-3 text-xs text-muted-foreground">{plan.reason}</p>}
              {canPay && action && (
                <Button className="mt-4" size="sm" disabled={!overview.online_payment || busyPlan !== null} onClick={() => onPay(plan)}>
                  {busyPlan === plan.id ? "Starting payment…" : action}
                </Button>
              )}
            </article>
          );
        })}
      </div>
    </ContentSection>
  );
}

export function PendingPaymentNotice({ payment }: { payment: SubscriptionPaymentItem }): ReactNode {
  const [label, variant] = paymentStatus(payment.status);
  const tone = payment.status === "confirmed" ? "border-success/30 bg-success/5" : payment.status === "pending" ? "border-warning/30 bg-warning/5" : "border-destructive/30 bg-destructive/5";
  const text =
    payment.status === "pending"
      ? `Payment of ${money(payment.amount, payment.currency)} started (invoice ${payment.invoice_number ?? "—"}, reference ${payment.payment_reference || payment.reference}). Complete it with the payment provider — your subscription activates automatically once the provider confirms. This page updates by itself.`
      : payment.status === "confirmed"
        ? `Payment received. ${payment.plan_name ?? "Your plan"} is active.`
        : `Payment ${label.toLowerCase()}: ${payment.failure_reason || "no charge was applied to your subscription."}`;
  return (
    <div role="status" className={`flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 text-sm ${tone}`}>
      <Badge variant={variant}>{label}</Badge>
      <span className="flex-1">{text}</span>
    </div>
  );
}

export function PaymentHistory({ payments }: { payments: SubscriptionPaymentItem[] }) {
  const columns: Column<SubscriptionPaymentItem>[] = [
    { key: "date", header: "Date", cell: (p) => date(p.created_at), exportValue: (p) => p.created_at },
    { key: "invoice", header: "Invoice", cell: (p) => p.invoice_number ?? p.reference, exportValue: (p) => p.invoice_number ?? p.reference },
    { key: "plan", header: "Plan", cell: (p) => p.plan_name ?? "—", exportValue: (p) => p.plan_name ?? "" },
    { key: "amount", header: "Amount", cell: (p) => money(p.amount, p.currency), exportValue: (p) => `${p.amount} ${p.currency}` },
    { key: "status", header: "Status", cell: (p) => { const [l, v] = paymentStatus(p.status); return <Badge variant={v}>{l}</Badge>; }, exportValue: (p) => p.status },
    { key: "paid", header: "Paid on", cell: (p) => date(p.confirmed_at), exportValue: (p) => p.confirmed_at ?? "" },
  ];
  return (
    <ContentSection title="Invoices & payments">
      {payments.length ? <DataTable columns={columns} data={payments} exportTitle="Subscription invoices" embedded /> : <EmptyState compact title="No subscription payments yet" />}
    </ContentSection>
  );
}

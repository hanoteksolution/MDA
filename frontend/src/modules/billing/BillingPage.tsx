import { useCallback, useEffect, useRef, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/layout/LoadingState";
import { EmptyState } from "@/components/layout/EmptyState";
import { appDialog } from "@/components/feedback/AppDialog";
import { usePermissions } from "@/hooks/usePermissions";
import { billingApi, type BillingOverview, type BillingPlan, type SubscriptionPaymentItem } from "@/services/api/billing";
import { CurrentPlanCards, PaymentHistory, PendingPaymentNotice, PlanCards, money } from "./BillingViews";

const errorText = (err: unknown, fallback: string) => (err instanceof Error && err.message ? err.message : fallback);

/**
 * Billing & Subscription (tenant). Starting a payment never activates anything: the page only
 * polls the server, which activates/renews after the provider's verified confirmation.
 */
export function BillingPage() {
  const { hasPermission } = usePermissions();
  const canPay = hasPermission("billing.subscription.pay");
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [current, setCurrent] = useState<SubscriptionPaymentItem | null>(null);
  const retryKey = useRef<{ planId: string; key: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = (await billingApi.overview()).data;
      setOverview(data);
      setError(null);
      setCurrent((prev) => prev ?? data.payments.find((p) => p.status === "pending") ?? null);
    } catch (err) {
      setError(errorText(err, "Could not load billing."));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  // Read-only polling of a pending payment; the server alone decides when it is paid.
  useEffect(() => {
    if (!current || current.status !== "pending") return;
    const timer = window.setInterval(async () => {
      try {
        const fresh = (await billingApi.payment(current.id)).data;
        if (fresh.status !== "pending") {
          setCurrent(fresh);
          void load();
        }
      } catch {
        /* keep polling */
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [current, load]);

  const pay = async (plan: BillingPlan) => {
    const ok = await appDialog.confirm(
      `${plan.is_current ? "Pay for" : "Switch to"} ${plan.name}: ${money(plan.monthly_price, overview?.subscription?.currency ?? "USD")} for the next billing period? Your subscription updates automatically after the payment provider confirms payment.`,
      { title: "Subscription payment", confirmLabel: "Start payment", tone: "default" }
    );
    if (!ok) return;
    // Same plan retried (e.g. after a network error) re-uses the key: never a second checkout.
    if (retryKey.current?.planId !== plan.id) retryKey.current = { planId: plan.id, key: crypto.randomUUID() };
    setBusyPlan(plan.id);
    try {
      const res = await billingApi.checkout(plan.id, retryKey.current.key);
      retryKey.current = null;
      setCurrent(res.data);
      void load();
    } catch (err) {
      await appDialog.alert(errorText(err, "Could not start the payment."), { tone: "danger", title: "Payment not started" });
    } finally {
      setBusyPlan(null);
    }
  };

  return (
    <PageLayout title="Billing & Subscription" description="Your ERP plan, renewal date, invoices and payments." breadcrumbs={["Settings", "Billing & Subscription"]}>
      {error && <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</div>}
      {!overview && !error && <LoadingState variant="page" label="Loading billing" />}
      {overview && !overview.subscription && <EmptyState title="No subscription on file" description="Contact Safari Technology support to set up your plan." />}
      {overview?.subscription && (
        <>
          {current && <PendingPaymentNotice payment={current} />}
          <CurrentPlanCards overview={overview} />
          <PlanCards overview={overview} busyPlan={busyPlan} canPay={canPay && current?.status !== "pending"} onPay={(p) => void pay(p)} />
          <PaymentHistory payments={overview.payments} />
        </>
      )}
    </PageLayout>
  );
}

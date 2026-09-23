import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { usePermissions } from "@/hooks/usePermissions";
import { useScopedPath } from "@/hooks/useScopedPath";
import { useBranchStore } from "@/store/branchStore";
import { integrationsApi } from "@/services/api/integrations";
import type { SmsPackage, SmsPurchase } from "@/services/api/integrations";
import { SmsBillingView } from "./components/smsBilling";
import { Notice } from "./components/primitives";
import { describeApiError, integrationCaps, shortId, summarize } from "./lib";
import { useLoad } from "./useLoad";
import type { Loaded } from "./useLoad";
import { Panel } from "./components/primitives";
import { TemplateFormView, TestSmsPanel } from "./components/forms";
import type { Load } from "./components/views";
import { OverviewView, PaymentIntentsView, PaymentTransactionsView, SmsLogsView, SmsTemplatesView } from "./components/views";

type Section = "overview" | "sms" | "payments";

export function asLoad<T>(l: Loaded<T>): Load<T> {
  return { data: l.data, loading: l.loading, error: l.error, onRetry: () => void l.reload() };
}

/**
 * Settings → Integrations (tenant). Operations only: SMS templates, message logs, test SMS and
 * payment intents. Provider configuration, credentials, webhooks and reconciliation are platform
 * infrastructure — see Platform Admin → Integrations; the backend refuses them to tenant users.
 */
export function IntegrationsPage() {
  const { hasPermission } = usePermissions();
  const { scoped } = useScopedPath();
  const caps = useMemo(() => integrationCaps(hasPermission), [hasPermission]);
  const branchList = useBranchStore((s) => s.branches);
  const scopeVersion = useBranchStore((s) => s.scopeVersion);
  const [params, setParams] = useSearchParams();
  const [composing, setComposing] = useState(false);

  const sections = [
    { id: "overview", label: "Overview" },
    ...(caps.sms ? [{ id: "sms", label: "SMS" }] : []),
    ...(caps.payments ? [{ id: "payments", label: "Payments" }] : []),
  ];
  const requested = params.get("section") as Section | null;
  const section: Section = sections.some((s) => s.id === requested) ? (requested as Section) : "overview";

  const smsTabs = [
    { id: "templates", label: "Templates", show: caps.view },
    { id: "logs", label: "Message logs", show: caps.view },
    { id: "test", label: "Test SMS", show: caps.sendSms },
    { id: "billing", label: "Packages & billing", show: caps.billingView },
  ].filter((t) => t.show);
  const paymentTabs = [
    { id: "transactions", label: "Transactions" },
    { id: "intents", label: "Payment intents" },
  ];
  const tabs = section === "sms" ? smsTabs : paymentTabs;
  const requestedTab = params.get("tab");
  const tab = tabs.some((t) => t.id === requestedTab) ? (requestedTab as string) : tabs[0]?.id;

  const go = (nextSection: Section, nextTab?: string) => {
    setComposing(false);
    setParams(nextSection === "overview" ? {} : { section: nextSection, ...(nextTab ? { tab: nextTab } : {}) });
  };

  const deps = [scopeVersion];
  const templates = useLoad(() => integrationsApi.sms.templates(), caps.view, deps);
  const smsLogs = useLoad(() => integrationsApi.sms.logs(), caps.view, deps);
  const intents = useLoad(() => integrationsApi.payments.intents(), caps.paymentsView, deps);
  const billingSummary = useLoad(() => integrationsApi.smsBilling.summary().then((r) => ({ data: [r.data] })), caps.billingView, deps);
  const packages = useLoad(() => integrationsApi.smsBilling.packages(), caps.billingView, deps);
  const purchases = useLoad(() => integrationsApi.smsBilling.purchases(), caps.billingView, deps);
  const ledger = useLoad(() => integrationsApi.smsBilling.ledger(), caps.billingView, deps);
  const [buying, setBuying] = useState<string | null>(null);
  const [pending, setPending] = useState<SmsPurchase | null>(null);
  const [buyError, setBuyError] = useState<string | null>(null);
  const buyKey = useRef<{ packageId: string; key: string } | null>(null);

  // Poll the purchase until the provider's verified confirmation credits it (or it fails).
  useEffect(() => {
    if (!pending || pending.status !== "pending") return;
    const timer = window.setInterval(async () => {
      try {
        const fresh = (await integrationsApi.smsBilling.purchase(pending.id)).data;
        if (fresh.status !== "pending") {
          setPending(fresh);
          void Promise.all([billingSummary.reload(), purchases.reload(), ledger.reload()]);
        }
      } catch {
        /* keep polling; the history table shows the final state */
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [pending]); // eslint-disable-line react-hooks/exhaustive-deps

  const buy = async (pkg: SmsPackage) => {
    const ok = await appDialog.confirm(
      `Buy ${pkg.name}: ${pkg.sms_quantity.toLocaleString()} SMS for ${pkg.currency} ${pkg.price}? Credits are added after the payment provider confirms payment.`,
      { title: "Buy SMS package", confirmLabel: "Start payment", tone: "default" }
    );
    if (!ok) return;
    // Re-use the key if the same package is retried (e.g. after a network error): never double-buy.
    if (buyKey.current?.packageId !== pkg.id) buyKey.current = { packageId: pkg.id, key: crypto.randomUUID() };
    setBuying(pkg.id);
    setBuyError(null);
    try {
      const res = await integrationsApi.smsBilling.buy(pkg.id, buyKey.current.key);
      buyKey.current = null;
      setPending(res.data);
      void purchases.reload();
    } catch (err) {
      setBuyError(describeApiError(err, "Could not start the purchase."));
    } finally {
      setBuying(null);
    }
  };

  const watching = section === "sms" ? tab === "logs" : section === "payments";
  useAutoRefresh(() => (section === "sms" ? smsLogs.reload() : intents.reload()), { intervalMs: 30_000, enabled: watching });

  const branchOptions = useMemo(() => branchList.map((b) => ({ id: b.id, name: b.name })), [branchList]);
  const branches = useMemo(
    () => ({ name: (id: string | null | undefined) => (id ? branchList.find((b) => b.id === id)?.name ?? "Other branch" : "—") }),
    [branchList]
  );
  // Provider names are platform configuration; tenants see a short reference only.
  const providerName = (id: string) => shortId(id);

  const loads = [smsLogs, intents];
  const overview = useMemo(
    () => summarize({ smsProviders: [], smsLogs: smsLogs.data, paymentProviders: [], intents: intents.data, events: [], records: [] }),
    [smsLogs.data, intents.data]
  );

  const saveTemplate = async (input: { code: string; name: string; body: string }) => {
    try {
      await integrationsApi.sms.createTemplate(input);
      await templates.reload();
      setComposing(false);
      return null;
    } catch (err) {
      return describeApiError(err, "Could not save the template.");
    }
  };

  const sendTest = async (input: { to: string; body: string; branch_id?: string }) => {
    try {
      const res = await integrationsApi.sms.send(input);
      void smsLogs.reload();
      const status = res.data.status;
      return {
        ok: status !== "FAILED",
        message: status === "FAILED" ? `Not sent: ${res.data.error || "see message log"}.` : `Queued (${status.toLowerCase()}). Check Message logs for delivery.`,
      };
    } catch (err) {
      return { ok: false, message: describeApiError(err, "Could not send the test message.") };
    }
  };

  let body;
  if (!caps.any) {
    body = (
      <Panel>
        <p role="alert" className="p-6 text-sm text-muted-foreground">You do not have permission to view integrations.</p>
      </Panel>
    );
  } else if (section === "overview") {
    body = (
      <OverviewView
        caps={caps}
        summary={overview}
        loading={loads.some((l) => l.loading)}
        error={loads.find((l) => l.error)?.error ?? null}
        onRetry={() => void Promise.all(loads.map((l) => l.reload()))}
        onOpen={go}
      />
    );
  } else if (section === "sms" && composing) {
    body = <TemplateFormView onSave={saveTemplate} onCancel={() => setComposing(false)} />;
  } else if (section === "sms") {
    body = tab === "logs"
      ? <SmsLogsView load={asLoad(smsLogs)} branches={branches} />
      : tab === "test"
        ? <TestSmsPanel branches={branchOptions} onSend={sendTest} />
        : tab === "billing"
        ? (
          <SmsBillingView
            summary={{ data: billingSummary.data[0] ?? null, loading: billingSummary.loading, error: billingSummary.error, onRetry: () => void billingSummary.reload() }}
            packages={asLoad(packages)}
            purchases={asLoad(purchases)}
            ledger={asLoad(ledger)}
            canPurchase={caps.billingPurchase}
            buying={buying}
            onBuy={(p) => void buy(p)}
            message={
              buyError ? <Notice tone="warning">{buyError}</Notice>
              : pending ? (
                <Notice tone={pending.status === "credited" ? "info" : "warning"}>
                  {pending.status === "pending"
                    ? `Payment started for ${pending.package_name} (reference ${pending.payment_reference || "—"}). Complete it with the payment provider; credits appear here once the provider confirms.`
                    : pending.status === "credited"
                      ? `${pending.sms_quantity.toLocaleString()} SMS credits added from ${pending.package_name}.`
                      : `Purchase ${pending.status}: ${pending.failure_reason || "contact support if you were charged."}`}
                </Notice>
              ) : undefined
            }
          />
        )
        : <SmsTemplatesView load={asLoad(templates)} caps={caps} onAdd={() => setComposing(true)} />;
  } else {
    body = tab === "intents"
      ? <PaymentIntentsView load={asLoad(intents)} providerName={providerName} branches={branches} onRefresh={() => void intents.reload()} />
      : <PaymentTransactionsView load={asLoad(intents)} providerName={providerName} branches={branches} />;
  }

  return (
    <PageLayout
      title="Integrations"
      description="SMS templates, message delivery and payment status. Providers are configured by the platform administrator."
      breadcrumbs={["Settings", "Integrations"]}
      backTo={scoped("/settings")}
      backLabel="Settings"
    >
      {caps.any && <TabNav tabs={sections} active={section} onChange={(id) => go(id as Section)} />}
      {caps.any && section !== "overview" && tabs.length > 0 && (
        <TabNav tabs={tabs} active={tab ?? ""} onChange={(id) => { setComposing(false); setParams({ section, tab: id }); }} className="bg-transparent" />
      )}
      {body}
    </PageLayout>
  );
}

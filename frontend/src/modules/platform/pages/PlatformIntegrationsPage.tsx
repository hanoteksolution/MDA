import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { Button } from "@/components/ui/button";
import { appDialog } from "@/components/feedback/AppDialog";
import { platformApi, type PlatformTenantRow } from "@/services/api/platform";
import { platformIntegrationsApi, platformSmsBillingApi } from "@/services/api/integrations";
import type { SmsPackage, SmsPackageInput } from "@/services/api/integrations";
import { LedgerTable, PurchasesTable, BalanceCards, SmsAdjustmentForm, SmsBalancesView, SmsPackageFormView, SmsPackagesAdminView } from "@/modules/settings/integrations/components/smsBilling";
import { DataState } from "@/modules/settings/integrations/components/primitives";
import type {
  PaymentProvider,
  PaymentProviderInput,
  ReconciliationRecord,
  SmsProvider,
  SmsProviderInput,
} from "@/services/api/integrations";
import { commitCredential, CredentialDraftError } from "@/modules/settings/integrations/credentialFlow";
import type { CredentialDraft } from "@/modules/settings/integrations/credentialFlow";
import { describeApiError, platformIntegrationCaps, shortId, summarize } from "@/modules/settings/integrations/lib";
import { useLoad } from "@/modules/settings/integrations/useLoad";
import { asLoad } from "@/modules/settings/integrations/IntegrationsPage";
import { Panel } from "@/modules/settings/integrations/components/primitives";
import { PaymentProviderFormView, SmsProviderFormView } from "@/modules/settings/integrations/components/forms";
import type { SaveResult } from "@/modules/settings/integrations/components/forms";
import {
  OverviewView,
  PaymentProvidersView,
  ReconciliationView,
  SmsProvidersView,
  WebhookEventsView,
} from "@/modules/settings/integrations/components/views";

type Section = "overview" | "sms" | "payments" | "billing";
type Editor = { kind: "sms"; item: SmsProvider | null } | { kind: "payment"; item: PaymentProvider | null } | null;
type Branch = { id: string; name: string };

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "sms", label: "SMS providers" },
  { id: "payments", label: "Payments" },
  { id: "billing", label: "SMS billing" },
];
const BILLING_TABS = [
  { id: "packages", label: "Packages" },
  { id: "balances", label: "Tenant balances" },
  { id: "ledger", label: "Tenant ledger" },
  { id: "provider", label: "Billing provider" },
];
const PAYMENT_TABS = [
  { id: "providers", label: "Providers / merchants" },
  { id: "webhooks", label: "Webhook events" },
  { id: "reconciliation", label: "Reconciliation" },
];

/**
 * Platform Admin → Integrations. SMS and payment provider infrastructure for a selected tenant:
 * providers, write-only credentials, webhook events and reconciliation. Super Admin only — the
 * backend (`/api/v1/platform/integrations/`) refuses every tenant user.
 */
export function PlatformIntegrationsPage() {
  const caps = platformIntegrationCaps();
  const [params, setParams] = useSearchParams();
  const tenantId = params.get("tenant") ?? "";
  const [tenants, setTenants] = useState<PlatformTenantRow[]>([]);
  const [tenantsError, setTenantsError] = useState<string | null>(null);
  const [branchList, setBranchList] = useState<Branch[]>([]);

  useEffect(() => {
    platformApi.tenants().then((r) => setTenants(r.data)).catch((err) => setTenantsError(describeApiError(err, "Could not load tenants.")));
  }, []);
  const api = useMemo(() => platformIntegrationsApi(tenantId), [tenantId]);
  useEffect(() => {
    setBranchList([]);
    if (tenantId) api.branches().then((r) => setBranchList(r.data.map((b) => ({ id: b.id, name: b.name })))).catch(() => setBranchList([]));
  }, [api, tenantId]);
  const requested = params.get("section") as Section | null;
  const section: Section = SECTIONS.some((s) => s.id === requested) ? (requested as Section) : "overview";
  const tabs = section === "payments" ? PAYMENT_TABS : section === "billing" ? BILLING_TABS : [];
  const tab = tabs.some((t) => t.id === params.get("tab")) ? (params.get("tab") as string) : tabs[0]?.id;
  const [editor, setEditor] = useState<Editor>(null);
  const [running, setRunning] = useState(false);
  const [resolving, setResolving] = useState<ReconciliationRecord | null>(null);
  const [resolveNote, setResolveNote] = useState("");
  const [resolveError, setResolveError] = useState<string | null>(null);

  const go = (next: Section, nextTab?: string) => {
    setEditor(null);
    setParams({ ...(tenantId ? { tenant: tenantId } : {}), ...(next === "overview" ? {} : { section: next }), ...(nextTab ? { tab: nextTab } : {}) });
  };
  const selectTenant = (id: string) => {
    setEditor(null);
    setResolving(null);
    setParams(id ? { tenant: id } : {});
  };

  const ready = Boolean(tenantId);
  const deps = [tenantId];
  const credentials = useLoad(() => api.credentials.list(), ready, deps);
  const smsProviders = useLoad(() => api.sms.providers(), ready, deps);
  const payProviders = useLoad(() => api.payments.providers(), ready, deps);
  const events = useLoad(() => api.payments.webhookEvents(), ready, deps);
  const records = useLoad(() => api.payments.reconciliation(), ready, deps);
  const loads = [smsProviders, payProviders, events, records];
  const smsPackages = useLoad(() => platformSmsBillingApi.packages(), section === "billing", [section]);
  const balances = useLoad(() => platformSmsBillingApi.balances(), section === "billing", [section]);
  const tenantLedger = useLoad(() => platformSmsBillingApi.ledger(tenantId).then((r) => ({ data: [r.data] })), ready && section === "billing", [tenantId, section]);
  const billingSettings = useLoad(() => platformSmsBillingApi.settings().then((r) => ({ data: [r.data] })), section === "billing", [section]);
  const [packageEditor, setPackageEditor] = useState<SmsPackage | "new" | null>(null);
  const [billingProvider, setBillingProvider] = useState("");

  const branchOptions = branchList;
  const branches = useMemo(
    () => ({ name: (id: string | null | undefined) => (id ? branchList.find((b) => b.id === id)?.name ?? "Branch" : "—") }),
    [branchList]
  );
  const providerName = useMemo(
    () => (id: string) => payProviders.data.find((p) => p.id === id)?.name ?? shortId(id),
    [payProviders.data]
  );
  const overview = useMemo(
    () => summarize({ smsProviders: smsProviders.data, smsLogs: [], paymentProviders: payProviders.data, intents: [], events: events.data, records: records.data }),
    [smsProviders.data, payProviders.data, events.data, records.data]
  );

  /** Sends any typed secret exactly once, then reports what to link. Never echoes a secret. */
  async function commitDrafts(
    drafts: { key: "api" | "webhook"; selectedId: string; draft: CredentialDraft }[],
    created: Record<string, string>
  ): Promise<Record<string, string | null>> {
    const ids: Record<string, string | null> = {};
    for (const { key, selectedId, draft } of drafts) {
      const id = await commitCredential(selectedId, draft, api.credentials);
      ids[key] = id;
      if (draft.mode === "new" && id) created[key] = id;
    }
    if (Object.keys(created).length) void credentials.reload();
    return ids;
  }

  const failed = (err: unknown, created: Record<string, string>): SaveResult => ({
    error: err instanceof CredentialDraftError ? err.message : describeApiError(err, "Could not save the provider."),
    createdCredentialIds: created,
  });

  const saveSms = (item: SmsProvider | null) => async (input: SmsProviderInput, draft: CredentialDraft): Promise<SaveResult> => {
    const created: Record<string, string> = {};
    try {
      const ids = await commitDrafts([{ key: "api", selectedId: input.credential_id ?? "", draft }], created);
      const payload = { ...input, credential_id: ids.api };
      if (item) await api.sms.updateProvider(item.id, payload);
      else await api.sms.createProvider(payload);
      await smsProviders.reload();
      setEditor(null);
      return {};
    } catch (err) {
      return failed(err, created);
    }
  };

  const savePayment = (item: PaymentProvider | null) =>
    async (input: PaymentProviderInput, apiKey: CredentialDraft, webhook: CredentialDraft): Promise<SaveResult> => {
      const created: Record<string, string> = {};
      try {
        const ids = await commitDrafts(
          [
            { key: "api", selectedId: input.credential_id ?? "", draft: apiKey },
            { key: "webhook", selectedId: input.webhook_credential_id ?? "", draft: webhook },
          ],
          created
        );
        const payload = { ...input, credential_id: ids.api, webhook_credential_id: ids.webhook };
        if (item) await api.payments.updateProvider(item.id, payload);
        else await api.payments.createProvider(payload);
        await payProviders.reload();
        setEditor(null);
        return {};
      } catch (err) {
        return failed(err, created);
      }
    };

  const toggleProvider = async (kind: "sms" | "payment", p: SmsProvider | PaymentProvider) => {
    if (p.is_active) {
      const ok = await appDialog.confirm(
        kind === "sms"
          ? `Disable “${p.name}”? Messages will stop using this provider and may fail if no other provider is active.`
          : `Disable “${p.name}”? New payments cannot start through it; callbacks for existing intents are no longer accepted.`,
        { title: "Disable provider", confirmLabel: "Disable", tone: "danger" }
      );
      if (!ok) return;
    }
    try {
      if (kind === "sms") await api.sms.updateProvider(p.id, { is_active: !p.is_active });
      else await api.payments.updateProvider(p.id, { is_active: !p.is_active });
      await (kind === "sms" ? smsProviders : payProviders).reload();
    } catch (err) {
      await appDialog.alert(describeApiError(err, "Could not update the provider."), { tone: "danger" });
    }
  };

  const runReconciliation = async () => {
    const ok = await appDialog.confirm(
      "Compare provider records with this tenant's ledger now? This only reports differences — it never changes payments, invoices or journals.",
      { title: "Run reconciliation", confirmLabel: "Run", tone: "default" }
    );
    if (!ok) return;
    setRunning(true);
    try {
      const res = await api.payments.runReconciliation();
      await records.reload();
      await appDialog.alert(`Checked ${res.data.checked} payment(s); ${res.data.mismatches} discrepancy(ies) found.`, { tone: "success", title: "Reconciliation complete" });
    } catch (err) {
      await appDialog.alert(describeApiError(err, "Reconciliation failed."), { tone: "danger" });
    } finally {
      setRunning(false);
    }
  };

  const submitResolve = async () => {
    if (!resolving) return;
    if (!resolveNote.trim()) {
      setResolveError("A resolution note is required.");
      return;
    }
    const ok = await appDialog.confirm(
      "Mark this discrepancy as resolved? It only closes the record — any refund or correction must already have been made.",
      { title: "Resolve discrepancy", confirmLabel: "Mark resolved", tone: "default" }
    );
    if (!ok) return;
    try {
      await api.payments.resolveReconciliation(resolving.id, resolveNote.trim());
      setResolving(null);
      setResolveNote("");
      setResolveError(null);
      await records.reload();
    } catch (err) {
      setResolveError(describeApiError(err, "Could not resolve the record."));
    }
  };

  const savePackage = async (input: Partial<SmsPackageInput>) => {
    try {
      if (packageEditor && packageEditor !== "new") await platformSmsBillingApi.updatePackage(packageEditor.id, input);
      else await platformSmsBillingApi.createPackage(input);
      setPackageEditor(null);
      await smsPackages.reload();
      return null;
    } catch (err) {
      return describeApiError(err, "Could not save the package.");
    }
  };
  const togglePackage = async (p: SmsPackage) => {
    if (p.is_active && !(await appDialog.confirm(`Deactivate “${p.name}”? Tenants can no longer buy it; credits already bought are unaffected.`, { title: "Deactivate package", confirmLabel: "Deactivate", tone: "danger" }))) return;
    try {
      await platformSmsBillingApi.updatePackage(p.id, { is_active: !p.is_active });
      await smsPackages.reload();
    } catch (err) {
      await appDialog.alert(describeApiError(err, "Could not update the package."), { tone: "danger" });
    }
  };
  const adjust = async (input: { units: number; reason: string; expires_at?: string }) => {
    if (!(await appDialog.confirm(`${input.units > 0 ? "Add" : "Remove"} ${Math.abs(input.units)} SMS credits? This is recorded in the audit log.`, { title: "Manual adjustment", confirmLabel: "Record", tone: "default" }))) return "Cancelled.";
    try {
      await platformSmsBillingApi.adjust(tenantId, input);
      await Promise.all([tenantLedger.reload(), balances.reload()]);
      return null;
    } catch (err) {
      return describeApiError(err, "Could not record the adjustment.");
    }
  };
  const saveBillingProvider = async () => {
    try {
      await platformSmsBillingApi.saveSettings(billingProvider || null);
      await billingSettings.reload();
      await appDialog.alert("SMS package payments will be collected through this provider.", { tone: "success", title: "Billing provider saved" });
    } catch (err) {
      await appDialog.alert(describeApiError(err, "Could not save the billing provider."), { tone: "danger" });
    }
  };
  const needsTenant = section !== "billing" || tab === "ledger" || tab === "provider";

  let body;
  if (section === "billing" && tab === "packages") {
    body = packageEditor
      ? <SmsPackageFormView initial={packageEditor === "new" ? null : packageEditor} onSave={savePackage} onCancel={() => setPackageEditor(null)} />
      : <SmsPackagesAdminView load={asLoad(smsPackages)} onAdd={() => setPackageEditor("new")} onEdit={(p) => setPackageEditor(p)} onToggle={(p) => void togglePackage(p)} />;
  } else if (section === "billing" && tab === "balances") {
    body = <SmsBalancesView load={asLoad(balances)} onOpen={(id) => setParams({ tenant: id, section: "billing", tab: "ledger" })} />;
  } else if (needsTenant && !ready) {
    body = (
      <Panel title="Select a tenant" description="Providers and credentials are configured per tenant.">
        <p className="p-6 text-sm text-muted-foreground">{tenantsError ?? "Choose the tenant whose SMS and payment providers you want to manage."}</p>
      </Panel>
    );
  } else if (section === "overview") {
    body = <OverviewView caps={caps} summary={overview} loading={loads.some((l) => l.loading)} error={loads.find((l) => l.error)?.error ?? null} onRetry={() => void Promise.all(loads.map((l) => l.reload()))} onOpen={go} />;
  } else if (section === "billing" && tab === "ledger") {
    const detail = tenantLedger.data[0];
    body = (
      <div className="space-y-4">
        <DataState loading={tenantLedger.loading} error={tenantLedger.error} onRetry={() => void tenantLedger.reload()} isEmpty={!detail} empty={{ title: "No SMS activity" }}>
          {detail && <BalanceCards summary={detail.summary} />}
        </DataState>
        <SmsAdjustmentForm onSubmit={adjust} />
        {detail && (
          <>
            <Panel title="Purchases"><PurchasesTable rows={detail.purchases} /></Panel>
            <Panel title="Credit ledger" description="Immutable; corrections are new entries."><LedgerTable rows={detail.entries} /></Panel>
          </>
        )}
      </div>
    );
  } else if (section === "billing") {
    const current = billingSettings.data[0];
    body = (
      <Panel title="SMS billing provider" description="Tenants pay for SMS packages through this Safari Technology payment provider. Choose one of the selected tenant's (Safari's house account) payment providers.">
        <div className="space-y-3 p-4 text-sm">
          <p>Current: <strong>{current?.payment_provider_name ?? "Not configured — tenants cannot buy packages"}</strong></p>
          <div className="flex flex-wrap items-center gap-2">
            <select aria-label="Billing provider" className="h-9 min-w-[240px] rounded-lg border border-input bg-background px-3" value={billingProvider} onChange={(e) => setBillingProvider(e.target.value)}>
              <option value="">None (disable package payments)</option>
              {payProviders.data.filter((p) => p.is_active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <Button onClick={() => void saveBillingProvider()}>Save</Button>
          </div>
        </div>
      </Panel>
    );
  } else if (section === "sms" && editor?.kind === "sms") {
    body = <SmsProviderFormView initial={editor.item} credentials={credentials.data} branches={branchOptions} canManageCredentials onSave={saveSms(editor.item)} onCancel={() => setEditor(null)} />;
  } else if (section === "sms") {
    body = <SmsProvidersView load={asLoad(smsProviders)} credentials={credentials.data} branches={branches} caps={caps} onAdd={() => setEditor({ kind: "sms", item: null })} onEdit={(p) => setEditor({ kind: "sms", item: p })} onToggle={(p) => void toggleProvider("sms", p)} />;
  } else if (editor?.kind === "payment") {
    body = <PaymentProviderFormView initial={editor.item} credentials={credentials.data} branches={branchOptions} canManageCredentials onSave={savePayment(editor.item)} onCancel={() => setEditor(null)} />;
  } else if (tab === "webhooks") {
    body = <WebhookEventsView load={asLoad(events)} providerName={providerName} />;
  } else if (tab === "reconciliation") {
    body = (
      <div className="space-y-4">
        <ReconciliationView load={asLoad(records)} caps={caps} running={running} providerName={providerName} branches={branches} onRun={() => void runReconciliation()} onResolve={(r) => { setResolving(r); setResolveNote(""); setResolveError(null); }} />
        {resolving && (
          <Panel title="Resolve discrepancy" description={`Intent ${shortId(resolving.intent_id)} — describe what was done outside this screen (refund, journal fix…).`}>
            <div className="space-y-3 p-4">
              <textarea aria-label="Resolution note" rows={3} maxLength={300} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" value={resolveNote} onChange={(e) => setResolveNote(e.target.value)} />
              {resolveError && <p role="alert" className="text-sm text-destructive">{resolveError}</p>}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setResolving(null)}>Cancel</Button>
                <Button onClick={() => void submitResolve()}>Mark resolved</Button>
              </div>
            </div>
          </Panel>
        )}
      </div>
    );
  } else {
    body = <PaymentProvidersView load={asLoad(payProviders)} credentials={credentials.data} branches={branches} caps={caps} onAdd={() => setEditor({ kind: "payment", item: null })} onEdit={(p) => setEditor({ kind: "payment", item: p })} onToggle={(p) => void toggleProvider("payment", p)} />;
  }

  return (
    <PageLayout
      title="Integrations"
      description="Platform infrastructure: SMS gateways, payment providers, write-only credentials, webhooks and reconciliation per tenant."
      breadcrumbs={["Platform", "Integrations"]}
      actions={
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Tenant</span>
          <select
            aria-label="Tenant"
            className="h-9 min-w-[220px] rounded-lg border border-input bg-background px-3 text-sm"
            value={tenantId}
            onChange={(e) => selectTenant(e.target.value)}
          >
            <option value="">Select a tenant…</option>
            {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>
      }
    >
      <TabNav tabs={SECTIONS} active={section} onChange={(id) => go(id as Section)} />
      {tabs.length > 0 && (
        <TabNav tabs={tabs} active={tab ?? ""} onChange={(id) => go(section, id)} className="bg-transparent" />
      )}
      {body}
    </PageLayout>
  );
}

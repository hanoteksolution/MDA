/**
 * Presentational views for the Integrations tabs. Every view is a pure function of its props
 * (data, loading, error, capabilities) — the page container owns fetching and mutations.
 *
 * Security notes that shape this file:
 *  - Credentials appear only as `describeCredential` output (label + masked tail).
 *  - Provider `config` is never rendered in list views; the edit forms load it through
 *    `redactConfig`, so a literal secret that slipped into a config is masked.
 *  - Payment status is displayed exactly as the backend reports it. There is no "mark paid",
 *    "confirm" or "retry" control for payments anywhere in the UI.
 */
import type { ReactNode } from "react";
import { CheckCircle2, CreditCard, MessageSquare, Pencil, Plus, Power, ShieldCheck, Webhook } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import {
  activeView,
  credentialLabelFor,
  extractPlaceholders,
  formatMoney,
  intentStatusView,
  reconciliationKindLabel,
  settledTransactions,
  shortId,
  smsStatusView,
  webhookStatusView,
} from "../lib";
import type { IntegrationCaps, OverviewSummary } from "../lib";
import { DataState, ListTable, Notice, Panel, StatusBadge } from "./primitives";

export interface Load<T> {
  data: T[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}

export interface BranchLookup {
  name: (id: string | null | undefined) => string;
}

const dateTime = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString() : "—");
const scopeLabel = (branches: BranchLookup, id: string | null) => (id ? branches.name(id) : "All branches");

// ─── overview ───────────────────────────────────────────────────────────────────

export function StatCard({ icon, label, value, hint, tone }: { icon: ReactNode; label: string; value: ReactNode; hint?: string; tone?: "warn" }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">{icon}</span>
        {label}
      </div>
      <div className={tone === "warn" ? "mt-3 text-2xl font-semibold text-warning" : "mt-3 text-2xl font-semibold text-foreground"}>
        {value}
      </div>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function OverviewView({
  caps,
  summary,
  loading,
  error,
  onRetry,
  onOpen,
}: {
  caps: IntegrationCaps;
  summary: OverviewSummary | null;
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  onOpen: (section: "sms" | "payments", tab: string) => void;
}) {
  return (
    <div className="space-y-4">
      <Notice>
        {caps.providers
          ? "Provider secrets are encrypted on the server and never shown again after saving. Payments are settled only by the backend after a verified provider callback."
          : "SMS and payment providers are configured by the platform administrator. Payments are settled only by the backend after a verified provider callback — this screen is read-only for payment status."}
      </Notice>
      <DataState
        loading={loading}
        error={error}
        onRetry={onRetry}
        isEmpty={!summary}
        empty={{ title: "Nothing to summarise yet" }}
      >
        {summary && (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {caps.sms && caps.providers && (
              <StatCard icon={<MessageSquare className="h-4 w-4" />} label="SMS providers" value={`${summary.smsActive}/${summary.smsProviders}`} hint={summary.smsDefaultSet ? "Default provider set" : "No active default provider"} />
            )}
            {caps.sms && caps.operations && caps.view && (
              <StatCard icon={<MessageSquare className="h-4 w-4" />} label="SMS needing attention" value={summary.smsFailed + summary.smsRetrying} hint={`${summary.smsFailed} failed · ${summary.smsRetrying} retrying`} tone={summary.smsFailed + summary.smsRetrying > 0 ? "warn" : undefined} />
            )}
            {caps.payments && caps.providers && (
              <StatCard icon={<CreditCard className="h-4 w-4" />} label="Payment providers" value={`${summary.paymentsActive}/${summary.paymentProviders}`} hint="Enabled / configured" />
            )}
            {caps.paymentsView && caps.operations && (
              <StatCard icon={<CreditCard className="h-4 w-4" />} label="Payments in progress" value={summary.intentsPending} hint="Intents awaiting the provider" />
            )}
            {caps.paymentsView && caps.providers && (
              <>
                <StatCard icon={<Webhook className="h-4 w-4" />} label="Webhook problems" value={summary.webhookProblems} hint="Rejected, invalid or errored" tone={summary.webhookProblems > 0 ? "warn" : undefined} />
                <StatCard icon={<ShieldCheck className="h-4 w-4" />} label="Open reconciliation" value={summary.openReconciliation} hint="Unresolved discrepancies" tone={summary.openReconciliation > 0 ? "warn" : undefined} />
              </>
            )}
          </div>
        )}
      </DataState>
      <div className="grid gap-4 md:grid-cols-2">
        {caps.sms && (
          <Panel title="SMS" description={caps.providers ? "Gateways and their credentials." : "Message templates and delivery logs."}>
            <div className="flex flex-wrap gap-2 p-4">
              {caps.providers && <Button variant="outline" size="sm" onClick={() => onOpen("sms", "providers")}>Providers</Button>}
              {caps.operations && caps.view && (
                <>
                  <Button variant="outline" size="sm" onClick={() => onOpen("sms", "templates")}>Templates</Button>
                  <Button variant="outline" size="sm" onClick={() => onOpen("sms", "logs")}>Message logs</Button>
                </>
              )}
            </div>
          </Panel>
        )}
        {caps.payments && (
          <Panel title="Payments" description={caps.providers ? "Merchants, webhooks and reconciliation." : "Payment transactions and intents."}>
            <div className="flex flex-wrap gap-2 p-4">
              {caps.providers ? (
                <>
                  <Button variant="outline" size="sm" onClick={() => onOpen("payments", "providers")}>Providers</Button>
                  <Button variant="outline" size="sm" onClick={() => onOpen("payments", "webhooks")}>Webhooks</Button>
                  <Button variant="outline" size="sm" onClick={() => onOpen("payments", "reconciliation")}>Reconciliation</Button>
                </>
              ) : (
                <>
                  <Button variant="outline" size="sm" onClick={() => onOpen("payments", "transactions")}>Transactions</Button>
                  <Button variant="outline" size="sm" onClick={() => onOpen("payments", "intents")}>Intents</Button>
                </>
              )}
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}

// ─── SMS ────────────────────────────────────────────────────────────────────────

export function SmsProvidersView({
  load,
  credentials,
  branches,
  caps,
  onAdd,
  onEdit,
  onToggle,
}: {
  load: Load<SmsProvider>;
  credentials: IntegrationCredential[];
  branches: BranchLookup;
  caps: IntegrationCaps;
  onAdd: () => void;
  onEdit: (p: SmsProvider) => void;
  onToggle: (p: SmsProvider) => void;
}) {
  return (
    <Panel
      title="SMS providers"
      description="A branch-specific provider overrides the tenant-wide default for that branch."
      actions={caps.manage && <Button size="sm" onClick={onAdd}><Plus className="mr-1.5 h-3.5 w-3.5" />Add provider</Button>}
    >
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{
          title: "No SMS provider configured",
          description: "Messages cannot be delivered until an active provider exists.",
          action: caps.manage ? <Button size="sm" onClick={onAdd}>Add provider</Button> : undefined,
        }}
      >
        <ListTable
          rows={load.data}
          rowKey={(p) => p.id}
          searchPlaceholder="Search providers…"
          searchText={(p) => [p.name, p.provider_type, p.sender_id]}
          columns={[
            { key: "name", header: "Provider", cell: (p) => (
              <div>
                <div className="font-medium text-foreground">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.provider_type === "MOCK" ? "Mock (testing)" : "Custom HTTP"}</div>
              </div>
            ) },
            { key: "scope", header: "Scope", cell: (p) => scopeLabel(branches, p.branch_id) },
            { key: "sender", header: "Sender ID", cell: (p) => p.sender_id || "—" },
            { key: "cred", header: "Credential", cell: (p) => (
              <span className="text-xs text-muted-foreground">{credentialLabelFor(credentials, p.credential_id)}</span>
            ) },
            { key: "state", header: "Status", cell: (p) => (
              <div className="flex flex-wrap gap-1.5">
                <StatusBadge view={activeView(p.is_active)} />
                {p.is_default && <StatusBadge view={{ label: "Default", variant: "default" }} />}
              </div>
            ) },
            { key: "actions", header: "", className: "text-right", cell: (p) =>
              caps.manage ? (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" aria-label={`Edit ${p.name}`} onClick={() => onEdit(p)}><Pencil className="h-3.5 w-3.5" /></Button>
                  <Button variant="ghost" size="sm" aria-label={`${p.is_active ? "Disable" : "Enable"} ${p.name}`} onClick={() => onToggle(p)}><Power className="h-3.5 w-3.5" /></Button>
                </div>
              ) : null },
          ]}
        />
      </DataState>
    </Panel>
  );
}

export function SmsTemplatesView({ load, caps, onAdd }: { load: Load<SmsTemplate>; caps: IntegrationCaps; onAdd: () => void }) {
  return (
    <Panel
      title="Message templates"
      description="Use {name} placeholders. Sending fails loudly if a placeholder has no value."
      actions={caps.manage && <Button size="sm" onClick={onAdd}><Plus className="mr-1.5 h-3.5 w-3.5" />Add template</Button>}
    >
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{ title: "No templates yet", description: "Templates let business events send consistent messages.", action: caps.manage ? <Button size="sm" onClick={onAdd}>Add template</Button> : undefined }}
      >
        <ListTable
          rows={load.data}
          rowKey={(t) => t.id}
          searchPlaceholder="Search templates…"
          searchText={(t) => [t.code, t.name, t.body]}
          columns={[
            { key: "code", header: "Code", cell: (t) => <code className="text-xs">{t.code}</code> },
            { key: "name", header: "Name", cell: (t) => t.name },
            { key: "body", header: "Body", cell: (t) => (
              <div className="max-w-md">
                <p className="truncate text-sm">{t.body}</p>
                <p className="text-xs text-muted-foreground">
                  {extractPlaceholders(t.body).map((p) => `{${p}}`).join(" ") || "no placeholders"}
                </p>
              </div>
            ) },
            { key: "state", header: "Status", cell: (t) => <StatusBadge view={activeView(t.is_active)} /> },
          ]}
        />
      </DataState>
    </Panel>
  );
}

const SMS_STATUS_OPTIONS = ["QUEUED", "RETRYING", "SENT", "FAILED"].map((v) => ({ value: v, label: smsStatusView(v).label }));

export function SmsLogsView({ load, branches }: { load: Load<SmsLog>; branches: BranchLookup }) {
  return (
    <Panel title="Message logs" description="Every attempt is recorded. Failures show a sanitised reason — never credentials.">
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{ title: "No messages yet", description: "Sent and queued messages will appear here." }}
      >
        <ListTable
          rows={load.data}
          rowKey={(l) => l.id}
          searchPlaceholder="Search number, message, reference…"
          searchText={(l) => [l.to, l.body, l.provider_reference, l.error]}
          statusOptions={SMS_STATUS_OPTIONS}
          statusOf={(l) => l.status}
          columns={[
            { key: "when", header: "Created", cell: (l) => <span className="whitespace-nowrap text-xs">{dateTime(l.created_at)}</span> },
            { key: "to", header: "To", cell: (l) => l.to },
            { key: "branch", header: "Branch", cell: (l) => scopeLabel(branches, l.branch_id) },
            { key: "body", header: "Message", cell: (l) => <span className="line-clamp-2 max-w-xs text-sm">{l.body}</span> },
            { key: "status", header: "Status", cell: (l) => (
              <div className="space-y-1">
                <StatusBadge view={smsStatusView(l.status)} />
                {l.error && <p className="max-w-[16rem] text-xs text-destructive">{l.error}</p>}
                {l.status === "RETRYING" && l.next_retry_at && (
                  <p className="text-xs text-muted-foreground">Next attempt {dateTime(l.next_retry_at)}</p>
                )}
              </div>
            ) },
            { key: "attempts", header: "Attempts", cell: (l) => l.attempts },
            { key: "ref", header: "Provider ref", cell: (l) => <span className="text-xs">{l.provider_reference || "—"}</span> },
          ]}
        />
      </DataState>
    </Panel>
  );
}

// ─── payments ───────────────────────────────────────────────────────────────────

export function PaymentProvidersView({
  load,
  credentials,
  branches,
  caps,
  onAdd,
  onEdit,
  onToggle,
}: {
  load: Load<PaymentProvider>;
  credentials: IntegrationCredential[];
  branches: BranchLookup;
  caps: IntegrationCaps;
  onAdd: () => void;
  onEdit: (p: PaymentProvider) => void;
  onToggle: (p: PaymentProvider) => void;
}) {
  return (
    <Panel
      title="Payment providers / merchants"
      description="Each provider has its own webhook address and a separate signing secret."
      actions={caps.manage && <Button size="sm" onClick={onAdd}><Plus className="mr-1.5 h-3.5 w-3.5" />Add provider</Button>}
    >
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{ title: "No payment provider configured", description: "Invoices cannot be paid through a provider until one is enabled.", action: caps.manage ? <Button size="sm" onClick={onAdd}>Add provider</Button> : undefined }}
      >
        <ListTable
          rows={load.data}
          rowKey={(p) => p.id}
          searchPlaceholder="Search providers…"
          searchText={(p) => [p.name, p.provider_type]}
          columns={[
            { key: "name", header: "Provider", cell: (p) => (
              <div>
                <div className="font-medium text-foreground">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.provider_type === "MOCK" ? "Mock (testing)" : p.provider_type}</div>
              </div>
            ) },
            { key: "scope", header: "Scope", cell: (p) => scopeLabel(branches, p.branch_id) },
            { key: "cred", header: "API credential", cell: (p) => <span className="text-xs text-muted-foreground">{credentialLabelFor(credentials, p.credential_id)}</span> },
            { key: "wh", header: "Webhook signing secret", cell: (p) => <span className="text-xs text-muted-foreground">{credentialLabelFor(credentials, p.webhook_credential_id)}</span> },
            { key: "path", header: "Webhook path", cell: (p) => <code className="break-all text-xs">{p.webhook_path}</code> },
            { key: "state", header: "Status", cell: (p) => <StatusBadge view={activeView(p.is_active)} /> },
            { key: "actions", header: "", className: "text-right", cell: (p) =>
              caps.manage ? (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" aria-label={`Edit ${p.name}`} onClick={() => onEdit(p)}><Pencil className="h-3.5 w-3.5" /></Button>
                  <Button variant="ghost" size="sm" aria-label={`${p.is_active ? "Disable" : "Enable"} ${p.name}`} onClick={() => onToggle(p)}><Power className="h-3.5 w-3.5" /></Button>
                </div>
              ) : null },
          ]}
        />
      </DataState>
    </Panel>
  );
}

const INTENT_STATUS_OPTIONS = ["created", "pending", "succeeded", "failed", "expired"].map((v) => ({ value: v, label: intentStatusView(v).label }));

const BackendVerifiedNote = () => (
  <Notice>
    Status is reported by the backend. A payment becomes “Succeeded” only after a signed provider callback (or a
    provider status check) has been verified server-side — never from this page or the browser.
  </Notice>
);

function intentColumns(providerName: (id: string) => string, branches: BranchLookup) {
  return [
    { key: "when", header: "Created", cell: (i: PaymentIntent) => <span className="whitespace-nowrap text-xs">{dateTime(i.created_at)}</span> },
    { key: "id", header: "Intent", cell: (i: PaymentIntent) => <code className="text-xs">{shortId(i.id)}</code> },
    { key: "invoice", header: "Invoice", cell: (i: PaymentIntent) => <code className="text-xs">{shortId(i.invoice_id)}</code> },
    { key: "branch", header: "Branch", cell: (i: PaymentIntent) => branches.name(i.branch_id) },
    { key: "provider", header: "Provider", cell: (i: PaymentIntent) => providerName(i.provider_id) },
    { key: "amount", header: "Amount", className: "text-right", cell: (i: PaymentIntent) => formatMoney(i.amount, i.currency) },
    { key: "ref", header: "Provider ref", cell: (i: PaymentIntent) => <span className="text-xs">{i.provider_reference || "—"}</span> },
  ];
}

export function PaymentIntentsView({
  load,
  providerName,
  branches,
  onRefresh,
}: {
  load: Load<PaymentIntent>;
  providerName: (id: string) => string;
  branches: BranchLookup;
  onRefresh?: () => void;
}) {
  return (
    <Panel
      title="Payment intents"
      description="Attempts to collect money for an invoice. Read-only."
      actions={onRefresh && <Button variant="outline" size="sm" onClick={onRefresh}>Refresh</Button>}
    >
      <div className="p-4 pb-0"><BackendVerifiedNote /></div>
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{ title: "No payment intents", description: "Intents are created when a payment is started on an invoice." }}
      >
        <ListTable
          rows={load.data}
          rowKey={(i) => i.id}
          searchPlaceholder="Search reference, invoice or intent id…"
          searchText={(i) => [i.id, i.invoice_id, i.provider_reference, i.idempotency_key]}
          statusOptions={INTENT_STATUS_OPTIONS}
          statusOf={(i) => i.status}
          columns={[
            ...intentColumns(providerName, branches),
            { key: "status", header: "Status (backend)", cell: (i) => (
              <div className="space-y-1">
                <StatusBadge view={intentStatusView(i.status)} />
                {i.failure_reason && <p className="max-w-[16rem] text-xs text-destructive">{i.failure_reason}</p>}
                {i.status === "pending" && i.expires_at && <p className="text-xs text-muted-foreground">Expires {dateTime(i.expires_at)}</p>}
              </div>
            ) },
          ]}
        />
      </DataState>
    </Panel>
  );
}

export function PaymentTransactionsView({
  load,
  providerName,
  branches,
}: {
  load: Load<PaymentIntent>;
  providerName: (id: string) => string;
  branches: BranchLookup;
}) {
  const settled = settledTransactions(load.data);
  return (
    <Panel title="Transactions" description="Payments the backend has settled against an invoice.">
      <div className="p-4 pb-0">
        <Notice>
          There is no separate transactions endpoint yet: this list is the payment intents the backend has already
          settled into a payment record.
        </Notice>
      </div>
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={settled.length === 0}
        empty={{ title: "No settled transactions", description: "Settled payments will appear here after provider confirmation." }}
      >
        <ListTable
          rows={settled}
          rowKey={(i) => i.id}
          searchPlaceholder="Search reference or invoice…"
          searchText={(i) => [i.id, i.invoice_id, i.provider_reference]}
          columns={[
            { key: "settled", header: "Settled", cell: (i) => <span className="whitespace-nowrap text-xs">{dateTime(i.settled_at)}</span> },
            { key: "invoice", header: "Invoice", cell: (i) => <code className="text-xs">{shortId(i.invoice_id)}</code> },
            { key: "branch", header: "Branch", cell: (i) => branches.name(i.branch_id) },
            { key: "provider", header: "Provider", cell: (i) => providerName(i.provider_id) },
            { key: "method", header: "Method", cell: (i) => i.method },
            { key: "amount", header: "Amount", className: "text-right", cell: (i) => formatMoney(i.amount, i.currency) },
            { key: "ref", header: "Provider ref", cell: (i) => <span className="text-xs">{i.provider_reference || "—"}</span> },
            { key: "status", header: "Status (backend)", cell: (i) => <StatusBadge view={intentStatusView(i.status)} /> },
          ]}
        />
      </DataState>
    </Panel>
  );
}

const WEBHOOK_STATUS_OPTIONS = ["received", "processed", "ignored", "rejected", "invalid", "error"].map((v) => ({ value: v, label: webhookStatusView(v).label }));

export function WebhookEventsView({ load, providerName }: { load: Load<PaymentWebhookEvent>; providerName: (id: string) => string }) {
  return (
    <Panel title="Webhook events" description="Every inbound callback. Bodies and signatures are never shown.">
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{ title: "No webhook events yet", description: "Provider callbacks will be listed here as they arrive." }}
      >
        <ListTable
          rows={load.data}
          rowKey={(e) => e.id}
          searchPlaceholder="Search event id or reason…"
          searchText={(e) => [e.event_id, e.reason, e.intent_id]}
          statusOptions={WEBHOOK_STATUS_OPTIONS}
          statusOf={(e) => e.status}
          columns={[
            { key: "when", header: "Received", cell: (e) => <span className="whitespace-nowrap text-xs">{dateTime(e.received_at)}</span> },
            { key: "provider", header: "Provider", cell: (e) => providerName(e.provider_id) },
            { key: "event", header: "Event id", cell: (e) => <span className="text-xs">{e.event_id || "—"}</span> },
            { key: "sig", header: "Signature", cell: (e) => (
              <StatusBadge view={e.signature_valid ? { label: "Verified", variant: "success" } : { label: "Not verified", variant: "destructive" }} />
            ) },
            { key: "status", header: "Status", cell: (e) => (
              <div className="space-y-1">
                <StatusBadge view={webhookStatusView(e.status)} />
                {e.reason && <p className="max-w-[16rem] text-xs text-muted-foreground">{e.reason}</p>}
              </div>
            ) },
            { key: "intent", header: "Intent", cell: (e) => <code className="text-xs">{shortId(e.intent_id)}</code> },
          ]}
        />
      </DataState>
    </Panel>
  );
}

export function ReconciliationView({
  load,
  caps,
  running,
  providerName,
  branches,
  onRun,
  onResolve,
}: {
  load: Load<ReconciliationRecord>;
  caps: IntegrationCaps;
  running: boolean;
  providerName: (id: string) => string;
  branches: BranchLookup;
  onRun: () => void;
  onResolve: (r: ReconciliationRecord) => void;
}) {
  return (
    <Panel
      title="Reconciliation"
      description="Differences between what the provider reports and what the ledger holds. Nothing is corrected automatically."
      actions={caps.reconcile && <Button size="sm" loading={running} onClick={onRun}><CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />Run reconciliation</Button>}
    >
      <DataState
        loading={load.loading}
        error={load.error}
        onRetry={load.onRetry}
        isEmpty={load.data.length === 0}
        empty={{ title: "No discrepancies", description: "Run reconciliation to compare provider records with the ledger." }}
      >
        <ListTable
          rows={load.data}
          rowKey={(r) => r.id}
          searchPlaceholder="Search intent or detail…"
          searchText={(r) => [r.intent_id, r.detail, r.kind]}
          statusOptions={[{ value: "open", label: "Open" }, { value: "resolved", label: "Resolved" }]}
          statusOf={(r) => r.status}
          columns={[
            { key: "when", header: "Detected", cell: (r) => <span className="whitespace-nowrap text-xs">{dateTime(r.created_at)}</span> },
            { key: "kind", header: "Issue", cell: (r) => (
              <div>
                <div className="font-medium text-foreground">{reconciliationKindLabel(r.kind)}</div>
                {r.detail && <p className="max-w-xs text-xs text-muted-foreground">{r.detail}</p>}
              </div>
            ) },
            { key: "branch", header: "Branch", cell: (r) => branches.name(r.branch_id) },
            { key: "provider", header: "Provider", cell: (r) => providerName(r.provider_id) },
            { key: "intent", header: "Intent", cell: (r) => <code className="text-xs">{shortId(r.intent_id)}</code> },
            { key: "prov", header: "Provider says", cell: (r) => `${r.provider_status || "—"}${r.provider_amount ? ` · ${r.provider_amount}` : ""}` },
            { key: "ledger", header: "Ledger says", cell: (r) => `${r.ledger_status || "—"}${r.ledger_amount ? ` · ${r.ledger_amount}` : ""}` },
            { key: "state", header: "Status", cell: (r) => (
              <div className="space-y-1">
                <StatusBadge view={r.status === "open" ? { label: "Open", variant: "warning" } : { label: "Resolved", variant: "success" }} />
                {r.resolution_note && <p className="max-w-[14rem] text-xs text-muted-foreground">{r.resolution_note}</p>}
              </div>
            ) },
            { key: "actions", header: "", className: "text-right", cell: (r) =>
              caps.reconcile && r.status === "open" ? (
                <Button variant="outline" size="sm" onClick={() => onResolve(r)}>Resolve</Button>
              ) : null },
          ]}
        />
      </DataState>
    </Panel>
  );
}

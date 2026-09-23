import { useState } from "react";
import type { ReactNode } from "react";
import { Clock, MessageSquare, Plus, ShoppingCart, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SmsBillingSummary, SmsCreditEntry, SmsPackage, SmsPackageInput, SmsPurchase, SmsTenantBalance } from "@/services/api/integrations";
import { activeView, creditKindLabel, formatPrice, purchaseStatusView, validatePackageForm, validityLabel } from "../lib";
import { DataState, ListTable, Notice, Panel, StatusBadge } from "./primitives";
import { StatCard } from "./views";
import type { Load } from "./views";

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");
const signed = (n: number) => (n > 0 ? `+${n}` : String(n));

export function BalanceCards({ summary }: { summary: SmsBillingSummary }) {
  const next = summary.next_expiry[0];
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard icon={<Wallet className="h-4 w-4" />} label="SMS balance" value={summary.balance.toLocaleString()} hint={summary.reserved ? `${summary.reserved} reserved for messages in progress` : "Credits available to send"} tone={summary.balance === 0 ? "warn" : undefined} />
      <StatCard icon={<MessageSquare className="h-4 w-4" />} label="Used (30 days)" value={summary.used_30d.toLocaleString()} hint={`${summary.used_total.toLocaleString()} used in total`} />
      <StatCard icon={<ShoppingCart className="h-4 w-4" />} label="Purchased" value={summary.purchased_total.toLocaleString()} hint="Credits from packages" />
      <StatCard icon={<Clock className="h-4 w-4" />} label="Next expiry" value={next ? next.units.toLocaleString() : "—"} hint={next ? `Expire ${when(next.expires_at)}` : "No expiring credits"} />
    </div>
  );
}

export function LedgerTable({ rows }: { rows: SmsCreditEntry[] }) {
  return (
    <ListTable
      rows={rows}
      rowKey={(e) => e.id}
      searchPlaceholder="Search activity…"
      searchText={(e) => [creditKindLabel(e.kind), e.reason]}
      statusOptions={[
        { value: "purchase", label: "Packages" },
        { value: "reserve", label: "SMS sent" },
        { value: "release", label: "Returned" },
        { value: "adjust_credit", label: "Manual credit" },
        { value: "adjust_debit", label: "Manual debit" },
        { value: "expire", label: "Expired" },
      ]}
      statusOf={(e) => e.kind}
      columns={[
        { key: "when", header: "Date", cell: (e) => when(e.created_at) },
        { key: "kind", header: "Activity", cell: (e) => creditKindLabel(e.kind) },
        { key: "units", header: "Credits", cell: (e) => <span className={e.units < 0 ? "text-destructive" : "text-success"}>{signed(e.units)}</span> },
        { key: "balance", header: "Balance", cell: (e) => e.balance_after.toLocaleString() },
        { key: "reason", header: "Details", cell: (e) => <span className="text-muted-foreground">{e.reason || "—"}{e.expires_at ? ` · expires ${when(e.expires_at)}` : ""}</span> },
      ]}
    />
  );
}

export function PurchasesTable({ rows }: { rows: SmsPurchase[] }) {
  return (
    <ListTable
      rows={rows}
      rowKey={(p) => p.id}
      searchPlaceholder="Search purchases…"
      searchText={(p) => [p.package_name, p.payment_reference]}
      columns={[
        { key: "when", header: "Date", cell: (p) => when(p.created_at) },
        { key: "pkg", header: "Package", cell: (p) => `${p.package_name} · ${p.sms_quantity.toLocaleString()} SMS` },
        { key: "price", header: "Price", cell: (p) => formatPrice(p.price, p.currency) },
        { key: "status", header: "Status", cell: (p) => <StatusBadge view={purchaseStatusView(p.status)} /> },
        { key: "ref", header: "Payment reference", cell: (p) => <code className="text-xs">{p.payment_reference || "—"}</code> },
      ]}
    />
  );
}

/** Tenant: Settings → Integrations → SMS → Packages & billing. No provider data exists here. */
export function SmsBillingView({
  summary,
  packages,
  purchases,
  ledger,
  canPurchase,
  buying,
  onBuy,
  message,
}: {
  summary: { data: SmsBillingSummary | null; loading: boolean; error: string | null; onRetry?: () => void };
  packages: Load<SmsPackage>;
  purchases: Load<SmsPurchase>;
  ledger: Load<SmsCreditEntry>;
  canPurchase: boolean;
  buying: string | null;
  onBuy: (pkg: SmsPackage) => void;
  message?: ReactNode;
}) {
  const payable = summary.data?.payments_available !== false;
  return (
    <div className="space-y-4">
      <Notice>
        SMS credits are sold by Safari Technology. Each message segment uses one credit; messages that fail are returned to your balance.
        Credits are added only after the payment provider confirms your payment.
      </Notice>
      {message}
      <DataState loading={summary.loading} error={summary.error} onRetry={summary.onRetry} isEmpty={!summary.data} empty={{ title: "No balance yet" }}>
        {summary.data && <BalanceCards summary={summary.data} />}
      </DataState>
      <Panel title="SMS packages" description={payable ? "Choose a package to top up your balance." : "Package payments are not available yet. Contact Safari Technology support."}>
        <DataState loading={packages.loading} error={packages.error} onRetry={packages.onRetry} isEmpty={packages.data.length === 0} empty={{ title: "No packages available", description: "Safari Technology has not published SMS packages yet." }}>
          <div className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {packages.data.map((p) => (
              <article key={p.id} className="flex flex-col rounded-2xl border border-border p-4" aria-label={`${p.name} package`}>
                <h4 className="text-sm font-semibold">{p.name}</h4>
                <p className="mt-2 text-2xl font-semibold">{p.sms_quantity.toLocaleString()} <span className="text-sm font-normal text-muted-foreground">SMS</span></p>
                <p className="text-sm">{formatPrice(p.price, p.currency)}</p>
                <p className="mt-1 text-xs text-muted-foreground">{validityLabel(p.validity_days)}</p>
                {p.description && <p className="mt-2 text-xs text-muted-foreground">{p.description}</p>}
                {canPurchase && (
                  <Button className="mt-4" size="sm" disabled={!payable || buying !== null} onClick={() => onBuy(p)}>
                    {buying === p.id ? "Starting payment…" : "Buy package"}
                  </Button>
                )}
              </article>
            ))}
          </div>
        </DataState>
      </Panel>
      <Panel title="Purchase history">
        <DataState loading={purchases.loading} error={purchases.error} onRetry={purchases.onRetry} isEmpty={purchases.data.length === 0} empty={{ title: "No purchases yet" }}>
          <PurchasesTable rows={purchases.data} />
        </DataState>
      </Panel>
      <Panel title="Credit activity" description="Every credit movement, newest first. Entries cannot be edited.">
        <DataState loading={ledger.loading} error={ledger.error} onRetry={ledger.onRetry} isEmpty={ledger.data.length === 0} empty={{ title: "No credit activity yet" }}>
          <LedgerTable rows={ledger.data} />
        </DataState>
      </Panel>
    </div>
  );
}

// ─── platform ──────────────────────────────────────────────────────────────────

export function SmsPackagesAdminView({ load, onAdd, onEdit, onToggle }: { load: Load<SmsPackage>; onAdd: () => void; onEdit: (p: SmsPackage) => void; onToggle: (p: SmsPackage) => void }) {
  return (
    <Panel title="SMS packages" description="Sold to every tenant. Price and quantity are snapshotted on each purchase." actions={<Button size="sm" onClick={onAdd}><Plus className="mr-1.5 h-3.5 w-3.5" />Add package</Button>}>
      <DataState loading={load.loading} error={load.error} onRetry={load.onRetry} isEmpty={load.data.length === 0} empty={{ title: "No packages yet", action: <Button size="sm" onClick={onAdd}>Add package</Button> }}>
        <ListTable
          rows={load.data}
          rowKey={(p) => p.id}
          searchPlaceholder="Search packages…"
          searchText={(p) => [p.name, p.code]}
          columns={[
            { key: "name", header: "Package", cell: (p) => <div><p className="font-medium">{p.name}</p><code className="text-xs text-muted-foreground">{p.code}</code></div> },
            { key: "qty", header: "SMS", cell: (p) => p.sms_quantity.toLocaleString() },
            { key: "price", header: "Price", cell: (p) => formatPrice(p.price, p.currency) },
            { key: "validity", header: "Validity", cell: (p) => validityLabel(p.validity_days) },
            { key: "status", header: "Status", cell: (p) => <StatusBadge view={activeView(p.is_active)} /> },
            { key: "actions", header: "", cell: (p) => (
              <div className="flex justify-end gap-2">
                <Button size="sm" variant="outline" onClick={() => onEdit(p)}>Edit</Button>
                <Button size="sm" variant="outline" onClick={() => onToggle(p)}>{p.is_active ? "Deactivate" : "Activate"}</Button>
              </div>
            ) },
          ]}
        />
      </DataState>
    </Panel>
  );
}

type PackageDraft = { name: string; code: string; sms_quantity: string; price: string; currency: string; validity_days: string; description: string };

export function SmsPackageFormView({ initial, onSave, onCancel }: { initial: SmsPackage | null; onSave: (input: Partial<SmsPackageInput>) => Promise<string | null>; onCancel: () => void }) {
  const [draft, setDraft] = useState<PackageDraft>({
    name: initial?.name ?? "", code: initial?.code ?? "", sms_quantity: initial ? String(initial.sms_quantity) : "",
    price: initial?.price ?? "", currency: initial?.currency ?? "USD", validity_days: initial?.validity_days ? String(initial.validity_days) : "",
    description: initial?.description ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const field = (key: keyof PackageDraft, label: string, props: Record<string, string> = {}) => (
    <label className="space-y-1 text-sm">
      <span className="font-medium">{label}</span>
      <Input aria-label={label} aria-invalid={Boolean(errors[key])} value={draft[key]} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} {...props} />
      {errors[key] && <span role="alert" className="block text-xs text-destructive">{errors[key]}</span>}
    </label>
  );
  const submit = async () => {
    const found = validatePackageForm(draft);
    setErrors(found);
    if (Object.keys(found).length) return;
    setSaving(true);
    setError(await onSave({
      name: draft.name.trim(), code: draft.code.trim(), sms_quantity: Number(draft.sms_quantity), price: draft.price.trim(),
      currency: draft.currency.trim().toUpperCase() || "USD", validity_days: draft.validity_days.trim() ? Number(draft.validity_days) : null,
      description: draft.description.trim(),
    }));
    setSaving(false);
  };
  return (
    <Panel title={initial ? `Edit ${initial.name}` : "New SMS package"} description="Existing purchases keep the quantity and price they were bought with.">
      <form className="grid gap-4 p-4 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
        {field("name", "Name")}
        {field("code", "Code")}
        {field("sms_quantity", "SMS quantity", { inputMode: "numeric" })}
        {field("price", "Selling price", { inputMode: "decimal" })}
        {field("currency", "Currency", { maxLength: "3" })}
        {field("validity_days", "Validity (days, empty = no expiry)", { inputMode: "numeric" })}
        <label className="space-y-1 text-sm md:col-span-2">
          <span className="font-medium">Description</span>
          <textarea aria-label="Description" rows={2} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
        </label>
        {error && <p role="alert" className="text-sm text-destructive md:col-span-2">{error}</p>}
        <div className="flex justify-end gap-2 md:col-span-2">
          <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save package"}</Button>
        </div>
      </form>
    </Panel>
  );
}

export function SmsBalancesView({ load, onOpen }: { load: Load<SmsTenantBalance>; onOpen: (tenantId: string) => void }) {
  return (
    <Panel title="Tenant SMS balances" description="Balances, package purchases and usage across all tenants.">
      <DataState loading={load.loading} error={load.error} onRetry={load.onRetry} isEmpty={load.data.length === 0} empty={{ title: "No tenants" }}>
        <ListTable
          rows={load.data}
          rowKey={(r) => r.tenant_id}
          searchPlaceholder="Search tenants…"
          searchText={(r) => [r.tenant_name]}
          columns={[
            { key: "tenant", header: "Tenant", cell: (r) => r.tenant_name },
            { key: "balance", header: "Balance", cell: (r) => <span className={r.balance === 0 ? "text-warning" : undefined}>{r.balance.toLocaleString()}</span> },
            { key: "purchased", header: "Purchased", cell: (r) => r.purchased.toLocaleString() },
            { key: "used", header: "Used", cell: (r) => r.used.toLocaleString() },
            { key: "flags", header: "Purchases", cell: (r) => `${r.pending_purchases} pending${r.review_purchases ? ` · ${r.review_purchases} to review` : ""}` },
            { key: "open", header: "", cell: (r) => <Button size="sm" variant="outline" onClick={() => onOpen(r.tenant_id)}>Ledger</Button> },
          ]}
        />
      </DataState>
    </Panel>
  );
}

export function SmsAdjustmentForm({ onSubmit }: { onSubmit: (input: { units: number; reason: string; expires_at?: string }) => Promise<string | null> }) {
  const [direction, setDirection] = useState<"credit" | "debit">("credit");
  const [units, setUnits] = useState("");
  const [reason, setReason] = useState("");
  const [expires, setExpires] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    if (!/^\d+$/.test(units) || Number(units) <= 0) return setError("Enter a whole number of credits above zero.");
    if (!reason.trim()) return setError("A reason is required; it is recorded in the audit log.");
    setSaving(true);
    const result = await onSubmit({ units: direction === "credit" ? Number(units) : -Number(units), reason: reason.trim(), ...(direction === "credit" && expires ? { expires_at: expires } : {}) });
    setSaving(false);
    setError(result);
    if (!result) { setUnits(""); setReason(""); setExpires(""); }
  };
  return (
    <Panel title="Manual adjustment" description="Audited. A debit can never take the balance below zero.">
      <form className="grid gap-3 p-4 md:grid-cols-4" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
        <select aria-label="Adjustment type" className="h-10 rounded-lg border border-input bg-background px-3 text-sm" value={direction} onChange={(e) => setDirection(e.target.value as "credit" | "debit")}>
          <option value="credit">Add credits</option>
          <option value="debit">Remove credits</option>
        </select>
        <Input aria-label="Credits" inputMode="numeric" placeholder="Credits" value={units} onChange={(e) => setUnits(e.target.value)} />
        <Input aria-label="Expires (optional)" type="date" disabled={direction === "debit"} value={expires} onChange={(e) => setExpires(e.target.value)} />
        <Input aria-label="Reason" placeholder="Reason (required)" value={reason} onChange={(e) => setReason(e.target.value)} />
        {error && <p role="alert" className="text-sm text-destructive md:col-span-4">{error}</p>}
        <div className="flex justify-end md:col-span-4"><Button type="submit" disabled={saving}>{saving ? "Saving…" : "Record adjustment"}</Button></div>
      </form>
    </Panel>
  );
}

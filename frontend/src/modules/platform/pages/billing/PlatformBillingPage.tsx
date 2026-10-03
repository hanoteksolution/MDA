import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, Building2, CalendarClock, CreditCard, Receipt, Wallet } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { DataTable, type Column } from "@/components/data/DataTable";
import type { FilterConfig } from "@/components/data/FilterBar";
import { KpiCard } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { appDialog } from "@/components/feedback/AppDialog";
import { platformApi } from "@/services/api/platform";
import {
  platformBillingApi,
  type BillingInvoiceRow,
  type BillingOverview,
  type BillingPaymentRow,
  type BillingPlanRow,
  type BillingReconciliationRow,
  type BillingSubscriptionRow,
} from "@/services/api/platformBilling";
import { BillingBadge, ErrorNote, RecoveryDialog, date, humanize, money, option, useBillingTable } from "./billingUi";

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "subscriptions", label: "Subscriptions" },
  { id: "payments", label: "Payments" },
  { id: "invoices", label: "Invoices" },
  { id: "reconciliation", label: "Reconciliation" },
  { id: "plans", label: "Plans" },
] as const;
type Section = (typeof SECTIONS)[number]["id"];

const all = (label: string) => ({ value: "", label });
const tenantLink = (id: string | null, name: string | null) =>
  id ? (
    <Link className="font-medium text-primary hover:underline" to={`/platform/billing/tenants/${id}`}>
      {name ?? "—"}
    </Link>
  ) : (
    <span className="text-muted-foreground">Unassigned</span>
  );

/**
 * Platform Admin → Billing. Subscription billing across all tenants, read from the existing
 * subscription / payment / reconciliation rows. Elevated users only; the API enforces the same.
 */
export function PlatformBillingPage() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("section") as Section | null;
  const section: Section = SECTIONS.some((s) => s.id === requested) ? (requested as Section) : "overview";

  return (
    <PlatformBillingLayout>
      <TabNav tabs={[...SECTIONS]} active={section} onChange={(id) => setParams(id === "overview" ? {} : { section: id })} />
      {section === "overview" && <OverviewSection />}
      {section === "subscriptions" && <SubscriptionsSection />}
      {section === "payments" && <PaymentsSection />}
      {section === "invoices" && <InvoicesSection />}
      {section === "reconciliation" && <ReconciliationSection />}
      {section === "plans" && <PlansSection />}
    </PlatformBillingLayout>
  );
}

function PlatformBillingLayout({ children }: { children: React.ReactNode }) {
  return (
    <PageLayout
      title="Billing"
      description="Subscriptions, payments, invoices and reconciliation for every tenant. Figures come only from recorded billing data."
      breadcrumbs={["Platform", "Billing"]}
    >
      {children}
    </PageLayout>
  );
}

function OverviewSection() {
  const [data, setData] = useState<BillingOverview>();
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setError("");
    platformBillingApi
      .overview()
      .then((r) => setData(r.data))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the billing overview."));
  }, [reload]);
  const loading = !data && !error;
  const n = (v: number | undefined) => (v === undefined ? "—" : String(v));
  const totals = (list: { currency: string; amount: string }[] | undefined) =>
    list && list.length ? list.map((t) => money(t.amount, t.currency)).join(" · ") : "None recorded";
  const s = data?.subscriptions;
  const p = data?.payments;

  return (
    <div className="space-y-6">
      <ErrorNote message={error} onRetry={() => setReload((v) => v + 1)} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard index={0} title="Tenants" value={n(data?.tenants.total)} icon={<Building2 className="h-5 w-5" />} loading={loading}
          trend={data ? `${data.tenants.without_subscription} without subscription · ${data.tenants.demo} demo` : undefined} />
        <KpiCard index={1} title="Active subscriptions" value={n(s?.active)} accent="success" icon={<CreditCard className="h-5 w-5" />} loading={loading}
          trend={s ? `${s.trial} trial · ${s.expired} expired · ${s.suspended} suspended` : undefined} />
        <KpiCard index={2} title="Expiring soon" value={n(s?.expiring_soon)} accent="warning" icon={<CalendarClock className="h-5 w-5" />} loading={loading}
          trend={s ? `${s.overdue} overdue` : undefined} />
        <KpiCard index={3} title="Payments needing attention" value={p ? String(p.pending + p.failed + p.review) : "—"} accent="warning"
          icon={<AlertTriangle className="h-5 w-5" />} loading={loading}
          trend={p ? `${p.pending} pending · ${p.failed} failed · ${p.review} in review` : undefined} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <KpiCard index={4} title="Verified subscription revenue" value={loading ? "—" : totals(data?.revenue.verified)} accent="success"
          icon={<Wallet className="h-5 w-5" />} loading={loading} trend="Paid checkout invoices posted to the ledger" />
        <KpiCard index={5} title="Open reconciliation issues" value={n(data?.reconciliation_open)} accent="info"
          icon={<Receipt className="h-5 w-5" />} loading={loading}
          trend={data ? `Manually confirmed (not posted): ${totals(data.revenue.manual_unposted)}` : undefined} />
      </div>
      <div className="flex flex-wrap gap-2 text-sm">
        <Button asChild size="sm" variant="secondary"><Link to="?section=subscriptions&billing_status=expiring_soon">Review expiring subscriptions</Link></Button>
        <Button asChild size="sm" variant="secondary"><Link to="?section=payments&status=review">Payments in review</Link></Button>
        <Button asChild size="sm" variant="secondary"><Link to="?section=reconciliation&status=open">Open reconciliation</Link></Button>
      </div>
    </div>
  );
}

function SubscriptionsSection() {
  const t = useBillingTable<BillingSubscriptionRow>(platformBillingApi.subscriptions, ["status", "billing_status", "plan"]);
  const [plans, setPlans] = useState<{ value: string; label: string }[]>([]);
  const [canRecover, setCanRecover] = useState(false);
  const [target, setTarget] = useState<{ id: string; label: string } | null>(null);
  useEffect(() => {
    platformBillingApi.plans().then((r) => setPlans(r.data.map((p) => ({ value: p.code, label: p.name })))).catch(() => setPlans([]));
    platformBillingApi.overview().then((r) => setCanRecover(r.data.can_recover)).catch(() => setCanRecover(false));
  }, []);

  const filters: FilterConfig[] = [
    { key: "status", label: "Subscription", ...t.filter("status"), options: [all("All statuses"), ...["active", "trial", "expired", "suspended"].map((v) => option(v))] },
    { key: "billing_status", label: "Billing", ...t.filter("billing_status"),
      options: [all("All billing states"), ...["current", "due_soon", "expiring_soon", "overdue", "pending", "review", "failed", "no_billing"].map((v) => option(v))] },
    { key: "plan", label: "Plan", ...t.filter("plan"), options: [all("All plans"), ...plans] },
  ];
  const columns: Column<BillingSubscriptionRow>[] = [
    { key: "tenant", header: "Company / workspace", exportValue: (r) => r.tenant_name ?? "Unassigned",
      cell: (r) => <div>{tenantLink(r.tenant_id, r.tenant_name)}<div className="text-xs text-muted-foreground">{r.workspace ?? r.reference_code}</div></div> },
    { key: "plan", header: "Plan", exportValue: (r) => r.plan_name, cell: (r) => <div>{r.plan_name}<div className="text-xs text-muted-foreground">{money(r.monthly_fee)}/mo</div></div> },
    { key: "status", header: "Subscription", exportValue: (r) => r.status, cell: (r) => <BillingBadge status={r.status} /> },
    { key: "billing_status", header: "Billing", exportValue: (r) => r.billing_status, cell: (r) => <BillingBadge status={r.billing_status} /> },
    { key: "started_at", header: "Start", exportValue: (r) => r.started_at ?? "", cell: (r) => date(r.started_at) },
    { key: "expires_at", header: "Expiry", exportValue: (r) => r.expires_at ?? "",
      cell: (r) => <div>{date(r.expires_at)}{r.days_until_expiry !== null && <div className="text-xs text-muted-foreground">{r.days_until_expiry >= 0 ? `${r.days_until_expiry} days left` : `${-r.days_until_expiry} days ago`}</div>}</div> },
    { key: "next_billing_at", header: "Next billing", exportValue: (r) => r.next_billing_at ?? "", cell: (r) => date(r.next_billing_at) },
    { key: "last_payment", header: "Last payment", exportValue: (r) => r.last_payment_amount ?? "",
      cell: (r) => r.last_payment_amount ? <div>{money(r.last_payment_amount)}<div className="text-xs text-muted-foreground">{date(r.last_payment_at)}</div></div> : <span className="text-muted-foreground">None</span> },
    { key: "actions", header: "", className: "text-right",
      cell: (r) => (
        <div className="flex justify-end gap-1">
          {r.tenant_id && <Button asChild size="sm" variant="ghost"><Link to={`/platform/billing/tenants/${r.tenant_id}`}>View</Link></Button>}
          {canRecover && r.tenant_id && (
            <Button size="sm" variant="ghost" onClick={() => setTarget({ id: r.id, label: r.tenant_name ?? r.reference_code })}>Recover</Button>
          )}
        </div>
      ) },
  ];
  return (
    <div className="space-y-4">
      <ErrorNote message={t.error} onRetry={t.refresh} />
      <DataTable columns={columns} data={t.rows} {...t.table} filters={filters} searchPlaceholder="Search company, workspace, reference or plan…"
        exportTitle="Subscriptions" emptyMessage={t.error ? "Subscriptions could not be loaded." : "No subscriptions match these filters."} />
      <RecoveryDialog target={target} onClose={() => setTarget(null)} onDone={t.refresh} />
    </div>
  );
}

function PaymentsSection() {
  const t = useBillingTable<BillingPaymentRow>(platformBillingApi.payments, ["status", "kind"]);
  const filters: FilterConfig[] = [
    { key: "status", label: "Status", ...t.filter("status"), options: [all("All statuses"), ...["pending", "confirmed", "review", "failed", "expired"].map((v) => option(v))] },
    { key: "kind", label: "Type", ...t.filter("kind"), options: [all("All types"), option("checkout", "Online checkout"), option("manual", "Manual / legacy")] },
  ];
  const columns: Column<BillingPaymentRow>[] = [
    { key: "reference", header: "Reference", exportValue: (r) => r.payment_reference, cell: (r) => <span className="font-mono text-xs">{r.payment_reference}</span> },
    { key: "tenant", header: "Company", exportValue: (r) => r.tenant_name ?? "", cell: (r) => tenantLink(r.tenant_id, r.tenant_name) },
    { key: "plan", header: "Plan", exportValue: (r) => r.plan_name, cell: (r) => r.plan_name },
    { key: "kind", header: "Type", exportValue: (r) => r.kind, cell: (r) => (r.kind === "checkout" ? "Online checkout" : "Manual / legacy") },
    { key: "amount", header: "Amount", exportValue: (r) => r.amount, cell: (r) => money(r.amount, r.currency) },
    { key: "status", header: "Status", exportValue: (r) => r.status,
      cell: (r) => <div><BillingBadge status={r.status} />{r.failure_reason && <div className="mt-1 max-w-[16rem] text-xs text-muted-foreground">{r.failure_reason}</div>}</div> },
    { key: "invoice", header: "Invoice", exportValue: (r) => r.invoice_number ?? "", cell: (r) => r.invoice_number ?? "—" },
    { key: "created_at", header: "Created", exportValue: (r) => r.created_at, cell: (r) => date(r.created_at) },
    { key: "confirmed_at", header: "Confirmed", exportValue: (r) => r.confirmed_at ?? "", cell: (r) => date(r.confirmed_at) },
  ];
  return (
    <div className="space-y-4">
      <ErrorNote message={t.error} onRetry={t.refresh} />
      <DataTable columns={columns} data={t.rows} {...t.table} filters={filters} searchPlaceholder="Search reference, transaction id or company…"
        exportTitle="Subscription payments" emptyMessage={t.error ? "Payments could not be loaded." : "No subscription payments recorded."} />
    </div>
  );
}

function InvoicesSection() {
  const t = useBillingTable<BillingInvoiceRow>(platformBillingApi.invoices, ["status"]);
  const filters: FilterConfig[] = [
    { key: "status", label: "Status", ...t.filter("status"), options: [all("All statuses"), ...["sent", "paid", "overdue", "cancelled"].map((v) => option(v))] },
  ];
  const columns: Column<BillingInvoiceRow>[] = [
    { key: "number", header: "Invoice", exportValue: (r) => r.invoice_number, cell: (r) => <span className="font-medium">{r.invoice_number}</span> },
    { key: "tenant", header: "Company", exportValue: (r) => r.tenant_name ?? "", cell: (r) => tenantLink(r.tenant_id, r.tenant_name) },
    { key: "plan", header: "Plan", exportValue: (r) => r.plan_name, cell: (r) => r.plan_name },
    { key: "issue_date", header: "Issued", exportValue: (r) => r.issue_date ?? "", cell: (r) => date(r.issue_date) },
    { key: "total", header: "Total", exportValue: (r) => r.total_amount, cell: (r) => money(r.total_amount, r.currency) },
    { key: "paid", header: "Paid", exportValue: (r) => r.amount_paid, cell: (r) => money(r.amount_paid, r.currency) },
    { key: "status", header: "Invoice status", exportValue: (r) => r.status, cell: (r) => <BillingBadge status={r.status} /> },
    { key: "payment_status", header: "Payment", exportValue: (r) => r.payment_status, cell: (r) => <BillingBadge status={r.payment_status} /> },
  ];
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">Invoices are issued by online checkout in the platform's own books. Legacy manual payment requests have no invoice.</p>
      <ErrorNote message={t.error} onRetry={t.refresh} />
      <DataTable columns={columns} data={t.rows} {...t.table} filters={filters} searchPlaceholder="Search invoice number, reference or company…"
        exportTitle="Subscription invoices" emptyMessage={t.error ? "Invoices could not be loaded." : "No subscription invoices issued yet."} />
    </div>
  );
}

function ReconciliationSection() {
  const t = useBillingTable<BillingReconciliationRow>(platformBillingApi.reconciliation, ["status", "kind"]);
  const filters: FilterConfig[] = [
    { key: "status", label: "Status", ...t.filter("status"), options: [all("All statuses"), option("open"), option("resolved")] },
    { key: "kind", label: "Issue", ...t.filter("kind"),
      options: [all("All issues"), ...["amount_mismatch", "status_mismatch", "missing_payment", "missing_journal", "late_success", "unapplied_payment"].map((v) => option(v))] },
  ];
  const columns: Column<BillingReconciliationRow>[] = [
    { key: "kind", header: "Issue", exportValue: (r) => r.kind_label, cell: (r) => <span className="font-medium">{r.kind_label}</span> },
    { key: "tenant", header: "Company", exportValue: (r) => r.tenant_name ?? "", cell: (r) => tenantLink(r.tenant_id, r.tenant_name) },
    { key: "reference", header: "Payment", exportValue: (r) => r.payment_reference ?? "", cell: (r) => <span className="font-mono text-xs">{r.payment_reference ?? "—"}</span> },
    { key: "provider", header: "Provider", exportValue: (r) => `${r.provider_status} ${r.provider_amount ?? ""}`,
      cell: (r) => <div>{humanize(r.provider_status)}<div className="text-xs text-muted-foreground">{money(r.provider_amount)}</div></div> },
    { key: "ledger", header: "Ledger", exportValue: (r) => `${r.ledger_status} ${r.ledger_amount ?? ""}`,
      cell: (r) => <div>{humanize(r.ledger_status)}<div className="text-xs text-muted-foreground">{money(r.ledger_amount)}</div></div> },
    { key: "detail", header: "Detail", exportValue: (r) => r.detail, cell: (r) => <span className="line-clamp-2 max-w-[20rem] text-sm">{r.detail || "—"}</span> },
    { key: "status", header: "Status", exportValue: (r) => r.status, cell: (r) => <BillingBadge status={r.status} /> },
    { key: "created_at", header: "Found", exportValue: (r) => r.created_at, cell: (r) => date(r.created_at) },
  ];
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Discrepancies between the payment provider and the ledger are never auto-fixed. Resolve them in{" "}
        <Link className="text-primary hover:underline" to="/platform/integrations?section=payments">Platform → Integrations → Reconciliation</Link>.
      </p>
      <ErrorNote message={t.error} onRetry={t.refresh} />
      <DataTable columns={columns} data={t.rows} {...t.table} filters={filters} searchPlaceholder="Search detail, reference or company…"
        exportTitle="Billing reconciliation" emptyMessage={t.error ? "Reconciliation could not be loaded." : "No reconciliation issues."} />
    </div>
  );
}

function PlansSection() {
  const [plans, setPlans] = useState<BillingPlanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", monthly_price: "", max_users: "10", max_branches: "3", description: "" });
  useEffect(() => {
    setLoading(true);
    setError("");
    platformBillingApi.plans().then((r) => setPlans(r.data)).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load plans.")).finally(() => setLoading(false));
  }, [reload]);

  const save = async () => {
    const price = Number(form.monthly_price);
    if (!form.name.trim() || !Number.isFinite(price) || price < 0) {
      await appDialog.alert("Enter a plan name and a monthly price of 0 or more.", { tone: "danger" });
      return;
    }
    try {
      await platformApi.createPlan({ name: form.name.trim(), monthly_price: price, max_users: Number(form.max_users) || 10,
        max_branches: Number(form.max_branches) || 3, description: form.description });
      setCreating(false);
      setForm({ name: "", monthly_price: "", max_users: "10", max_branches: "3", description: "" });
      setReload((v) => v + 1);
    } catch (e) {
      await appDialog.alert(e instanceof Error ? e.message : "Could not create plan.", { tone: "danger" });
    }
  };

  const columns: Column<BillingPlanRow>[] = [
    { key: "name", header: "Plan", exportValue: (r) => r.name, cell: (r) => <div className="font-medium">{r.name}<div className="text-xs font-normal text-muted-foreground">{r.code}</div></div> },
    { key: "price", header: "Monthly price", exportValue: (r) => r.monthly_price, cell: (r) => money(r.monthly_price) },
    { key: "limits", header: "Limits", exportValue: (r) => `${r.max_users} users / ${r.max_branches} branches`, cell: (r) => `${r.max_users} users · ${r.max_branches} branches` },
    { key: "modules", header: "Modules", exportValue: (r) => r.modules.join(", "), cell: (r) => <span className="line-clamp-2 max-w-[18rem] text-xs text-muted-foreground">{r.modules.join(", ") || "—"}</span> },
    { key: "subscriptions", header: "Subscriptions", exportValue: (r) => String(r.subscriptions), cell: (r) => r.subscriptions },
    { key: "status", header: "Status", exportValue: (r) => (r.is_active ? "active" : "inactive"), cell: (r) => <BillingBadge status={r.is_active ? "active" : "cancelled"} /> },
  ];
  const field = (key: keyof typeof form, label: string, type = "text") => (
    <label className="space-y-1 text-sm">
      <span className="font-medium">{label}</span>
      <Input type={type} value={form[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
    </label>
  );
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">Plans use the existing plan catalogue. Plans can be created here; editing or retiring plans is not supported by the backend yet.</p>
      <ErrorNote message={error} onRetry={() => setReload((v) => v + 1)} />
      {creating && (
        <div className="grid gap-3 rounded-xl border bg-card p-4 sm:grid-cols-2 lg:grid-cols-5">
          {field("name", "Name")}
          {field("monthly_price", "Monthly price", "number")}
          {field("max_users", "Max users", "number")}
          {field("max_branches", "Max branches", "number")}
          {field("description", "Description")}
          <div className="flex gap-2 sm:col-span-2 lg:col-span-5">
            <Button size="sm" onClick={() => void save()}>Create plan</Button>
            <Button size="sm" variant="secondary" onClick={() => setCreating(false)}>Cancel</Button>
          </div>
        </div>
      )}
      <DataTable columns={columns} data={plans} loading={loading} clientPagination exportTitle="Subscription plans"
        actions={!creating ? <Button size="sm" onClick={() => setCreating(true)}>New plan</Button> : undefined}
        emptyMessage={error ? "Plans could not be loaded." : "No plans defined."} />
    </div>
  );
}

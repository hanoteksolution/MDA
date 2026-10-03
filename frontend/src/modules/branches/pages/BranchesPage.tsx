import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowLeftRight, Boxes, Building2, Receipt, ShoppingCart, Wallet } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { KpiCard } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import type { FilterConfig } from "@/components/data/FilterBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { branchOpsApi, type BranchOverviewRow, type BranchReportName, type CrossBranchSearchResult } from "@/services/api/branchOps";
import { ALL_BRANCHES } from "@/services/api/branchContext";
import { useBranchStore } from "@/store/branchStore";
import { activeBranchLabel } from "@/components/branch/BranchSwitcher";
import { BranchTransfersPage } from "./BranchTransfersPage";
import { BranchReportTable, ReconcileBadge, REPORT_COLUMNS, REPORT_LABELS, fmt } from "../components/BranchReportTable";
import { CrossBranchPanel } from "../components/CrossBranchPanel";
import { TransferRequestDialog, type TransferDraft } from "../components/TransferRequestDialog";
import { useBranchReports } from "../hooks";
import { usePermissions } from "@/hooks/usePermissions";
import { money, num, qtyText } from "../lib";

const SECTIONS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "branches", label: "Branches" },
  { id: "transfers", label: "Transfers" },
  { id: "stock", label: "Stock across branches" },
  { id: "reports", label: "Reports" },
] as const;
type Section = (typeof SECTIONS)[number]["id"];

/** Branch scope for a page: "all" or one branch id, chosen locally so admins can compare without switching the app. */
function useScopeParam() {
  const [params, setParams] = useSearchParams();
  const { branches, coversAll, activeBranchId } = useBranchStore();
  const fallback = activeBranchId ?? (coversAll ? ALL_BRANCHES : branches[0]?.id ?? "");
  const scope = params.get("scope") || fallback || "";
  const options = [
    ...(coversAll ? [{ value: ALL_BRANCHES, label: "All branches" }] : []),
    ...branches.map((b) => ({ value: b.id, label: b.name })),
  ];
  const setScope = (value: string) => setParams((cur) => {
    const next = new URLSearchParams(cur);
    next.set("scope", value);
    return next;
  });
  return { scope, setScope, options, label: activeBranchLabel(scope, branches) };
}

/** Branch Management: consolidated dashboard, branch list, transfers, stock visibility and reports. */
export function BranchesPage() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("section") as Section | null;
  const section: Section = SECTIONS.some((s) => s.id === requested) ? (requested as Section) : "dashboard";
  const { loaded, loadBranches, loading } = useBranchStore();
  useEffect(() => {
    if (!loaded && !loading) void loadBranches();
  }, [loaded, loading, loadBranches]);
  return (
    <PageLayout title="Branches" description="Every branch runs its own stock, sales and cash; this is the company-wide view." breadcrumbs={["Branches"]}>
      <div className="space-y-5">
        <TabNav tabs={[...SECTIONS]} active={section} onChange={(id) => setParams(id === "dashboard" ? {} : { section: id })} />
        {section === "dashboard" && <BranchDashboard />}
        {section === "branches" && <BranchList />}
        {section === "transfers" && <BranchTransfersPage embedded />}
        {section === "stock" && <StockAcrossBranches />}
        {section === "reports" && <BranchReports />}
      </div>
    </PageLayout>
  );
}

function ScopeBar({ scope, setScope, options, extra }: { scope: string; setScope: (v: string) => void; options: { value: string; label: string }[]; extra?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="space-y-1 text-sm">
        <span className="font-medium">Branch</span>
        <select aria-label="Report branch" className="block h-10 rounded-xl border border-input bg-background px-3 text-sm" value={scope} onChange={(e) => setScope(e.target.value)}>
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
      {extra}
    </div>
  );
}

function DateRange({ from, to, onChange }: { from: string; to: string; onChange: (from: string, to: string) => void }) {
  return (
    <>
      <label className="space-y-1 text-sm"><span className="font-medium">From</span><Input type="date" value={from} onChange={(e) => onChange(e.target.value, to)} /></label>
      <label className="space-y-1 text-sm"><span className="font-medium">To</span><Input type="date" value={to} onChange={(e) => onChange(from, e.target.value)} /></label>
    </>
  );
}

const monthStart = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
};

function useDates() {
  const [params, setParams] = useSearchParams();
  const from = params.get("from") ?? monthStart();
  const to = params.get("to") ?? "";
  const set = (f: string, t: string) => setParams((cur) => {
    const next = new URLSearchParams(cur);
    if (f) next.set("from", f); else next.delete("from");
    if (t) next.set("to", t); else next.delete("to");
    return next;
  });
  return { from, to, set };
}

const DASHBOARD_REPORTS: BranchReportName[] = ["sales", "stock-value", "inventory", "purchases", "cash", "expenses", "profit-loss", "transfers"];

function BranchDashboard() {
  const { scope, setScope, options, label } = useScopeParam();
  const { from, to, set } = useDates();
  const { reports, loading, error, retry } = useBranchReports(DASHBOARD_REPORTS, { branch_id: scope, date_from: from, date_to: to }, Boolean(scope));
  const c = (r: BranchReportName, k: string) => reports[r]?.consolidated?.[k];
  const allReconcile = DASHBOARD_REPORTS.every((r) => reports[r]?.reconciles !== false);
  const comparison = reports.sales?.branches ?? [];
  const byBranch = (r: BranchReportName) => Object.fromEntries((reports[r]?.branches ?? []).map((b) => [b.branch_id, b]));
  const stock = byBranch("stock-value"), inv = byBranch("inventory"), cash = byBranch("cash"), pnl = byBranch("profit-loss"), tr = byBranch("transfers");

  return (
    <div className="space-y-5">
      <ScopeBar scope={scope} setScope={setScope} options={options} extra={<DateRange from={from} to={to} onChange={set} />} />
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant={scope === ALL_BRANCHES ? "warning" : "default"}>Viewing: {label}</Badge>
        {!loading && !error && <Badge variant={allReconcile ? "success" : "destructive"}>{allReconcile ? "All figures reconcile with branch totals" : "Some figures do not reconcile"}</Badge>}
      </div>
      {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">{error} <button className="underline" onClick={retry}>Retry</button></p>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard index={0} title="Net sales" value={money(c("sales", "net"))} loading={loading} icon={<ShoppingCart className="h-5 w-5" />} trend={`${qtyText(c("sales", "invoices"))} invoices`} />
        <KpiCard index={1} title="Stock value (cost)" value={money(c("stock-value", "value"))} loading={loading} accent="info" icon={<Boxes className="h-5 w-5" />} trend={`${qtyText(c("stock-value", "units"))} units`} />
        <KpiCard index={2} title="Low / out of stock" value={`${qtyText(c("inventory", "low_stock"))} / ${qtyText(c("inventory", "out_of_stock"))}`} loading={loading} accent="warning" icon={<AlertTriangle className="h-5 w-5" />} />
        <KpiCard index={3} title="Purchases ordered" value={money(c("purchases", "ordered_total"))} loading={loading} icon={<Receipt className="h-5 w-5" />} trend={`${qtyText(c("purchases", "open_orders"))} open orders`} />
        <KpiCard index={4} title="Net cash" value={money(c("cash", "net_cash"))} loading={loading} accent="success" icon={<Wallet className="h-5 w-5" />} trend={`Variance ${money(c("cash", "variance"))}`} />
        <KpiCard index={5} title="Expenses" value={money(c("expenses", "amount"))} loading={loading} accent="warning" icon={<Receipt className="h-5 w-5" />} />
        <KpiCard index={6} title="Net profit (ledger)" value={money(c("profit-loss", "net_profit"))} loading={loading} accent="success" icon={<Building2 className="h-5 w-5" />} trend={`Revenue ${money(c("profit-loss", "revenue"))}`} />
        <KpiCard index={7} title="Open transfers" value={qtyText(num(c("transfers", "outgoing_open")) + num(c("transfers", "incoming_open")))} loading={loading} accent="info" icon={<ArrowLeftRight className="h-5 w-5" />} trend={`${qtyText(c("transfers", "awaiting_approval"))} awaiting approval`} />
      </div>
      {comparison.length > 1 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold">Branch comparison</h2>
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>{["Branch", "Net sales", "Invoices", "Stock value", "Low / out", "Net cash", "Net profit", "Open transfers"].map((h, i) => <th key={h} className={`px-3 py-2 ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {comparison.map((b) => (
                  <tr key={b.branch_id} className="border-t">
                    <td className="px-3 py-2 font-medium"><Link className="text-primary hover:underline" to={`/branches/${b.branch_id}`}>{b.branch_name}</Link></td>
                    <td className="px-3 py-2 text-right tabular-nums">{money(b.net)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{qtyText(b.invoices)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{money(stock[b.branch_id]?.value)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{qtyText(inv[b.branch_id]?.low_stock)} / {qtyText(inv[b.branch_id]?.out_of_stock)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{money(cash[b.branch_id]?.net_cash)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{money(pnl[b.branch_id]?.net_profit)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{qtyText(num(tr[b.branch_id]?.outgoing_open) + num(tr[b.branch_id]?.incoming_open))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {reports["profit-loss"]?.unassigned && <p className="text-xs text-muted-foreground">Company total P&L also includes company-level (unassigned) postings of {money(reports["profit-loss"]?.unassigned?.net_profit)}.</p>}
        </div>
      )}
    </div>
  );
}

function BranchList() {
  const { from, to } = useDates();
  const { hasPermission } = usePermissions();
  const [rows, setRows] = useState<BranchOverviewRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  useEffect(() => {
    setLoading(true);
    branchOpsApi.overview({ branch_id: ALL_BRANCHES, date_from: from, date_to: to })
      .then((r) => { setRows(r.data.branches); setError(""); })
      .catch(() =>
        // Branch managers cannot request "all": fall back to their own accessible branches.
        branchOpsApi.overview({ date_from: from, date_to: to }).then((r) => { setRows(r.data.branches); setError(""); })
      )
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load branches."))
      .finally(() => setLoading(false));
  }, [from, to]);
  const visible = useMemo(() => rows.filter((r) =>
    (!status || (status === "active" ? r.is_active : !r.is_active)) &&
    (!search || `${r.name} ${r.code} ${r.managers.join(" ")}`.toLowerCase().includes(search.toLowerCase()))
  ), [rows, search, status]);
  const filters: FilterConfig[] = [{ key: "status", label: "Status", value: status, onChange: setStatus,
    options: [{ value: "", label: "All statuses" }, { value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }] }];
  const columns: Column<BranchOverviewRow>[] = [
    { key: "name", header: "Branch", exportValue: (r) => r.name,
      cell: (r) => <div><Link className="font-medium text-primary hover:underline" to={`/branches/${r.branch_id}`}>{r.name}</Link><div className="text-xs text-muted-foreground">{r.code}{r.is_default ? " · default" : ""}</div></div> },
    { key: "status", header: "Status", exportValue: (r) => r.status, cell: (r) => <Badge variant={r.is_active ? "success" : "secondary"}>{r.is_active ? "Active" : "Inactive"}</Badge> },
    { key: "manager", header: "Manager", exportValue: (r) => r.managers.join(", "), cell: (r) => r.managers.join(", ") || <span className="text-muted-foreground">—</span> },
    { key: "structure", header: "Warehouses · users · POS", exportValue: (r) => `${r.warehouses}/${r.users}/${r.pos_terminals}`,
      cell: (r) => `${r.warehouses} · ${r.users} · ${r.pos_terminals}${r.open_shifts ? ` (${r.open_shifts} open shift)` : ""}` },
    { key: "stock", header: "Stock value", exportValue: (r) => String(r.stock_value), cell: (r) => <span className="tabular-nums">{money(r.stock_value)}</span> },
    { key: "sales", header: "Net sales (period)", exportValue: (r) => String(r.sales_net), cell: (r) => <span className="tabular-nums">{money(r.sales_net)}</span> },
    { key: "alerts", header: "Indicators", exportValue: (r) => `${r.low_stock} low, ${r.out_of_stock} out, ${r.transfers_open} transfers`,
      cell: (r) => (
        <div className="flex flex-wrap gap-1">
          {r.out_of_stock > 0 && <Badge variant="destructive">{qtyText(r.out_of_stock)} out</Badge>}
          {r.low_stock > 0 && <Badge variant="warning">{qtyText(r.low_stock)} low</Badge>}
          {r.transfers_awaiting_approval > 0 && <Badge variant="warning">{qtyText(r.transfers_awaiting_approval)} to approve</Badge>}
          {r.transfers_open > 0 && <Badge>{qtyText(r.transfers_open)} transfers</Badge>}
        </div>
      ) },
    { key: "actions", header: "", className: "text-right", cell: (r) => <Button asChild size="sm" variant="ghost"><Link to={`/branches/${r.branch_id}`}>Open</Link></Button> },
  ];
  return (
    <div className="space-y-3">
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <DataTable columns={columns} data={visible} loading={loading} clientPagination searchValue={search} onSearchChange={setSearch}
        searchPlaceholder="Search branch, code or manager…" filters={filters} exportTitle="Branches"
        actions={hasPermission("branches.create") ? <Button asChild size="sm" variant="secondary"><Link to="/settings/branches/new">New branch</Link></Button> : undefined}
        emptyMessage={error ? "Branches could not be loaded." : "No branches match."} />
    </div>
  );
}

function StockAcrossBranches() {
  const activeBranchId = useBranchStore((s) => s.activeBranchId);
  const [term, setTerm] = useState("");
  const [result, setResult] = useState<CrossBranchSearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState<TransferDraft | null>(null);
  const [reload, setReload] = useState(0);
  const single = Boolean(activeBranchId && activeBranchId !== ALL_BRANCHES);
  useEffect(() => {
    if (!single || term.trim().length < 2) { setResult(null); return; }
    const t = setTimeout(() => {
      setLoading(true);
      branchOpsApi.crossBranchSearch(term.trim())
        .then((r) => { setResult(r.data); setError(""); })
        .catch((e: unknown) => setError(e instanceof Error ? e.message : "Search failed."))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(t);
  }, [term, single, reload]);
  if (!single) return <p className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm">Select one branch in the header: availability is always shown relative to the branch you are working in.</p>;
  return (
    <div className="space-y-4">
      <Input className="max-w-lg" placeholder="Search product name, SKU or barcode…" value={term} onChange={(e) => setTerm(e.target.value)} aria-label="Search stock across branches" />
      {loading && <p className="text-sm text-muted-foreground">Searching…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {result?.results.length === 0 && <p className="text-sm text-muted-foreground">No products match “{term}”.</p>}
      <div className="grid gap-4 xl:grid-cols-2">
        {result?.results.map((p) => (
          <div key={p.product_id} className="rounded-2xl border bg-card p-4">
            <div className="mb-3 font-semibold">{p.product_name} <span className="text-xs font-normal text-muted-foreground">{p.product_sku}</span></div>
            <CrossBranchPanel data={p} onRequestTransfer={(sourceId, sourceName, suggested) => setDraft({
              productId: p.product_id, productName: p.product_name, sourceBranchId: sourceId, sourceBranchName: sourceName,
              destinationBranchId: p.current_branch.branch_id, destinationBranchName: p.current_branch.branch_name, quantity: suggested,
            })} />
          </div>
        ))}
      </div>
      <TransferRequestDialog draft={draft} onClose={() => setDraft(null)} onCreated={() => setReload((v) => v + 1)} />
    </div>
  );
}

const REPORT_NAMES = Object.keys(REPORT_COLUMNS) as BranchReportName[];

function BranchReports() {
  const [params, setParams] = useSearchParams();
  const { scope, setScope, options } = useScopeParam();
  const { from, to, set } = useDates();
  const report = (params.get("report") as BranchReportName) || "sales";
  const { reports, loading, error, retry } = useBranchReports([report], { branch_id: scope, date_from: from, date_to: to }, Boolean(scope));
  const data = reports[report];
  const snapshot = report === "inventory" || report === "stock-value";
  return (
    <div className="space-y-4">
      <ScopeBar scope={scope} setScope={setScope} options={options} extra={
        <>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Report</span>
            <select aria-label="Report type" className="block h-10 rounded-xl border border-input bg-background px-3 text-sm" value={report}
              onChange={(e) => setParams((cur) => { const n = new URLSearchParams(cur); n.set("report", e.target.value); return n; })}>
              {REPORT_NAMES.map((r) => <option key={r} value={r}>{REPORT_LABELS[r]}</option>)}
            </select>
          </label>
          {!snapshot && <DateRange from={from} to={to} onChange={set} />}
        </>
      } />
      {snapshot && <p className="text-xs text-muted-foreground">Current stock snapshot — dates do not apply.</p>}
      {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">{error} <button className="underline" onClick={retry}>Retry</button></p>}
      {loading && <p className="text-sm text-muted-foreground">Loading report…</p>}
      {data && !loading && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2"><Badge>{REPORT_LABELS[report]} · {data.mode === "single" ? "single branch" : "consolidated"}</Badge>{data.mode !== "single" && <ReconcileBadge report={data} />}</div>
          <BranchReportTable report={data} />
          {data.mode !== "single" && (
            <p className="text-xs text-muted-foreground">
              The company total is computed independently from the branch rows; “reconcile” means they agree. {REPORT_COLUMNS[report].slice(0, 1).map((c) => `${c.label}: ${fmt(c.kind, data.consolidated[c.key])}.`)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

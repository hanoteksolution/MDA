import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/services/api/http";
import { branchOpsApi, type BranchOverviewRow, type BranchReportName } from "@/services/api/branchOps";
import { usePermissions } from "@/hooks/usePermissions";
import { BranchTransfersPage } from "./BranchTransfersPage";
import { BranchReportTable, REPORT_LABELS } from "../components/BranchReportTable";
import { useBranchReports } from "../hooks";
import { money, qtyText } from "../lib";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "sales", label: "Sales" },
  { id: "inventory", label: "Inventory" },
  { id: "purchases", label: "Purchases" },
  { id: "transfers", label: "Transfers" },
  { id: "finance", label: "Finance" },
  { id: "users", label: "Users" },
  { id: "reports", label: "Reports" },
] as const;
type Tab = (typeof TABS)[number]["id"];

const TAB_REPORTS: Record<string, BranchReportName[]> = {
  sales: ["sales", "cash"],
  inventory: ["inventory", "stock-value"],
  purchases: ["purchases"],
  finance: ["profit-loss", "cash", "expenses"],
  reports: ["sales", "stock-value", "inventory", "purchases", "cash", "expenses", "profit-loss", "transfers"],
};

interface AccessRow {
  id: string;
  username: string;
  profile_name: string | null;
  status: string;
  is_default: boolean;
  is_effective: boolean;
}

/** One branch: its figures from the branch reports (never recomputed here), its transfers and its people. */
export function BranchDetailPage() {
  const { branchId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tab: Tab = TABS.some((t) => t.id === params.get("tab")) ? (params.get("tab") as Tab) : "overview";
  const { hasPermission } = usePermissions();
  const [row, setRow] = useState<BranchOverviewRow | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    branchOpsApi.overview({ branch_id: branchId })
      .then((r) => { setRow(r.data.branches[0] ?? null); setError(""); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "You cannot view this branch."));
  }, [branchId]);

  return (
    <PageLayout
      title={row ? `${row.name} branch` : "Branch"}
      description={
        row
          ? `${row.company_name ? `${row.company_name} · ` : ""}${row.code}${row.managers.length ? ` · Manager: ${row.managers.join(", ")}` : ""}`
          : undefined
      }
      breadcrumbs={["Branches", row?.name ?? "Branch"]}
      backTo="/branches?section=branches"
      backLabel="Branches"
      actions={hasPermission("branches.update") ? <Button asChild size="sm" variant="secondary"><Link to={`/settings/branches/${branchId}/edit`}>Edit branch</Link></Button> : undefined}
    >
      {error ? (
        <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</p>
      ) : (
        <div className="space-y-5">
          <TabNav tabs={[...TABS]} active={tab} onChange={(id) => setParams(id === "overview" ? {} : { tab: id })} />
          {tab === "overview" && <Overview row={row} />}
          {TAB_REPORTS[tab] && <ReportsFor branchId={branchId} names={TAB_REPORTS[tab]} />}
          {tab === "transfers" && <BranchTransfersPage embedded branchId={branchId} />}
          {tab === "users" && <Users branchId={branchId} />}
        </div>
      )}
    </PageLayout>
  );
}

function Overview({ row }: { row: BranchOverviewRow | null }) {
  if (!row) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const items: [string, React.ReactNode][] = [
    ["Status", <Badge key="s" variant={row.is_active ? "success" : "secondary"}>{row.is_active ? "Active" : "Inactive"}</Badge>],
    ["Shop / Company", row.company_name
      ? <Link key="c" to="/settings" className="text-primary hover:underline">{row.company_name}</Link>
      : "—"],
    ["Type", row.branch_type || "—"],
    ["Phone", row.phone || "—"],
    ["Address", row.address || "—"],
    ["Warehouses", row.warehouses],
    ["Users with access", row.users],
    ["POS terminals / registers", `${row.pos_terminals} / ${row.cash_registers}`],
    ["Open cashier shifts", row.open_shifts],
    ["Stock value (cost)", money(row.stock_value)],
    ["Net sales (this month)", money(row.sales_net)],
    ["Invoices (this month)", qtyText(row.sales_invoices)],
    ["Low / out of stock", `${qtyText(row.low_stock)} / ${qtyText(row.out_of_stock)}`],
    ["Open transfers", `${qtyText(row.transfers_open)} (${qtyText(row.transfers_awaiting_approval)} awaiting approval)`],
  ];
  return (
    <ContentSection title="At a glance">
      <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        {items.map(([label, value]) => (
          <div key={label}><dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>
        ))}
      </dl>
    </ContentSection>
  );
}

function ReportsFor({ branchId, names }: { branchId: string; names: BranchReportName[] }) {
  const { reports, loading, error, retry } = useBranchReports(names, { branch_id: branchId });
  if (error) return <p role="alert" className="text-sm text-destructive">{error} <button className="underline" onClick={retry}>Retry</button></p>;
  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  return (
    <div className="space-y-4">
      {names.map((n) => reports[n] && (
        <ContentSection key={n} title={REPORT_LABELS[n]}>
          <BranchReportTable report={reports[n]!} />
        </ContentSection>
      ))}
      <Button asChild size="sm" variant="ghost"><Link to={`/branches?section=reports&scope=${branchId}`}>Open in branch reports (date range)</Link></Button>
    </div>
  );
}

function Users({ branchId }: { branchId: string }) {
  const [rows, setRows] = useState<AccessRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    apiRequest<{ data: AccessRow[] }>(`/organization/branch-access/?branch=${branchId}`)
      .then((r) => { setRows(r.data); setError(""); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "You cannot view branch access."))
      .finally(() => setLoading(false));
  }, [branchId]);
  const columns: Column<AccessRow>[] = [
    { key: "user", header: "User", exportValue: (r) => r.username, cell: (r) => <span className="font-medium">{r.username}</span> },
    { key: "profile", header: "Branch role", exportValue: (r) => r.profile_name ?? "Full role permissions", cell: (r) => r.profile_name ?? <span className="text-muted-foreground">Full role permissions</span> },
    { key: "status", header: "Access", exportValue: (r) => r.status, cell: (r) => <Badge variant={r.is_effective ? "success" : "secondary"}>{r.is_effective ? "Active" : r.status.toLowerCase()}</Badge> },
    { key: "default", header: "Default branch", exportValue: (r) => (r.is_default ? "yes" : ""), cell: (r) => (r.is_default ? "Yes" : "—") },
  ];
  return (
    <div className="space-y-2">
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <DataTable columns={columns} data={rows} loading={loading} clientPagination exportTitle="Branch users"
        emptyMessage={error ? "Branch access could not be loaded." : "No users have access to this branch."} />
      <p className="text-xs text-muted-foreground">Access and per-branch roles are managed in Administration → Branch access.</p>
    </div>
  );
}

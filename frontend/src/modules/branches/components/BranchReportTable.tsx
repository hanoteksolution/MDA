import { Badge } from "@/components/ui/badge";
import type { BranchReport, BranchReportName } from "@/services/api/branchOps";
import { money, qtyText } from "../lib";

/** Column set per report. Every value is a backend figure — nothing is summed here. */
export const REPORT_COLUMNS: Record<BranchReportName, { key: string; label: string; kind: "money" | "qty" }[]> = {
  sales: [
    { key: "invoices", label: "Invoices", kind: "qty" },
    { key: "gross", label: "Gross sales", kind: "money" },
    { key: "refunded", label: "Refunds", kind: "money" },
    { key: "net", label: "Net sales", kind: "money" },
  ],
  "stock-value": [
    { key: "units", label: "Units", kind: "qty" },
    { key: "value", label: "Stock value (cost)", kind: "money" },
  ],
  inventory: [
    { key: "stock_lines", label: "Stock lines", kind: "qty" },
    { key: "units", label: "Units", kind: "qty" },
    { key: "reserved", label: "Reserved", kind: "qty" },
    { key: "low_stock", label: "Low stock", kind: "qty" },
    { key: "out_of_stock", label: "Out of stock", kind: "qty" },
  ],
  purchases: [
    { key: "orders", label: "Orders", kind: "qty" },
    { key: "ordered_total", label: "Ordered", kind: "money" },
    { key: "received_total", label: "Received", kind: "money" },
    { key: "open_orders", label: "Open orders", kind: "qty" },
    { key: "open_total", label: "Open value", kind: "money" },
  ],
  cash: [
    { key: "cash_received", label: "Cash received", kind: "money" },
    { key: "cash_refunded", label: "Cash refunded", kind: "money" },
    { key: "cash_in", label: "Cash in", kind: "money" },
    { key: "cash_out", label: "Cash out", kind: "money" },
    { key: "variance", label: "Variance", kind: "money" },
    { key: "net_cash", label: "Net cash", kind: "money" },
  ],
  expenses: [
    { key: "entries", label: "Entries", kind: "qty" },
    { key: "amount", label: "Expenses", kind: "money" },
  ],
  "profit-loss": [
    { key: "revenue", label: "Revenue", kind: "money" },
    { key: "expenses", label: "Expenses", kind: "money" },
    { key: "net_profit", label: "Net profit", kind: "money" },
  ],
  transfers: [
    { key: "outgoing", label: "Outgoing", kind: "qty" },
    { key: "outgoing_open", label: "Outgoing open", kind: "qty" },
    { key: "awaiting_approval", label: "Awaiting approval", kind: "qty" },
    { key: "incoming", label: "Incoming", kind: "qty" },
    { key: "incoming_open", label: "Incoming open", kind: "qty" },
    { key: "in_transit", label: "In transit", kind: "qty" },
  ],
};

export const REPORT_LABELS: Record<BranchReportName, string> = {
  sales: "Sales",
  "stock-value": "Stock valuation",
  inventory: "Inventory",
  purchases: "Purchases",
  cash: "Cash",
  expenses: "Expenses",
  "profit-loss": "Profit & loss",
  transfers: "Transfers",
};

export function fmt(kind: "money" | "qty", v: unknown) {
  return kind === "money" ? money(v) : qtyText(v);
}

export function ReconcileBadge({ report }: { report: Pick<BranchReport, "reconciles"> }) {
  return report.reconciles ? (
    <Badge variant="success">Branches reconcile with company total</Badge>
  ) : (
    <Badge variant="destructive">Branch totals do not reconcile — investigate</Badge>
  );
}

/** Per-branch rows + the independently computed consolidated row (+ unassigned for P&L). */
export function BranchReportTable({ report }: { report: BranchReport }) {
  const cols = REPORT_COLUMNS[report.report] ?? [];
  const showTotals = report.mode !== "single";
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Branch</th>
            {cols.map((c) => <th key={c.key} className="px-3 py-2 text-right">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {report.branches.map((b) => (
            <tr key={b.branch_id} className="border-t">
              <td className="px-3 py-2 font-medium">{b.branch_name} <span className="text-xs text-muted-foreground">{b.branch_code}</span></td>
              {cols.map((c) => <td key={c.key} className="px-3 py-2 text-right tabular-nums">{fmt(c.kind, b[c.key])}</td>)}
            </tr>
          ))}
          {report.unassigned && (
            <tr className="border-t text-muted-foreground">
              <td className="px-3 py-2">Unassigned (company-level)</td>
              {cols.map((c) => <td key={c.key} className="px-3 py-2 text-right tabular-nums">{fmt(c.kind, report.unassigned?.[c.key])}</td>)}
            </tr>
          )}
          {showTotals && (
            <tr className="border-t-2 bg-muted/30 font-semibold">
              <td className="px-3 py-2">Company total</td>
              {cols.map((c) => <td key={c.key} className="px-3 py-2 text-right tabular-nums">{fmt(c.kind, report.consolidated[c.key])}</td>)}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

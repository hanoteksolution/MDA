import { useEffect, useState } from "react";
import {
  BarChart3, FileSpreadsheet, Package, Users, DollarSign,
  TrendingUp, Download, Calendar, Filter, Loader2,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { ChartCard } from "@/components/data/ChartCard";
import { RevenueChart } from "@/components/data/charts/DashboardCharts";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, formatCurrency } from "@/utils/cn";
import { reportsApi, type ReportResult } from "@/services/api/reports";

const REPORT_CATEGORIES = [
  {
    id: "sales",
    title: "Sales Reports",
    description: "Revenue, invoices, and sales performance by period",
    icon: DollarSign,
    reports: ["Daily Sales", "Sales by Product", "Sales by Customer", "Tax Summary"],
  },
  {
    id: "inventory",
    title: "Inventory Reports",
    description: "Stock levels, valuation, and movement history",
    icon: Package,
    reports: ["Stock Valuation", "Low Stock"],
  },
  {
    id: "purchases",
    title: "Purchase Reports",
    description: "Supplier orders, receiving, and payables",
    icon: TrendingUp,
    reports: ["Purchase Summary", "Supplier Analysis"],
  },
  {
    id: "customers",
    title: "Customer Reports",
    description: "Customer activity, credit, and loyalty metrics",
    icon: Users,
    reports: ["Customer Ledger"],
  },
  {
    id: "finance",
    title: "Financial Reports",
    description: "Profit & loss and expense breakdown",
    icon: BarChart3,
    reports: ["Profit & Loss", "Expense Breakdown"],
  },
  {
    id: "custom",
    title: "Custom Reports",
    description: "Build and save custom report configurations",
    icon: FileSpreadsheet,
    reports: ["Report Builder", "Saved Reports"],
  },
];

export function ReportsPage() {
  const [selected, setSelected] = useState<string>("sales");
  const [activeReport, setActiveReport] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [reportData, setReportData] = useState<ReportResult | null>(null);
  const [chartData, setChartData] = useState<{ month: string; revenue: number }[]>([]);
  const [loading, setLoading] = useState(false);

  const category = REPORT_CATEGORIES.find((c) => c.id === selected);

  const loadReport = (reportName: string) => {
    if (selected === "custom") return;
    setActiveReport(reportName);
    setLoading(true);
    Promise.all([
      reportsApi.data({
        category: selected,
        report: reportName,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
      reportsApi.chart(selected),
    ])
      .then(([dataRes, chartRes]) => {
        setReportData(dataRes.data);
        setChartData(
          chartRes.data.map((d) => ({
            month: d.month,
            revenue: d.revenue ?? d.profit ?? 0,
          }))
        );
      })
      .catch(() => {
        setReportData({ columns: [], rows: [] });
        setChartData([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (category && category.reports[0] && selected !== "custom") {
      loadReport(category.reports[0]);
    }
  }, [selected]);

  const columns: Column<Record<string, string | number>>[] =
    reportData?.columns.map((col) => ({
      key: col,
      header: col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      cell: (r) => {
        const val = r[col];
        if (typeof val === "number" && (col.includes("amount") || col.includes("total") || col.includes("revenue") || col.includes("value") || col.includes("cost") || col === "value")) {
          return formatCurrency(val);
        }
        return String(val ?? "");
      },
    })) ?? [];

  const exportCsv = () => {
    if (!reportData?.rows.length) return;
    const header = reportData.columns.join(",");
    const rows = reportData.rows.map((r) =>
      reportData.columns.map((c) => JSON.stringify(r[c] ?? "")).join(",")
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selected}-${activeReport?.replace(/\s+/g, "-").toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageLayout
      title="Reports"
      description="Analytics, exports, and business intelligence."
      breadcrumbs={["Home", "Reports"]}
    >
      <div className="ds-card flex flex-wrap items-center gap-4 px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Calendar className="h-4 w-4" />
          Date Range
        </div>
        <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-auto" />
        <span className="text-muted-foreground text-sm">to</span>
        <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-auto" />
        <Button
          variant="secondary"
          size="sm"
          onClick={() => activeReport && loadReport(activeReport)}
          disabled={!activeReport || selected === "custom"}
        >
          <Filter className="h-4 w-4" />
          Apply
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-1 space-y-3">
          {REPORT_CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelected(cat.id)}
                className={cn(
                  "ds-card w-full flex items-start gap-4 p-4 text-left transition-all",
                  selected === cat.id
                    ? "border-primary/40 bg-primary/5 shadow-md"
                    : "hover:border-primary/20 hover:shadow-sm"
                )}
              >
                <div className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                  selected === cat.id ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary"
                )}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold">{cat.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{cat.description}</p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="xl:col-span-2 space-y-6">
          {category && (
            <>
              <ContentSection title={category.title} description={category.description}>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {category.reports.map((report) => (
                    <button
                      key={report}
                      type="button"
                      onClick={() => loadReport(report)}
                      disabled={selected === "custom"}
                      className={cn(
                        "flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-all",
                        activeReport === report
                          ? "border-primary bg-primary/5"
                          : "border-border bg-muted/30 hover:border-primary/30"
                      )}
                    >
                      <span className="text-sm font-medium">{report}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          loadReport(report);
                          setTimeout(exportCsv, 500);
                        }}
                        disabled={selected === "custom"}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </button>
                  ))}
                </div>
              </ContentSection>

              {selected === "custom" ? (
                <ContentSection title="Custom Reports" description="Coming in a future release">
                  <p className="text-sm text-muted-foreground py-8 text-center">
                    Custom report builder and scheduled exports are planned for a future release.
                  </p>
                </ContentSection>
              ) : (
                <>
                  <ContentSection
                    title={activeReport ?? "Report Data"}
                    description={`${reportData?.rows.length ?? 0} records`}
                    noPadding
                  >
                    {loading ? (
                      <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Loading report...
                      </div>
                    ) : (
                      <DataTable
                        embedded
                        exportTitle={activeReport ?? "Report"}
                        columns={columns}
                        data={reportData?.rows ?? []}
                        emptyMessage="No data for this report in the selected period."
                        defaultPageSize={15}
                      />
                    )}
                  </ContentSection>

                  <ChartCard title={`${category.title} Trend`} description="Last 6 months" height={280}>
                    <RevenueChart data={chartData} />
                  </ChartCard>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

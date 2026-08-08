import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  BedDouble,
  Building2,
  Calendar,
  DollarSign,
  Download,
  Dumbbell,
  FileDown,
  FileOutput,
  FileSpreadsheet,
  Filter,
  Loader2,
  Package,
  Pill,
  Printer,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
  UtensilsCrossed,
} from "lucide-react";
import { useSalesReportPrint } from "../hooks/useSalesReportPrint";
import { useReportPrint } from "../hooks/useReportPrint";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { ChartCard } from "@/components/data/ChartCard";
import { ProfitChart, RevenueChart, SalesTrendChart } from "@/components/data/charts/DashboardCharts";
import { DataTable, type Column } from "@/components/data/DataTable";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency } from "@/utils/cn";
import { reportsApi, type ReportPack, type ReportResult } from "@/services/api/reports";
import { AnimatePresence, motion, animate, useMotionValue, useTransform } from "framer-motion";

const REPORT_CATEGORIES = [
  {
    id: "sales",
    title: "Sales Reports",
    description: "Revenue, invoices, and sales performance by period",
    icon: DollarSign,
    reports: ["Daily Sales", "Products Sold", "Unpaid Receipts", "Customer Monthly", "Sales by Product", "Sales by Customer", "Tax Summary"],
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
    id: "gym",
    title: "Gym Reports",
    description: "Members, subscriptions, attendance, and classes",
    icon: Dumbbell,
    reports: ["Active Members", "Subscription Summary", "Attendance Log", "Class Bookings", "Plan Catalog"],
  },
  {
    id: "pharmacy",
    title: "Pharmacy Reports",
    description: "Batch stock, expiry, and FEFO dispenses",
    icon: Pill,
    reports: ["Batch Stock", "Expiring Soon", "FEFO Dispenses"],
  },
  {
    id: "hotel",
    title: "Hotel Reports",
    description: "Occupancy, in-house guests, and open folios",
    icon: BedDouble,
    reports: [
      "Room Occupancy",
      "In-House Guests",
      "Open Folios",
      "Arrivals & Departures",
    ],
  },
  {
    id: "restaurant",
    title: "Restaurant Reports",
    description: "Tables, open tickets, and menu catalog",
    icon: UtensilsCrossed,
    reports: ["Table Status", "Open Orders", "Orders by Status", "Menu Catalog"],
  },
  {
    id: "property",
    title: "Property Reports",
    description: "Units, housing/office leases, and pending charges",
    icon: Building2,
    reports: [
      "Unit Occupancy",
      "Units by Kind",
      "Housing Leases",
      "Office Leases",
      "Pending Charges",
    ],
  },
  {
    id: "custom",
    title: "Custom Reports",
    description: "Build and save custom report configurations",
    icon: FileSpreadsheet,
    reports: ["Report Builder", "Saved Reports"],
  },
];

const MONEY_HINTS = ["amount", "total", "revenue", "value", "cost", "price", "profit", "tax"];
const CHART_TABS = [
  { id: "revenue", label: "Revenue" },
  { id: "profit", label: "Profit vs Expenses" },
  { id: "momentum", label: "Momentum" },
] as const;
const COMPARE_MODES = [
  { id: "previous", label: "vs Previous Month" },
  { id: "average", label: "vs 3-Month Average" },
] as const;
const CATEGORY_THEMES = {
  sales: {
    badge: "bg-emerald-500/10 text-emerald-700 border-emerald-300/40",
    chipActive: "bg-emerald-600 text-white hover:bg-emerald-600",
  },
  inventory: {
    badge: "bg-sky-500/10 text-sky-700 border-sky-300/40",
    chipActive: "bg-sky-600 text-white hover:bg-sky-600",
  },
  purchases: {
    badge: "bg-violet-500/10 text-violet-700 border-violet-300/40",
    chipActive: "bg-violet-600 text-white hover:bg-violet-600",
  },
  customers: {
    badge: "bg-amber-500/10 text-amber-700 border-amber-300/40",
    chipActive: "bg-amber-600 text-white hover:bg-amber-600",
  },
  finance: {
    badge: "bg-indigo-500/10 text-indigo-700 border-indigo-300/40",
    chipActive: "bg-indigo-600 text-white hover:bg-indigo-600",
  },
  gym: {
    badge: "bg-orange-500/10 text-orange-700 border-orange-300/40",
    chipActive: "bg-orange-600 text-white hover:bg-orange-600",
  },
  pharmacy: {
    badge: "bg-teal-500/10 text-teal-700 border-teal-300/40",
    chipActive: "bg-teal-600 text-white hover:bg-teal-600",
  },
  hotel: {
    badge: "bg-rose-500/10 text-rose-700 border-rose-300/40",
    chipActive: "bg-rose-600 text-white hover:bg-rose-600",
  },
  restaurant: {
    badge: "bg-lime-500/10 text-lime-800 border-lime-300/40",
    chipActive: "bg-lime-600 text-white hover:bg-lime-600",
  },
  property: {
    badge: "bg-stone-500/10 text-stone-700 border-stone-300/40",
    chipActive: "bg-stone-700 text-white hover:bg-stone-700",
  },
  custom: {
    badge: "bg-muted text-foreground border-border",
    chipActive: "bg-primary text-primary-foreground",
  },
} as const;

function isMoneyColumn(col: string): boolean {
  const c = col.toLowerCase();
  return MONEY_HINTS.some((hint) => c.includes(hint));
}

function AnimatedMetricValue({
  value,
  formatter,
}: {
  value: number;
  formatter: (value: number) => string;
}) {
  const motionValue = useMotionValue(value);
  const rounded = useTransform(motionValue, (latest) => Math.round(latest));
  const [display, setDisplay] = useState(() => formatter(value));

  useEffect(() => {
    const controls = animate(motionValue, value, {
      type: "spring",
      stiffness: 95,
      damping: 20,
      mass: 0.8,
    });
    return () => controls.stop();
  }, [motionValue, value]);

  useEffect(() => {
    const unsub = rounded.on("change", (latest) => {
      setDisplay(formatter(latest));
    });
    return () => unsub();
  }, [rounded, formatter]);

  return <span>{display}</span>;
}

export function ReportsPage() {
  const [categories, setCategories] = useState(REPORT_CATEGORIES);
  const [selected, setSelected] = useState<string>("sales");
  const [activeReport, setActiveReport] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [reportData, setReportData] = useState<ReportResult | null>(null);
  const [chartData, setChartData] = useState<{ month: string; revenue: number; profit: number; expenses: number }[]>([]);
  const [chartTab, setChartTab] = useState<(typeof CHART_TABS)[number]["id"]>("revenue");
  const [compareMode, setCompareMode] = useState<(typeof COMPARE_MODES)[number]["id"]>("previous");
  const [compactMode, setCompactMode] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(false);

  const { printing: salesPrintBusy, printSalesReport, downloadSalesReport } = useSalesReportPrint(
    dateFrom,
    dateTo
  );
  const {
    printing: reportPrintBusy,
    printReportData,
    downloadReportData,
    printReport,
    downloadReport,
  } = useReportPrint(dateFrom, dateTo);

  const printBusy = salesPrintBusy || reportPrintBusy;
  const category = categories.find((c) => c.id === selected);

  useEffect(() => {
    reportsApi
      .catalog()
      .then((res) => {
        const iconById: Record<string, typeof DollarSign> = {
          sales: DollarSign,
          inventory: Package,
          purchases: TrendingUp,
          customers: Users,
          finance: BarChart3,
          gym: Dumbbell,
          pharmacy: Pill,
          hotel: BedDouble,
          restaurant: UtensilsCrossed,
          property: Building2,
        };
        const mapped = res.data.map((pack: ReportPack) => {
          return {
            id: pack.id,
            title: pack.title,
            description: pack.description,
            icon: iconById[pack.id] ?? BarChart3,
            reports: pack.reports,
          };
        });
        if (mapped.length) {
          setCategories([...mapped, REPORT_CATEGORIES.find((c) => c.id === "custom")!]);
        }
      })
      .catch(() => {
        setCategories(REPORT_CATEGORIES);
      });
  }, []);

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
            profit: d.profit ?? d.revenue ?? 0,
            expenses: d.expenses ?? 0,
          }))
        );
        setLastUpdatedAt(new Date());
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

  const rows = reportData?.rows ?? [];
  const columnsRaw = reportData?.columns ?? [];
  const numericColumns = useMemo(
    () =>
      columnsRaw.filter((col) =>
        rows.some((row) => typeof row[col] === "number")
      ),
    [columnsRaw, rows]
  );

  const summary = useMemo(() => {
    const recordCount = rows.length;
    const moneyCol = numericColumns.find((col) => isMoneyColumn(col));
    const moneyTotal = moneyCol
      ? rows.reduce((acc, row) => acc + (typeof row[moneyCol] === "number" ? Number(row[moneyCol]) : 0), 0)
      : null;
    const primaryLabel = columnsRaw[0];
    const uniquePrimary = primaryLabel
      ? new Set(rows.map((r) => String(r[primaryLabel] ?? "")).filter(Boolean)).size
      : 0;
    const monthlyTrend = chartData.length >= 2
      ? chartData[chartData.length - 1].revenue - chartData[chartData.length - 2].revenue
      : 0;

    return { recordCount, moneyTotal, uniquePrimary, monthlyTrend };
  }, [rows, numericColumns, columnsRaw, chartData]);

  const chartSeries = useMemo(() => {
    const revenueSeries = chartData.map((d) => ({ month: d.month, revenue: d.revenue }));
    const profitSeries = chartData.map((d) => ({ month: d.month, profit: d.profit, expenses: d.expenses }));
    const momentumSeries = chartData.map((d) => ({ month: d.month, sales: d.revenue, revenue: d.revenue }));
    return { revenueSeries, profitSeries, momentumSeries };
  }, [chartData]);
  const activeTheme = CATEGORY_THEMES[selected as keyof typeof CATEGORY_THEMES] ?? CATEGORY_THEMES.custom;

  const chartInsights = useMemo(() => {
    if (!chartData.length) {
      return { current: 0, baseline: 0, delta: 0, deltaPct: 0 };
    }

    const values =
      chartTab === "profit"
        ? chartData.map((d) => d.profit)
        : chartData.map((d) => d.revenue);
    const current = values[values.length - 1] ?? 0;
    let baseline = 0;
    if (compareMode === "previous") {
      baseline = values[values.length - 2] ?? 0;
    } else {
      const lastThree = values.slice(Math.max(0, values.length - 4), Math.max(0, values.length - 1));
      baseline = lastThree.length
        ? lastThree.reduce((acc, value) => acc + value, 0) / lastThree.length
        : 0;
    }
    const delta = current - baseline;
    const deltaPct = baseline === 0 ? 0 : (delta / baseline) * 100;
    return { current, baseline, delta, deltaPct };
  }, [chartData, chartTab, compareMode]);
  const chartAnnotations = useMemo(() => {
    if (!chartData.length) {
      return { peak: null as null | { month: string; value: number }, low: null as null | { month: string; value: number } };
    }
    const values =
      chartTab === "profit"
        ? chartData.map((d) => ({ month: d.month, value: d.profit }))
        : chartData.map((d) => ({ month: d.month, value: d.revenue }));
    const peak = values.reduce((best, item) => (item.value > best.value ? item : best), values[0]);
    const low = values.reduce((best, item) => (item.value < best.value ? item : best), values[0]);
    return { peak, low };
  }, [chartData, chartTab]);

  useEffect(() => {
    const applyMode = () => setCompactMode(window.innerWidth < 1280);
    applyMode();
    window.addEventListener("resize", applyMode);
    return () => window.removeEventListener("resize", applyMode);
  }, []);

  const columns: Column<Record<string, string | number>>[] = columnsRaw.map((col) => ({
    key: col,
    header: col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    cell: (r) => {
      const val = r[col];
      if (typeof val === "number" && isMoneyColumn(col)) return formatCurrency(val);
      if (typeof val === "number") return val.toLocaleString();
      return String(val ?? "");
    },
  }));

  const exportCsv = () => {
    if (!reportData?.rows.length || !activeReport || selected === "custom") return;
    void reportsApi
      .exportCsv({
        category: selected,
        report: activeReport,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
      .catch(() => {
        const header = reportData.columns.join(",");
        const rowsCsv = reportData.rows.map((r) =>
          reportData.columns.map((c) => JSON.stringify(r[c] ?? "")).join(",")
        );
        const blob = new Blob([[header, ...rowsCsv].join("\n")], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${selected}-${activeReport.replace(/\s+/g, "-").toLowerCase()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      });
  };

  return (
    <PageLayout
      title="Reports Intelligence"
      description="Professional analytics workspace with richer insights and premium exports."
      breadcrumbs={["Home", "Reports"]}
      backTo="/dashboard"
      backLabel="Dashboard"
    >
      <div className="ds-card-premium relative overflow-hidden border-border/60 px-5 py-4">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="secondary" className="gap-1">
            <Sparkles className="h-3.5 w-3.5" />
            Advanced Analytics
          </Badge>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Calendar className="h-4 w-4" />
            Date Range
          </div>
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-auto" />
          <span className="text-sm text-muted-foreground">to</span>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-auto" />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => activeReport && loadReport(activeReport)}
            disabled={!activeReport || selected === "custom"}
          >
            <Filter className="h-4 w-4" />
            Apply Filters
          </Button>
          {selected === "sales" && (
            <>
              <Button variant="secondary" size="sm" disabled={printBusy} onClick={() => void printSalesReport()}>
                {printBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileOutput className="h-4 w-4" />}
                Analytics Report
              </Button>
              <Button variant="ghost" size="sm" disabled={printBusy} onClick={() => void downloadSalesReport()}>
                <Download className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {selected !== "custom" && (
        <KpiGrid columns={4} className="mt-5">
          <KpiCard
            index={0}
            title="Records"
            value={summary.recordCount.toLocaleString()}
            icon={<BarChart3 className="h-5 w-5" />}
            accent="info"
          />
          <KpiCard
            index={1}
            title="Primary Metric"
            value={summary.moneyTotal != null ? formatCurrency(summary.moneyTotal) : "—"}
            icon={<DollarSign className="h-5 w-5" />}
            accent="success"
          />
          <KpiCard
            index={2}
            title={columnsRaw[0] ? `Unique ${columnsRaw[0].replace(/_/g, " ")}` : "Unique Values"}
            value={summary.uniquePrimary.toLocaleString()}
            icon={<Users className="h-5 w-5" />}
            accent="warning"
          />
          <KpiCard
            index={3}
            title="Last Trend Delta"
            value={formatCurrency(summary.monthlyTrend)}
            trend={summary.monthlyTrend === 0 ? "No change" : `${summary.monthlyTrend > 0 ? "+" : ""}${formatCurrency(Math.abs(summary.monthlyTrend))}`}
            trendUp={summary.monthlyTrend >= 0}
            icon={<TrendingUp className="h-5 w-5" />}
            accent="primary"
          />
        </KpiGrid>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="xl:col-span-4 space-y-3">
          {categories.map((cat) => {
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelected(cat.id)}
                className={cn(
                  "ds-card-premium w-full flex items-start gap-4 p-4 text-left transition-all duration-300",
                  selected === cat.id
                    ? "border-primary/40 bg-primary/5 shadow-elevated"
                    : "hover:border-primary/20 hover:shadow-sm"
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                    selected === cat.id ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary"
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold">{cat.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{cat.description}</p>
                </div>
              </button>
            );
          })}
          {selected !== "custom" && (
            <>
              <div className="ds-card-premium rounded-xl border border-border/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Executive Snapshot
                </p>
                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Active report</span>
                    <span className="font-semibold">{activeReport ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Rows analyzed</span>
                    <span className="font-semibold">{summary.recordCount.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Primary metric</span>
                    <span className="font-semibold">
                      {summary.moneyTotal != null ? formatCurrency(summary.moneyTotal) : "—"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="ds-card-premium rounded-xl border border-border/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Narrative Highlights
                </p>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2">
                    <p className="text-xs text-muted-foreground">Peak period</p>
                    <p className="font-semibold">
                      {chartAnnotations.peak
                        ? `${chartAnnotations.peak.month} · ${formatCurrency(chartAnnotations.peak.value)}`
                        : "No peak yet"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2">
                    <p className="text-xs text-muted-foreground">Lowest period</p>
                    <p className="font-semibold">
                      {chartAnnotations.low
                        ? `${chartAnnotations.low.month} · ${formatCurrency(chartAnnotations.low.value)}`
                        : "No low yet"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2">
                    <p className="text-xs text-muted-foreground">Last refresh</p>
                    <p className="font-semibold">
                      {lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : "Not loaded"}
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="xl:col-span-8 space-y-6">
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
                        "rounded-xl border px-4 py-3 text-left transition-all",
                        activeReport === report
                          ? "border-primary/40 bg-primary/5"
                          : "border-border bg-muted/20 hover:border-primary/30"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">{report}</span>
                        <div className="flex items-center gap-0.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            type="button"
                            title="Print report"
                            onClick={(e) => {
                              e.stopPropagation();
                              void printReport(selected, report);
                            }}
                            disabled={selected === "custom" || printBusy}
                          >
                            <Printer className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            type="button"
                            title="Download PDF"
                            onClick={(e) => {
                              e.stopPropagation();
                              void downloadReport(selected, report);
                            }}
                            disabled={selected === "custom" || printBusy}
                          >
                            <FileDown className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </ContentSection>

              {selected === "custom" ? (
                <ContentSection title="Custom Reports" description="Coming in a future release">
                  <p className="text-sm text-muted-foreground py-10 text-center">
                    Custom report builder, saved templates, and scheduled distribution are planned for the next release.
                  </p>
                </ContentSection>
              ) : (
                <>
                  <ContentSection
                    title={activeReport ?? "Report Data"}
                    description={`${rows.length} records`}
                    noPadding
                    action={
                      activeReport ? (
                        <div className="flex gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={printBusy || !rows.length}
                            onClick={() => void exportCsv()}
                          >
                            <Download className="h-4 w-4" />
                            CSV
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={printBusy}
                            onClick={() =>
                              reportData && void printReportData(reportData, activeReport)
                            }
                          >
                            {printBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Printer className="h-4 w-4" />}
                            Print
                          </Button>
                          <Button
                            size="sm"
                            disabled={printBusy}
                            onClick={() =>
                              reportData && void downloadReportData(reportData, activeReport)
                            }
                          >
                            {printBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
                            PDF
                          </Button>
                        </div>
                      ) : undefined
                    }
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
                        listPrint={false}
                        listPdf={false}
                        columns={columns}
                        data={rows}
                        emptyMessage="No data for this report in the selected period."
                        defaultPageSize={15}
                      />
                    )}
                  </ContentSection>

                  <ChartCard
                    title={`${category.title} Intelligence`}
                    description="Executive analytics view"
                    height={320}
                    action={
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {COMPARE_MODES.map((mode) => (
                          <Button
                            key={mode.id}
                            variant={compareMode === mode.id ? "default" : "secondary"}
                            size="sm"
                            className={cn(
                              "h-8",
                              compareMode === mode.id && activeTheme.chipActive,
                              compactMode && "px-2 text-xs"
                            )}
                            onClick={() => setCompareMode(mode.id)}
                          >
                            {compactMode ? mode.label.replace("vs ", "") : mode.label}
                          </Button>
                        ))}
                      </div>
                    }
                  >
                    <div className={cn("flex h-full flex-col gap-3 px-2 py-1", compactMode && "gap-2 px-1")}>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className={cn("text-xs", activeTheme.badge)}>
                          {category.title}
                        </Badge>
                        {CHART_TABS.map((tab) => (
                          <Button
                            key={tab.id}
                            size="sm"
                            variant={chartTab === tab.id ? "default" : "ghost"}
                            onClick={() => setChartTab(tab.id)}
                            className={cn(
                              "h-8 rounded-lg transition-all",
                              chartTab === tab.id && activeTheme.chipActive,
                              compactMode && "h-7 px-2 text-xs"
                            )}
                          >
                            {tab.label}
                          </Button>
                        ))}
                      </div>

                      <div className={cn("grid grid-cols-1 gap-2 sm:grid-cols-3", compactMode && "gap-1")}>
                        <motion.div
                          layout
                          className={cn("rounded-lg border border-border/70 bg-background/70 px-3 py-2", compactMode && "px-2 py-1.5")}
                        >
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Current</p>
                          <p className="text-sm font-semibold">
                            <AnimatedMetricValue value={chartInsights.current} formatter={formatCurrency} />
                          </p>
                        </motion.div>
                        <motion.div
                          layout
                          className={cn("rounded-lg border border-border/70 bg-background/70 px-3 py-2", compactMode && "px-2 py-1.5")}
                        >
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                            {compareMode === "previous" ? "Previous" : "3-Month Avg"}
                          </p>
                          <p className="text-sm font-semibold">
                            <AnimatedMetricValue value={chartInsights.baseline} formatter={formatCurrency} />
                          </p>
                        </motion.div>
                        <motion.div
                          layout
                          className={cn(
                            "rounded-lg border px-3 py-2",
                            compactMode && "px-2 py-1.5",
                            chartInsights.delta >= 0
                              ? "border-emerald-300/50 bg-emerald-500/10"
                              : "border-rose-300/50 bg-rose-500/10"
                          )}
                        >
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Trend</p>
                          <div className="flex items-center gap-1">
                            {chartInsights.delta >= 0 ? (
                              <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />
                            ) : (
                              <TrendingDown className="h-3.5 w-3.5 text-rose-600" />
                            )}
                            <p className="text-sm font-semibold">
                              {chartInsights.delta >= 0 ? "+" : "-"}
                              <AnimatedMetricValue
                                value={Math.abs(chartInsights.delta)}
                                formatter={formatCurrency}
                              />{" "}
                              ({chartInsights.deltaPct.toFixed(1)}%)
                            </p>
                          </div>
                        </motion.div>
                      </div>

                      <div className="min-h-0 flex-1">
                        <AnimatePresence mode="wait">
                          {chartTab === "revenue" && (
                            <motion.div
                              key="revenue"
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -8 }}
                              transition={{ duration: 0.22 }}
                              className="h-full"
                            >
                              <RevenueChart data={chartSeries.revenueSeries} />
                            </motion.div>
                          )}
                          {chartTab === "profit" && (
                            <motion.div
                              key="profit"
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -8 }}
                              transition={{ duration: 0.22 }}
                              className="h-full"
                            >
                              <ProfitChart data={chartSeries.profitSeries} />
                            </motion.div>
                          )}
                          {chartTab === "momentum" && (
                            <motion.div
                              key="momentum"
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -8 }}
                              transition={{ duration: 0.22 }}
                              className="h-full"
                            >
                              <SalesTrendChart data={chartSeries.momentumSeries} />
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                      <div className={cn("grid grid-cols-1 gap-2 sm:grid-cols-3", compactMode && "gap-1")}>
                        <div className="rounded-lg border border-border/70 bg-background/70 px-3 py-2">
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Peak</p>
                          <p className="text-sm font-semibold">
                            {chartAnnotations.peak
                              ? `${chartAnnotations.peak.month} · ${formatCurrency(chartAnnotations.peak.value)}`
                              : "—"}
                          </p>
                        </div>
                        <div className="rounded-lg border border-border/70 bg-background/70 px-3 py-2">
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Low</p>
                          <p className="text-sm font-semibold">
                            {chartAnnotations.low
                              ? `${chartAnnotations.low.month} · ${formatCurrency(chartAnnotations.low.value)}`
                              : "—"}
                          </p>
                        </div>
                        <div className="rounded-lg border border-border/70 bg-background/70 px-3 py-2">
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Last Updated</p>
                          <p className="text-sm font-semibold">
                            {lastUpdatedAt ? lastUpdatedAt.toLocaleString() : "Not loaded"}
                          </p>
                        </div>
                      </div>
                    </div>
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

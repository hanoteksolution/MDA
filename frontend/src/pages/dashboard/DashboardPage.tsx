import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  DollarSign,
  TrendingUp,
  Package,
  Wallet,
  AlertTriangle,
  ShoppingCart,
  Plus,
  Truck,
  BarChart3,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ChartCard } from "@/components/data/ChartCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { QuickActions } from "@/components/data/QuickActions";
import {
  SalesTrendChart,
  RevenueChart,
  ProfitChart,
} from "@/components/data/charts/DashboardCharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  dashboardApi,
  type DashboardLowStock,
  type DashboardTopProduct,
  type DashboardTransaction,
} from "@/services/api/dashboard";
import { formatCurrency } from "@/utils/cn";
import type { DashboardKPIs } from "@/types/models";

const topProductColumns: Column<DashboardTopProduct>[] = [
  { key: "name", header: "Product", cell: (r) => <span className="font-medium">{r.name}</span>, exportValue: (r) => r.name },
  { key: "sku", header: "SKU", cell: (r) => <span className="text-muted-foreground">{r.sku}</span>, exportValue: (r) => r.sku },
  { key: "sold", header: "Sold", cell: (r) => r.sold.toLocaleString(), exportValue: (r) => String(r.sold) },
  { key: "revenue", header: "Revenue", cell: (r) => formatCurrency(r.revenue), exportValue: (r) => formatCurrency(r.revenue) },
];

const transactionColumns: Column<DashboardTransaction>[] = [
  { key: "id", header: "Invoice", cell: (r) => <span className="font-medium text-primary">{r.id}</span>, exportValue: (r) => r.id },
  { key: "customer", header: "Customer", cell: (r) => r.customer, exportValue: (r) => r.customer },
  { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
  {
    key: "status",
    header: "Status",
    cell: (r) => (
      <Badge variant={r.status === "completed" || r.status === "paid" ? "success" : "warning"}>
        {r.status}
      </Badge>
    ),
    exportValue: (r) => r.status,
  },
  { key: "date", header: "Date", cell: (r) => <span className="text-muted-foreground">{r.date}</span>, exportValue: (r) => r.date },
];

const lowStockColumns: Column<DashboardLowStock>[] = [
  { key: "product", header: "Product", cell: (r) => <span className="font-medium">{r.product}</span>, exportValue: (r) => r.product },
  { key: "sku", header: "SKU", cell: (r) => <span className="text-muted-foreground">{r.sku}</span>, exportValue: (r) => r.sku },
  {
    key: "current",
    header: "Stock",
    cell: (r) => (
      <Badge variant={r.current === 0 ? "destructive" : "warning"}>
        {r.current} units
      </Badge>
    ),
    exportValue: (r) => `${r.current} units`,
  },
  { key: "minimum", header: "Min.", cell: (r) => r.minimum, exportValue: (r) => String(r.minimum) },
  { key: "warehouse", header: "Warehouse", cell: (r) => r.warehouse, exportValue: (r) => r.warehouse },
];

export function DashboardPage() {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [transactions, setTransactions] = useState<DashboardTransaction[]>([]);
  const [lowStock, setLowStock] = useState<DashboardLowStock[]>([]);
  const [topProducts, setTopProducts] = useState<DashboardTopProduct[]>([]);
  const [charts, setCharts] = useState<{
    sales_trend: { month: string; sales: number; revenue: number }[];
    revenue: { month: string; revenue: number }[];
    profit: { month: string; profit: number; expenses: number }[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("month");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      dashboardApi.kpis(period),
      dashboardApi.recentSales(),
      dashboardApi.lowStock(),
      dashboardApi.topProducts(period),
      dashboardApi.charts(),
    ])
      .then(([kpiRes, txRes, stockRes, topRes, chartRes]) => {
        setKpis(kpiRes.data);
        setTransactions(txRes.data.results);
        setLowStock(stockRes.data.results);
        setTopProducts(topRes.data);
        setCharts(chartRes.data);
      })
      .catch(() => {
        setKpis(null);
        setTransactions([]);
        setLowStock([]);
        setTopProducts([]);
        setCharts(null);
      })
      .finally(() => setLoading(false));
  }, [period]);

  const displayKpis = {
    total_sales: kpis?.total_sales ?? 0,
    revenue: kpis?.revenue ?? 0,
    cash_collected: kpis?.cash_collected ?? 0,
    profit: kpis?.profit ?? 0,
    expenses: kpis?.expenses ?? 0,
    inventory_value: kpis?.inventory_value ?? 0,
  };

  return (
    <PageLayout
      title="Executive Dashboard"
      description="Real-time overview of sales, revenue, inventory, and business performance."
      breadcrumbs={["Home", "Dashboard"]}
      actions={
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="h-10 w-[140px] border-border/70 bg-card/80 backdrop-blur-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Today</SelectItem>
            <SelectItem value="week">This Week</SelectItem>
            <SelectItem value="month">This Month</SelectItem>
            <SelectItem value="year">This Year</SelectItem>
          </SelectContent>
        </Select>
      }
    >
      <KpiGrid columns={5}>
        <KpiCard index={0} accent="primary" title="Total Sales" value={formatCurrency(displayKpis.total_sales)} icon={<DollarSign className="h-5 w-5" />} loading={loading} />
        <KpiCard index={1} accent="success" title="Cash Collected" value={formatCurrency(displayKpis.cash_collected)} icon={<TrendingUp className="h-5 w-5" />} loading={loading} />
        <KpiCard index={2} accent="info" title="Net Profit" value={formatCurrency(displayKpis.profit)} icon={<Wallet className="h-5 w-5" />} loading={loading} />
        <KpiCard index={3} accent="warning" title="Expenses" value={formatCurrency(displayKpis.expenses)} icon={<AlertTriangle className="h-5 w-5" />} trendUp={false} loading={loading} />
        <KpiCard index={4} accent="primary" title="Inventory Value" value={formatCurrency(displayKpis.inventory_value)} icon={<Package className="h-5 w-5" />} loading={loading} />
      </KpiGrid>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartCard index={0} title="Sales Trend" description="Monthly sales from invoices" className="xl:col-span-2" height={300}>
          <SalesTrendChart data={charts?.sales_trend ?? []} />
        </ChartCard>
        <ChartCard index={1} title="Revenue" description="Last 6 months" height={300}>
          <RevenueChart data={charts?.revenue ?? []} />
        </ChartCard>
      </div>

      <ChartCard index={2} title="Profit vs Expenses" description="From sales and purchases" height={280}>
        <ProfitChart data={charts?.profit ?? []} />
      </ChartCard>

      <ContentSection index={3} title="Quick Actions" description="Common tasks to get started">
        <QuickActions
          actions={[
            { label: "New Sale", description: "Open POS terminal", icon: <ShoppingCart className="h-5 w-5" />, to: "/pos", variant: "primary" },
            { label: "New Purchase", description: "Create purchase order", icon: <Truck className="h-5 w-5" />, to: "/purchases/new" },
            { label: "Add Product", description: "Add to catalog", icon: <Plus className="h-5 w-5" />, to: "/products/new" },
            { label: "View Reports", description: "Analytics & exports", icon: <BarChart3 className="h-5 w-5" />, to: "/reports" },
          ]}
        />
      </ContentSection>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ContentSection
          index={4}
          title="Recent Transactions"
          description="Latest invoices"
          noPadding
          action={
            <Button variant="ghost" size="sm" asChild>
              <Link to="/sales">View all</Link>
            </Button>
          }
        >
          <DataTable
            embedded
            exportTitle="Recent Transactions"
            columns={transactionColumns}
            data={transactions}
            loading={loading}
            emptyMessage="No invoices yet. Create a sale to see activity here."
            defaultPageSize={5}
          />
        </ContentSection>

        <ContentSection
          index={5}
          title="Low Stock Alerts"
          description="Products below minimum threshold"
          noPadding
          action={
            <Button variant="ghost" size="sm" asChild>
              <Link to="/inventory/stock">View inventory</Link>
            </Button>
          }
        >
          <DataTable
            embedded
            exportTitle="Low Stock Alerts"
            columns={lowStockColumns}
            data={lowStock}
            loading={loading}
            emptyMessage="All products are above minimum stock levels."
            defaultPageSize={5}
          />
        </ContentSection>
      </div>

      <ContentSection index={6} title="Top Products" description="Best sellers by invoice revenue" noPadding>
        <DataTable
          embedded
          exportTitle="Top Products"
          columns={topProductColumns}
          data={topProducts}
          loading={loading}
          emptyMessage="No sales data yet for this period."
          defaultPageSize={10}
        />
      </ContentSection>
    </PageLayout>
  );
}

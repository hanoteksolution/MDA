import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Wallet, TrendingUp, TrendingDown, PiggyBank, ArrowUpRight, ArrowDownRight,
  Plus, BookOpen,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { ChartCard } from "@/components/data/ChartCard";
import { ProfitChart } from "@/components/data/charts/DashboardCharts";
import { DataTable, type Column } from "@/components/data/DataTable";
import { EmptyState } from "@/components/layout/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/utils/cn";
import {
  financeApi,
  type FinanceAccount,
  type FinanceExpense,
  type FinanceSummary,
} from "@/services/api/finance";

const EXPENSE_STATUS: Record<string, "warning" | "secondary" | "success"> = {
  pending: "warning",
  approved: "secondary",
  paid: "success",
};

export function FinancePage() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    financeApi
      .summary("month")
      .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const accountColumns: Column<FinanceAccount>[] = [
    { key: "name", header: "Account", cell: (r) => <span className="font-medium">{r.name}</span>, exportValue: (r) => r.name },
    { key: "type", header: "Type", cell: (r) => <Badge variant="secondary">{r.type}</Badge>, exportValue: (r) => r.type },
    { key: "balance", header: "Balance", cell: (r) => formatCurrency(r.balance), exportValue: (r) => formatCurrency(r.balance) },
  ];

  const expenseColumns: Column<FinanceExpense>[] = [
    { key: "desc", header: "Description", cell: (r) => r.description, exportValue: (r) => r.description },
    { key: "category", header: "Category", cell: (r) => r.category, exportValue: (r) => r.category },
    { key: "date", header: "Date", cell: (r) => r.date, exportValue: (r) => r.date },
    { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={EXPENSE_STATUS[r.status] ?? "secondary"} className="capitalize">
          {r.status}
        </Badge>
      ),
      exportValue: (r) => r.status,
    },
  ];

  const kpis = data?.kpis;

  return (
    <PageLayout
      title="Finance"
      description="Accounts, journal entries, expenses, and profit analysis."
      breadcrumbs={["Home", "Finance"]}
      backTo="/dashboard"
      backLabel="Dashboard"
      actions={
        <Button asChild>
          <Link to="/purchases/new">
            <Plus className="h-4 w-4" />
            New Purchase
          </Link>
        </Button>
      }
    >
      <KpiGrid>
        <KpiCard title="Total Revenue" value={formatCurrency(kpis?.revenue ?? 0)} icon={<TrendingUp className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Total Expenses" value={formatCurrency(kpis?.expenses ?? 0)} icon={<TrendingDown className="h-5 w-5" />} trendUp={false} loading={loading} />
        <KpiCard title="Net Profit" value={formatCurrency(kpis?.net_profit ?? 0)} icon={<PiggyBank className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Cash Balance" value={formatCurrency(kpis?.cash_balance ?? 0)} icon={<Wallet className="h-5 w-5" />} loading={loading} />
      </KpiGrid>

      <TabNav
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "accounts", label: "Accounts" },
          { id: "expenses", label: "Expenses" },
          { id: "journal", label: "Journal" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "overview" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChartCard title="Revenue vs Expenses" description="Monthly from invoices & purchases" height={280}>
            <ProfitChart data={data?.chart ?? []} />
          </ChartCard>
          <ContentSection title="Recent Activity">
            {loading ? (
              <div className="h-40 animate-pulse rounded-xl bg-muted" />
            ) : !data?.activity.length ? (
              <p className="text-sm text-muted-foreground py-4">No financial activity recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {data.activity.map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-xl bg-muted/40 px-4 py-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${item.type === "in" ? "bg-primary/10 text-primary" : "bg-destructive/10 text-destructive"}`}>
                        {item.type === "in" ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                      </div>
                      <span className="text-sm font-medium truncate">{item.label}</span>
                    </div>
                    <span className={`text-sm font-semibold shrink-0 ${item.type === "in" ? "text-primary" : "text-destructive"}`}>
                      {item.type === "in" ? "+" : "-"}{formatCurrency(item.amount)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </ContentSection>
        </div>
      )}

      {tab === "accounts" && (
        <ContentSection title="Chart of Accounts" description="Derived from live sales, purchases, and inventory" noPadding>
          <DataTable
            embedded
            exportTitle="Finance Accounts"
            columns={accountColumns}
            data={data?.accounts ?? []}
            loading={loading}
            emptyMessage="No account data available."
            defaultPageSize={10}
          />
        </ContentSection>
      )}

      {tab === "expenses" && (
        <ContentSection title="Expenses" description="Purchase orders as business expenses" noPadding>
          {!loading && !data?.expenses.length ? (
            <EmptyState
              icon={<TrendingDown className="h-8 w-8" />}
              title="No expenses recorded"
              description="Received and ordered purchase orders appear here as expenses."
            />
          ) : (
            <DataTable embedded exportTitle="Expenses" columns={expenseColumns} data={data?.expenses ?? []} loading={loading} defaultPageSize={10} />
          )}
        </ContentSection>
      )}

      {tab === "journal" && (
        <ContentSection title="Journal Entries" description="Double-entry bookkeeping records">
          <EmptyState
            icon={<BookOpen className="h-8 w-8" />}
            title="Journal module"
            description="Full journal entries will be available in a future release. Use Accounts and Expenses tabs for live financial data."
          />
        </ContentSection>
      )}
    </PageLayout>
  );
}

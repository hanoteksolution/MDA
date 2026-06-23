import { useEffect, useMemo, useState } from "react";
import { Users, TrendingUp, DollarSign, LogIn, ClipboardPen } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  platformApi,
  staffPerformanceApi,
  type PlatformTenantRow,
  type StaffPerformanceRow,
} from "@/services/api/platform";
import { RatingBadge, StaffEvaluationPanel } from "@/modules/platform/components/StaffEvaluationPanel";
import { useAuthStore } from "@/store/authStore";
import { formatCurrency } from "@/utils/cn";

export function StaffPerformancePage() {
  const user = useAuthStore((s) => s.user);
  const [rows, setRows] = useState<StaffPerformanceRow[]>([]);
  const [shops, setShops] = useState<PlatformTenantRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("month");
  const [shopFilter, setShopFilter] = useState<string>("all");
  const [selected, setSelected] = useState<StaffPerformanceRow | null>(null);

  const multiShop = shops.length > 1;
  const showShopColumn = multiShop && (shopFilter === "all" || rows.some((r) => r.shop_name));

  useEffect(() => {
    if (user?.managed_shop_group || user?.permissions?.includes("platform.view")) {
      platformApi
        .tenants(period)
        .then((res) => setShops(res.data))
        .catch(() => setShops([]));
    }
  }, [user, period]);

  const load = () => {
    setLoading(true);
    const params: { period: string; tenant_id?: string; all_shops?: boolean } = { period };
    if (multiShop) {
      if (shopFilter === "all") {
        params.all_shops = true;
      } else {
        params.tenant_id = shopFilter;
      }
    }
    staffPerformanceApi
      .list(params)
      .then((res) => setRows(res.data))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    setSelected(null);
  }, [period, shopFilter, multiShop]);

  const totals = rows.reduce(
    (acc, r) => ({
      sales: acc.sales + r.sales_count,
      revenue: acc.revenue + r.total_sales,
      cash: acc.cash + r.cash_collected,
      rated: acc.rated + (r.evaluation?.rating ? 1 : 0),
    }),
    { sales: 0, revenue: 0, cash: 0, rated: 0 }
  );

  const handleSaved = (staffId: string, rating: number, notes: string) => {
    setRows((current) =>
      current.map((row) =>
        row.user_id === staffId
          ? {
              ...row,
              evaluation: {
                ...(row.evaluation ?? {
                  id: "",
                  staff_id: staffId,
                  period,
                  period_start: "",
                  evaluator_id: "",
                  evaluator_name: "You",
                  updated_at: new Date().toISOString(),
                }),
                rating,
                notes,
                updated_at: new Date().toISOString(),
              },
            }
          : row
      )
    );
    setSelected(null);
  };

  const columns: Column<StaffPerformanceRow>[] = useMemo(() => {
    const base: Column<StaffPerformanceRow>[] = [];
    if (showShopColumn) {
      base.push({
        key: "shop",
        header: "Shop",
        cell: (r) => r.shop_name ?? "—",
        exportValue: (r) => r.shop_name ?? "",
      });
    }
    base.push(
      { key: "name", header: "Staff", cell: (r) => <span className="font-medium">{r.full_name}</span>, exportValue: (r) => r.full_name },
      { key: "role", header: "Role", cell: (r) => r.role },
      { key: "branch", header: "Branch", cell: (r) => r.branch },
      { key: "sales_count", header: "Sales", cell: (r) => r.sales_count.toLocaleString() },
      { key: "total_sales", header: "Revenue", cell: (r) => formatCurrency(r.total_sales) },
      { key: "cash_collected", header: "Cash", cell: (r) => formatCurrency(r.cash_collected) },
      { key: "average_sale", header: "Avg Sale", cell: (r) => formatCurrency(r.average_sale) },
      { key: "login_sessions", header: "Logins", cell: (r) => r.login_sessions },
      {
        key: "rating",
        header: "Rating",
        cell: (r) => <RatingBadge rating={r.evaluation?.rating} />,
        exportValue: (r) => (r.evaluation?.rating ? `${r.evaluation.rating}/5` : "Not rated"),
      },
      {
        key: "notes",
        header: "Notes",
        cell: (r) => (
          <span className="line-clamp-2 max-w-[220px] text-sm text-muted-foreground">
            {r.evaluation?.notes || "—"}
          </span>
        ),
        exportValue: (r) => r.evaluation?.notes || "",
      },
      {
        key: "actions",
        header: "",
        exportable: false,
        cell: (r) => (
          <Button variant="secondary" size="sm" onClick={() => setSelected(r)}>
            <ClipboardPen className="h-4 w-4" />
            Evaluate
          </Button>
        ),
      }
    );
    return base;
  }, [showShopColumn]);

  const groupName = user?.managed_shop_group?.name;

  return (
    <PageLayout
      title="Staff Performance"
      description={
        groupName
          ? `Compare staff across your shops (${groupName}).`
          : "Evaluate shop workers by sales metrics, manager ratings, and notes."
      }
      breadcrumbs={["Home", "Staff Performance"]}
      actions={
        <div className="flex flex-wrap gap-2">
          {multiShop && (
            <Select value={shopFilter} onValueChange={setShopFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All shops" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All shops</SelectItem>
                {shops.map((shop) => (
                  <SelectItem key={shop.id} value={shop.id}>
                    {shop.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="year">This Year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      }
    >
      <KpiGrid columns={5}>
        <KpiCard index={0} title="Active Staff" value={rows.length.toLocaleString()} icon={<Users className="h-5 w-5" />} loading={loading} />
        <KpiCard index={1} title="Total Sales" value={totals.sales.toLocaleString()} icon={<TrendingUp className="h-5 w-5" />} loading={loading} />
        <KpiCard index={2} title="Revenue" value={formatCurrency(totals.revenue)} icon={<DollarSign className="h-5 w-5" />} loading={loading} />
        <KpiCard index={3} title="Cash Collected" value={formatCurrency(totals.cash)} icon={<LogIn className="h-5 w-5" />} loading={loading} />
        <KpiCard index={4} title="Evaluated" value={`${totals.rated}/${rows.length || 0}`} icon={<ClipboardPen className="h-5 w-5" />} loading={loading} />
      </KpiGrid>

      {selected && (
        <StaffEvaluationPanel
          staff={selected}
          period={period}
          onSaved={handleSaved}
          onClose={() => setSelected(null)}
        />
      )}

      <DataTable
        exportTitle="Staff Performance"
        columns={columns}
        data={rows}
        loading={loading}
        emptyMessage="No staff activity for this period."
        defaultPageSize={15}
      />
    </PageLayout>
  );
}

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Clock3,
  MapPin,
  Package,
  RefreshCw,
  ShoppingCart,
  Users,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import { PlatformProfileHero } from "@/components/platform/PlatformProfileHero";
import {
  platformApi,
  type PlatformShopOverview,
  type PlatformShopProduct,
  type PlatformShopSale,
  type StaffPerformanceRow,
} from "@/services/api/platform";
import { cn, formatCurrency } from "@/utils/cn";

type Tab = "overview" | "products" | "sales" | "users" | "performance";

export function PlatformShopDetailPage() {
  const { shopId } = useParams<{ shopId: string }>();
  const [data, setData] = useState<PlatformShopOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("month");
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (!shopId) return;
    setLoading(true);
    setError(null);
    platformApi
      .tenantDetail(shopId, period)
      .then((res) => setData(res.data))
      .catch((err) => {
        setData(null);
        setError(err instanceof Error ? err.message : "Failed to load shop.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [shopId, period]);

  const tenant = data?.tenant;
  const groupId = tenant?.shop_group_id;
  const products = (data?.catalog?.products || []) as PlatformShopProduct[];
  const sales = (data?.recent_sales || []) as PlatformShopSale[];
  const users = data?.users || [];
  const staff = (data?.staff_performance || []) as StaffPerformanceRow[];
  const synced = Boolean(tenant?.last_synced_at);

  const productCols: Column<PlatformShopProduct>[] = [
    { key: "name", header: "Product", cell: (r) => <span className="font-medium">{r.name}</span> },
    { key: "sku", header: "SKU", cell: (r) => r.sku || "—" },
    { key: "qty", header: "Qty", cell: (r) => String(r.quantity) },
    { key: "price", header: "Price", cell: (r) => formatCurrency(r.unit_price) },
  ];

  const saleCols: Column<PlatformShopSale>[] = [
    { key: "number", header: "Invoice", cell: (r) => <span className="font-mono text-sm">{r.invoice_number}</span> },
    { key: "customer", header: "Customer", cell: (r) => r.customer_name },
    { key: "date", header: "Date", cell: (r) => r.issue_date || "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    { key: "total", header: "Total", cell: (r) => formatCurrency(r.total_amount) },
    { key: "cashier", header: "Cashier", cell: (r) => r.cashier || "—" },
  ];

  const userCols: Column<(typeof users)[number]>[] = [
    {
      key: "user",
      header: "User",
      cell: (r) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-xs font-semibold text-primary">
            {(r.full_name || r.username).slice(0, 1).toUpperCase()}
          </div>
          <div>
            <p className="font-medium">{r.full_name}</p>
            <p className="text-xs text-muted-foreground">@{r.username}</p>
          </div>
        </div>
      ),
    },
    { key: "email", header: "Email", cell: (r) => r.email || "—" },
    { key: "role", header: "Role", cell: (r) => r.role || "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.is_active ? "success" : "secondary"}>
          {r.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
  ];

  const staffCols: Column<StaffPerformanceRow>[] = [
    { key: "name", header: "Staff", cell: (r) => r.full_name || r.username },
    { key: "role", header: "Role", cell: (r) => r.role || "—" },
    { key: "sales", header: "Sales", cell: (r) => String(r.sales_count) },
    { key: "revenue", header: "Revenue", cell: (r) => formatCurrency(r.total_sales) },
    { key: "cash", header: "Cash", cell: (r) => formatCurrency(r.cash_collected) },
  ];

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "products", label: "Products", count: data?.catalog?.products_count },
    { id: "sales", label: "Sales", count: sales.length },
    { id: "users", label: "Users", count: users.length },
    { id: "performance", label: "Performance", count: staff.length },
  ];

  return (
    <PageLayout
      title={tenant?.name || "Shop"}
      description="Live shop profile across catalog, sales, users, and staff"
      breadcrumbs={[
        "Home",
        "Platform",
        "Tenants",
        tenant?.shop_group_name || "Tenant",
        tenant?.name || "Shop",
      ]}
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to={groupId ? `/platform/tenants/${groupId}` : "/platform/tenants"}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Link>
          </Button>
          <select
            className="h-9 rounded-xl border border-border/70 bg-card px-3 text-sm shadow-sm"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="today">Today</option>
            <option value="week">This week</option>
            <option value="month">This month</option>
            <option value="year">This year</option>
          </select>
          <Button variant="secondary" onClick={load}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      }
    >
      <div className="platform-shell space-y-6">
        <PlatformCloudNotice />

        {error && (
          <p className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        )}

        <PlatformProfileHero
          monogram={tenant?.name || "S"}
          title={tenant?.name || (loading ? "Loading…" : "Shop")}
          subtitle={
            tenant
              ? `${tenant.shop_group_name || "Ungrouped"} · ${tenant.slug}`
              : undefined
          }
          status={
            tenant
              ? {
                  label: tenant.is_active ? "Active shop" : "Inactive",
                  tone: tenant.is_active ? "success" : "neutral",
                }
              : undefined
          }
          meta={[
            {
              label: "Sync",
              value: synced
                ? new Date(tenant!.last_synced_at!).toLocaleString()
                : "Never synced",
            },
            ...(data?.branch?.name ? [{ label: "Branch", value: data.branch.name }] : []),
            ...(data?.subscription?.plan
              ? [{ label: "Plan", value: data.subscription.plan }]
              : []),
          ]}
        />

        <KpiGrid>
          <KpiCard
            title="Sales"
            value={String(data?.kpis?.total_sales ?? 0)}
            icon={<ShoppingCart className="h-5 w-5" />}
            loading={loading}
            index={0}
            accent="primary"
          />
          <KpiCard
            title="Revenue"
            value={formatCurrency(Number(data?.kpis?.revenue ?? 0))}
            icon={<ShoppingCart className="h-5 w-5" />}
            loading={loading}
            index={1}
            accent="success"
          />
          <KpiCard
            title="Products"
            value={String(data?.catalog?.products_count ?? 0)}
            icon={<Package className="h-5 w-5" />}
            loading={loading}
            index={2}
            accent="info"
          />
          <KpiCard
            title="Users"
            value={String(users.length)}
            icon={<Users className="h-5 w-5" />}
            loading={loading}
            index={3}
            accent="warning"
          />
        </KpiGrid>

        <div className="flex flex-wrap gap-1.5 rounded-2xl border border-border/60 bg-muted/30 p-1.5">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={cn(
                "relative rounded-xl px-4 py-2.5 text-sm font-medium transition-colors",
                tab === item.id
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {item.label}
              {item.count != null && (
                <span
                  className={cn(
                    "ml-2 text-xs",
                    tab === item.id ? "text-primary" : "text-muted-foreground"
                  )}
                >
                  {item.count}
                </span>
              )}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
          >
            {tab === "overview" && (
              <div className="grid gap-4 lg:grid-cols-5">
                <div className="platform-panel space-y-1 p-6 lg:col-span-3">
                  <p className="mb-2 text-sm font-semibold tracking-tight">Shop details</p>
                  <div className="platform-meta-row">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant={tenant?.is_active ? "success" : "secondary"}>
                      {tenant?.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <div className="platform-meta-row">
                    <span className="text-muted-foreground">Email</span>
                    <span className="font-medium">{tenant?.contact_email || "—"}</span>
                  </div>
                  <div className="platform-meta-row">
                    <span className="text-muted-foreground">Phone</span>
                    <span className="font-medium">{tenant?.contact_phone || "—"}</span>
                  </div>
                  <div className="platform-meta-row">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5" /> Branch
                    </span>
                    <span className="font-medium">{data?.branch?.name || "—"}</span>
                  </div>
                  <div className="platform-meta-row">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      {synced ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
                      Last sync
                    </span>
                    <span className="font-medium">
                      {synced ? new Date(tenant!.last_synced_at!).toLocaleString() : "Never"}
                    </span>
                  </div>
                </div>

                <div className="platform-panel relative overflow-hidden p-6 lg:col-span-2">
                  <div className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />
                  <p className="mb-4 text-sm font-semibold tracking-tight">Subscription</p>
                  {data?.subscription ? (
                    <div className="space-y-4">
                      <div>
                        <p className="text-3xl font-semibold tracking-tight">
                          {formatCurrency(
                            data.subscription.monthly_fee ?? data.subscription.monthly_price
                          )}
                        </p>
                        <p className="text-xs text-muted-foreground">Monthly fee · {data.subscription.plan}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-xl bg-muted/40 px-3 py-3">
                          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Status</p>
                          <p className="mt-1 text-sm font-semibold capitalize">{data.subscription.status}</p>
                        </div>
                        <div className="rounded-xl bg-muted/40 px-3 py-3">
                          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Expires</p>
                          <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                            <Clock3 className="h-3.5 w-3.5 text-muted-foreground" />
                            {data.subscription.expires_at || "—"}
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Inventory {formatCurrency(data?.catalog?.stock_value ?? 0)} · Low stock{" "}
                        {data?.catalog?.low_stock ?? 0}
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No subscription assigned.</p>
                  )}
                </div>
              </div>
            )}

            {tab === "products" && (
              <DataTable
                columns={productCols}
                data={products}
                loading={loading}
                exportTitle={`${tenant?.name || "Shop"} products`}
                searchPlaceholder="Search products..."
              />
            )}

            {tab === "sales" && (
              <DataTable
                columns={saleCols}
                data={sales}
                loading={loading}
                exportTitle={`${tenant?.name || "Shop"} sales`}
                searchPlaceholder="Search sales..."
              />
            )}

            {tab === "users" && (
              <DataTable
                columns={userCols}
                data={users}
                loading={loading}
                exportTitle={`${tenant?.name || "Shop"} users`}
                searchPlaceholder="Search users..."
              />
            )}

            {tab === "performance" && (
              <div className="space-y-3">
                <DataTable
                  columns={staffCols}
                  data={staff}
                  loading={loading}
                  exportTitle={`${tenant?.name || "Shop"} performance`}
                  searchPlaceholder="Search staff..."
                />
                <p className="text-xs text-muted-foreground">
                  For ratings and evaluations, open{" "}
                  <Link className="font-medium text-primary underline-offset-2 hover:underline" to="/staff-performance">
                    Staff Performance
                  </Link>
                  .
                </p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </PageLayout>
  );
}

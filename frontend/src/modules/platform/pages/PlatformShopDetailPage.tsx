import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Clock3,
  MapPin,
  Package,
  Plus,
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
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import { PlatformProfileHero } from "@/components/platform/PlatformProfileHero";
import { appDialog } from "@/components/feedback/AppDialog";
import {
  platformApi,
  type PlatformShopOverview,
  type PlatformShopProduct,
  type PlatformShopSale,
  type StaffPerformanceRow,
} from "@/services/api/platform";
import { cn, formatCurrency } from "@/utils/cn";

type Tab = "overview" | "modules" | "products" | "sales" | "users" | "performance";

const SHOP_USER_ROLES = [
  { slug: "admin", name: "Shop Admin (desktop POS)" },
  { slug: "cashier", name: "Cashier (desktop POS)" },
  { slug: "branch_manager", name: "Branch Manager" },
  { slug: "accountant", name: "Accountant" },
  { slug: "inventory_manager", name: "Inventory Manager" },
  { slug: "futsal_manager", name: "Futsal Manager" },
];

const EMPTY_USER_FORM = {
  username: "",
  password: "",
  email: "",
  first_name: "",
  last_name: "",
  role_slug: "admin",
};

export function PlatformShopDetailPage() {
  const { shopId } = useParams<{ shopId: string }>();
  const [data, setData] = useState<PlatformShopOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("month");
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState<string | null>(null);
  const [showAddUser, setShowAddUser] = useState(false);
  const [savingUser, setSavingUser] = useState(false);
  const [userForm, setUserForm] = useState(EMPTY_USER_FORM);
  const [userFormError, setUserFormError] = useState("");
  const [moduleItems, setModuleItems] = useState<
    {
      code: string;
      name: string;
      enabled: boolean;
      category: string;
      dependencies?: string[];
      features?: Record<string, boolean>;
      feature_catalog?: { code: string; name: string; is_default?: boolean }[];
    }[]
  >([]);
  const [moduleBusy, setModuleBusy] = useState(false);
  const [moduleMsg, setModuleMsg] = useState<string | null>(null);

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

  const loadModules = () => {
    if (!shopId) return;
    platformApi
      .tenantModules(shopId)
      .then((res) => setModuleItems(res.data.items ?? []))
      .catch(() => setModuleItems([]));
  };

  useEffect(() => {
    load();
  }, [shopId, period]);

  useEffect(() => {
    if (tab === "modules") loadModules();
  }, [tab, shopId]);

  const toggleModule = (code: string) => {
    setModuleItems((prev) =>
      prev.map((m) => (m.code === code ? { ...m, enabled: !m.enabled } : m))
    );
  };

  const toggleFeature = (moduleCode: string, feature: string) => {
    setModuleItems((prev) =>
      prev.map((m) => {
        if (m.code !== moduleCode) return m;
        const next = { ...(m.features || {}), [feature]: !(m.features?.[feature] !== false) };
        if (feature === "batches" && !next.batches) next.expiry_alerts = false;
        return { ...m, features: next };
      })
    );
  };

  const moduleGaps = useMemo(() => {
    const enabled = new Set(moduleItems.filter((m) => m.enabled).map((m) => m.code));
    return moduleItems
      .filter((m) => m.enabled && (m.dependencies || []).some((d) => !enabled.has(d)))
      .map((m) => ({
        code: m.code,
        missing: (m.dependencies || []).filter((d) => !enabled.has(d)),
      }));
  }, [moduleItems]);

  const saveModules = async () => {
    if (!shopId) return;
    setModuleBusy(true);
    setModuleMsg(null);
    try {
      const enabled = moduleItems.filter((m) => m.enabled).map((m) => m.code);
      const module_features: Record<string, Record<string, boolean>> = {};
      for (const m of moduleItems) {
        if (m.enabled && m.features && Object.keys(m.features).length) {
          module_features[m.code] = m.features;
        }
      }
      const res = await platformApi.updateTenantModules(shopId, enabled, module_features);
      setModuleItems(res.data.items ?? []);
      setModuleMsg("Modules saved. Dependencies may auto-enable required modules.");
    } catch (err) {
      setModuleMsg(err instanceof Error ? err.message : "Could not update modules.");
      loadModules();
    } finally {
      setModuleBusy(false);
    }
  };

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId) return;
    setUserFormError("");
    if (!userForm.username.trim()) {
      setUserFormError("Username is required.");
      return;
    }
    if (userForm.password.length < 8) {
      setUserFormError("Password must be at least 8 characters.");
      return;
    }
    setSavingUser(true);
    try {
      const res = await platformApi.createTenantUser(shopId, {
        username: userForm.username.trim(),
        password: userForm.password,
        email: userForm.email.trim() || undefined,
        first_name: userForm.first_name.trim() || undefined,
        last_name: userForm.last_name.trim() || undefined,
        role_slug: userForm.role_slug,
      });
      setUserForm(EMPTY_USER_FORM);
      setShowAddUser(false);
      load();
      await appDialog.alert(
        `User created. Desktop login: ${res.data.username}. Use Settings → Connection (shop slug + sync secret), then sign in once online.`,
        { tone: "success", title: "Shop user ready" }
      );
    } catch (err) {
      setUserFormError(err instanceof Error ? err.message : "Could not create user.");
    } finally {
      setSavingUser(false);
    }
  };

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
    { id: "modules", label: "Modules", count: moduleItems.filter((m) => m.enabled).length || undefined },
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
                      {tenant?.status || (tenant?.is_active ? "Active" : "Inactive")}
                    </Badge>
                  </div>
                  <div className="platform-meta-row">
                    <span className="text-muted-foreground">Business type</span>
                    <span className="font-medium">
                      {(tenant?.business_type as { name?: string } | undefined)?.name ||
                        tenant?.business_type_code ||
                        "—"}
                    </span>
                  </div>
                  <div className="platform-meta-row">
                    <span className="text-muted-foreground">Domain</span>
                    <span className="font-medium font-mono text-xs">
                      {(tenant?.primary_domain as { domain?: string } | undefined)?.domain ||
                        tenant?.slug ||
                        "—"}
                    </span>
                  </div>
                  <div className="platform-meta-row">
                    <span className="text-muted-foreground">Currency</span>
                    <span className="font-medium">{tenant?.currency || "—"}</span>
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

            {tab === "modules" && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground">
                    Enable capabilities for this tenant. Required dependencies are added automatically.
                  </p>
                  <div className="flex gap-2">
                    <Button type="button" variant="secondary" size="sm" onClick={loadModules}>
                      Refresh
                    </Button>
                    <Button type="button" size="sm" onClick={saveModules} disabled={moduleBusy}>
                      {moduleBusy ? "Saving…" : "Save modules"}
                    </Button>
                  </div>
                </div>
                {moduleMsg ? <p className="text-sm text-muted-foreground">{moduleMsg}</p> : null}
                {moduleGaps.length ? (
                  <p className="text-sm text-amber-700 dark:text-amber-400">
                    Unusable until dependencies are enabled:{" "}
                    {moduleGaps.map((g) => `${g.code} needs ${g.missing.join(", ")}`).join("; ")}.
                  </p>
                ) : null}
                <div className="grid gap-2 sm:grid-cols-2">
                  {moduleItems.map((m) => (
                    <div
                      key={m.code}
                      className="flex items-start gap-3 rounded-xl border border-border/60 px-4 py-3"
                    >
                      <input
                        type="checkbox"
                        className="mt-1 cursor-pointer"
                        checked={m.enabled}
                        onChange={() => toggleModule(m.code)}
                      />
                      <span>
                        <span className="font-medium">{m.name}</span>
                        <span className="ml-2 font-mono text-xs text-muted-foreground">{m.code}</span>
                        <span className="mt-0.5 block text-xs text-muted-foreground capitalize">
                          {m.category}
                          {m.dependencies?.length
                            ? ` · needs ${m.dependencies.join(", ")}`
                            : ""}
                        </span>
                        {m.enabled && m.feature_catalog?.length ? (
                          <span className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                            {m.feature_catalog.map((f) => (
                              <label
                                key={f.code}
                                className="flex items-center gap-1 text-xs font-normal normal-case text-foreground"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <input
                                  type="checkbox"
                                  checked={m.features?.[f.code] !== false}
                                  disabled={f.code === "expiry_alerts" && m.features?.batches === false}
                                  onChange={() => toggleFeature(m.code, f.code)}
                                />
                                {f.name}
                              </label>
                            ))}
                          </span>
                        ) : null}
                      </span>
                    </div>
                  ))}
                </div>
                {!moduleItems.length ? (
                  <p className="text-sm text-muted-foreground">No modules loaded.</p>
                ) : null}
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
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground">
                    Create a Shop Admin or Cashier for the desktop app (offline POS). Share username and password securely.
                  </p>
                  <Button
                    type="button"
                    onClick={() => {
                      setShowAddUser((v) => !v);
                      setUserFormError("");
                    }}
                  >
                    <Plus className="h-4 w-4" />
                    {showAddUser ? "Cancel" : "Add user"}
                  </Button>
                </div>

                {showAddUser && (
                  <form
                    onSubmit={createUser}
                    className="platform-panel space-y-4 p-5"
                  >
                    <div>
                      <p className="text-sm font-semibold">New shop user</p>
                      <p className="text-xs text-muted-foreground">
                        After creating, connect the desktop app with this shop&apos;s slug and sync secret, then sign in online once.
                      </p>
                    </div>
                    {userFormError && (
                      <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                        {userFormError}
                      </p>
                    )}
                    <FormGrid>
                      <FormField label="Username" required>
                        <Input
                          required
                          value={userForm.username}
                          onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                          placeholder="e.g. somfutsal_admin"
                          autoComplete="off"
                        />
                      </FormField>
                      <FormField label="Password" required hint="Minimum 8 characters">
                        <Input
                          required
                          type="password"
                          minLength={8}
                          value={userForm.password}
                          onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                          autoComplete="new-password"
                        />
                      </FormField>
                      <FormField label="First name">
                        <Input
                          value={userForm.first_name}
                          onChange={(e) => setUserForm({ ...userForm, first_name: e.target.value })}
                        />
                      </FormField>
                      <FormField label="Last name">
                        <Input
                          value={userForm.last_name}
                          onChange={(e) => setUserForm({ ...userForm, last_name: e.target.value })}
                        />
                      </FormField>
                      <FormField label="Email">
                        <Input
                          type="email"
                          value={userForm.email}
                          onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                        />
                      </FormField>
                      <FormField label="Role" required>
                        <Select
                          value={userForm.role_slug}
                          onValueChange={(v) => setUserForm({ ...userForm, role_slug: v })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {SHOP_USER_ROLES.map((role) => (
                              <SelectItem key={role.slug} value={role.slug}>
                                {role.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormField>
                    </FormGrid>
                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          setShowAddUser(false);
                          setUserFormError("");
                        }}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" loading={savingUser}>
                        Create user
                      </Button>
                    </div>
                  </form>
                )}

                <DataTable
                  columns={userCols}
                  data={users}
                  loading={loading}
                  exportTitle={`${tenant?.name || "Shop"} users`}
                  searchPlaceholder="Search users..."
                />
              </div>
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

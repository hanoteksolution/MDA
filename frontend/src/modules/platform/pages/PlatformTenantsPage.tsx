import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Building2, ChevronRight, Plus, RefreshCw, Store, Users } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import { platformApi, type PlatformShopGroupRow } from "@/services/api/platform";
import { useAuthStore } from "@/store/authStore";
import { formatCurrency } from "@/utils/cn";

export function PlatformTenantsPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const isGlobal =
    Boolean(user?.is_super_admin) ||
    Boolean(user?.is_platform_admin) ||
    Boolean(user?.is_superuser) ||
    user?.role?.slug === "super_admin" ||
    user?.role?.slug === "platform_admin";
  const canCreate = isGlobal;
  const [rows, setRows] = useState<PlatformShopGroupRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("month");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", contact_email: "", contact_phone: "" });
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    platformApi
      .shopGroups({ enrich: true, period })
      .then((res) => setRows(res.data || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [period]);

  useEffect(() => {
    if (!loading && !isGlobal && rows.length === 1 && user?.managed_shop_group) {
      const only = rows[0];
      if (only?.id) navigate(`/platform/tenants/${only.id}`, { replace: true });
    }
  }, [loading, isGlobal, rows, user?.managed_shop_group, navigate]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await platformApi.createShopGroup(form);
      setCreating(false);
      setForm({ name: "", contact_email: "", contact_phone: "" });
      navigate(`/platform/tenants/${res.data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create tenant.");
    }
  };

  const totals = rows.reduce(
    (acc, r) => ({
      tenants: acc.tenants + 1,
      shops: acc.shops + (r.totals?.shops ?? r.shop_count ?? 0),
      revenue: acc.revenue + (r.totals?.revenue ?? 0),
      users: acc.users + (r.totals?.users ?? 0),
    }),
    { tenants: 0, shops: 0, revenue: 0, users: 0 }
  );

  return (
    <PageLayout
      title={isGlobal ? "Tenants" : "My Tenant"}
      description={
        isGlobal
          ? "Organizations on the platform — open a tenant to manage its shops"
          : "Your organization and the shops you manage"
      }
      breadcrumbs={["Home", "Platform", "Tenants"]}
      actions={
        <div className="flex gap-2">
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
          {canCreate && (
            <Button onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" /> Add Tenant
            </Button>
          )}
        </div>
      }
    >
      <div className="platform-shell space-y-6">
        <PlatformCloudNotice />

        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="platform-hero p-6 sm:p-8"
        >
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary">
            Multi-tenant platform
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            {isGlobal ? "All tenant organizations" : "Your tenant workspace"}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Each tenant owns one or more shops. Drill into a profile for managers, portfolio
            performance, and shop-level operations.
          </p>
        </motion.section>

        <KpiGrid>
          <KpiCard
            title="Tenants"
            value={String(totals.tenants)}
            icon={<Building2 className="h-5 w-5" />}
            loading={loading}
            index={0}
            accent="primary"
          />
          <KpiCard
            title="Shops"
            value={String(totals.shops)}
            icon={<Store className="h-5 w-5" />}
            loading={loading}
            index={1}
            accent="success"
          />
          <KpiCard
            title="Revenue"
            value={formatCurrency(totals.revenue)}
            icon={<Building2 className="h-5 w-5" />}
            loading={loading}
            index={2}
            accent="info"
          />
          <KpiCard
            title="Users"
            value={String(totals.users)}
            icon={<Users className="h-5 w-5" />}
            loading={loading}
            index={3}
            accent="warning"
          />
        </KpiGrid>

        {creating && canCreate && (
          <form onSubmit={handleCreate} className="platform-panel p-5 sm:p-6">
            <FormSection title="New tenant organization">
              <FormGrid>
                <FormField label="Name" required>
                  <Input
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </FormField>
                <FormField label="Contact email">
                  <Input
                    type="email"
                    value={form.contact_email}
                    onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                  />
                </FormField>
                <FormField label="Contact phone">
                  <Input
                    value={form.contact_phone}
                    onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
                  />
                </FormField>
              </FormGrid>
              {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
              <div className="mt-4 flex gap-2">
                <Button type="submit">Create</Button>
                <Button type="button" variant="secondary" onClick={() => setCreating(false)}>
                  Cancel
                </Button>
              </div>
            </FormSection>
          </form>
        )}

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-48 animate-pulse rounded-2xl bg-muted/60" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="platform-panel flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
            <Building2 className="h-10 w-10 text-muted-foreground/50" />
            <p className="font-medium">No tenants yet</p>
            {canCreate && (
              <Button onClick={() => setCreating(true)}>
                <Plus className="h-4 w-4" /> Add Tenant
              </Button>
            )}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {rows.map((tenant, index) => (
              <motion.div
                key={tenant.id}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05, duration: 0.35 }}
              >
                <Link to={`/platform/tenants/${tenant.id}`} className="platform-shop-tile group h-full">
                  <div className="mb-5 flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-emerald-700 text-lg font-semibold text-primary-foreground">
                        {tenant.name.slice(0, 1).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-semibold tracking-tight group-hover:text-primary">
                          {tenant.name}
                        </p>
                        <p className="text-xs text-muted-foreground">{tenant.slug}</p>
                      </div>
                    </div>
                    <Badge variant={tenant.is_active ? "success" : "secondary"}>
                      {tenant.is_active ? "Active" : "Off"}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-2 rounded-xl bg-muted/40 px-3 py-3 text-center">
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Shops</p>
                      <p className="text-sm font-semibold">{tenant.totals?.shops ?? tenant.shop_count}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Users</p>
                      <p className="text-sm font-semibold">{tenant.totals?.users ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Revenue</p>
                      <p className="truncate text-sm font-semibold">
                        {formatCurrency(tenant.totals?.revenue ?? 0)}
                      </p>
                    </div>
                  </div>

                  <p className="mt-4 line-clamp-1 text-xs text-muted-foreground">
                    {tenant.managers?.length
                      ? `Managers: ${tenant.managers.map((m) => m.full_name || m.username).join(", ")}`
                      : "No managers assigned"}
                  </p>

                  <div className="mt-4 flex items-center justify-between text-sm text-primary">
                    <span className="font-medium">Open tenant</span>
                    <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </PageLayout>
  );
}

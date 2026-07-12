import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Building2,
  ChevronRight,
  Mail,
  Phone,
  RefreshCw,
  Store,
  Users,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import { PlatformProfileHero } from "@/components/platform/PlatformProfileHero";
import {
  platformApi,
  type PlatformShopGroupRow,
  type PlatformTenantRow,
} from "@/services/api/platform";
import { formatCurrency } from "@/utils/cn";

export function PlatformTenantDetailPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const [data, setData] = useState<PlatformShopGroupRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("month");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (!groupId) return;
    setLoading(true);
    setError(null);
    platformApi
      .shopGroup(groupId, period)
      .then((res) => setData(res.data))
      .catch((err) => {
        setData(null);
        setError(err instanceof Error ? err.message : "Failed to load tenant.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [groupId, period]);

  const shops = (data?.shops || []) as PlatformTenantRow[];

  return (
    <PageLayout
      title={data?.name || "Tenant"}
      description="Organization profile, managers, and shop portfolio"
      breadcrumbs={["Home", "Platform", "Tenants", data?.name || "…"]}
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to="/platform/tenants">
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
          <Button asChild>
            <Link to="/platform">Manage shops</Link>
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
          monogram={data?.name || "T"}
          title={data?.name || (loading ? "Loading…" : "Tenant")}
          subtitle={
            data
              ? `${data.shop_count ?? shops.length} shop${(data.shop_count ?? shops.length) === 1 ? "" : "s"} in this organization`
              : undefined
          }
          status={
            data
              ? { label: data.is_active ? "Active tenant" : "Inactive", tone: data.is_active ? "success" : "neutral" }
              : undefined
          }
          meta={[
            ...(data?.contact_email ? [{ label: "Email", value: data.contact_email }] : []),
            ...(data?.contact_phone ? [{ label: "Phone", value: data.contact_phone }] : []),
            ...(data?.slug ? [{ label: "Slug", value: data.slug }] : []),
          ]}
        />

        <KpiGrid>
          <KpiCard
            title="Shops"
            value={String(data?.totals?.shops ?? shops.length)}
            icon={<Store className="h-5 w-5" />}
            loading={loading}
            index={0}
            accent="primary"
          />
          <KpiCard
            title="Active shops"
            value={String(data?.totals?.active_shops ?? 0)}
            icon={<Building2 className="h-5 w-5" />}
            loading={loading}
            index={1}
            accent="success"
          />
          <KpiCard
            title="Revenue"
            value={formatCurrency(data?.totals?.revenue ?? 0)}
            icon={<Building2 className="h-5 w-5" />}
            loading={loading}
            index={2}
            accent="info"
          />
          <KpiCard
            title="Users"
            value={String(data?.totals?.users ?? 0)}
            icon={<Users className="h-5 w-5" />}
            loading={loading}
            index={3}
            accent="warning"
          />
        </KpiGrid>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
          <section className="space-y-4">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold tracking-tight">Shop portfolio</h3>
                <p className="text-sm text-muted-foreground">
                  Open a shop to inspect products, sales, users, and performance
                </p>
              </div>
            </div>

            {loading ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {[0, 1].map((i) => (
                  <div key={i} className="h-40 animate-pulse rounded-2xl bg-muted/60" />
                ))}
              </div>
            ) : shops.length === 0 ? (
              <div className="platform-panel flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
                <Store className="h-10 w-10 text-muted-foreground/50" />
                <p className="font-medium">No shops in this tenant yet</p>
                <Button asChild>
                  <Link to="/platform">Create a shop</Link>
                </Button>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {shops.map((shop, index) => (
                  <motion.div
                    key={shop.id}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 * index, duration: 0.35 }}
                  >
                    <Link to={`/platform/shops/${shop.id}`} className="platform-shop-tile group">
                      <div className="mb-4 flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-sm font-semibold text-primary">
                            {shop.name.slice(0, 1).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-semibold tracking-tight group-hover:text-primary">
                              {shop.name}
                            </p>
                            <p className="text-xs text-muted-foreground">{shop.slug}</p>
                          </div>
                        </div>
                        <Badge variant={shop.is_active ? "success" : "secondary"}>
                          {shop.is_active ? "Active" : "Off"}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-2 rounded-xl bg-muted/40 px-3 py-3 text-center">
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Sales</p>
                          <p className="text-sm font-semibold">{shop.kpis?.total_sales ?? 0}</p>
                        </div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Revenue</p>
                          <p className="text-sm font-semibold">{formatCurrency(shop.kpis?.revenue ?? 0)}</p>
                        </div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Plan</p>
                          <p className="truncate text-sm font-semibold">{shop.subscription?.plan || "—"}</p>
                        </div>
                      </div>
                      <div className="mt-4 flex items-center justify-between text-sm text-primary">
                        <span className="font-medium">Open profile</span>
                        <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                      </div>
                    </Link>
                  </motion.div>
                ))}
              </div>
            )}
          </section>

          <aside className="space-y-4">
            <div className="platform-panel p-5">
              <p className="mb-4 text-sm font-semibold tracking-tight">Tenant managers</p>
              {(data?.managers?.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No managers assigned yet.</p>
              ) : (
                <ul className="space-y-3">
                  {data!.managers!.map((m) => (
                    <li key={m.id} className="rounded-xl border border-border/50 bg-muted/30 p-3">
                      <p className="text-sm font-medium">{m.full_name || m.username}</p>
                      <p className="text-xs text-muted-foreground">@{m.username}</p>
                      {m.email && (
                        <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Mail className="h-3 w-3" /> {m.email}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="platform-panel p-5">
              <p className="mb-3 text-sm font-semibold tracking-tight">Contact</p>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="h-4 w-4 shrink-0" />
                  <span className="truncate text-foreground">{data?.contact_email || "—"}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="h-4 w-4 shrink-0" />
                  <span className="text-foreground">{data?.contact_phone || "—"}</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </PageLayout>
  );
}

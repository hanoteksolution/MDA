import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { ContentSection } from "@/components/layout/ContentSection";
import { useModules } from "@/hooks/useModules";
import { usePermissions } from "@/hooks/usePermissions";
import { dashboardApi } from "@/services/api/dashboard";
import {
  DASHBOARD_WIDGET_FALLBACK,
  DASHBOARD_WIDGET_LOADERS,
  filterDashboardWidgets,
  widgetIcon,
  type DashboardWidgetDef,
  type DashboardWidgetStat,
} from "@/modules/dashboard/widgets/registry";
import { cn } from "@/utils/cn";

/**
 * Module home cards on the main dashboard — composed from the widget registry.
 * Gated by TenantModule (useModules) + permissions; never BusinessType.
 */
export function DashboardModuleCards() {
  const { hasModule, modules } = useModules();
  const { hasPermission, isSuperAdmin, permissions } = usePermissions();
  const [catalog, setCatalog] = useState<DashboardWidgetDef[]>(DASHBOARD_WIDGET_FALLBACK);
  const [statsById, setStatsById] = useState<Record<string, DashboardWidgetStat[]>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    dashboardApi
      .widgets()
      .then((res) => {
        if (!alive) return;
        const rows = res.data?.results ?? [];
        if (rows.length) setCatalog(rows);
      })
      .catch(() => {
        /* keep fallback catalog */
      });
    return () => {
      alive = false;
    };
  }, []);

  const visible = useMemo(
    () =>
      filterDashboardWidgets(catalog, {
        hasModule,
        hasPermission,
        isSuperAdmin,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- gate on module/perm lists, not callback identity
    [catalog, modules, permissions, isSuperAdmin]
  );

  const visibleKey = visible.map((w) => w.id).join(",");

  useEffect(() => {
    if (!visible.length) {
      setStatsById({});
      return;
    }
    let alive = true;
    setLoading(true);
    Promise.all(
      visible.map(async (w) => {
        const loader = DASHBOARD_WIDGET_LOADERS[w.id];
        if (!loader) return [w.id, [] as DashboardWidgetStat[]] as const;
        try {
          const res = await loader.fetch();
          return [w.id, loader.mapStats(res.data)] as const;
        } catch {
          return [w.id, loader.mapStats(null)] as const;
        }
      })
    )
      .then((pairs) => {
        if (!alive) return;
        const next: Record<string, DashboardWidgetStat[]> = {};
        for (const [id, stats] of pairs) next[id] = stats;
        setStatsById(next);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleKey]);

  if (!visible.length) return null;

  return (
    <ContentSection
      index={1}
      title="Module overview"
      description="Live summaries for enabled verticals"
    >
      <div
        className={cn(
          "grid gap-4",
          visible.length > 1 ? "md:grid-cols-2 xl:grid-cols-3" : "grid-cols-1"
        )}
      >
        {visible.map((w) => (
          <ModuleCard
            key={w.id}
            to={w.route}
            title={w.title}
            icon={widgetIcon(w.icon)}
            loading={loading && !statsById[w.id]}
            stats={statsById[w.id] ?? []}
          />
        ))}
      </div>
    </ContentSection>
  );
}

function ModuleCard({
  to,
  title,
  icon,
  stats,
  loading,
}: {
  to: string;
  title: string;
  icon: ReactNode;
  stats: DashboardWidgetStat[];
  loading?: boolean;
}) {
  return (
    <Link
      to={to}
      className="group block rounded-2xl border border-border/70 bg-card/60 p-5 transition-colors hover:border-primary/40 hover:bg-card"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {icon}
          </span>
          <h3 className="text-base font-semibold text-foreground">{title}</h3>
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {(stats.length ? stats : [{ label: "…", value: 0 }, { label: "…", value: 0 }]).map(
          (s, idx) => (
            <div key={`${s.label}-${idx}`}>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {s.label}
              </p>
              <p className="mt-0.5 text-xl font-semibold tabular-nums text-foreground">
                {loading ? "—" : Number(s.value).toLocaleString()}
              </p>
            </div>
          )
        )}
      </div>
    </Link>
  );
}

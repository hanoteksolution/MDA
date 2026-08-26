import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, Reorder, motion } from "framer-motion";
import {
  Briefcase,
  Database,
  LayoutGrid,
  Search,
  Star,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePermissions } from "@/hooks/usePermissions";
import { hubWorkspacesForUser } from "@/navigation/postLogin";
import {
  HUB_CATEGORY_GROUPS,
  HUB_QUICK_ACTIONS,
  TONE_STYLES,
  filterQuickActions,
  type WorkspaceCategoryId,
} from "@/navigation/moduleWorkspaces";
import { cn } from "@/utils/cn";
import { HubWorkspaceCard } from "./hub/HubWorkspaceCard";
import { HubWorkspaceZone } from "./hub/HubWorkspaceZone";
import { AnimatedNumber } from "./hub/AnimatedNumber";
import { HubSparkline, TONE_HEX } from "./hub/HubSparkline";
import { useHubOverview, type HubKpi } from "./hub/useHubOverview";
import { fadeUp, staggerFast, staggerSlow } from "./hub/hubMotion";
import {
  greetingForHour,
  loadHubFavorites,
  loadHubRecents,
  recordHubVisit,
  saveHubFavorites,
  toggleHubFavorite,
} from "./hub/hubStorage";

type HubFilter = "all" | "favorites" | "recent" | "business" | "core";

const BUSINESS_CATS = new Set(
  HUB_CATEGORY_GROUPS.find((g) => g.id === "business")?.categories ?? []
);
const CORE_CATS = new Set(HUB_CATEGORY_GROUPS.find((g) => g.id === "core")?.categories ?? []);

function isBusinessWorkspace(category: WorkspaceCategoryId) {
  return BUSINESS_CATS.has(category);
}

function isCoreWorkspace(category: WorkspaceCategoryId) {
  return CORE_CATS.has(category);
}

export function ModuleHubPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const setActiveWorkspace = useUIStore((s) => s.setActiveWorkspace);
  const { hasPermission, isSuperAdmin } = usePermissions();
  const [favorites, setFavorites] = useState<string[]>(() => loadHubFavorites());
  const [recents, setRecents] = useState(() => loadHubRecents());
  const [filter, setFilter] = useState<HubFilter>("all");
  const [workspaceQuery, setWorkspaceQuery] = useState("");

  const workspaces = useMemo(
    () => hubWorkspacesForUser(user, hasPermission),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, isSuperAdmin, user?.enabled_modules, user?.permissions]
  );

  const quickActions = useMemo(
    () =>
      filterQuickActions(HUB_QUICK_ACTIONS, {
        enabled: user?.enabled_modules,
        isSuperAdmin,
        hasPermission,
      }).slice(0, 8),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, isSuperAdmin, user?.enabled_modules, user?.permissions]
  );

  const overview = useHubOverview(workspaces);
  const workspaceByCode = useMemo(
    () => Object.fromEntries(workspaces.map((w) => [w.code, w])),
    [workspaces]
  );

  const launcherWorkspaces = useMemo(
    () => workspaces.filter((w) => w.code !== "overview" && w.kind !== "capability"),
    [workspaces]
  );

  const displayName =
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || "there";
  const greeting = greetingForHour();
  const todayLabel = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const openWorkspace = (code: string, route: string) => {
    setActiveWorkspace(code);
    setRecents(recordHubVisit(code));
    navigate(route);
  };

  const toggleFavorite = (code: string) => {
    setFavorites(toggleHubFavorite(code));
  };

  const filteredWorkspaces = useMemo(() => {
    let list = launcherWorkspaces;
    if (filter === "favorites") list = favorites.map((c) => workspaceByCode[c]).filter(Boolean);
    else if (filter === "recent") list = recents.map((r) => workspaceByCode[r.code]).filter(Boolean);
    else if (filter === "business") list = launcherWorkspaces.filter((w) => isBusinessWorkspace(w.category));
    else if (filter === "core") list = launcherWorkspaces.filter((w) => isCoreWorkspace(w.category));

    const q = workspaceQuery.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (w) =>
          w.label.toLowerCase().includes(q) ||
          w.description.toLowerCase().includes(q) ||
          w.pages.some((p) => p.toLowerCase().includes(q))
      );
    }
    return list;
  }, [filter, favorites, recents, workspaceByCode, launcherWorkspaces, workspaceQuery]);

  const gridWorkspaces =
    filter === "all" && favorites.length && !workspaceQuery
      ? [
          ...favorites.map((c) => workspaceByCode[c]).filter(Boolean),
          ...filteredWorkspaces.filter((w) => !favorites.includes(w.code)),
        ]
      : filteredWorkspaces;

  const businessGrid = gridWorkspaces.filter((w) => isBusinessWorkspace(w.category));
  const coreGrid = gridWorkspaces.filter((w) => isCoreWorkspace(w.category));
  const showGrouped = filter === "all" && !workspaceQuery;

  const kpis = overview.loading ? placeholderKpis : overview.kpis;

  const renderWorkspaceGrid = (
    items: typeof gridWorkspaces,
    gridKey?: string,
    columns: "zone" | "full" = "full"
  ) => (
    <motion.div
      key={gridKey ?? `${filter}-${workspaceQuery}-${items.map((w) => w.code).join(",")}`}
      variants={staggerFast}
      initial="hidden"
      animate="show"
      className={cn(
        "grid grid-cols-1 gap-4",
        columns === "full" && "sm:grid-cols-2 xl:grid-cols-3",
        columns === "zone" && "sm:grid-cols-2 lg:grid-cols-3"
      )}
    >
      <AnimatePresence mode="popLayout">
        {items.map((ws, i) => (
          <HubWorkspaceCard
            key={ws.code}
            workspace={ws}
            live={overview.live[ws.code]}
            loading={overview.loading}
            favorite={favorites.includes(ws.code)}
            index={i}
            onOpen={() => openWorkspace(ws.code, ws.route)}
            onAction={(route) => openWorkspace(ws.code, route)}
            onToggleFavorite={() => toggleFavorite(ws.code)}
          />
        ))}
      </AnimatePresence>
    </motion.div>
  );

  const renderBusinessZone = (items: typeof gridWorkspaces, columns: "zone" | "full" = "zone") => (
    <HubWorkspaceZone
      id="business"
      title="Business"
      description="Industry workspaces for the businesses you operate."
      icon={Briefcase}
      count={items.length}
      className="h-full min-w-0"
    >
      {renderWorkspaceGrid(items, `business-${items.map((w) => w.code).join(",")}`, columns)}
    </HubWorkspaceZone>
  );

  const renderCoreZone = (items: typeof gridWorkspaces, columns: "zone" | "full" = "zone") => (
    <HubWorkspaceZone
      id="core"
      title="Core"
      description="Shared platform services — finance, reports, and administration."
      icon={Database}
      count={items.length}
      className="h-full min-w-0"
    >
      {renderWorkspaceGrid(items, `core-${items.map((w) => w.code).join(",")}`, columns)}
    </HubWorkspaceZone>
  );

  return (
    <div className="hub-canvas min-h-[calc(100dvh-3.75rem)]">
      <div className="relative z-10 mx-auto w-full max-w-[1920px] space-y-6 p-4 sm:p-6 2xl:p-8">
        <motion.div variants={staggerSlow} initial="hidden" animate="show">
          <motion.div variants={fadeUp} className="hub-hero">
            <div className="relative z-[1] flex flex-col gap-5 px-5 pb-1 pt-6 sm:flex-row sm:items-end sm:justify-between sm:px-7 sm:pt-7">
              <div className="min-w-0">
                <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/70 px-2.5 py-1 text-[11px] font-medium text-muted-foreground shadow-sm backdrop-blur-sm">
                  <span className="hub-live-dot h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {user?.branch?.name || "Main Branch"} · {todayLabel}
                </div>
                <h1 className="mt-3 font-[family-name:var(--font-display,inherit)] text-[1.85rem] font-semibold tracking-[-0.045em] text-foreground sm:text-[2.15rem]">
                  {greeting}, {displayName}.
                </h1>
                <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-muted-foreground">
                  One workspace. One platform. Everything your business needs to operate.
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <div className="rounded-2xl border border-border/60 bg-background/70 px-3.5 py-2.5 shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Business</p>
                  <p className="mt-0.5 text-lg font-semibold tabular-nums tracking-tight">
                    {launcherWorkspaces.filter((w) => isBusinessWorkspace(w.category)).length}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-background/70 px-3.5 py-2.5 shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Core</p>
                  <p className="mt-0.5 text-lg font-semibold tabular-nums tracking-tight">
                    {launcherWorkspaces.filter((w) => isCoreWorkspace(w.category)).length}
                  </p>
                </div>
              </div>
            </div>

            <div className="hub-kpi-strip mt-5">
              {kpis.map((kpi) => {
                const up = (kpi.delta ?? 0) >= 0;
                const hasTrend = Boolean(kpi.sparkline?.length) && kpi.value !== 0;
                return (
                  <motion.div key={kpi.id} variants={fadeUp} className="hub-kpi-cell">
                    <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                      {kpi.label}
                    </p>
                    {overview.loading ? (
                      <div className="hub-shimmer mt-2 h-7 w-[4.5rem] rounded-md" />
                    ) : (
                      <p className="mt-1.5 text-[1.35rem] font-semibold tabular-nums tracking-tight">
                        <AnimatedNumber value={kpi.value} money={kpi.money} integer={kpi.integer} duration={900} />
                      </p>
                    )}
                    <div className="mt-2 flex items-end justify-between gap-2">
                      {hasTrend ? (
                        <HubSparkline
                          data={kpi.sparkline}
                          color={up ? TONE_HEX.emerald : TONE_HEX.rose}
                          className="h-7 w-14 opacity-80"
                          height={28}
                        />
                      ) : (
                        <span className="text-[10px] text-muted-foreground">
                          {kpi.value === 0 ? "No activity yet" : kpi.hint || "vs previous period"}
                        </span>
                      )}
                      {kpi.delta != null && kpi.value !== 0 ? (
                        <span
                          className={cn(
                            "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                            up
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                          )}
                        >
                          {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                          {Math.abs(kpi.delta).toFixed(1)}%
                        </span>
                      ) : null}
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {quickActions.length ? (
              <div className="relative z-[1] flex gap-2 overflow-x-auto border-t border-border/60 px-4 py-3.5 scrollbar-thin sm:px-5">
                {quickActions.map((action) => {
                  const Icon = action.icon;
                  return (
                    <button
                      key={action.id}
                      type="button"
                      onClick={() => navigate(action.route)}
                      className="hub-action-chip"
                    >
                      <span className={cn("flex h-6 w-6 items-center justify-center rounded-lg bg-muted/80", TONE_STYLES[action.tone].text)}>
                        <Icon className="h-3.5 w-3.5" />
                      </span>
                      {action.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </motion.div>
        </motion.div>

        <div>
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="hub-section-label">Launch</p>
              <h2 className="mt-1 text-[17px] font-semibold tracking-tight">Workspaces</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Business industries and core platform services side by side
              </p>
            </div>
            <div className="hub-filter-bar">
              <label className="relative hidden sm:block">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={workspaceQuery}
                  onChange={(e) => setWorkspaceQuery(e.target.value)}
                  placeholder="Search workspaces…"
                  className="h-8 w-48 rounded-xl border-0 bg-transparent pl-8 pr-3 text-[12px] outline-none ring-0 placeholder:text-muted-foreground focus:bg-muted/40"
                  aria-label="Search workspaces"
                />
              </label>
              <div className="relative flex rounded-xl bg-muted/60 p-0.5 text-[12px]">
                {(["all", "favorites", "business", "core"] as const).map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setFilter(id)}
                    className={cn(
                      "relative rounded-lg px-2.5 py-1.5 font-medium capitalize",
                      filter === id ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {filter === id ? (
                      <motion.span
                        layoutId="hub-view-pill"
                        className="absolute inset-0 rounded-lg bg-card shadow-sm"
                        transition={{ type: "spring", stiffness: 400, damping: 32 }}
                      />
                    ) : null}
                    <span className="relative">
                      {id === "all" ? "All" : id === "favorites" ? "Favorites" : id === "business" ? "Business" : "Core"}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {filter === "favorites" && favorites.length > 1 ? (
            <Reorder.Group
              axis="y"
              values={favorites}
              onReorder={(next) => {
                setFavorites(next);
                saveHubFavorites(next);
              }}
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
            >
              {favorites.map((code, i) => {
                const ws = workspaceByCode[code];
                if (!ws) return null;
                return (
                  <Reorder.Item key={code} value={code} className="cursor-grab active:cursor-grabbing">
                    <HubWorkspaceCard
                      workspace={ws}
                      live={overview.live[ws.code]}
                      loading={overview.loading}
                      favorite
                      index={i}
                      onOpen={() => openWorkspace(ws.code, ws.route)}
                      onAction={(route) => openWorkspace(ws.code, route)}
                      onToggleFavorite={() => toggleFavorite(ws.code)}
                    />
                  </Reorder.Item>
                );
              })}
            </Reorder.Group>
          ) : showGrouped ? (
            <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-2 lg:gap-6">
              {businessGrid.length ? renderBusinessZone(businessGrid, "zone") : null}
              {coreGrid.length ? renderCoreZone(coreGrid, "zone") : null}
            </div>
          ) : filter === "business" && gridWorkspaces.length ? (
            renderBusinessZone(gridWorkspaces, "full")
          ) : filter === "core" && gridWorkspaces.length ? (
            renderCoreZone(gridWorkspaces, "full")
          ) : (
            renderWorkspaceGrid(gridWorkspaces, undefined, "full")
          )}

          {!gridWorkspaces.length ? (
            <div className="hub-panel px-6 py-16 text-center">
              <LayoutGrid className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-3 text-sm font-medium">No workspaces in this view</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Pin a favorite or enable a module for this tenant.
              </p>
            </div>
          ) : null}
        </div>
      </div>

      <nav
        aria-label="Mobile hub"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border/80 bg-card/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl sm:hidden"
      >
        {[
          { id: "all" as const, label: "Home", icon: LayoutGrid },
          { id: "business" as const, label: "Business", icon: Briefcase },
          { id: "core" as const, label: "Core", icon: Database },
          { id: "favorites" as const, label: "Pinned", icon: Star },
        ].map((item) => {
          const Icon = item.icon;
          const active = filter === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setFilter(item.id)}
              className={cn(
                "flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium",
                active ? "text-foreground" : "text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </nav>
      <div className="h-16 sm:hidden" />
    </div>
  );
}

const placeholderKpis: HubKpi[] = [
  { id: "revenue", label: "Revenue", value: 0, money: true },
  { id: "profit", label: "Profit", value: 0, money: true },
  { id: "orders", label: "Orders", value: 0, integer: true },
  { id: "customers", label: "Customers", value: 0, integer: true },
  { id: "cash", label: "Cash", value: 0, money: true },
  { id: "receivables", label: "Receivables", value: 0, money: true },
  { id: "payables", label: "Payables", value: 0, money: true },
];

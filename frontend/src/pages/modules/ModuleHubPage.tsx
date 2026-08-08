import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, Reorder, motion } from "framer-motion";
import { ChevronRight, CreditCard, TrendingDown, TrendingUp } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePermissions } from "@/hooks/usePermissions";
import { hubWorkspacesForUser } from "@/navigation/postLogin";
import {
  HUB_NAV_SECTIONS,
  HUB_QUICK_ACTIONS,
  TONE_STYLES,
  WORKSPACE_CATEGORIES,
  filterQuickActions,
  type WorkspaceCategoryId,
} from "@/navigation/moduleWorkspaces";
import { cn } from "@/utils/cn";
import { HubWorkspaceCard } from "./hub/HubWorkspaceCard";
import { AnimatedNumber } from "./hub/AnimatedNumber";
import { HubSparkline, TONE_HEX } from "./hub/HubSparkline";
import { useHubOverview, type HubKpi } from "./hub/useHubOverview";
import { fadeUp, staggerFast, staggerSlow } from "./hub/hubMotion";
import {
  greetingForHour,
  loadHubFavorites,
  loadHubRecents,
  recordHubVisit,
  relativeTime,
  saveHubFavorites,
  toggleHubFavorite,
} from "./hub/hubStorage";

type HubFilter = "all" | "favorites" | "recent" | "actions" | WorkspaceCategoryId;

export function ModuleHubPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const setActiveWorkspace = useUIStore((s) => s.setActiveWorkspace);
  const { hasPermission, isSuperAdmin } = usePermissions();
  const [favorites, setFavorites] = useState<string[]>(() => loadHubFavorites());
  const [recents, setRecents] = useState(() => loadHubRecents());
  const [filter, setFilter] = useState<HubFilter>("all");
  const [railTab, setRailTab] = useState<"pinned" | "recent" | "activity">("activity");

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

  const visibleCategories = useMemo(() => {
    const used = new Set(workspaces.map((w) => w.category));
    return WORKSPACE_CATEGORIES.filter((c) => used.has(c.id));
  }, [workspaces]);

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
    if (filter === "favorites") return favorites.map((c) => workspaceByCode[c]).filter(Boolean);
    if (filter === "recent") return recents.map((r) => workspaceByCode[r.code]).filter(Boolean);
    if (filter === "actions" || filter === "all") return workspaces.filter((w) => w.code !== "overview");
    return workspaces.filter((w) => w.category === filter);
  }, [filter, favorites, recents, workspaceByCode, workspaces]);

  const gridWorkspaces =
    filter === "all" && favorites.length
      ? [
          ...favorites.map((c) => workspaceByCode[c]).filter(Boolean),
          ...filteredWorkspaces.filter((w) => !favorites.includes(w.code)),
        ]
      : filteredWorkspaces;

  const subscriptionLabel =
    overview.entitlements?.plan_name ||
    (overview.entitlements?.trial_or_demo ? "Trial" : "Enterprise");

  const kpis = overview.loading ? placeholderKpis : overview.kpis;

  return (
    <div className="hub-canvas min-h-[calc(100dvh-3.75rem)]">
      <div className="relative z-10 mx-auto grid max-w-[1600px] grid-cols-1 gap-6 p-4 lg:grid-cols-[200px_minmax(0,1fr)] lg:p-6 xl:grid-cols-[212px_minmax(0,1fr)_292px] xl:gap-7 2xl:p-8">
        <motion.aside
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="hub-glass hidden h-fit p-3 lg:sticky lg:top-5 lg:block"
        >
          <nav aria-label="Hub navigation" className="space-y-0.5">
            {HUB_NAV_SECTIONS.map((item) => {
              const Icon = item.icon;
              const active = filter === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setFilter(item.id)}
                  className={cn(
                    "relative flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors",
                    active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {active ? (
                    <motion.span
                      layoutId="hub-nav-pill"
                      className="absolute inset-0 rounded-lg bg-muted"
                      transition={{ type: "spring", stiffness: 380, damping: 34 }}
                    />
                  ) : null}
                  <Icon className="relative h-4 w-4" />
                  <span className="relative">{item.label}</span>
                </button>
              );
            })}
          </nav>

          <p className="mb-1.5 mt-7 px-2.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
            Categories
          </p>
          <nav aria-label="Workspace categories" className="space-y-0.5">
            {visibleCategories.map((cat) => {
              const Icon = cat.icon;
              const active = filter === cat.id;
              const count = workspaces.filter((w) => w.category === cat.id).length;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setFilter(cat.id)}
                  className={cn(
                    "relative flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] transition-colors",
                    active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {active ? (
                    <motion.span
                      layoutId="hub-nav-pill"
                      className="absolute inset-0 rounded-lg bg-muted"
                      transition={{ type: "spring", stiffness: 380, damping: 34 }}
                    />
                  ) : null}
                  <Icon className={cn("relative h-3.5 w-3.5", TONE_STYLES[cat.tone].text)} />
                  <span className="relative min-w-0 flex-1 truncate text-left">{cat.label}</span>
                  <span className="relative text-[11px] tabular-nums text-muted-foreground/70">{count}</span>
                </button>
              );
            })}
          </nav>

          <div className="mt-8 border-t border-border/70 px-2.5 pt-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">Plan</p>
            <p className="mt-1.5 text-sm font-semibold tracking-tight">{subscriptionLabel}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {overview.entitlements?.days_until_expiry != null
                ? `${overview.entitlements.days_until_expiry} days remaining`
                : overview.entitlements?.status || "Active"}
            </p>
            <button
              type="button"
              onClick={() => navigate("/platform/subscriptions")}
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <CreditCard className="h-3.5 w-3.5" />
              Manage
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </motion.aside>

        <section className="min-w-0 space-y-7">
          <motion.div variants={staggerSlow} initial="hidden" animate="show">
            <motion.div variants={fadeUp} className="hub-panel hub-shine relative overflow-hidden">
              <span className="hub-orb -left-10 -top-16 h-44 w-44 bg-violet-400/35" />
              <span className="hub-orb right-0 top-0 h-40 w-40 bg-emerald-400/25" style={{ animationDelay: "-6s" }} />
              <span className="hub-orb bottom-0 left-1/3 h-32 w-32 bg-sky-400/20" style={{ animationDelay: "-11s" }} />

              <div className="relative px-5 pb-2 pt-6 sm:px-7 sm:pt-7">
                <p className="text-[13px] text-muted-foreground">
                  {user?.branch?.name ? `${user.branch.name}` : "Enterprise"} · {todayLabel}
                </p>
                <h1 className="mt-1 text-[1.9rem] font-semibold tracking-[-0.045em] sm:text-[2.25rem]">
                  {greeting}, {displayName}
                </h1>
                <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">
                  A live command center for every workspace on this tenant.
                </p>
              </div>

              <div className="relative mt-4 grid grid-cols-2 gap-px border-t border-white/40 bg-white/30 sm:grid-cols-4 xl:grid-cols-7 dark:border-white/10 dark:bg-white/5">
                {kpis.map((kpi) => {
                  const up = (kpi.delta ?? 0) >= 0;
                  return (
                    <motion.div key={kpi.id} variants={fadeUp} className="bg-white/40 px-4 py-4 backdrop-blur-sm sm:px-5 dark:bg-white/5">
                      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
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
                        <HubSparkline
                          data={kpi.sparkline}
                          color={up ? TONE_HEX.emerald : TONE_HEX.rose}
                          className="h-8 w-16 opacity-90"
                          height={32}
                        />
                        {kpi.delta != null && kpi.value !== 0 ? (
                          <span
                            className={cn(
                              "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                              up ? "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400" : "bg-rose-500/12 text-rose-600 dark:text-rose-400"
                            )}
                          >
                            {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                            {Math.abs(kpi.delta).toFixed(1)}%
                          </span>
                        ) : kpi.hint ? (
                          <span className="text-[10px] text-muted-foreground">{kpi.hint}</span>
                        ) : null}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
              <div className="relative flex flex-wrap gap-1.5 border-t border-white/40 px-3 py-2.5 dark:border-white/10">
                {quickActions.map((action) => {
                  const Icon = action.icon;
                  return (
                    <motion.button
                      key={action.id}
                      type="button"
                      whileHover={{ y: -2, scale: 1.03 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => navigate(action.route)}
                      className="inline-flex items-center gap-2 rounded-full border border-white/50 bg-white/50 px-3 py-1.5 text-[12px] font-medium text-muted-foreground shadow-sm backdrop-blur-md transition-colors hover:border-white/80 hover:text-foreground dark:border-white/10 dark:bg-white/10"
                    >
                      <Icon className={cn("h-3.5 w-3.5", TONE_STYLES[action.tone].text)} />
                      {action.label}
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>

          <div>
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-[15px] font-semibold tracking-tight">Workspaces</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {gridWorkspaces.length} available · click any card to enter
                </p>
              </div>
              <div className="relative flex rounded-lg bg-muted/70 p-0.5 text-[12px]">
                {(["all", "favorites"] as const).map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setFilter(id)}
                    className={cn(
                      "relative rounded-md px-3 py-1.5 font-medium",
                      filter === id ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {filter === id ? (
                      <motion.span
                        layoutId="hub-view-pill"
                        className="absolute inset-0 rounded-md bg-card shadow-sm"
                        transition={{ type: "spring", stiffness: 400, damping: 32 }}
                      />
                    ) : null}
                    <span className="relative">{id === "all" ? "All" : "Pinned"}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4 flex gap-1.5 overflow-x-auto pb-1 lg:hidden scrollbar-thin">
              {[...HUB_NAV_SECTIONS, ...visibleCategories.map((c) => ({ id: c.id, label: c.label }))].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setFilter(item.id as HubFilter)}
                  className={cn(
                    "shrink-0 rounded-full px-3 py-1 text-[12px] font-medium",
                    filter === item.id ? "bg-foreground text-background" : "bg-muted text-muted-foreground"
                  )}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {filter === "favorites" && favorites.length > 1 ? (
              <Reorder.Group
                axis="y"
                values={favorites}
                onReorder={(next) => {
                  setFavorites(next);
                  saveHubFavorites(next);
                }}
                className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3"
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
            ) : (
              <motion.div
                key={filter}
                variants={staggerFast}
                initial="hidden"
                animate="show"
                className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3"
              >
                <AnimatePresence mode="popLayout">
                  {gridWorkspaces.map((ws, i) => (
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
            )}

            {!gridWorkspaces.length ? (
              <div className="hub-panel px-6 py-16 text-center text-sm text-muted-foreground">
                No workspaces in this view. Pin a favorite or enable a module.
              </div>
            ) : null}
          </div>
        </section>

        <motion.aside variants={fadeUp} initial="hidden" animate="show" className="xl:sticky xl:top-5 xl:h-fit">
          <div className="hub-panel hub-spotlight overflow-hidden">
            <div className="relative flex border-b border-border/70 p-1">
              {(["activity", "pinned", "recent"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setRailTab(tab)}
                  className={cn(
                    "relative flex-1 rounded-md py-1.5 text-[12px] font-medium capitalize",
                    railTab === tab ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {railTab === tab ? (
                    <motion.span
                      layoutId="hub-rail-pill"
                      className="absolute inset-0 rounded-md bg-muted"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  ) : null}
                  <span className="relative">{tab === "pinned" ? "Pinned" : tab === "recent" ? "Recent" : "Activity"}</span>
                </button>
              ))}
            </div>

            <div className="min-h-[280px] p-3">
              <AnimatePresence mode="wait">
                {railTab === "pinned" ? (
                  <motion.div key="pinned" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    {favorites.length === 0 ? (
                      <p className="px-2 py-8 text-center text-xs text-muted-foreground">Star a workspace to pin it here.</p>
                    ) : (
                      <ul className="space-y-0.5">
                        {favorites.slice(0, 8).map((code) => {
                          const ws = workspaceByCode[code];
                          if (!ws) return null;
                          const Icon = ws.icon;
                          return (
                            <li key={code}>
                              <button
                                type="button"
                                onClick={() => openWorkspace(ws.code, ws.route)}
                                className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left transition-colors hover:bg-muted/80"
                              >
                                <span className={cn("flex h-7 w-7 items-center justify-center rounded-md", TONE_STYLES[ws.tone].accent)}>
                                  <Icon className="h-3.5 w-3.5" />
                                </span>
                                <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{ws.label}</span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </motion.div>
                ) : null}

                {railTab === "recent" ? (
                  <motion.div key="recent" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    {recents.length === 0 ? (
                      <p className="px-2 py-8 text-center text-xs text-muted-foreground">Open a workspace to build recents.</p>
                    ) : (
                      <ul className="space-y-0.5">
                        {recents.slice(0, 8).map((r) => {
                          const ws = workspaceByCode[r.code];
                          if (!ws) return null;
                          const Icon = ws.icon;
                          return (
                            <li key={r.code}>
                              <button
                                type="button"
                                onClick={() => openWorkspace(ws.code, ws.route)}
                                className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left transition-colors hover:bg-muted/80"
                              >
                                <span className={cn("flex h-7 w-7 items-center justify-center rounded-md", TONE_STYLES[ws.tone].accent)}>
                                  <Icon className="h-3.5 w-3.5" />
                                </span>
                                <span className="min-w-0 flex-1">
                                  <span className="block truncate text-[13px] font-medium">{ws.label}</span>
                                  <span className="block text-[11px] text-muted-foreground">{relativeTime(r.visitedAt)}</span>
                                </span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </motion.div>
                ) : null}

                {railTab === "activity" ? (
                  <motion.div key="activity" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    {overview.loading ? (
                      <div className="space-y-3 px-1 py-2">
                        <div className="hub-shimmer h-10 rounded-lg" />
                        <div className="hub-shimmer h-10 rounded-lg" />
                        <div className="hub-shimmer h-10 rounded-lg" />
                      </div>
                    ) : overview.activity.length === 0 ? (
                      <p className="px-2 py-8 text-center text-xs text-muted-foreground">No activity yet today.</p>
                    ) : (
                      <ol className="space-y-3 px-1 py-1">
                        {overview.activity.slice(0, 8).map((item, i) => (
                          <motion.li
                            key={item.id}
                            initial={{ opacity: 0, x: 8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="flex gap-2.5"
                          >
                            <span
                              className={cn(
                                "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                                item.tone === "alert" ? "bg-destructive" : item.tone === "sale" ? "bg-emerald-500" : "bg-sky-500"
                              )}
                            />
                            <span className="min-w-0">
                              <span className="block text-[13px] font-medium leading-snug">{item.title}</span>
                              {item.detail ? (
                                <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">{item.detail}</span>
                              ) : null}
                              <span className="mt-0.5 block text-[11px] text-muted-foreground">
                                {item.at ? relativeTime(new Date(item.at).getTime()) : ""}
                              </span>
                            </span>
                          </motion.li>
                        ))}
                      </ol>
                    )}
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>

            {overview.announcements[0] ? (
              <div className="border-t border-border/70 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Status</p>
                <p className="mt-1 text-[13px] font-medium">{overview.announcements[0].title}</p>
                <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{overview.announcements[0].body}</p>
              </div>
            ) : null}
          </div>
        </motion.aside>
      </div>
    </div>
  );
}

const placeholderKpis: HubKpi[] = [
  { id: "revenue", label: "Revenue Today", value: 0, money: true },
  { id: "profit", label: "Profit", value: 0, money: true },
  { id: "orders", label: "Orders", value: 0, integer: true },
  { id: "customers", label: "Customers", value: 0, integer: true },
  { id: "cash", label: "Cash Balance", value: 0, money: true },
  { id: "receivables", label: "Receivables", value: 0, money: true },
  { id: "payables", label: "Payables", value: 0, money: true },
];

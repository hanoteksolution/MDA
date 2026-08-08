import { memo, useCallback, useRef, type PointerEvent } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Star } from "lucide-react";
import type { ModuleWorkspace, WorkspaceTone } from "@/navigation/moduleWorkspaces";
import { TONE_STYLES } from "@/navigation/moduleWorkspaces";
import { cn } from "@/utils/cn";
import type { WorkspaceLiveState } from "./useHubOverview";
import { cardEnter } from "./hubMotion";
import { HubSparkline, TONE_HEX } from "./HubSparkline";

const BAR: Record<WorkspaceTone, string> = {
  sky: "bg-sky-500",
  orange: "bg-orange-500",
  blue: "bg-blue-500",
  teal: "bg-teal-500",
  indigo: "bg-indigo-500",
  violet: "bg-violet-500",
  emerald: "bg-emerald-500",
  green: "bg-green-500",
  amber: "bg-amber-500",
  cyan: "bg-cyan-500",
  stone: "bg-stone-500",
  lime: "bg-lime-500",
  slate: "bg-slate-500",
  fuchsia: "bg-fuchsia-500",
  rose: "bg-rose-500",
  zinc: "bg-zinc-500",
  neutral: "bg-neutral-500",
  purple: "bg-purple-500",
  pink: "bg-pink-500",
};

interface HubWorkspaceCardProps {
  workspace: ModuleWorkspace;
  live?: WorkspaceLiveState;
  loading?: boolean;
  favorite?: boolean;
  index?: number;
  onOpen: () => void;
  onAction: (route: string) => void;
  onToggleFavorite: () => void;
}

export const HubWorkspaceCard = memo(function HubWorkspaceCard({
  workspace,
  live,
  loading,
  favorite,
  index = 0,
  onOpen,
  onAction,
  onToggleFavorite,
}: HubWorkspaceCardProps) {
  const Icon = workspace.icon;
  const tone = TONE_STYLES[workspace.tone];
  const metrics = live?.metrics?.slice(0, 3) ?? [];
  const attention = live?.status === "attention";
  const cardRef = useRef<HTMLElement>(null);

  const onPointerMove = useCallback((e: PointerEvent<HTMLElement>) => {
    const el = cardRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${((e.clientX - r.left) / r.width) * 100}%`);
    el.style.setProperty("--my", `${((e.clientY - r.top) / r.height) * 100}%`);
  }, []);

  return (
    <motion.article
      ref={cardRef}
      layout
      variants={cardEnter}
      initial="hidden"
      animate="show"
      exit="exit"
      transition={{ delay: Math.min(index, 8) * 0.045 }}
      whileHover={{ y: -8 }}
      onPointerMove={onPointerMove}
      className="hub-card hub-spotlight group flex h-full cursor-pointer flex-col overflow-hidden rounded-[1.35rem]"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Open ${workspace.label} workspace`}
    >
      <span className={cn("absolute inset-y-6 left-0 w-[3px] rounded-full", BAR[workspace.tone])} />
      <span
        className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-80"
        style={{ background: TONE_HEX[workspace.tone] }}
      />

      <div className="relative flex items-start justify-between gap-3 px-5 pb-1 pt-5">
        <div className="flex min-w-0 items-center gap-3">
          <motion.div
            whileHover={{ scale: 1.06, rotate: -4 }}
            className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl", tone.icon)}
          >
            <Icon className="h-5 w-5" />
          </motion.div>
          <div className="min-w-0">
            <h3 className="truncate text-[15px] font-semibold tracking-tight">{workspace.label}</h3>
            <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span
                className={cn(
                  "hub-live-dot h-1.5 w-1.5 rounded-full",
                  attention ? "bg-destructive" : "bg-emerald-500"
                )}
              />
              {attention ? live?.alertLabel || "Needs attention" : "Live"}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleFavorite();
          }}
          aria-label={favorite ? `Unpin ${workspace.label}` : `Pin ${workspace.label}`}
          className={cn(
            "rounded-lg p-1.5 transition-colors hover:bg-white/50 dark:hover:bg-white/10",
            favorite ? "text-amber-500" : "text-muted-foreground/70"
          )}
        >
          <motion.span whileTap={{ scale: 0.85 }} className="block">
            <Star className={cn("h-4 w-4", favorite && "fill-current")} />
          </motion.span>
        </button>
      </div>

      <div className="relative mt-2 px-2">
        <HubSparkline
          data={live?.sparkline}
          color={TONE_HEX[workspace.tone]}
          className="h-12 w-full opacity-90"
          height={48}
        />
      </div>

      <div className="relative mt-1 grid grid-cols-3 gap-px border-y border-white/50 bg-white/40 dark:border-white/10 dark:bg-white/5">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-card/70 px-3 py-3 backdrop-blur-sm">
                <div className="hub-shimmer h-2.5 w-12 rounded" />
                <div className="hub-shimmer mt-2 h-4 w-16 rounded" />
              </div>
            ))
          : metrics.length
            ? metrics.map((m) => (
                <div key={m.label} className="bg-card/55 px-3 py-3 backdrop-blur-sm">
                  <p className="truncate text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                    {m.label}
                  </p>
                  <p
                    className={cn(
                      "mt-1 truncate text-[13px] font-semibold tabular-nums tracking-tight",
                      m.alert && "text-destructive"
                    )}
                  >
                    {m.value}
                  </p>
                </div>
              ))
            : (
              <div className="col-span-3 bg-card/55 px-4 py-3 text-xs text-muted-foreground backdrop-blur-sm">
                {workspace.description}
              </div>
            )}
      </div>

      <div className="relative mt-auto px-4 py-3">
        {workspace.pages.length ? (
          <p className="mb-2 line-clamp-1 text-[11px] text-muted-foreground">
            {workspace.pages.slice(0, 5).join(" · ")}
          </p>
        ) : null}
        <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-0.5">
          {workspace.quickActions.slice(0, 3).map((action) => {
            const AIcon = action.icon;
            return (
              <button
                key={action.label}
                type="button"
                title={action.label}
                aria-label={action.label}
                onClick={(e) => {
                  e.stopPropagation();
                  onAction(action.route);
                }}
                className="rounded-lg p-1.5 text-muted-foreground/80 transition-colors hover:bg-white/60 hover:text-foreground dark:hover:bg-white/10"
              >
                <AIcon className="h-3.5 w-3.5" />
              </button>
            );
          })}
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-foreground/90 px-2.5 py-1 text-[11px] font-semibold text-background opacity-0 shadow-sm transition-all duration-300 group-hover:opacity-100">
          Open {workspace.label}
          <ArrowUpRight className="h-3.5 w-3.5" />
        </span>
        </div>
      </div>
    </motion.article>
  );
});

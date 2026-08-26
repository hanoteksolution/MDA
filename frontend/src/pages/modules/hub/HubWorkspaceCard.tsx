import { memo, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Star } from "lucide-react";
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

const ICON_SOFT: Record<WorkspaceTone, string> = {
  sky: "bg-sky-500/12 text-sky-700 ring-1 ring-sky-500/15 dark:text-sky-300",
  orange: "bg-orange-500/12 text-orange-700 ring-1 ring-orange-500/15 dark:text-orange-300",
  blue: "bg-blue-500/12 text-blue-700 ring-1 ring-blue-500/15 dark:text-blue-300",
  teal: "bg-teal-500/12 text-teal-700 ring-1 ring-teal-500/15 dark:text-teal-300",
  indigo: "bg-indigo-500/12 text-indigo-700 ring-1 ring-indigo-500/15 dark:text-indigo-300",
  violet: "bg-violet-500/12 text-violet-700 ring-1 ring-violet-500/15 dark:text-violet-300",
  emerald: "bg-emerald-500/12 text-emerald-700 ring-1 ring-emerald-500/15 dark:text-emerald-300",
  green: "bg-green-500/12 text-green-700 ring-1 ring-green-500/15 dark:text-green-300",
  amber: "bg-amber-500/12 text-amber-700 ring-1 ring-amber-500/15 dark:text-amber-300",
  cyan: "bg-cyan-500/12 text-cyan-700 ring-1 ring-cyan-500/15 dark:text-cyan-300",
  stone: "bg-stone-500/12 text-stone-700 ring-1 ring-stone-500/15 dark:text-stone-300",
  lime: "bg-lime-500/12 text-lime-700 ring-1 ring-lime-500/15 dark:text-lime-300",
  slate: "bg-slate-500/12 text-slate-700 ring-1 ring-slate-500/15 dark:text-slate-300",
  fuchsia: "bg-fuchsia-500/12 text-fuchsia-700 ring-1 ring-fuchsia-500/15 dark:text-fuchsia-300",
  rose: "bg-rose-500/12 text-rose-700 ring-1 ring-rose-500/15 dark:text-rose-300",
  zinc: "bg-zinc-500/12 text-zinc-700 ring-1 ring-zinc-500/15 dark:text-zinc-300",
  neutral: "bg-neutral-500/12 text-neutral-700 ring-1 ring-neutral-500/15 dark:text-neutral-300",
  purple: "bg-purple-500/12 text-purple-700 ring-1 ring-purple-500/15 dark:text-purple-300",
  pink: "bg-pink-500/12 text-pink-700 ring-1 ring-pink-500/15 dark:text-pink-300",
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
  const metrics = live?.metrics?.slice(0, 3) ?? [];
  const attention = live?.status === "attention";
  const hasSpark = Boolean(live?.sparkline?.length);
  const toneHex = TONE_HEX[workspace.tone];

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onOpen();
    }
  };

  return (
    <motion.article
      layout
      variants={cardEnter}
      initial="hidden"
      animate="show"
      exit="exit"
      transition={{ delay: Math.min(index, 8) * 0.04 }}
      whileHover={{ y: -4 }}
      className="hub-card group flex h-full cursor-pointer flex-col overflow-hidden"
      onClick={onOpen}
      onKeyDown={onKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`Open ${workspace.label} workspace`}
    >
      <span
        className="pointer-events-none absolute inset-x-0 top-0 h-24 opacity-80 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `linear-gradient(180deg, ${toneHex}14 0%, transparent 100%)`,
        }}
        aria-hidden
      />
      <span className={cn("absolute inset-y-6 left-0 w-[3px] rounded-full", BAR[workspace.tone])} />

      <div className="relative flex items-start justify-between gap-3 px-5 pb-1 pt-5">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-[1.05]",
              ICON_SOFT[workspace.tone]
            )}
          >
            <Icon className="h-5 w-5" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
              {workspace.label}
            </h3>
            <p className="hub-status-pill mt-1.5">
              <span
                className={cn(
                  "hub-live-dot h-1.5 w-1.5 rounded-full",
                  attention ? "bg-amber-500" : "bg-emerald-500"
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
            "rounded-xl p-2 transition-all hover:bg-background/80",
            favorite
              ? "text-amber-500"
              : "text-muted-foreground/50 hover:text-muted-foreground"
          )}
        >
          <Star className={cn("h-4 w-4", favorite && "fill-current")} />
        </button>
      </div>

      <p className="relative mt-3 line-clamp-2 px-5 text-[13px] leading-relaxed text-muted-foreground">
        {workspace.description}
      </p>

      <div className="relative mt-3 px-2">
        {hasSpark ? (
          <HubSparkline
            data={live?.sparkline}
            color={toneHex}
            className="h-11 w-full opacity-90"
            height={44}
          />
        ) : (
          <div
            className="mx-3 h-11 rounded-xl opacity-60"
            style={{
              background: `linear-gradient(90deg, transparent, ${toneHex}18, transparent)`,
            }}
            aria-hidden
          />
        )}
      </div>

      <div className="relative mx-4 mt-2 grid grid-cols-3 gap-2">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="rounded-xl bg-muted/50 px-2.5 py-2.5">
                <div className="hub-shimmer h-2 w-10 rounded" />
                <div className="hub-shimmer mt-2 h-3.5 w-12 rounded" />
              </div>
            ))
          : metrics.length
            ? metrics.map((m) => (
                <div
                  key={m.label}
                  className="rounded-xl border border-border/50 bg-background/70 px-2.5 py-2.5 backdrop-blur-sm"
                >
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
              <div className="col-span-3 rounded-xl border border-dashed border-border/60 bg-muted/20 px-3 py-3 text-center text-xs text-muted-foreground">
                No activity yet
              </div>
            )}
      </div>

      <div className="relative mt-auto px-5 pb-4 pt-4">
        {workspace.pages.length ? (
          <p className="mb-3 line-clamp-1 text-[11px] text-muted-foreground/90">
            {workspace.pages.slice(0, 5).join(" · ")}
          </p>
        ) : null}
        <div className="flex items-center justify-between gap-2 border-t border-border/50 pt-3">
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
                  className="rounded-lg p-1.5 text-muted-foreground/70 transition-colors hover:bg-muted hover:text-foreground"
                >
                  <AIcon className="h-3.5 w-3.5" />
                </button>
              );
            })}
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold transition-all group-hover:gap-2",
              TONE_STYLES[workspace.tone].text,
              "bg-foreground/[0.03] group-hover:bg-foreground/[0.06]"
            )}
          >
            Open
            <ArrowRight className="h-3.5 w-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
          </span>
        </div>
      </div>
    </motion.article>
  );
});

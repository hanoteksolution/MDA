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
  sky: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  orange: "bg-orange-500/10 text-orange-700 dark:text-orange-300",
  blue: "bg-blue-500/10 text-blue-700 dark:text-blue-300",
  teal: "bg-teal-500/10 text-teal-700 dark:text-teal-300",
  indigo: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300",
  violet: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
  emerald: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  green: "bg-green-500/10 text-green-700 dark:text-green-300",
  amber: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  cyan: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300",
  stone: "bg-stone-500/10 text-stone-700 dark:text-stone-300",
  lime: "bg-lime-500/10 text-lime-700 dark:text-lime-300",
  slate: "bg-slate-500/10 text-slate-700 dark:text-slate-300",
  fuchsia: "bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300",
  rose: "bg-rose-500/10 text-rose-700 dark:text-rose-300",
  zinc: "bg-zinc-500/10 text-zinc-700 dark:text-zinc-300",
  neutral: "bg-neutral-500/10 text-neutral-700 dark:text-neutral-300",
  purple: "bg-purple-500/10 text-purple-700 dark:text-purple-300",
  pink: "bg-pink-500/10 text-pink-700 dark:text-pink-300",
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
      whileHover={{ y: -3 }}
      className="hub-card group flex h-full cursor-pointer flex-col overflow-hidden rounded-[1.125rem]"
      onClick={onOpen}
      onKeyDown={onKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`Open ${workspace.label} workspace`}
    >
      <span className={cn("absolute inset-y-5 left-0 w-[2px] rounded-full", BAR[workspace.tone])} />

      <div className="flex items-start justify-between gap-3 px-5 pb-1 pt-5">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-transform duration-300 group-hover:scale-[1.04]",
              ICON_SOFT[workspace.tone]
            )}
          >
            <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
              {workspace.label}
            </h3>
            <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
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
            "rounded-lg p-1.5 transition-colors hover:bg-muted",
            favorite ? "text-amber-500" : "text-muted-foreground/60 hover:text-muted-foreground"
          )}
        >
          <Star className={cn("h-4 w-4", favorite && "fill-current")} />
        </button>
      </div>

      <p className="mt-2 line-clamp-2 px-5 text-[13px] leading-relaxed text-muted-foreground">
        {workspace.description}
      </p>

      {hasSpark ? (
        <div className="mt-3 px-3">
          <HubSparkline
            data={live?.sparkline}
            color={TONE_HEX[workspace.tone]}
            className="h-10 w-full opacity-80"
            height={40}
          />
        </div>
      ) : null}

      <div className="mt-3 grid grid-cols-3 gap-px border-y border-border/70 bg-border/40">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-card px-3 py-3">
                <div className="hub-shimmer h-2.5 w-10 rounded" />
                <div className="hub-shimmer mt-2 h-4 w-14 rounded" />
              </div>
            ))
          : metrics.length
            ? metrics.map((m) => (
                <div key={m.label} className="bg-card px-3 py-3">
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
              <div className="col-span-3 bg-card px-4 py-3 text-xs text-muted-foreground">
                No activity yet
              </div>
            )}
      </div>

      <div className="mt-auto px-5 py-4">
        {workspace.pages.length ? (
          <p className="mb-3 line-clamp-1 text-[11px] text-muted-foreground">
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
                  className="rounded-lg p-1.5 text-muted-foreground/70 transition-colors hover:bg-muted hover:text-foreground"
                >
                  <AIcon className="h-3.5 w-3.5" />
                </button>
              );
            })}
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 text-[12px] font-medium transition-colors",
              TONE_STYLES[workspace.tone].text
            )}
          >
            Open Workspace
            <ArrowRight className="h-3.5 w-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
          </span>
        </div>
      </div>
    </motion.article>
  );
});

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/utils/cn";
import { fadeUp } from "./hubMotion";

interface HubWorkspaceZoneProps {
  id: "business" | "core";
  title: string;
  description: string;
  icon: LucideIcon;
  count: number;
  children: ReactNode;
  className?: string;
}

const ZONE_STYLES = {
  business: {
    accent: "bg-gradient-to-r from-orange-500 via-amber-500 to-orange-400",
    icon: "bg-orange-500/12 text-orange-700 ring-1 ring-orange-500/20 dark:text-orange-300",
    badge: "border border-orange-500/20 bg-orange-500/10 text-orange-700 dark:text-orange-300",
    eyebrow: "Industry",
  },
  core: {
    accent: "bg-gradient-to-r from-slate-500 via-sky-600 to-slate-400",
    icon: "bg-sky-500/12 text-sky-700 ring-1 ring-sky-500/20 dark:text-sky-300",
    badge: "border border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
    eyebrow: "Platform",
  },
} as const;

export function HubWorkspaceZone({
  id,
  title,
  description,
  icon: Icon,
  count,
  children,
  className,
}: HubWorkspaceZoneProps) {
  const tone = ZONE_STYLES[id];

  return (
    <motion.section
      variants={fadeUp}
      initial="hidden"
      animate="show"
      aria-labelledby={`hub-zone-${id}`}
      className={cn("hub-workspace-zone", `hub-workspace-zone--${id}`, className)}
    >
      <span className={cn("hub-workspace-zone-accent", tone.accent)} aria-hidden />
      <header className="hub-workspace-zone-header">
        <div className="flex min-w-0 items-start gap-3">
          <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl", tone.icon)}>
            <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
          </span>
          <div className="min-w-0">
            <p className="hub-section-label">{tone.eyebrow}</p>
            <h3
              id={`hub-zone-${id}`}
              className="mt-0.5 text-[16px] font-semibold tracking-tight text-foreground"
            >
              {title}
            </h3>
            <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{description}</p>
          </div>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums",
            tone.badge
          )}
        >
          {count} {count === 1 ? "workspace" : "workspaces"}
        </span>
      </header>
      <div className="hub-workspace-zone-body">{children}</div>
    </motion.section>
  );
}

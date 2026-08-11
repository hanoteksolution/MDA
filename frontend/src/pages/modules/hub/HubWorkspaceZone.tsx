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
    accent: "bg-orange-500",
    icon: "bg-orange-500/10 text-orange-700 dark:text-orange-300",
    badge: "bg-orange-500/10 text-orange-700 dark:text-orange-300",
  },
  core: {
    accent: "bg-slate-500",
    icon: "bg-slate-500/10 text-slate-700 dark:text-slate-300",
    badge: "bg-slate-500/10 text-slate-700 dark:text-slate-300",
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
          <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", tone.icon)}>
            <Icon className="h-4 w-4" strokeWidth={1.75} />
          </span>
          <div className="min-w-0">
            <h3 id={`hub-zone-${id}`} className="text-[15px] font-semibold tracking-tight text-foreground">
              {title}
            </h3>
            <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{description}</p>
          </div>
        </div>
        <span className={cn("shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums", tone.badge)}>
          {count} {count === 1 ? "workspace" : "workspaces"}
        </span>
      </header>
      <div className="hub-workspace-zone-body">{children}</div>
    </motion.section>
  );
}

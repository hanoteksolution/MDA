import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/utils/cn";
import { Badge } from "@/components/ui/badge";

interface PlatformProfileHeroProps {
  monogram: string;
  title: string;
  subtitle?: string;
  status?: { label: string; tone?: "success" | "warning" | "neutral" };
  meta?: { label: string; value: string }[];
  actions?: ReactNode;
  className?: string;
}

export function PlatformProfileHero({
  monogram,
  title,
  subtitle,
  status,
  meta = [],
  actions,
  className,
}: PlatformProfileHeroProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className={cn("platform-hero relative overflow-hidden rounded-2xl", className)}
    >
      <div className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 left-1/3 h-48 w-48 rounded-full bg-emerald-500/8 blur-3xl" />

      <div className="relative flex flex-col gap-6 p-6 sm:flex-row sm:items-end sm:justify-between sm:p-8">
        <div className="flex min-w-0 items-start gap-4 sm:gap-5">
          <motion.div
            initial={{ scale: 0.88, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-emerald-700 text-2xl font-semibold tracking-tight text-primary-foreground shadow-[0_12px_28px_-10px_hsl(var(--primary)/0.55)] sm:h-[4.5rem] sm:w-[4.5rem] sm:text-3xl"
          >
            {monogram.slice(0, 1).toUpperCase()}
          </motion.div>
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="truncate text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                {title}
              </h2>
              {status && (
                <Badge
                  variant={
                    status.tone === "success"
                      ? "success"
                      : status.tone === "warning"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {status.label}
                </Badge>
              )}
            </div>
            {subtitle && <p className="max-w-xl text-sm text-muted-foreground">{subtitle}</p>}
            {meta.length > 0 && (
              <div className="flex flex-wrap gap-x-5 gap-y-1.5 pt-1">
                {meta.map((item) => (
                  <div key={item.label} className="text-xs">
                    <span className="text-muted-foreground">{item.label}</span>
                    <span className="ml-1.5 font-medium text-foreground">{item.value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </motion.section>
  );
}

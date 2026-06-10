import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/utils/cn";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export interface KpiCardProps {
  title: string;
  value: string;
  icon?: ReactNode;
  trend?: string;
  trendUp?: boolean;
  loading?: boolean;
  className?: string;
  index?: number;
  accent?: "primary" | "success" | "warning" | "info";
}

const accentStyles = {
  primary: "from-primary/15 via-primary/5 to-transparent text-primary",
  success: "from-emerald-500/15 via-emerald-500/5 to-transparent text-emerald-600",
  warning: "from-amber-500/15 via-amber-500/5 to-transparent text-amber-600",
  info: "from-sky-500/15 via-sky-500/5 to-transparent text-sky-600",
};

const iconBg = {
  primary: "bg-gradient-to-br from-primary/20 to-primary/5 text-primary shadow-[0_8px_24px_-8px_hsl(var(--primary)/0.45)]",
  success: "bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 text-emerald-600",
  warning: "bg-gradient-to-br from-amber-500/20 to-amber-500/5 text-amber-600",
  info: "bg-gradient-to-br from-sky-500/20 to-sky-500/5 text-sky-600",
};

export function KpiCard({
  title,
  value,
  icon,
  trend,
  trendUp = true,
  loading,
  className,
  index = 0,
  accent = "primary",
}: KpiCardProps) {
  if (loading) {
    return (
      <Card className={cn("ds-card-premium min-h-[148px] overflow-hidden", className)}>
        <CardContent className="flex min-h-[148px] flex-col justify-center px-7 py-8">
          <Skeleton className="mb-5 h-4 w-24" />
          <Skeleton className="mb-3 h-9 w-32" />
          <Skeleton className="h-3 w-16" />
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="h-full"
    >
      <Card
        className={cn(
          "ds-card-premium group relative h-full min-h-[148px] overflow-hidden border-border/60 transition-all duration-300",
          "hover:border-primary/25 hover:shadow-elevated",
          className
        )}
      >
        <div
          className={cn(
            "pointer-events-none absolute inset-0 bg-gradient-to-br opacity-60 transition-opacity group-hover:opacity-100",
            accentStyles[accent]
          )}
        />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
        <CardContent className="relative flex min-h-[148px] flex-col justify-center px-7 py-8">
          <div className="flex items-center justify-between gap-5">
            <div className="min-w-0 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {title}
              </p>
              <motion.p
                className="text-2xl font-bold tracking-tight text-foreground xl:text-[1.65rem]"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.06 + 0.15, duration: 0.35 }}
              >
                {value}
              </motion.p>
              {trend && (
                <div className="flex items-center gap-1.5">
                  {trendUp ? (
                    <TrendingUp className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5 text-destructive" />
                  )}
                  <span
                    className={cn(
                      "text-xs font-semibold",
                      trendUp ? "text-success" : "text-destructive"
                    )}
                  >
                    {trend}
                  </span>
                  <span className="text-xs text-muted-foreground">vs last period</span>
                </div>
              )}
            </div>
            {icon && (
              <motion.div
                className={cn(
                  "flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-105",
                  iconBg[accent]
                )}
                whileHover={{ rotate: 3 }}
              >
                {icon}
              </motion.div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

interface KpiGridProps {
  children: ReactNode;
  className?: string;
  columns?: 3 | 4 | 5;
}

export function KpiGrid({ children, className, columns = 4 }: KpiGridProps) {
  const colClass = {
    3: "sm:grid-cols-2 lg:grid-cols-3",
    4: "sm:grid-cols-2 lg:grid-cols-4",
    5: "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5",
  }[columns];

  return (
    <div className={cn("grid w-full grid-cols-1 gap-4", colClass, className)}>
      {children}
    </div>
  );
}

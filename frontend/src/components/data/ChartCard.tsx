import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/utils/cn";

interface ChartCardProps {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  height?: number;
  index?: number;
}

export function ChartCard({
  title,
  description,
  action,
  children,
  className,
  height = 280,
  index = 0,
}: ChartCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
      className={cn("h-full", className)}
    >
      <Card
        className={cn(
          "ds-card-premium group relative h-full overflow-hidden border-border/60 transition-all duration-300",
          "hover:border-primary/20 hover:shadow-elevated"
        )}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
        <CardHeader className="flex-row items-start justify-between space-y-0 pb-2">
          <div>
            <CardTitle className="text-base font-semibold tracking-tight">{title}</CardTitle>
            {description && (
              <CardDescription className="mt-1 text-xs">{description}</CardDescription>
            )}
          </div>
          {action}
        </CardHeader>
        <CardContent className="pt-0">
          <div
            className="rounded-xl bg-gradient-to-b from-muted/30 to-transparent p-1"
            style={{ height }}
          >
            {children}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

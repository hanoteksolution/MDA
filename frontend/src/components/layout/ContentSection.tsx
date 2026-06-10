import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/utils/cn";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ContentSectionProps {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
  index?: number;
}

export function ContentSection({
  title,
  description,
  action,
  children,
  className,
  noPadding,
  index = 0,
}: ContentSectionProps) {
  if (!title) {
    return <div className={cn("ds-card-premium", className)}>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
    >
      <Card
        className={cn(
          "ds-card-premium relative overflow-hidden border-border/60 transition-all duration-300 hover:shadow-elevated",
          className
        )}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent" />
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base font-semibold tracking-tight">{title}</CardTitle>
            {description && (
              <CardDescription className="mt-1 text-xs">{description}</CardDescription>
            )}
          </div>
          {action}
        </CardHeader>
        <CardContent className={cn(noPadding && "p-0 pt-0")}>{children}</CardContent>
      </Card>
    </motion.div>
  );
}

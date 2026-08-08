import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { cn } from "@/utils/cn";
import { typography } from "@/design-system";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  /** Compact variant for tables / inline panels */
  compact?: boolean;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "px-4 py-10" : "py-16",
        className
      )}
      role="status"
    >
      <div
        className={cn(
          "mb-4 flex items-center justify-center rounded-2xl bg-muted/70 text-muted-foreground",
          compact ? "mb-3 h-12 w-12" : "mb-6 h-16 w-16 bg-primary/10 text-primary"
        )}
      >
        {icon ?? <Inbox className={compact ? "h-5 w-5" : "h-7 w-7"} />}
      </div>
      <h3 className={cn(typography.emptyTitle, compact && "text-sm")}>{title}</h3>
      {description && (
        <p className={cn(typography.emptyDescription, "mt-1.5 max-w-md", compact && "text-xs")}>
          {description}
        </p>
      )}
      {action && <div className={cn(compact ? "mt-4" : "mt-6")}>{action}</div>}
    </div>
  );
}

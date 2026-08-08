import { Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";
import { Skeleton } from "@/components/ui/skeleton";

interface LoadingStateProps {
  label?: string;
  className?: string;
  /** Skeleton rows for list/table placeholders */
  variant?: "spinner" | "page" | "rows";
  rows?: number;
}

export function LoadingState({
  label = "Loading…",
  className,
  variant = "spinner",
  rows = 5,
}: LoadingStateProps) {
  if (variant === "rows") {
    return (
      <div className={cn("space-y-2 p-4", className)} role="status" aria-label={label}>
        {[...Array(rows)].map((_, i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (variant === "page") {
    return (
      <div className={cn("space-y-4", className)} role="status" aria-label={label}>
        <div className="flex items-center justify-between gap-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-9 w-28" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 text-sm text-muted-foreground",
        className
      )}
      role="status"
    >
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <span>{label}</span>
    </div>
  );
}

import type { ReactNode } from "react";
import { cn } from "@/utils/cn";

interface FormPageLayoutProps {
  main: ReactNode;
  aside?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

/** Full-width form layout: 2/3 main column + 1/3 sticky sidebar on xl screens. */
export function FormPageLayout({ main, aside, actions, className }: FormPageLayoutProps) {
  return (
    <div className={cn("w-full space-y-6", className)}>
      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">{main}</div>
        {aside && (
          <div className="space-y-6 xl:sticky xl:top-0 xl:max-h-[calc(100vh-8rem)] xl:overflow-y-auto xl:scrollbar-thin">
            {aside}
          </div>
        )}
      </div>
      {actions}
    </div>
  );
}

interface FormActionsProps {
  children: ReactNode;
  className?: string;
}

export function FormActions({ children, className }: FormActionsProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 rounded-2xl border border-border",
        "bg-card px-6 py-4 shadow-sm",
        className
      )}
    >
      {children}
    </div>
  );
}

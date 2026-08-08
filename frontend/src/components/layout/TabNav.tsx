import { cn } from "@/utils/cn";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

interface TabNavProps {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}

export function TabNav({ tabs, active, onChange, className }: TabNavProps) {
  return (
    <div
      className={cn(
        "flex flex-nowrap gap-1 overflow-x-auto rounded-xl border border-border bg-muted/40 p-1 scrollbar-thin",
        className
      )}
      role="tablist"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            "inline-flex min-h-9 shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all",
            active === tab.id
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:bg-card/60 hover:text-foreground"
          )}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span
              className={cn(
                "rounded-full px-1.5 py-0.5 text-[11px] tabular-nums",
                active === tab.id ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
              )}
            >
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

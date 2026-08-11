import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import type { ModuleWorkspace } from "@/navigation/moduleWorkspaces";
import { HUB_CATEGORY_GROUPS, TONE_STYLES } from "@/navigation/moduleWorkspaces";
import { cn } from "@/utils/cn";

interface HubWorkspaceSwitcherProps {
  workspaces: ModuleWorkspace[];
  activeCode?: string | null;
  onSelect: (code: string, route: string) => void;
  className?: string;
}

const BUSINESS_CATS = new Set(
  HUB_CATEGORY_GROUPS.find((g) => g.id === "business")?.categories ?? []
);

export function HubWorkspaceSwitcher({
  workspaces,
  activeCode,
  onSelect,
  className,
}: HubWorkspaceSwitcherProps) {
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const launchers = useMemo(
    () => workspaces.filter((w) => w.code !== "overview" && w.kind !== "capability"),
    [workspaces]
  );
  const businessItems = useMemo(
    () => launchers.filter((w) => BUSINESS_CATS.has(w.category)),
    [launchers]
  );
  const coreItems = useMemo(
    () => launchers.filter((w) => !BUSINESS_CATS.has(w.category)),
    [launchers]
  );
  const flat = useMemo(() => [...businessItems, ...coreItems], [businessItems, coreItems]);
  const active = launchers.find((w) => w.code === activeCode) || flat[0];
  const ActiveIcon = active?.icon;

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlight((h) => Math.min(h + 1, flat.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlight((h) => Math.max(h - 1, 0));
      }
      if (e.key === "Enter" && flat[highlight]) {
        e.preventDefault();
        const w = flat[highlight];
        onSelect(w.code, w.route);
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, flat, highlight, onSelect]);

  if (!flat.length) return null;

  const renderGroup = (label: string, items: ModuleWorkspace[]) => {
    if (!items.length) return null;
    return (
      <div className="py-1.5">
        <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </p>
        <ul role="listbox" aria-label={label}>
          {items.map((w) => {
            const idx = flat.findIndex((f) => f.code === w.code);
            const Icon = w.icon;
            const selected = w.code === active?.code;
            return (
              <li key={w.code}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onMouseEnter={() => setHighlight(idx)}
                  onClick={() => {
                    onSelect(w.code, w.route);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors",
                    highlight === idx || selected ? "bg-muted/80" : "hover:bg-muted/50"
                  )}
                >
                  <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg", TONE_STYLES[w.tone].accent)}>
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-medium">{w.label}</span>
                    <span className="block truncate text-[11px] text-muted-foreground">{w.description}</span>
                  </span>
                  {selected ? <Check className="h-3.5 w-3.5 shrink-0 text-foreground" /> : null}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    );
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex max-w-[11rem] items-center gap-2 rounded-xl border border-border/80 bg-background px-2.5 py-1.5 text-left transition-colors hover:border-foreground/20 hover:bg-muted/40"
      >
        {ActiveIcon ? (
          <span className={cn("flex h-6 w-6 items-center justify-center rounded-md", TONE_STYLES[active!.tone].accent)}>
            <ActiveIcon className="h-3.5 w-3.5" />
          </span>
        ) : null}
        <span className="min-w-0 flex-1 truncate text-[12px] font-medium">{active?.label || "Workspace"}</span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      </button>

      {open ? (
        <div className="absolute right-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-border/80 bg-card shadow-lg">
          <div className="max-h-[min(24rem,70vh)] overflow-y-auto scrollbar-thin">
            {renderGroup("Your Workspaces", businessItems)}
            {renderGroup("Core", coreItems)}
          </div>
        </div>
      ) : null}
    </div>
  );
}

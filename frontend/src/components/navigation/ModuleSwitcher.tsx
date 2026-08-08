import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, LayoutGrid } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePermissions } from "@/hooks/usePermissions";
import { useModules } from "@/hooks/useModules";
import { workspacesForModules, type ModuleWorkspace } from "@/navigation/moduleWorkspaces";
import { cn } from "@/utils/cn";

function workspaceFromPath(pathname: string): string | null {
  if (pathname.startsWith("/gym")) return "gym";
  if (pathname.startsWith("/hotel")) return "hotel";
  if (pathname.startsWith("/housing")) return "housing";
  if (pathname.startsWith("/office")) return "office";
  if (pathname.startsWith("/property")) return "property";
  if (pathname.startsWith("/restaurant")) return "restaurant";
  if (pathname.startsWith("/pharmacy")) return "pharmacy";
  if (pathname.startsWith("/futsal")) return "futsal";
  if (pathname.startsWith("/pos")) return "pos";
  if (pathname.startsWith("/inventory") || pathname.startsWith("/products")) return "inventory";
  if (pathname.startsWith("/finance")) return "finance";
  if (pathname.startsWith("/dashboard")) return "overview";
  return null;
}

export function ModuleSwitcher({ compact }: { compact?: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const { isSuperAdmin, hasPermission } = usePermissions();
  const { modules } = useModules();
  const activeWorkspace = useUIStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useUIStore((s) => s.setActiveWorkspace);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const list = workspacesForModules(user?.enabled_modules ?? modules, {
    isSuperAdmin,
    includeFinance: isSuperAdmin || hasPermission("finance.view"),
  });

  useEffect(() => {
    const inferred = workspaceFromPath(location.pathname);
    if (inferred && inferred !== activeWorkspace) {
      setActiveWorkspace(inferred);
    }
    // Sync workspace from URL only — avoid looping on store updates
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const current =
    list.find((w) => w.code === activeWorkspace) || list.find((w) => w.code === "overview") || list[0];

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const select = (w: ModuleWorkspace) => {
    setActiveWorkspace(w.code);
    setOpen(false);
    navigate(w.route);
  };

  if (list.length <= 2) {
    return null;
  }

  const Icon = current?.icon || LayoutGrid;

  return (
    <div ref={ref} className="relative hidden md:block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex items-center gap-2 rounded-xl border border-border bg-background text-sm transition-colors hover:bg-muted/50",
          compact ? "px-2.5 py-1.5" : "px-3 py-2"
        )}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <Icon className="h-4 w-4 text-primary" />
        <span className="max-w-[100px] truncate font-medium xl:max-w-[140px]">{current?.label}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </button>
      {open ? (
        <div
          role="listbox"
          className="absolute left-0 z-50 mt-1.5 min-w-[200px] rounded-xl border border-border bg-card p-1.5 shadow-lg"
        >
          <p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Workspaces
          </p>
          {list.map((w) => {
            const WIcon = w.icon;
            const active = w.code === current?.code;
            return (
              <button
                key={w.code}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => select(w)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                  active ? "bg-primary/10 text-primary" : "hover:bg-muted/60"
                )}
              >
                <WIcon className="h-4 w-4 shrink-0" />
                <span className="font-medium">{w.label}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

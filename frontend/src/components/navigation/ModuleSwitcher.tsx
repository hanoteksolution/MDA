import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, LayoutGrid } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePermissions } from "@/hooks/usePermissions";
import { useModules } from "@/hooks/useModules";
import { TONE_STYLES, type ModuleWorkspace } from "@/navigation/moduleWorkspaces";
import { switcherWorkspacesForUser } from "@/navigation/businessWorkspaces";
import { recordHubVisit } from "@/pages/modules/hub/hubStorage";
import { workspaceFromPath } from "@/theme/workspaceBrand";
import { cn } from "@/utils/cn";

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

  const list = switcherWorkspacesForUser(user?.enabled_modules ?? modules, {
    elevated: isSuperAdmin,
    includeFinance: isSuperAdmin || hasPermission("finance.view"),
    hasPermission,
  });

  const industries = list.filter((w) => w.kind === "industry");
  const centralFinance = list.filter((w) => w.code === "finance" || w.code === "reports");
  const platform = list.filter(
    (w) => w.kind === "platform" && w.code !== "finance" && w.code !== "reports"
  );

  useEffect(() => {
    const inferred = workspaceFromPath(location.pathname);
    if (inferred && inferred !== activeWorkspace) {
      setActiveWorkspace(inferred);
    }
    // Sync workspace from URL only — avoid looping on store updates
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const current =
    list.find((w) => w.code === activeWorkspace) ||
    list.find((w) => w.code === "overview") ||
    list[0];

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const select = (w: ModuleWorkspace) => {
    setActiveWorkspace(w.code);
    recordHubVisit(w.code);
    setOpen(false);
    navigate(w.route);
  };

  if (list.length <= 1) {
    return null;
  }

  const Icon = current?.icon || LayoutGrid;

  const renderItem = (w: ModuleWorkspace) => {
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
        <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-lg", TONE_STYLES[w.tone].accent)}>
          <WIcon className="h-3.5 w-3.5" />
        </span>
        <span className="font-medium">{w.label}</span>
      </button>
    );
  };

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
        <Icon className="h-4 w-4 text-primary" aria-hidden />
        <span className="max-w-[100px] truncate font-medium xl:max-w-[140px]">{current?.label}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </button>
      {open ? (
        <div
          role="listbox"
          className="absolute left-0 z-50 mt-1.5 min-w-[220px] rounded-xl border border-border bg-card p-1.5 shadow-lg"
        >
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/modules");
            }}
            className="mb-1 flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm hover:bg-muted/60"
          >
            <LayoutGrid className="h-4 w-4 shrink-0 text-primary" />
            <span className="font-medium">All workspaces</span>
          </button>
          {industries.length ? (
            <>
              <p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Business workspaces
              </p>
              {industries.map(renderItem)}
            </>
          ) : null}
          {centralFinance.length ? (
            <>
              <p className="mt-1 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Central Finance
              </p>
              {centralFinance.map(renderItem)}
            </>
          ) : null}
          {platform.length ? (
            <>
              <p className="mt-1 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Platform
              </p>
              {platform.map(renderItem)}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

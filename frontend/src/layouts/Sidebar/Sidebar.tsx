import { useEffect, useMemo, useState } from "react";
import { LogOut, PanelLeftClose, PanelLeft } from "lucide-react";
import { NavLink } from "react-router-dom";
import { resolveMediaUrl } from "@/config/api";
import { cn } from "@/utils/cn";
import { settingsApi } from "@/services/api/admin";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import { useModules } from "@/hooks/useModules";
import { MODULE_WORKSPACES } from "@/navigation/moduleWorkspaces";
import {
  industryNavSections,
  industryWorkspacesForUser,
  isIndustryPath,
  overviewNavSections,
  platformNavSections,
  type WorkspaceNavSection,
} from "@/navigation/businessWorkspaces";

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, activeWorkspace } = useUIStore();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const { hasPermission, hasAnyPermission, isSuperAdmin } = usePermissions();
  const { hasModule, hasAnyModule, modules } = useModules();
  const [companyName, setCompanyName] = useState("MDA ERP");
  const [logoUrl, setLogoUrl] = useState<string | undefined>();

  useEffect(() => {
    let active = true;
    const loadCompany = async () => {
      try {
        const res = await settingsApi.company();
        if (!active || !res.data) return;
        setCompanyName(res.data.name || "MDA ERP");
        setLogoUrl(resolveMediaUrl(res.data.logo));
      } catch {
        /* keep defaults */
      }
    };
    loadCompany();
    const onUpdate = () => loadCompany();
    window.addEventListener("mda:company-updated", onUpdate);
    return () => {
      active = false;
      window.removeEventListener("mda:company-updated", onUpdate);
    };
  }, []);

  const focused =
    activeWorkspace && activeWorkspace !== "overview" && activeWorkspace !== "hub"
      ? MODULE_WORKSPACES.find((w) => w.code === activeWorkspace)
      : null;

  const industryList = useMemo(
    () =>
      industryWorkspacesForUser(user?.enabled_modules ?? modules, {
        elevated: isSuperAdmin,
        hasPermission,
      }),
    [user?.enabled_modules, modules, isSuperAdmin, hasPermission]
  );

  const visibleSections: WorkspaceNavSection[] = useMemo(() => {
    const opts = {
      elevated: isSuperAdmin,
      enabled: user?.enabled_modules ?? modules,
      hasPermission,
      hasAnyPermission,
      hasModule,
      hasAnyModule,
    };
    if (focused && isIndustryPath(focused.code)) {
      return industryNavSections(focused.code, opts);
    }
    if (focused && (focused.kind === "platform" || ["finance", "reports", "admin", "settings", "platform"].includes(focused.code))) {
      const platform = platformNavSections(focused.code, opts);
      if (platform.length) return platform;
    }
    return overviewNavSections(industryList, {
      elevated: isSuperAdmin,
      hasPermission,
      includeFinance: isSuperAdmin || hasPermission("finance.view"),
      includeAdmin: true,
      includePlatform: isSuperAdmin || hasPermission("platform.view"),
    });
  }, [
    focused,
    industryList,
    isSuperAdmin,
    user?.enabled_modules,
    modules,
    hasPermission,
    hasAnyPermission,
    hasModule,
    hasAnyModule,
  ]);

  const initial = (companyName || "M").charAt(0).toUpperCase();

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300",
        sidebarCollapsed ? "w-[64px] xl:w-[72px]" : "w-[220px] xl:w-[280px]"
      )}
    >
      <div
        className={cn(
          "flex shrink-0 items-center justify-between border-b border-sidebar-border px-3 xl:px-4",
          "h-12 xl:h-[72px]"
        )}
      >
        {!sidebarCollapsed ? (
          <NavLink to="/modules" className="flex min-w-0 flex-1 items-center gap-2.5" title="All workspaces">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt=""
                className="h-9 w-9 shrink-0 rounded-xl object-contain bg-background border border-border"
              />
            ) : (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold text-sm">
                {initial}
              </div>
            )}
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-foreground">{companyName}</p>
              <p className="text-[10px] text-muted-foreground">
                {focused?.kind === "industry" ? focused.label : "Enterprise Edition"}
              </p>
            </div>
          </NavLink>
        ) : (
          <NavLink to="/modules" className="flex flex-1 justify-center" title="All workspaces">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt=""
                className="h-8 w-8 rounded-lg object-contain bg-background border border-border"
                title={companyName}
              />
            ) : (
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-xs"
                title={companyName}
              >
                {initial}
              </div>
            )}
          </NavLink>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-2 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarCollapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3 scrollbar-thin xl:px-3 xl:py-4">
        {visibleSections.map((section) => (
          <div key={section.label} className="mb-4 xl:mb-5">
            {!sidebarCollapsed && (
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                {section.label}
              </p>
            )}
            {sidebarCollapsed && <div className="mx-auto mb-1.5 h-px w-6 bg-sidebar-border" aria-hidden />}
            <div className="space-y-0.5">
              {section.items.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={`${to}-${label}`}
                  to={to}
                  end={end}
                  title={label}
                  aria-label={label}
                  className={({ isActive }) =>
                    cn(
                      "group relative flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all",
                      sidebarCollapsed && "justify-center px-2",
                      isActive
                        ? "bg-primary/10 text-primary shadow-sm"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                      )}
                      <Icon className="h-[18px] w-[18px] shrink-0" />
                      {!sidebarCollapsed && <span className="truncate">{label}</span>}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        {!sidebarCollapsed && user && (
          <div className="mb-2 flex items-center gap-3 rounded-xl bg-sidebar-accent px-3 py-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary text-xs font-bold">
              {user.username?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{user.first_name || user.username}</p>
              <p className="truncate text-xs text-muted-foreground">{user.role?.name}</p>
            </div>
          </div>
        )}
        <button
          onClick={() => logout()}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-colors"
        >
          <LogOut className="h-[18px] w-[18px] shrink-0" />
          {!sidebarCollapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}

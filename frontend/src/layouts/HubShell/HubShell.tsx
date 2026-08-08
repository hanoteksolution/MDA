import { useEffect, useMemo, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { LayoutGrid, LogOut, Moon, Search, Sun } from "lucide-react";
import { PageMetaProvider } from "@/contexts/PageMetaContext";
import { NotificationDrawer, NotificationBellButton } from "@/components/notifications/NotificationDrawer";
import { SubscriptionAlertDialog } from "@/components/platform/SubscriptionAlertDialog";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePermissions } from "@/hooks/usePermissions";
import { useWorkspaceTheme } from "@/hooks/useWorkspaceTheme";
import { settingsApi } from "@/services/api/admin";
import { resolveMediaUrl } from "@/config/api";
import { hubWorkspacesForUser } from "@/navigation/postLogin";
import { HUB_QUICK_ACTIONS, filterQuickActions } from "@/navigation/moduleWorkspaces";
import { HubCommandSearch } from "@/pages/modules/hub/HubCommandSearch";
import { recordHubVisit } from "@/pages/modules/hub/hubStorage";
import { cn } from "@/utils/cn";

function HubHeader({ onOpenSearch }: { onOpenSearch: () => void }) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { darkMode, toggleDarkMode, setActiveWorkspace } = useUIStore();
  const [companyName, setCompanyName] = useState("MDA ERP");
  const [logoUrl, setLogoUrl] = useState<string | undefined>();

  useEffect(() => {
    let active = true;
    settingsApi
      .company()
      .then((res) => {
        if (!active || !res.data) return;
        setCompanyName(res.data.name || "MDA ERP");
        setLogoUrl(resolveMediaUrl(res.data.logo));
      })
      .catch(() => {
        /* keep defaults */
      });
    return () => {
      active = false;
    };
  }, []);

  const initial = (companyName || "M").charAt(0).toUpperCase();
  const displayName =
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || "User";
  const tenantLabel = user?.branch?.name || user?.managed_shop_group?.name;

  return (
    <header className="hub-topbar relative sticky top-0 z-40 flex h-[3.75rem] shrink-0 items-center gap-3 px-4 sm:px-6 lg:px-8">
      <span className="pointer-events-none absolute inset-x-0 bottom-0 h-0.5 bg-primary/70" aria-hidden />
      <button
        type="button"
        onClick={() => {
          setActiveWorkspace("hub");
          navigate("/modules");
        }}
        className="flex min-w-0 items-center gap-2.5"
      >
        {logoUrl ? (
          <img
            src={logoUrl}
            alt=""
            className="h-8 w-8 shrink-0 rounded-lg border border-border/80 bg-background object-contain"
          />
        ) : (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-foreground text-[11px] font-semibold text-background">
            {initial}
          </div>
        )}
        <span className="min-w-0 text-left">
          <span className="block truncate text-[13px] font-semibold tracking-tight">{companyName}</span>
          {tenantLabel ? (
            <span className="hidden truncate text-[11px] text-muted-foreground sm:block">{tenantLabel}</span>
          ) : null}
        </span>
      </button>

      <button
        type="button"
        onClick={onOpenSearch}
        className="mx-auto hidden min-w-0 max-w-xl flex-1 items-center gap-3 rounded-full border border-white/60 bg-white/50 px-4 py-2 text-left text-[13px] text-muted-foreground shadow-sm backdrop-blur-xl transition-colors hover:border-white hover:bg-white/80 md:flex dark:border-white/10 dark:bg-white/10 dark:hover:bg-white/15"
      >
        <Search className="h-3.5 w-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate">Search workspaces, customers, invoices…</span>
        <kbd className="hidden h-5 items-center rounded border border-border bg-background px-1.5 text-[10px] font-medium text-muted-foreground lg:inline-flex">
          ⌘K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
        <button
          type="button"
          onClick={onOpenSearch}
          className="rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground md:hidden"
          aria-label="Search"
        >
          <Search className="h-[18px] w-[18px]" />
        </button>
        <button
          type="button"
          onClick={() => navigate("/modules")}
          className="hidden rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:inline-flex"
          aria-label="All workspaces"
        >
          <LayoutGrid className="h-[18px] w-[18px]" />
        </button>
        <NotificationBellButton />
        <button
          type="button"
          onClick={toggleDarkMode}
          className="rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Toggle theme"
        >
          {darkMode ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </button>
        <div className={cn("hidden items-center gap-2 border-l border-border/70 pl-3 sm:flex")}>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-[12px] font-semibold">
            {displayName.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-medium leading-none">{displayName}</p>
            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{user?.role?.name || "User"}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => logout()}
          className="rounded-xl p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}

export function HubShell() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const { hasPermission, isSuperAdmin } = usePermissions();
  const setActiveWorkspace = useUIStore((s) => s.setActiveWorkspace);
  const [searchOpen, setSearchOpen] = useState(false);
  useWorkspaceTheme();

  const workspaces = useMemo(
    () => hubWorkspacesForUser(user, hasPermission),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, isSuperAdmin, user?.enabled_modules, user?.permissions]
  );
  const quickActions = useMemo(
    () =>
      filterQuickActions(HUB_QUICK_ACTIONS, {
        enabled: user?.enabled_modules,
        isSuperAdmin,
        hasPermission,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, isSuperAdmin, user?.enabled_modules, user?.permissions]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <PageMetaProvider>
      <SubscriptionAlertDialog />
      <NotificationDrawer />
      <HubCommandSearch
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        workspaces={workspaces}
        quickActions={quickActions}
        onOpenWorkspace={(code, route) => {
          setActiveWorkspace(code);
          recordHubVisit(code);
          navigate(route);
        }}
      />
      <div className="flex min-h-dvh flex-col bg-background">
        <HubHeader onOpenSearch={() => setSearchOpen(true)} />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </PageMetaProvider>
  );
}

import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Warehouse,
  Truck,
  Receipt,
  Users,
  Building2,
  Wallet,
  BarChart3,
  Settings,
  LogOut,
  PanelLeftClose,
  PanelLeft,
  Shield,
  UserCheck,
  Globe2,
  CreditCard,
  Goal,
  CalendarDays,
  ScrollText,
  Tags,
  Trash2,
  Pill,
  Dumbbell,
  FlaskConical,
  UtensilsCrossed,
  BedDouble,
  Home,
  Briefcase,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { resolveMediaUrl } from "@/config/api";
import { cn } from "@/utils/cn";
import { settingsApi } from "@/services/api/admin";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import { useModules } from "@/hooks/useModules";
import { MODULE_WORKSPACES } from "@/navigation/moduleWorkspaces";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  permission?: string | string[];
  module?: string | string[];
  /** When set, item stays visible in focused workspaces that include any of these codes */
  workspaces?: string[];
}

const navSections: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [{ to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, permission: "dashboard.view" }],
  },
  {
    label: "Operations",
    items: [
      { to: "/pos", label: "POS", icon: ShoppingCart, permission: "pos.access", module: "pos", workspaces: ["pos", "restaurant", "pharmacy"] },
      { to: "/sales", label: "Sales", icon: Receipt, permission: "sales.view", module: "sales", workspaces: ["pos", "restaurant"] },
      { to: "/receipts", label: "Receipts", icon: ScrollText, permission: "sales.view", module: "sales", workspaces: ["pos", "restaurant"] },
      { to: "/expenses", label: "Expenses", icon: Wallet, permission: ["finance.view", "sales.view"], module: "sales", workspaces: ["pos", "finance"] },
      { to: "/daily-ops", label: "Daily Ops", icon: CalendarDays, permission: "sales.view", module: "sales", workspaces: ["pos", "restaurant"] },
      { to: "/waiter-performance", label: "Waiters", icon: UserCheck, permission: ["pos.access", "sales.view"], module: "pos", workspaces: ["pos", "restaurant"] },
      { to: "/purchases", label: "Purchases", icon: Truck, permission: "purchases.view", module: "purchases", workspaces: ["inventory", "pharmacy"] },
      { to: "/trash", label: "Trash", icon: Trash2, permission: "trash.view", module: "sales", workspaces: ["pos"] },
    ],
  },
  {
    label: "Catalog",
    items: [
      { to: "/products", label: "Products", icon: Package, permission: "products.view", module: "inventory", workspaces: ["inventory", "pharmacy", "pos"] },
      { to: "/categories", label: "Categories", icon: Tags, permission: "products.view", module: "inventory", workspaces: ["inventory", "pharmacy"] },
      { to: "/inventory", label: "Inventory", icon: Warehouse, permission: "inventory.view", module: "inventory", workspaces: ["inventory", "pharmacy"] },
      { to: "/customers", label: "Customers", icon: Users, permission: "customers.view", module: "sales", workspaces: ["pos", "gym", "pharmacy"] },
      { to: "/suppliers", label: "Suppliers", icon: Building2, permission: "suppliers.view", module: "purchases", workspaces: ["inventory", "pharmacy"] },
    ],
  },
  {
    label: "Venue",
    items: [
      { to: "/futsal", label: "Futsal", icon: Goal, permission: "futsal.view", module: "futsal", workspaces: ["futsal"] },
      { to: "/pharmacy", label: "Pharmacy", icon: Pill, permission: "pharmacy.view", module: "pharmacy", workspaces: ["pharmacy"] },
      { to: "/gym", label: "Gym", icon: Dumbbell, permission: "gym.view", module: "gym", workspaces: ["gym"] },
      { to: "/restaurant", label: "Restaurant", icon: UtensilsCrossed, permission: "restaurant.view", module: "restaurant", workspaces: ["restaurant"] },
      { to: "/hotel", label: "Hotel", icon: BedDouble, permission: "hotel.view", module: "hotel", workspaces: ["hotel"] },
      { to: "/property", label: "Property", icon: Building2, permission: "property_management.view", module: "property_management", workspaces: ["property"] },
      { to: "/housing", label: "Housing", icon: Home, permission: "housing_rental.view", module: "housing_rental", workspaces: ["property", "housing"] },
      { to: "/office", label: "Office", icon: Briefcase, permission: "office_rental.view", module: "office_rental", workspaces: ["property", "office"] },
    ],
  },
  {
    label: "Finance & Reports",
    items: [
      { to: "/finance", label: "Finance", icon: Wallet, permission: "finance.view", workspaces: ["finance"] },
      { to: "/reports", label: "Reports", icon: BarChart3, permission: "reports.view", workspaces: ["finance"] },
      { to: "/staff-performance", label: "Staff Performance", icon: UserCheck, permission: "staff.performance.view", workspaces: ["finance"] },
    ],
  },
  {
    label: "Platform",
    items: [
      { to: "/platform/tenants", label: "Tenants", icon: Building2, permission: "platform.view" },
      { to: "/platform", label: "Shops", icon: Globe2, permission: "platform.view" },
      { to: "/platform/demos", label: "Demo Accounts", icon: FlaskConical, permission: "platform.view" },
      { to: "/platform/subscriptions", label: "Subscriptions", icon: CreditCard, permission: "subscriptions.manage" },
    ],
  },
  {
    label: "System",
    items: [
      {
        to: "/admin",
        label: "Administration",
        icon: Shield,
        permission: ["users.view", "roles.view"],
      },
      { to: "/settings", label: "Settings", icon: Settings, permission: "settings.view" },
    ],
  },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, activeWorkspace } = useUIStore();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const { hasPermission, hasAnyPermission } = usePermissions();
  const { hasModule, hasAnyModule } = useModules();
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

  const focusedWorkspace =
    activeWorkspace && activeWorkspace !== "overview"
      ? MODULE_WORKSPACES.find((w) => w.code === activeWorkspace)
      : null;

  const canSeeItem = (item: NavItem) => {
    if (item.module) {
      const ok = Array.isArray(item.module)
        ? hasAnyModule(...item.module)
        : hasModule(item.module);
      if (!ok) return false;
    }
    if (!item.permission) return true;
    const permOk = Array.isArray(item.permission)
      ? hasAnyPermission(...item.permission)
      : hasPermission(item.permission);
    if (!permOk) return false;
    // Workspace focus: keep System/Platform + items tagged for this workspace
    if (focusedWorkspace) {
      if (!item.workspaces) return true;
      if (item.workspaces.includes(focusedWorkspace.code)) return true;
      // Also show items whose module matches the workspace modules
      if (item.module) {
        const mods = Array.isArray(item.module) ? item.module : [item.module];
        if (focusedWorkspace.modules.some((m) => mods.includes(m))) return true;
      }
      return false;
    }
    return true;
  };

  const visibleSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(canSeeItem),
    }))
    .filter((section) => section.items.length > 0);

  const initial = (companyName || "M").charAt(0).toUpperCase();

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300",
        sidebarCollapsed ? "w-[64px] xl:w-[72px]" : "w-[220px] xl:w-[280px]"
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex shrink-0 items-center justify-between border-b border-sidebar-border px-3 xl:px-4",
          "h-12 xl:h-[72px]"
        )}
      >
        {!sidebarCollapsed ? (
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
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
              <p className="text-[10px] text-muted-foreground">Enterprise Edition</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-1 justify-center">
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
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-2 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 scrollbar-thin xl:px-3 xl:py-4">
        {visibleSections.map((section) => (
          <div key={section.label} className="mb-4 xl:mb-5">
            {!sidebarCollapsed && (
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                {section.label}
              </p>
            )}
            {sidebarCollapsed && (
              <div className="mx-auto mb-1.5 h-px w-6 bg-sidebar-border" aria-hidden />
            )}
            <div className="space-y-0.5">
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
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

      {/* User footer */}
      <div className="border-t border-sidebar-border p-3">
        {!sidebarCollapsed && user && (
          <div className="mb-2 flex items-center gap-3 rounded-xl bg-sidebar-accent px-3 py-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary text-xs font-bold">
              {user.username?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-foreground">
                {user.first_name || user.username}
              </p>
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

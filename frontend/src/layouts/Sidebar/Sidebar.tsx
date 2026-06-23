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
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/utils/cn";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  permission?: string | string[];
}

const navSections: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [{ to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, permission: "dashboard.view" }],
  },
  {
    label: "Operations",
    items: [
      { to: "/pos", label: "POS", icon: ShoppingCart, permission: "pos.access" },
      { to: "/sales", label: "Sales", icon: Receipt, permission: "sales.view" },
      { to: "/purchases", label: "Purchases", icon: Truck, permission: "purchases.view" },
    ],
  },
  {
    label: "Catalog",
    items: [
      { to: "/products", label: "Products", icon: Package, permission: "products.view" },
      { to: "/inventory", label: "Inventory", icon: Warehouse, permission: "inventory.view" },
      { to: "/customers", label: "Customers", icon: Users, permission: "customers.view" },
      { to: "/suppliers", label: "Suppliers", icon: Building2, permission: "suppliers.view" },
    ],
  },
  {
    label: "Venue",
    items: [
      { to: "/futsal", label: "Futsal", icon: Goal, permission: "futsal.view" },
    ],
  },
  {
    label: "Finance & Reports",
    items: [
      { to: "/finance", label: "Finance", icon: Wallet, permission: "finance.view" },
      { to: "/reports", label: "Reports", icon: BarChart3, permission: "reports.view" },
      { to: "/staff-performance", label: "Staff Performance", icon: UserCheck, permission: "staff.performance.view" },
    ],
  },
  {
    label: "Platform",
    items: [
      { to: "/platform", label: "Shops", icon: Globe2, permission: "platform.view" },
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
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const { hasPermission, hasAnyPermission } = usePermissions();

  const canSeeItem = (item: NavItem) => {
    if (!item.permission) return true;
    return Array.isArray(item.permission)
      ? hasAnyPermission(...item.permission)
      : hasPermission(item.permission);
  };

  const visibleSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(canSeeItem),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300",
        sidebarCollapsed ? "w-[72px]" : "w-[280px]"
      )}
    >
      {/* Logo */}
      <div className="flex h-[72px] items-center justify-between border-b border-sidebar-border px-4">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold text-sm">
              M
            </div>
            <div>
              <p className="text-sm font-bold text-foreground">MDA ERP</p>
              <p className="text-[10px] text-muted-foreground">Enterprise Edition</p>
            </div>
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
      <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {visibleSections.map((section) => (
          <div key={section.label} className="mb-6">
            {!sidebarCollapsed && (
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  title={sidebarCollapsed ? label : undefined}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                      isActive
                        ? "bg-primary/10 text-primary shadow-sm"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground"
                    )
                  }
                >
                  <Icon className="h-[18px] w-[18px] shrink-0" />
                  {!sidebarCollapsed && <span>{label}</span>}
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

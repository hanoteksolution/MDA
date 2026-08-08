import {
  LayoutDashboard,
  LayoutGrid,
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
  Shield,
  Globe2,
  CreditCard,
  Pill,
  Dumbbell,
  FlaskConical,
  UtensilsCrossed,
  Goal,
  BedDouble,
  Home,
  Briefcase,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import {
  MODULE_WORKSPACES,
  filterVisibleWorkspaces,
  retailUnlocked,
  propertyUnlocked,
  VENUE_MODULE_CODES,
  ENGINE_MODULE_CODES,
  type ModuleWorkspace,
} from "./moduleWorkspaces";

export { filterVisibleWorkspaces, retailUnlocked, propertyUnlocked, VENUE_MODULE_CODES, ENGINE_MODULE_CODES };

export const INDUSTRY_PATH_CODES = [
  "restaurant",
  "cafeteria",
  "gym",
  "pharmacy",
  "hotel",
  "property",
  "retail",
  "futsal",
] as const;

export type IndustryPathCode = (typeof INDUSTRY_PATH_CODES)[number];

export const INDUSTRY_PATH_SET = new Set<string>(INDUSTRY_PATH_CODES);

export interface WorkspaceNavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  permission?: string | string[];
  module?: string | string[];
  end?: boolean;
}

export interface WorkspaceNavSection {
  label: string;
  items: WorkspaceNavItem[];
}

export function isIndustryPath(code: string | null | undefined): boolean {
  return Boolean(code && INDUSTRY_PATH_SET.has(code));
}

export function workspacePath(workspace: string, suffix = ""): string {
  const clean = suffix.replace(/^\//, "");
  return clean ? `/${workspace}/${clean}` : `/${workspace}`;
}

type PermFn = (code: string) => boolean;

function permOk(
  permission: string | string[] | undefined,
  hasPermission: PermFn | undefined,
  elevated: boolean
): boolean {
  if (!permission || elevated || !hasPermission) return true;
  const codes = Array.isArray(permission) ? permission : [permission];
  return codes.some((c) => hasPermission(c));
}

function moduleOk(
  module: string | string[] | undefined,
  enabled: string[] | undefined,
  elevated: boolean
): boolean {
  if (!module?.length) return true;
  if (elevated || enabled == null) return true;
  const codes = Array.isArray(module) ? module : [module];
  return codes.some((m) => enabled.includes(m));
}

export function industryWorkspacesForUser(
  enabled: string[] | undefined,
  opts?: { elevated?: boolean; hasPermission?: PermFn }
): ModuleWorkspace[] {
  return filterVisibleWorkspaces(enabled, {
    ...opts,
    includeOverview: false,
    includeFinance: false,
  }).filter((w) => w.kind === "industry");
}

export function switcherWorkspacesForUser(
  enabled: string[] | undefined,
  opts?: { elevated?: boolean; hasPermission?: PermFn; includeFinance?: boolean }
): ModuleWorkspace[] {
  return filterVisibleWorkspaces(enabled, {
    elevated: opts?.elevated,
    hasPermission: opts?.hasPermission,
    includeOverview: true,
    includeFinance: opts?.includeFinance !== false,
  });
}

const CAP_NAV: Record<
  string,
  { label: string; suffix: string; icon: LucideIcon; permission?: string | string[]; module?: string | string[] }
> = {
  dashboard: { label: "Dashboard", suffix: "", icon: LayoutDashboard },
  pos: { label: "POS", suffix: "pos", icon: ShoppingCart, permission: "pos.access", module: "pos" },
  sales: { label: "Sales", suffix: "sales", icon: Receipt, permission: "sales.view", module: "sales" },
  products: { label: "Products", suffix: "products", icon: Package, permission: "products.view", module: "inventory" },
  inventory: { label: "Inventory", suffix: "inventory", icon: Warehouse, permission: "inventory.view", module: "inventory" },
  purchasing: {
    label: "Purchasing",
    suffix: "purchasing",
    icon: Truck,
    permission: "purchases.view",
    module: "purchases",
  },
  customers: { label: "Customers", suffix: "customers", icon: Users, permission: "customers.view", module: "sales" },
  suppliers: {
    label: "Suppliers",
    suffix: "suppliers",
    icon: Building2,
    permission: "suppliers.view",
    module: "purchases",
  },
  finance: { label: "Finance", suffix: "finance", icon: Wallet, permission: "finance.view" },
  reports: { label: "Reports", suffix: "reports", icon: BarChart3, permission: "reports.view" },
};

/** Capability + feature codes in sidebar order (matches product IA). */
const WORKSPACE_NAV_ORDER: Record<string, string[]> = {
  restaurant: [
    "dashboard",
    "pos",
    "sales",
    "products",
    "inventory",
    "purchasing",
    "customers",
    "suppliers",
    "kitchen",
    "tables",
    "finance",
    "reports",
  ],
  cafeteria: [
    "dashboard",
    "pos",
    "sales",
    "products",
    "inventory",
    "purchasing",
    "customers",
    "suppliers",
    "kitchen",
    "tables",
    "finance",
    "reports",
  ],
  gym: [
    "dashboard",
    "members",
    "memberships",
    "attendance",
    "classes",
    "pos",
    "products",
    "inventory",
    "sales",
    "finance",
    "reports",
  ],
  pharmacy: [
    "dashboard",
    "pos",
    "sales",
    "products",
    "batches",
    "expiry",
    "inventory",
    "purchasing",
    "prescriptions",
    "finance",
    "reports",
  ],
  hotel: [
    "dashboard",
    "reservations",
    "rooms",
    "guests",
    "front-desk",
    "housekeeping",
    "pos",
    "inventory",
    "purchasing",
    "finance",
    "reports",
  ],
  property: ["dashboard", "properties", "units", "housing", "office", "maintenance", "finance", "reports"],
  retail: [
    "dashboard",
    "pos",
    "sales",
    "products",
    "inventory",
    "purchasing",
    "customers",
    "suppliers",
    "finance",
    "reports",
  ],
  futsal: ["dashboard", "bookings", "teams", "pos", "sales", "ledger", "finance", "reports"],
};

type FeatureNavSpec = {
  label: string;
  suffix: string;
  icon: LucideIcon;
  permission?: string | string[];
  module?: string | string[];
};

const WORKSPACE_FEATURES: Record<string, Record<string, FeatureNavSpec>> = {
  restaurant: {
    kitchen: {
      label: "Kitchen",
      suffix: "kitchen",
      icon: UtensilsCrossed,
      permission: ["restaurant.kitchen", "restaurant.floor", "restaurant.view"],
      module: "restaurant",
    },
    tables: { label: "Tables", suffix: "tables", icon: UtensilsCrossed, permission: "restaurant.view", module: "restaurant" },
  },
  cafeteria: {
    kitchen: {
      label: "Kitchen",
      suffix: "kitchen",
      icon: UtensilsCrossed,
      permission: ["restaurant.kitchen", "restaurant.floor", "restaurant.view"],
      module: "restaurant",
    },
    tables: { label: "Tables", suffix: "tables", icon: UtensilsCrossed, permission: "restaurant.view", module: "restaurant" },
  },
  gym: {
    members: { label: "Members", suffix: "members", icon: Users, permission: "gym.view", module: "gym" },
    memberships: { label: "Memberships", suffix: "memberships", icon: Dumbbell, permission: "gym.view", module: "gym" },
    attendance: { label: "Attendance", suffix: "attendance", icon: UserCheck, permission: "gym.view", module: "gym" },
    classes: { label: "Classes", suffix: "classes", icon: Dumbbell, permission: "gym.view", module: "gym" },
  },
  pharmacy: {
    batches: { label: "Batches", suffix: "batches", icon: Pill, permission: "pharmacy.view", module: "pharmacy" },
    expiry: { label: "Expiry", suffix: "expiry", icon: Pill, permission: "pharmacy.view", module: "pharmacy" },
    prescriptions: {
      label: "Prescriptions",
      suffix: "prescriptions",
      icon: Pill,
      permission: "pharmacy.view",
      module: "pharmacy",
    },
  },
  hotel: {
    reservations: { label: "Reservations", suffix: "reservations", icon: BedDouble, permission: "hotel.view", module: "hotel" },
    rooms: { label: "Rooms", suffix: "rooms", icon: BedDouble, permission: "hotel.view", module: "hotel" },
    guests: { label: "Guests", suffix: "guests", icon: Users, permission: "hotel.view", module: "hotel" },
    "front-desk": { label: "Front desk", suffix: "front-desk", icon: BedDouble, permission: "hotel.view", module: "hotel" },
    housekeeping: { label: "Housekeeping", suffix: "housekeeping", icon: BedDouble, permission: "hotel.view", module: "hotel" },
  },
  property: {
    properties: {
      label: "Properties",
      suffix: "properties",
      icon: Building2,
      permission: "property_management.view",
      module: "property_management",
    },
    units: { label: "Units", suffix: "units", icon: Building2, permission: "property_management.view", module: "property_management" },
    maintenance: {
      label: "Maintenance",
      suffix: "maintenance",
      icon: Building2,
      permission: ["property_management.view", "property_management.maintenance"],
      module: "property_management",
    },
    housing: { label: "Housing", suffix: "housing", icon: Home, permission: "housing_rental.view", module: "housing_rental" },
    office: { label: "Office", suffix: "office", icon: Briefcase, permission: "office_rental.view", module: "office_rental" },
  },
  futsal: {
    bookings: { label: "Bookings", suffix: "bookings", icon: Goal, permission: "futsal.view", module: "futsal" },
    teams: { label: "Teams", suffix: "teams", icon: Users, permission: "futsal.view", module: "futsal" },
    ledger: { label: "Venue ledger", suffix: "ledger", icon: Wallet, permission: "futsal.finance", module: "futsal" },
  },
};

const PRODUCT_LABEL: Record<string, string> = {
  restaurant: "Menu",
  cafeteria: "Menu",
  pharmacy: "Medicines",
  gym: "Products",
  retail: "Products",
  hotel: "Products",
};

export function industryNavSections(
  workspace: string,
  opts: {
    elevated?: boolean;
    enabled?: string[];
    hasPermission?: PermFn;
    hasAnyPermission?: (...codes: string[]) => boolean;
    hasModule?: (code: string) => boolean;
    hasAnyModule?: (...codes: string[]) => boolean;
  }
): WorkspaceNavSection[] {
  const elevated = Boolean(opts.elevated);
  const enabled = opts.enabled;
  const hasPermission = opts.hasPermission;
  const order = WORKSPACE_NAV_ORDER[workspace] ?? ["dashboard", "finance", "reports"];
  const wsMeta = MODULE_WORKSPACES.find((w) => w.code === workspace);
  const label = wsMeta?.label ?? workspace;
  const features = WORKSPACE_FEATURES[workspace] ?? {};

  const can = (item: { permission?: string | string[]; module?: string | string[] }) =>
    permOk(item.permission, hasPermission, elevated) && moduleOk(item.module, enabled, elevated);

  const items: WorkspaceNavItem[] = [];

  order.forEach((code) => {
    const cap = CAP_NAV[code];
    if (cap) {
      if (!can(cap)) return;
      const labelText = code === "products" ? PRODUCT_LABEL[workspace] || cap.label : cap.label;
      items.push({
        to: workspacePath(workspace, cap.suffix),
        label: labelText,
        icon: cap.icon,
        permission: cap.permission,
        module: cap.module,
        end: !cap.suffix,
      });
      return;
    }
    const feat = features[code];
    if (!feat || !can(feat)) return;
    items.push({
      to: workspacePath(workspace, feat.suffix),
      label: feat.label,
      icon: feat.icon,
      permission: feat.permission,
      module: feat.module,
    });
  });

  return [
    { label, items },
    {
      label: "Platform",
      items: [
        { to: "/modules", label: "All workspaces", icon: LayoutGrid },
        { to: "/settings", label: "Settings", icon: Settings, permission: "settings.view" },
      ].filter((item) => permOk(item.permission, hasPermission, elevated)),
    },
  ];
}

export function overviewNavSections(
  industry: ModuleWorkspace[],
  opts: {
    elevated?: boolean;
    hasPermission?: PermFn;
    includeFinance?: boolean;
    includeAdmin?: boolean;
    includePlatform?: boolean;
  }
): WorkspaceNavSection[] {
  const elevated = Boolean(opts.elevated);
  const hasPermission = opts.hasPermission;
  const sections: WorkspaceNavSection[] = [
    {
      label: "Workspaces",
      items: [
        { to: "/modules", label: "All workspaces", icon: LayoutGrid },
        { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, permission: "dashboard.view", end: true },
        ...industry.map((w) => ({
          to: w.route,
          label: w.label,
          icon: w.icon,
          permission: w.permission,
          module: w.modules.length ? w.modules : undefined,
          end: true,
        })),
      ].filter((item) => permOk(item.permission, hasPermission, elevated)),
    },
  ];

  if (opts.includeFinance !== false) {
    const financeItems: WorkspaceNavItem[] = [
          { to: "/finance", label: "General Ledger", icon: Wallet, permission: "finance.view" },
      { to: "/reports", label: "Reports", icon: BarChart3, permission: "reports.view" },
    ].filter((item) => permOk(item.permission, hasPermission, elevated));
    if (financeItems.length) sections.push({ label: "Central Finance", items: financeItems });
  }

  const systemItems: WorkspaceNavItem[] = [];
  if (opts.includeAdmin !== false && permOk(["users.view", "roles.view"], hasPermission, elevated)) {
    systemItems.push({ to: "/admin", label: "Administration", icon: Shield, permission: ["users.view", "roles.view"] });
  }
  if (permOk("settings.view", hasPermission, elevated)) {
    systemItems.push({ to: "/settings", label: "Settings", icon: Settings, permission: "settings.view" });
  }
  if (opts.includePlatform && permOk("platform.view", hasPermission, elevated)) {
    systemItems.push({ to: "/platform", label: "Platform", icon: Globe2, permission: "platform.view" });
    systemItems.push({ to: "/platform/tenants", label: "Tenants", icon: Building2, permission: "platform.view" });
    systemItems.push({ to: "/platform/demos", label: "Demo Accounts", icon: FlaskConical, permission: "platform.view" });
    if (permOk("subscriptions.manage", hasPermission, elevated)) {
      systemItems.push({
        to: "/platform/subscriptions",
        label: "Subscriptions",
        icon: CreditCard,
        permission: "subscriptions.manage",
      });
    }
  }
  if (systemItems.length) sections.push({ label: "Administration", items: systemItems });

  return sections.filter((s) => s.items.length);
}

export function platformNavSections(
  workspace: string,
  opts: { elevated?: boolean; hasPermission?: PermFn }
): WorkspaceNavSection[] {
  const elevated = Boolean(opts.elevated);
  const hasPermission = opts.hasPermission;
  const can = (permission?: string | string[]) => permOk(permission, hasPermission, elevated);

  if (workspace === "finance" || workspace === "reports") {
    return [
      {
        label: "Central Finance",
        items: [
          { to: "/finance", label: "General Ledger", icon: Wallet, permission: "finance.view" },
          { to: "/reports", label: "Reports", icon: BarChart3, permission: "reports.view" },
          { to: "/expenses", label: "Expenses", icon: Wallet, permission: ["finance.view", "sales.view"] },
          { to: "/staff-performance", label: "Staff Performance", icon: UserCheck, permission: "staff.performance.view" },
        ].filter((i) => can(i.permission)),
      },
      {
        label: "Platform",
        items: [{ to: "/modules", label: "All workspaces", icon: LayoutGrid }],
      },
    ];
  }

  if (workspace === "admin" || workspace === "settings") {
    return [
      {
        label: "Administration",
        items: [
          { to: "/admin", label: "Administration", icon: Shield, permission: ["users.view", "roles.view"] },
          { to: "/settings", label: "Settings", icon: Settings, permission: "settings.view" },
        ].filter((i) => can(i.permission)),
      },
      {
        label: "Platform",
        items: [{ to: "/modules", label: "All workspaces", icon: LayoutGrid }],
      },
    ];
  }

  if (workspace === "platform") {
    return [
      {
        label: "Platform",
        items: [
          { to: "/platform/tenants", label: "Tenants", icon: Building2, permission: "platform.view" },
          { to: "/platform", label: "Shops", icon: Globe2, permission: "platform.view", end: true },
          { to: "/platform/demos", label: "Demo Accounts", icon: FlaskConical, permission: "platform.view" },
          { to: "/platform/subscriptions", label: "Subscriptions", icon: CreditCard, permission: "subscriptions.manage" },
          { to: "/modules", label: "All workspaces", icon: LayoutGrid },
        ].filter((i) => can(i.permission)),
      },
    ];
  }

  return [];
}

export function isPosPath(pathname: string): boolean {
  if (pathname === "/pos" || pathname.startsWith("/pos/")) return true;
  return INDUSTRY_PATH_CODES.some((ws) => pathname === `/${ws}/pos` || pathname.startsWith(`/${ws}/pos/`));
}

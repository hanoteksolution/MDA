import {
  LayoutDashboard,
  ShoppingCart,
  Warehouse,
  Dumbbell,
  Pill,
  Goal,
  Wallet,
  UtensilsCrossed,
  BedDouble,
  Building2,
  Home,
  Briefcase,
  Receipt,
  Truck,
  BarChart3,
  Globe2,
  Shield,
  Settings,
  Star,
  Clock,
  Zap,
  HeartPulse,
  Users,
  UserCog,
  FileText,
  Banknote,
  UserPlus,
  CalendarPlus,
  PackagePlus,
  Store,
  ShoppingBag,
  type LucideIcon,
} from "lucide-react";

export type WorkspaceTone =
  | "sky"
  | "orange"
  | "blue"
  | "teal"
  | "indigo"
  | "violet"
  | "emerald"
  | "green"
  | "amber"
  | "cyan"
  | "stone"
  | "lime"
  | "slate"
  | "fuchsia"
  | "rose"
  | "zinc"
  | "neutral"
  | "purple"
  | "pink";

export type WorkspaceCategoryId =
  | "operations"
  | "finance"
  | "retail"
  | "hospitality"
  | "healthcare"
  | "fitness"
  | "property"
  | "admin"
  | "reports"
  | "crm"
  | "hr"
  | "platform";

export interface WorkspaceToneStyle {
  accent: string;
  icon: string;
  glow: string;
  text: string;
  soft: string;
  ring: string;
}

export const TONE_STYLES: Record<WorkspaceTone, WorkspaceToneStyle> = {
  sky: {
    accent: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
    icon: "bg-gradient-to-br from-sky-400 via-sky-500 to-blue-600 text-white shadow-lg shadow-sky-500/25",
    glow: "hover:shadow-sky-500/20",
    text: "text-sky-600 dark:text-sky-400",
    soft: "from-sky-500/12 to-blue-500/5",
    ring: "ring-sky-500/20",
  },
  orange: {
    accent: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
    icon: "bg-gradient-to-br from-orange-400 via-orange-500 to-amber-600 text-white shadow-lg shadow-orange-500/25",
    glow: "hover:shadow-orange-500/20",
    text: "text-orange-600 dark:text-orange-400",
    soft: "from-orange-500/12 to-amber-500/5",
    ring: "ring-orange-500/20",
  },
  blue: {
    accent: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
    icon: "bg-gradient-to-br from-blue-400 via-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/25",
    glow: "hover:shadow-blue-500/20",
    text: "text-blue-600 dark:text-blue-400",
    soft: "from-blue-500/12 to-indigo-500/5",
    ring: "ring-blue-500/20",
  },
  teal: {
    accent: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
    icon: "bg-gradient-to-br from-teal-400 via-teal-500 to-cyan-600 text-white shadow-lg shadow-teal-500/25",
    glow: "hover:shadow-teal-500/20",
    text: "text-teal-600 dark:text-teal-400",
    soft: "from-teal-500/12 to-cyan-500/5",
    ring: "ring-teal-500/20",
  },
  indigo: {
    accent: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
    icon: "bg-gradient-to-br from-indigo-400 via-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/25",
    glow: "hover:shadow-indigo-500/20",
    text: "text-indigo-600 dark:text-indigo-400",
    soft: "from-indigo-500/12 to-violet-500/5",
    ring: "ring-indigo-500/20",
  },
  violet: {
    accent: "bg-violet-500/15 text-violet-700 dark:text-violet-300",
    icon: "bg-gradient-to-br from-violet-400 via-violet-500 to-fuchsia-600 text-white shadow-lg shadow-violet-500/25",
    glow: "hover:shadow-violet-500/20",
    text: "text-violet-600 dark:text-violet-400",
    soft: "from-violet-500/12 to-fuchsia-500/5",
    ring: "ring-violet-500/20",
  },
  emerald: {
    accent: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    icon: "bg-gradient-to-br from-emerald-400 via-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25",
    glow: "hover:shadow-emerald-500/20",
    text: "text-emerald-600 dark:text-emerald-400",
    soft: "from-emerald-500/12 to-teal-500/5",
    ring: "ring-emerald-500/20",
  },
  green: {
    accent: "bg-green-500/15 text-green-700 dark:text-green-300",
    icon: "bg-gradient-to-br from-green-400 via-green-500 to-emerald-600 text-white shadow-lg shadow-green-500/25",
    glow: "hover:shadow-green-500/20",
    text: "text-green-600 dark:text-green-400",
    soft: "from-green-500/12 to-emerald-500/5",
    ring: "ring-green-500/20",
  },
  amber: {
    accent: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    icon: "bg-gradient-to-br from-amber-400 via-amber-500 to-orange-600 text-white shadow-lg shadow-amber-500/25",
    glow: "hover:shadow-amber-500/20",
    text: "text-amber-600 dark:text-amber-400",
    soft: "from-amber-500/12 to-orange-500/5",
    ring: "ring-amber-500/20",
  },
  cyan: {
    accent: "bg-cyan-500/15 text-cyan-700 dark:text-cyan-300",
    icon: "bg-gradient-to-br from-cyan-400 via-cyan-500 to-sky-600 text-white shadow-lg shadow-cyan-500/25",
    glow: "hover:shadow-cyan-500/20",
    text: "text-cyan-600 dark:text-cyan-400",
    soft: "from-cyan-500/12 to-sky-500/5",
    ring: "ring-cyan-500/20",
  },
  stone: {
    accent: "bg-stone-500/15 text-stone-700 dark:text-stone-300",
    icon: "bg-gradient-to-br from-stone-400 via-stone-500 to-neutral-600 text-white shadow-lg shadow-stone-500/25",
    glow: "hover:shadow-stone-500/20",
    text: "text-stone-600 dark:text-stone-400",
    soft: "from-stone-500/12 to-neutral-500/5",
    ring: "ring-stone-500/20",
  },
  lime: {
    accent: "bg-lime-500/15 text-lime-700 dark:text-lime-300",
    icon: "bg-gradient-to-br from-lime-400 via-lime-500 to-green-600 text-white shadow-lg shadow-lime-500/25",
    glow: "hover:shadow-lime-500/20",
    text: "text-lime-600 dark:text-lime-400",
    soft: "from-lime-500/12 to-green-500/5",
    ring: "ring-lime-500/20",
  },
  slate: {
    accent: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
    icon: "bg-gradient-to-br from-slate-400 via-slate-500 to-zinc-600 text-white shadow-lg shadow-slate-500/25",
    glow: "hover:shadow-slate-500/20",
    text: "text-slate-600 dark:text-slate-400",
    soft: "from-slate-500/12 to-zinc-500/5",
    ring: "ring-slate-500/20",
  },
  fuchsia: {
    accent: "bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-300",
    icon: "bg-gradient-to-br from-fuchsia-400 via-fuchsia-500 to-pink-600 text-white shadow-lg shadow-fuchsia-500/25",
    glow: "hover:shadow-fuchsia-500/20",
    text: "text-fuchsia-600 dark:text-fuchsia-400",
    soft: "from-fuchsia-500/12 to-pink-500/5",
    ring: "ring-fuchsia-500/20",
  },
  rose: {
    accent: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
    icon: "bg-gradient-to-br from-rose-400 via-rose-500 to-pink-600 text-white shadow-lg shadow-rose-500/25",
    glow: "hover:shadow-rose-500/20",
    text: "text-rose-600 dark:text-rose-400",
    soft: "from-rose-500/12 to-pink-500/5",
    ring: "ring-rose-500/20",
  },
  zinc: {
    accent: "bg-zinc-500/15 text-zinc-700 dark:text-zinc-300",
    icon: "bg-gradient-to-br from-zinc-400 via-zinc-500 to-neutral-600 text-white shadow-lg shadow-zinc-500/25",
    glow: "hover:shadow-zinc-500/20",
    text: "text-zinc-600 dark:text-zinc-400",
    soft: "from-zinc-500/12 to-neutral-500/5",
    ring: "ring-zinc-500/20",
  },
  neutral: {
    accent: "bg-neutral-500/15 text-neutral-700 dark:text-neutral-300",
    icon: "bg-gradient-to-br from-neutral-400 via-neutral-500 to-stone-600 text-white shadow-lg shadow-neutral-500/25",
    glow: "hover:shadow-neutral-500/20",
    text: "text-neutral-600 dark:text-neutral-400",
    soft: "from-neutral-500/12 to-stone-500/5",
    ring: "ring-neutral-500/20",
  },
  purple: {
    accent: "bg-purple-500/15 text-purple-700 dark:text-purple-300",
    icon: "bg-gradient-to-br from-purple-400 via-purple-500 to-violet-600 text-white shadow-lg shadow-purple-500/25",
    glow: "hover:shadow-purple-500/20",
    text: "text-purple-600 dark:text-purple-400",
    soft: "from-purple-500/12 to-violet-500/5",
    ring: "ring-purple-500/20",
  },
  pink: {
    accent: "bg-pink-500/15 text-pink-700 dark:text-pink-300",
    icon: "bg-gradient-to-br from-pink-400 via-pink-500 to-rose-600 text-white shadow-lg shadow-pink-500/25",
    glow: "hover:shadow-pink-500/20",
    text: "text-pink-600 dark:text-pink-400",
    soft: "from-pink-500/12 to-rose-500/5",
    ring: "ring-pink-500/20",
  },
};

export interface WorkspaceCategory {
  id: WorkspaceCategoryId;
  label: string;
  icon: LucideIcon;
  tone: WorkspaceTone;
}

export const WORKSPACE_CATEGORIES: WorkspaceCategory[] = [
  { id: "operations", label: "Business Operations", icon: Briefcase, tone: "blue" },
  { id: "finance", label: "Finance", icon: Wallet, tone: "emerald" },
  { id: "retail", label: "Retail & Commerce", icon: ShoppingBag, tone: "cyan" },
  { id: "hospitality", label: "Hospitality", icon: UtensilsCrossed, tone: "orange" },
  { id: "healthcare", label: "Healthcare", icon: HeartPulse, tone: "purple" },
  { id: "fitness", label: "Fitness", icon: Dumbbell, tone: "pink" },
  { id: "property", label: "Property Management", icon: Building2, tone: "rose" },
  { id: "admin", label: "Administration", icon: Shield, tone: "zinc" },
  { id: "reports", label: "Reports & Analytics", icon: BarChart3, tone: "slate" },
  { id: "crm", label: "CRM", icon: Users, tone: "orange" },
  { id: "hr", label: "HR & Payroll", icon: UserCog, tone: "amber" },
  { id: "platform", label: "Platform", icon: Globe2, tone: "rose" },
];

export const HUB_NAV_SECTIONS = [
  { id: "all", label: "Overview", icon: LayoutDashboard },
  { id: "favorites", label: "Favorites", icon: Star },
  { id: "recent", label: "Recent", icon: Clock },
  { id: "actions", label: "Quick Actions", icon: Zap },
] as const;

export interface WorkspaceQuickAction {
  label: string;
  route: string;
  icon: LucideIcon;
}

export interface HubQuickAction {
  id: string;
  label: string;
  route: string;
  icon: LucideIcon;
  permission?: string | string[];
  modules?: string[];
  tone: WorkspaceTone;
}

export type WorkspaceKind = "industry" | "platform" | "capability";

/** Workspace entries for the module hub + switcher (derived from enabled modules). */
export interface ModuleWorkspace {
  code: string;
  label: string;
  description: string;
  route: string;
  icon: LucideIcon;
  tone: WorkspaceTone;
  /** Icon chip classes */
  accent: string;
  category: WorkspaceCategoryId;
  /** Module codes that unlock this workspace (any). Empty = permission-only. */
  modules: string[];
  permission?: string | string[];
  pages: string[];
  quickActions: WorkspaceQuickAction[];
  group: "overview" | "operations" | "venue" | "finance" | "platform" | "system";
  /** industry = business vertical; platform = finance/admin; capability = shared engine (not hub peer). */
  kind: WorkspaceKind;
}

function ws(
  spec: Omit<ModuleWorkspace, "accent" | "kind"> & { kind?: WorkspaceKind }
): ModuleWorkspace {
  return { kind: spec.kind ?? "capability", ...spec, accent: TONE_STYLES[spec.tone].accent };
}

export const MODULE_WORKSPACES: ModuleWorkspace[] = [
  ws({
    code: "overview",
    label: "Overview",
    description: "Executive KPIs, charts, and recent activity across the business.",
    route: "/dashboard",
    icon: LayoutDashboard,
    tone: "sky",
    category: "reports",
    modules: [],
    permission: "dashboard.view",
    pages: ["KPIs", "Charts", "Recent sales", "Low stock"],
    quickActions: [
      { label: "Dashboard", route: "/dashboard", icon: LayoutDashboard },
      { label: "Reports", route: "/reports", icon: BarChart3 },
    ],
    group: "overview",
    kind: "platform",
  }),
  ws({
    code: "pos",
    label: "POS",
    description: "Checkout, holds, waiters, and in-store receipts.",
    route: "/pos",
    icon: ShoppingCart,
    tone: "orange",
    category: "retail",
    modules: ["pos"],
    permission: "pos.access",
    pages: ["Checkout", "Holds", "Waiters", "Receipts"],
    quickActions: [
      { label: "Open POS", route: "/pos", icon: Store },
      { label: "New Sale", route: "/pos", icon: ShoppingCart },
      { label: "Receipts", route: "/receipts", icon: Receipt },
    ],
    group: "operations",
  }),
  ws({
    code: "sales",
    label: "Sales",
    description: "Invoices, quotations, receipts, and customer history.",
    route: "/sales",
    icon: Receipt,
    tone: "blue",
    category: "retail",
    modules: ["sales"],
    permission: "sales.view",
    pages: ["Invoices", "Receipts", "Quotations", "Customers", "Daily ops"],
    quickActions: [
      { label: "New Invoice", route: "/sales/invoices/new", icon: FileText },
      { label: "Receipts", route: "/receipts", icon: Banknote },
      { label: "Customers", route: "/customers", icon: Users },
    ],
    group: "operations",
  }),
  ws({
    code: "inventory",
    label: "Inventory",
    description: "Stock, products, categories, and warehouses.",
    route: "/inventory",
    icon: Warehouse,
    tone: "teal",
    category: "operations",
    modules: ["inventory"],
    permission: "inventory.view",
    pages: ["Stock", "Products", "Categories", "Adjustments"],
    quickActions: [
      { label: "Stock", route: "/inventory", icon: Warehouse },
      { label: "New Product", route: "/products/new", icon: PackagePlus },
      { label: "Adjustments", route: "/inventory/adjustments", icon: Settings },
    ],
    group: "operations",
  }),
  ws({
    code: "purchases",
    label: "Purchases",
    description: "Purchase orders, receiving, and suppliers.",
    route: "/purchases",
    icon: Truck,
    tone: "indigo",
    category: "operations",
    modules: ["purchases"],
    permission: "purchases.view",
    pages: ["Purchase orders", "Suppliers", "Receiving"],
    quickActions: [
      { label: "New PO", route: "/purchases/new", icon: Truck },
      { label: "Suppliers", route: "/suppliers", icon: Building2 },
    ],
    group: "operations",
  }),
  ws({
    code: "gym",
    label: "Gym",
    description: "Members, memberships, classes, and attendance.",
    route: "/gym",
    icon: Dumbbell,
    tone: "violet",
    category: "fitness",
    modules: ["gym"],
    permission: "gym.view",
    pages: ["Members", "Memberships", "Attendance", "Classes", "POS", "Finance"],
    quickActions: [
      { label: "Members", route: "/gym/members", icon: UserPlus },
      { label: "Attendance", route: "/gym/attendance", icon: Clock },
      { label: "Open POS", route: "/gym/pos", icon: Store },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "pharmacy",
    label: "Pharmacy",
    description: "Batches, prescriptions, FEFO, and dispensing.",
    route: "/pharmacy",
    icon: Pill,
    tone: "emerald",
    category: "healthcare",
    modules: ["pharmacy"],
    permission: "pharmacy.view",
    pages: ["POS", "Sales", "Medicines", "Batches", "Expiry", "Finance"],
    quickActions: [
      { label: "Batches", route: "/pharmacy/batches", icon: Pill },
      { label: "Open POS", route: "/pharmacy/pos", icon: Store },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "futsal",
    label: "Futsal",
    description: "Courts, teams, bookings, and venue finance.",
    route: "/futsal",
    icon: Goal,
    tone: "green",
    category: "hospitality",
    modules: ["futsal"],
    permission: "futsal.view",
    pages: ["Courts", "Bookings", "Teams", "POS", "Finance"],
    quickActions: [
      { label: "Bookings", route: "/futsal", icon: CalendarPlus },
      { label: "Open POS", route: "/futsal/pos", icon: Store },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "restaurant",
    label: "Restaurant",
    description: "Floor, kitchen display, menus, and tables.",
    route: "/restaurant",
    icon: UtensilsCrossed,
    tone: "amber",
    category: "hospitality",
    modules: ["restaurant"],
    permission: "restaurant.view",
    pages: ["POS", "Sales", "Kitchen", "Tables", "Finance"],
    quickActions: [
      { label: "Floor", route: "/restaurant", icon: UtensilsCrossed },
      { label: "Open POS", route: "/restaurant/pos", icon: Store },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "cafeteria",
    label: "Cafeteria",
    description: "Counter POS, menu, inventory, and purchasing.",
    route: "/cafeteria",
    icon: UtensilsCrossed,
    tone: "amber",
    category: "hospitality",
    modules: ["restaurant"],
    permission: "restaurant.view",
    pages: ["POS", "Orders", "Menu", "Inventory", "Finance"],
    quickActions: [
      { label: "Open POS", route: "/cafeteria/pos", icon: Store },
      { label: "Menu", route: "/cafeteria/products", icon: PackagePlus },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "hotel",
    label: "Hotel",
    description: "Rooms, reservations, folios, and housekeeping.",
    route: "/hotel",
    icon: BedDouble,
    tone: "cyan",
    category: "hospitality",
    modules: ["hotel"],
    permission: "hotel.view",
    pages: ["Reservations", "Rooms", "POS", "Housekeeping", "Finance"],
    quickActions: [
      { label: "Reservations", route: "/hotel/reservations", icon: CalendarPlus },
      { label: "Open POS", route: "/hotel/pos", icon: Store },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "property",
    label: "Property",
    description: "Assets, buildings, units, and maintenance.",
    route: "/property",
    icon: Building2,
    tone: "teal",
    category: "property",
    modules: ["property_management", "housing_rental", "office_rental"],
    permission: ["property_management.view", "housing_rental.view", "office_rental.view"],
    pages: ["Properties", "Units", "Tenants", "Leases", "Finance"],
    quickActions: [
      { label: "Units", route: "/property", icon: Building2 },
      { label: "Housing", route: "/property/housing", icon: Home },
    ],
    group: "venue",
    kind: "industry",
  }),
  ws({
    code: "retail",
    label: "Retail",
    description: "Shop POS, sales, products, inventory, and purchasing.",
    route: "/retail",
    icon: Store,
    tone: "orange",
    category: "retail",
    modules: ["pos", "sales", "inventory", "purchases"],
    permission: ["pos.access", "sales.view", "inventory.view"],
    pages: ["POS", "Sales", "Products", "Inventory", "Finance"],
    quickActions: [
      { label: "Open POS", route: "/retail/pos", icon: Store },
      { label: "New Invoice", route: "/retail/sales", icon: FileText },
    ],
    group: "operations",
    kind: "industry",
  }),
  ws({
    code: "housing",
    label: "Housing",
    description: "Residential leases and charges.",
    route: "/housing",
    icon: Home,
    tone: "lime",
    category: "property",
    modules: ["housing_rental"],
    permission: "housing_rental.view",
    pages: ["Leases", "Charges", "Units"],
    quickActions: [
      { label: "Leases", route: "/housing", icon: Home },
      { label: "Charges", route: "/housing", icon: Receipt },
    ],
    group: "venue",
  }),
  ws({
    code: "office",
    label: "Office",
    description: "Commercial office leases and charges.",
    route: "/office",
    icon: Briefcase,
    tone: "slate",
    category: "property",
    modules: ["office_rental"],
    permission: "office_rental.view",
    pages: ["Leases", "Charges", "Units"],
    quickActions: [
      { label: "Leases", route: "/office", icon: Briefcase },
      { label: "Charges", route: "/office", icon: Receipt },
    ],
    group: "venue",
  }),
  ws({
    code: "finance",
    label: "Central Finance",
    description: "Journals, P&L, business units, and accounting health.",
    route: "/finance",
    icon: Wallet,
    tone: "emerald",
    category: "finance",
    modules: [],
    permission: "finance.view",
    pages: ["Journals", "P&L", "Business units", "Health"],
    quickActions: [
      { label: "Journals", route: "/finance", icon: FileText },
      { label: "P&L", route: "/finance", icon: BarChart3 },
      { label: "Expense", route: "/expenses", icon: Receipt },
    ],
    group: "finance",
    kind: "platform",
  }),
  ws({
    code: "reports",
    label: "Reports",
    description: "Sales, inventory, finance, and venue report packs.",
    route: "/reports",
    icon: BarChart3,
    tone: "slate",
    category: "reports",
    modules: [],
    permission: "reports.view",
    pages: ["Sales", "Inventory", "Finance", "Staff"],
    quickActions: [
      { label: "Open Reports", route: "/reports", icon: BarChart3 },
      { label: "Staff", route: "/staff-performance", icon: Users },
    ],
    group: "finance",
    kind: "platform",
  }),
  ws({
    code: "platform",
    label: "Platform",
    description: "Tenants, shops, subscriptions, and demo accounts.",
    route: "/platform",
    icon: Globe2,
    tone: "rose",
    category: "platform",
    modules: [],
    permission: "platform.view",
    pages: ["Tenants", "Shops", "Subscriptions", "Demos"],
    quickActions: [
      { label: "Tenants", route: "/platform/tenants", icon: Building2 },
      { label: "Shops", route: "/platform", icon: Store },
      { label: "Plans", route: "/platform/subscriptions", icon: Wallet },
    ],
    group: "platform",
    kind: "platform",
  }),
  ws({
    code: "admin",
    label: "Administration",
    description: "Users, roles, and access control.",
    route: "/admin",
    icon: Shield,
    tone: "zinc",
    category: "admin",
    modules: [],
    permission: ["users.view", "roles.view"],
    pages: ["Users", "Roles", "Permissions"],
    quickActions: [
      { label: "Users", route: "/admin", icon: Users },
      { label: "Roles", route: "/admin", icon: Shield },
    ],
    group: "system",
    kind: "platform",
  }),
  ws({
    code: "settings",
    label: "Settings",
    description: "Company, branches, POS profile, and connection.",
    route: "/settings",
    icon: Settings,
    tone: "neutral",
    category: "admin",
    modules: [],
    permission: "settings.view",
    pages: ["Company", "Branches", "POS profile"],
    quickActions: [
      { label: "Company", route: "/settings", icon: Settings },
    ],
    group: "system",
    kind: "platform",
  }),
];

export const HUB_QUICK_ACTIONS: HubQuickAction[] = [
  {
    id: "new-sale",
    label: "New Sale",
    route: "/pos",
    icon: ShoppingCart,
    permission: "pos.access",
    modules: ["pos"],
    tone: "orange",
  },
  {
    id: "new-invoice",
    label: "New Invoice",
    route: "/sales/invoices/new",
    icon: FileText,
    permission: "sales.view",
    modules: ["sales"],
    tone: "blue",
  },
  {
    id: "new-purchase",
    label: "New Purchase",
    route: "/purchases/new",
    icon: Truck,
    permission: "purchases.view",
    modules: ["purchases"],
    tone: "indigo",
  },
  {
    id: "receive-payment",
    label: "Receive Payment",
    route: "/receipts",
    icon: Banknote,
    permission: "sales.view",
    modules: ["sales"],
    tone: "emerald",
  },
  {
    id: "add-customer",
    label: "Add Customer",
    route: "/customers/new",
    icon: UserPlus,
    permission: "customers.view",
    modules: ["sales"],
    tone: "cyan",
  },
  {
    id: "new-member",
    label: "New Member",
    route: "/gym/members/new",
    icon: Dumbbell,
    permission: "gym.view",
    modules: ["gym"],
    tone: "violet",
  },
  {
    id: "new-reservation",
    label: "New Reservation",
    route: "/hotel/reservations/new",
    icon: CalendarPlus,
    permission: "hotel.view",
    modules: ["hotel"],
    tone: "indigo",
  },
  {
    id: "new-booking",
    label: "New Booking",
    route: "/futsal",
    icon: Goal,
    permission: "futsal.view",
    modules: ["futsal"],
    tone: "green",
  },
  {
    id: "new-product",
    label: "New Product",
    route: "/products/new",
    icon: PackagePlus,
    permission: "products.view",
    modules: ["inventory"],
    tone: "teal",
  },
  {
    id: "create-expense",
    label: "Create Expense",
    route: "/expenses",
    icon: Receipt,
    permission: ["finance.view", "sales.view"],
    tone: "amber",
  },
  {
    id: "open-pos",
    label: "Open POS",
    route: "/pos",
    icon: Store,
    permission: "pos.access",
    modules: ["pos"],
    tone: "orange",
  },
];

export function categoryForId(id: WorkspaceCategoryId): WorkspaceCategory | undefined {
  return WORKSPACE_CATEGORIES.find((c) => c.id === id);
}

export const VENUE_MODULE_CODES = [
  "restaurant",
  "gym",
  "pharmacy",
  "hotel",
  "futsal",
  "property_management",
  "housing_rental",
  "office_rental",
] as const;

export const ENGINE_MODULE_CODES = ["pos", "sales", "inventory", "purchases"] as const;

export function retailUnlocked(enabled: string[] | undefined, elevated: boolean): boolean {
  if (elevated || enabled == null) return true;
  const hasEngine = ENGINE_MODULE_CODES.some((m) => enabled.includes(m));
  if (!hasEngine) return false;
  return !VENUE_MODULE_CODES.some((m) => enabled.includes(m));
}

export function propertyUnlocked(enabled: string[] | undefined, elevated: boolean): boolean {
  if (elevated || enabled == null) return true;
  return ["property_management", "housing_rental", "office_rental"].some((m) => enabled.includes(m));
}

function permOk(
  permission: string | string[] | undefined,
  hasPermission: ((code: string) => boolean) | undefined,
  elevated: boolean
): boolean {
  if (!permission || elevated || !hasPermission) return true;
  const codes = Array.isArray(permission) ? permission : [permission];
  return codes.some((c) => hasPermission(c));
}

/** Hub + switcher: industry verticals + platform. Engine peers (POS/Sales/…) stay off the top level. */
export function filterVisibleWorkspaces(
  enabled: string[] | undefined,
  opts?: {
    elevated?: boolean;
    hasPermission?: (code: string) => boolean;
    includeOverview?: boolean;
    includeFinance?: boolean;
    includeCafeteria?: boolean;
  }
): ModuleWorkspace[] {
  const mods = enabled ?? [];
  const elevated = Boolean(opts?.elevated || enabled == null);
  const hasPermission = opts?.hasPermission;

  return MODULE_WORKSPACES.filter((w) => {
    if (w.kind === "capability") return false;
    if (w.code === "cafeteria" && !opts?.includeCafeteria) return false;
    if (w.code === "overview") return opts?.includeOverview !== false;
    if (w.code === "finance") return opts?.includeFinance !== false && permOk(w.permission, hasPermission, elevated);
    if (!permOk(w.permission, hasPermission, elevated)) return false;
    if (w.code === "retail") return retailUnlocked(enabled, elevated);
    if (w.code === "property") return propertyUnlocked(enabled, elevated);
    if (!w.modules.length) return true;
    if (elevated) return true;
    return w.modules.some((m) => mods.includes(m));
  });
}

export function workspacesForModules(
  enabled: string[] | undefined,
  opts?: {
    includeFinance?: boolean;
    isSuperAdmin?: boolean;
    hasPermission?: (code: string) => boolean;
    includeOverview?: boolean;
  }
): ModuleWorkspace[] {
  return filterVisibleWorkspaces(enabled, {
    elevated: opts?.isSuperAdmin,
    hasPermission: opts?.hasPermission,
    includeFinance: opts?.includeFinance,
    includeOverview: opts?.includeOverview,
  });
}

export function filterQuickActions(
  actions: HubQuickAction[],
  opts: {
    enabled?: string[];
    isSuperAdmin?: boolean;
    hasPermission?: (code: string) => boolean;
  }
): HubQuickAction[] {
  const mods = opts.enabled ?? [];
  const open = opts.isSuperAdmin || opts.enabled == null;
  return actions.filter((a) => {
    if (a.permission && opts.hasPermission && !opts.isSuperAdmin) {
      const codes = Array.isArray(a.permission) ? a.permission : [a.permission];
      if (!codes.some((c) => opts.hasPermission?.(c))) return false;
    }
    if (!a.modules?.length) return true;
    if (open) return true;
    return a.modules.some((m) => mods.includes(m));
  });
}

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
  type LucideIcon,
} from "lucide-react";

/** Workspace entries for the module switcher (derived from enabled modules). */
export interface ModuleWorkspace {
  code: string;
  label: string;
  route: string;
  icon: LucideIcon;
  /** Module codes that unlock this workspace (any). Empty = always (overview). */
  modules: string[];
}

export const MODULE_WORKSPACES: ModuleWorkspace[] = [
  {
    code: "overview",
    label: "Overview",
    route: "/dashboard",
    icon: LayoutDashboard,
    modules: [],
  },
  {
    code: "pos",
    label: "POS",
    route: "/pos",
    icon: ShoppingCart,
    modules: ["pos"],
  },
  {
    code: "inventory",
    label: "Inventory",
    route: "/inventory",
    icon: Warehouse,
    modules: ["inventory"],
  },
  {
    code: "gym",
    label: "Gym",
    route: "/gym",
    icon: Dumbbell,
    modules: ["gym"],
  },
  {
    code: "pharmacy",
    label: "Pharmacy",
    route: "/pharmacy",
    icon: Pill,
    modules: ["pharmacy"],
  },
  {
    code: "futsal",
    label: "Futsal",
    route: "/futsal",
    icon: Goal,
    modules: ["futsal"],
  },
  {
    code: "restaurant",
    label: "Restaurant",
    route: "/restaurant",
    icon: UtensilsCrossed,
    modules: ["restaurant"],
  },
  {
    code: "hotel",
    label: "Hotel",
    route: "/hotel",
    icon: BedDouble,
    modules: ["hotel"],
  },
  {
    code: "property",
    label: "Property",
    route: "/property",
    icon: Building2,
    modules: ["property_management", "housing_rental", "office_rental"],
  },
  {
    code: "housing",
    label: "Housing",
    route: "/housing",
    icon: Home,
    modules: ["housing_rental"],
  },
  {
    code: "office",
    label: "Office",
    route: "/office",
    icon: Briefcase,
    modules: ["office_rental"],
  },
  {
    code: "finance",
    label: "Finance",
    route: "/finance",
    icon: Wallet,
    modules: [], // permission-gated in UI; always offered when finance.view
  },
];

export function workspacesForModules(
  enabled: string[] | undefined,
  opts?: { includeFinance?: boolean; isSuperAdmin?: boolean }
): ModuleWorkspace[] {
  const mods = enabled ?? [];
  const open = opts?.isSuperAdmin || !enabled;
  return MODULE_WORKSPACES.filter((w) => {
    if (w.code === "overview") return true;
    if (w.code === "finance") return opts?.includeFinance !== false;
    if (open) return w.modules.length > 0;
    return w.modules.some((m) => mods.includes(m));
  });
}

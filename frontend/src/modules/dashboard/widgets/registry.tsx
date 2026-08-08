/**
 * Frontend dashboard widget loaders — keyed by registry `id` from the backend catalog.
 * Composition is module-gated; BusinessType must not select widgets.
 */
import type { ReactNode } from "react";
import {
  BedDouble,
  Briefcase,
  Building2,
  Dumbbell,
  Home,
  Pill,
  UtensilsCrossed,
} from "lucide-react";
import { gymApi } from "@/services/api/gym";
import { pharmacyApi } from "@/services/api/pharmacy";
import { restaurantApi } from "@/services/api/restaurant";
import { hotelApi } from "@/services/api/hotel";
import { propertyApi } from "@/services/api/property";
import { housingApi } from "@/services/api/housing";
import { officeApi } from "@/services/api/office";

export type DashboardWidgetStat = { label: string; value: number };

export type DashboardWidgetDef = {
  id: string;
  module: string;
  permission: string;
  title: string;
  route: string;
  icon: string;
  sort_order: number;
};

export type DashboardWidgetLoader = {
  fetch: () => Promise<{ data: unknown }>;
  mapStats: (data: unknown) => DashboardWidgetStat[];
};

const ICON_MAP: Record<string, ReactNode> = {
  dumbbell: <Dumbbell className="h-5 w-5" />,
  pill: <Pill className="h-5 w-5" />,
  utensils: <UtensilsCrossed className="h-5 w-5" />,
  bed: <BedDouble className="h-5 w-5" />,
  building: <Building2 className="h-5 w-5" />,
  home: <Home className="h-5 w-5" />,
  briefcase: <Briefcase className="h-5 w-5" />,
};

export function widgetIcon(name: string): ReactNode {
  return ICON_MAP[name] ?? <Building2 className="h-5 w-5" />;
}

/** Local fallback catalog (same ids as backend) when API is unavailable. */
export const DASHBOARD_WIDGET_FALLBACK: DashboardWidgetDef[] = [
  {
    id: "finance_ledger_kpis",
    module: "",
    permission: "finance.view",
    title: "Finance",
    route: "/finance",
    icon: "wallet",
    sort_order: 5,
  },
  {
    id: "gym_summary",
    module: "gym",
    permission: "gym.view",
    title: "Gym",
    route: "/gym",
    icon: "dumbbell",
    sort_order: 10,
  },
  {
    id: "pharmacy_summary",
    module: "pharmacy",
    permission: "pharmacy.view",
    title: "Pharmacy",
    route: "/pharmacy",
    icon: "pill",
    sort_order: 20,
  },
  {
    id: "restaurant_summary",
    module: "restaurant",
    permission: "restaurant.view",
    title: "Restaurant",
    route: "/restaurant",
    icon: "utensils",
    sort_order: 30,
  },
  {
    id: "hotel_summary",
    module: "hotel",
    permission: "hotel.view",
    title: "Hotel",
    route: "/hotel",
    icon: "bed",
    sort_order: 40,
  },
  {
    id: "property_summary",
    module: "property_management",
    permission: "property_management.view",
    title: "Property",
    route: "/property",
    icon: "building",
    sort_order: 50,
  },
  {
    id: "housing_summary",
    module: "housing_rental",
    permission: "housing_rental.view",
    title: "Housing",
    route: "/housing",
    icon: "home",
    sort_order: 60,
  },
  {
    id: "office_summary",
    module: "office_rental",
    permission: "office_rental.view",
    title: "Office",
    route: "/office",
    icon: "briefcase",
    sort_order: 70,
  },
];

export const DASHBOARD_WIDGET_LOADERS: Record<string, DashboardWidgetLoader> = {
  gym_summary: {
    fetch: () => gymApi.summary(),
    mapStats: (data) => {
      const d = data as {
        members?: { active?: number };
        subscriptions?: { active?: number };
        attendance?: { today_checkins?: number; currently_inside?: number };
      } | null;
      return [
        { label: "Active members", value: d?.members?.active ?? 0 },
        { label: "Active memberships", value: d?.subscriptions?.active ?? 0 },
        { label: "Check-ins today", value: d?.attendance?.today_checkins ?? 0 },
        { label: "Inside now", value: d?.attendance?.currently_inside ?? 0 },
      ];
    },
  },
  pharmacy_summary: {
    fetch: () => pharmacyApi.summary(),
    mapStats: (data) => {
      const d = data as {
        batch_count?: number;
        total_quantity?: number;
        expiring_count?: number;
        expired_count?: number;
      } | null;
      return [
        { label: "Open batches", value: d?.batch_count ?? 0 },
        { label: "Units on hand", value: d?.total_quantity ?? 0 },
        { label: "Expiring soon", value: d?.expiring_count ?? 0 },
        { label: "Expired", value: d?.expired_count ?? 0 },
      ];
    },
  },
  restaurant_summary: {
    fetch: () => restaurantApi.summary(),
    mapStats: (data) => {
      const d = data as {
        orders_open?: number;
        tables_occupied?: number;
        menu_items?: number;
        orders_today?: number;
      } | null;
      return [
        { label: "Open orders", value: d?.orders_open ?? 0 },
        { label: "Tables occupied", value: d?.tables_occupied ?? 0 },
        { label: "Menu items", value: d?.menu_items ?? 0 },
        { label: "Orders today", value: d?.orders_today ?? 0 },
      ];
    },
  },
  hotel_summary: {
    fetch: () => hotelApi.summary(),
    mapStats: (data) => {
      const d = data as {
        in_house?: number;
        rooms_vacant?: number;
        arrivals_today?: number;
        rooms_dirty?: number;
      } | null;
      return [
        { label: "In house", value: d?.in_house ?? 0 },
        { label: "Vacant rooms", value: d?.rooms_vacant ?? 0 },
        { label: "Arrivals today", value: d?.arrivals_today ?? 0 },
        { label: "Dirty rooms", value: d?.rooms_dirty ?? 0 },
      ];
    },
  },
  property_summary: {
    fetch: () => propertyApi.summary(),
    mapStats: (data) => {
      const d = data as {
        properties?: number;
        units_vacant?: number;
        units_occupied?: number;
        maintenance_open?: number;
      } | null;
      return [
        { label: "Properties", value: d?.properties ?? 0 },
        { label: "Vacant units", value: d?.units_vacant ?? 0 },
        { label: "Occupied", value: d?.units_occupied ?? 0 },
        { label: "Open maintenance", value: d?.maintenance_open ?? 0 },
      ];
    },
  },
  housing_summary: {
    fetch: () => housingApi.summary(),
    mapStats: (data) => {
      const d = data as {
        leases_active?: number;
        units_vacant?: number;
        charges_overdue?: number;
        deposits_held?: number;
      } | null;
      return [
        { label: "Active leases", value: d?.leases_active ?? 0 },
        { label: "Vacant residential", value: d?.units_vacant ?? 0 },
        { label: "Overdue charges", value: d?.charges_overdue ?? 0 },
        { label: "Deposits held", value: d?.deposits_held ?? 0 },
      ];
    },
  },
  office_summary: {
    fetch: () => officeApi.summary(),
    mapStats: (data) => {
      const d = data as {
        leases_active?: number;
        units_vacant?: number;
        charges_overdue?: number;
        deposits_held?: number;
      } | null;
      return [
        { label: "Active leases", value: d?.leases_active ?? 0 },
        { label: "Vacant offices", value: d?.units_vacant ?? 0 },
        { label: "Overdue charges", value: d?.charges_overdue ?? 0 },
        { label: "Deposits held", value: d?.deposits_held ?? 0 },
      ];
    },
  },
};

export function filterDashboardWidgets(
  widgets: DashboardWidgetDef[],
  opts: {
    hasModule: (code: string) => boolean;
    hasPermission: (code: string) => boolean;
    isSuperAdmin?: boolean;
  }
): DashboardWidgetDef[] {
  const { hasModule, hasPermission, isSuperAdmin } = opts;
  return widgets
    .filter((w) => {
      // Finance strip is rendered separately; skip catalog cards without loaders.
      if (!DASHBOARD_WIDGET_LOADERS[w.id]) return false;
      if (w.module && !hasModule(w.module)) return false;
      if (w.permission && !isSuperAdmin && !hasPermission(w.permission)) return false;
      return true;
    })
    .sort((a, b) => a.sort_order - b.sort_order || a.id.localeCompare(b.id));
}

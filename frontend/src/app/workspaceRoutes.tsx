import type { ReactNode } from "react";
import { Route } from "react-router-dom";
import { PermissionGuard } from "@/components/auth/PermissionGuard";
import { WorkspaceGate } from "@/navigation/WorkspaceGate";
import { INDUSTRY_PATH_CODES } from "@/navigation/businessWorkspaces";
import {
  PosPage,
  SalesPage,
  PurchasesPage,
  CustomersPage,
  SuppliersPage,
  FinancePage,
  ReportsPage,
  FutsalPage,
  PharmacyPage,
  GymPage,
  RestaurantPage,
  HotelPage,
  PropertyPage,
  HousingPage,
  OfficePage,
} from "@/app/routes/modules";
import { ProductsPage, InventoryDashboardPage } from "@/app/routes/phase2";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import {
  GymMemberDetailPage,
  GymMemberEditPage,
  GymMemberFormPage,
} from "@/modules/gym/pages/GymMemberFormPage";
import {
  HotelReservationDetailPage,
  HotelReservationEditPage,
  HotelReservationFormPage,
} from "@/modules/hotel/pages/HotelReservationPages";
import {
  PropertyUnitDetailPage,
  PropertyUnitEditPage,
  PropertyUnitFormPage,
} from "@/modules/property/pages/PropertyUnitPages";

function gated(
  workspace: string,
  permission: string | string[] | undefined,
  module: string | string[] | undefined,
  page: ReactNode
) {
  const inner = <WorkspaceGate workspace={workspace}>{page}</WorkspaceGate>;
  if (!permission) return inner;
  return (
    <PermissionGuard permission={permission} module={module}>
      {inner}
    </PermissionGuard>
  );
}

const HOME_PAGE: Record<string, ReactNode> = {
  restaurant: <RestaurantPage />,
  cafeteria: <RestaurantPage />,
  gym: <GymPage />,
  pharmacy: <PharmacyPage />,
  hotel: <HotelPage />,
  property: <PropertyPage />,
  retail: <DashboardPage />,
  futsal: <FutsalPage />,
};

const HOME_GUARD: Record<string, { permission: string | string[]; module?: string | string[] }> = {
  restaurant: { permission: "restaurant.view", module: "restaurant" },
  cafeteria: { permission: "restaurant.view", module: "restaurant" },
  gym: { permission: "gym.view", module: "gym" },
  pharmacy: { permission: "pharmacy.view", module: "pharmacy" },
  hotel: { permission: "hotel.view", module: "hotel" },
  property: {
    permission: ["property_management.view", "housing_rental.view", "office_rental.view"],
    module: ["property_management", "housing_rental", "office_rental"],
  },
  retail: { permission: ["pos.access", "sales.view", "inventory.view", "dashboard.view"] },
  futsal: { permission: "futsal.view", module: "futsal" },
};

/** Shared-engine aliases: /restaurant/pos → PosPage, etc. Industry homes stay on existing pages. */
export function industryCapabilityRoutes() {
  return INDUSTRY_PATH_CODES.flatMap((ws) => {
    const home = HOME_GUARD[ws];
    const homePage = HOME_PAGE[ws];
    return [
      <Route key={`${ws}-home`} path={`/${ws}/dashboard`} element={gated(ws, home.permission, home.module, homePage)} />,
      <Route
        key={`${ws}-pos`}
        path={`/${ws}/pos`}
        element={gated(ws, "pos.access", "pos", <PosPage />)}
      />,
      <Route
        key={`${ws}-sales`}
        path={`/${ws}/sales`}
        element={gated(ws, "sales.view", "sales", <SalesPage />)}
      />,
      <Route
        key={`${ws}-products`}
        path={`/${ws}/products`}
        element={gated(ws, "products.view", "inventory", <ProductsPage />)}
      />,
      <Route
        key={`${ws}-inventory`}
        path={`/${ws}/inventory`}
        element={gated(ws, "inventory.view", "inventory", <InventoryDashboardPage />)}
      />,
      <Route
        key={`${ws}-purchasing`}
        path={`/${ws}/purchasing`}
        element={gated(ws, "purchases.view", "purchases", <PurchasesPage />)}
      />,
      <Route
        key={`${ws}-customers`}
        path={`/${ws}/customers`}
        element={gated(ws, "customers.view", "sales", <CustomersPage />)}
      />,
      <Route
        key={`${ws}-suppliers`}
        path={`/${ws}/suppliers`}
        element={gated(ws, "suppliers.view", "purchases", <SuppliersPage />)}
      />,
      <Route
        key={`${ws}-finance`}
        path={`/${ws}/finance`}
        element={gated(ws, "finance.view", undefined, <FinancePage />)}
      />,
      <Route
        key={`${ws}-reports`}
        path={`/${ws}/reports`}
        element={gated(ws, "reports.view", undefined, <ReportsPage />)}
      />,
    ];
  });
}

export function industryFeatureRoutes() {
  return [
    <Route
      key="cafeteria-home"
      path="/cafeteria"
      element={gated("cafeteria", "restaurant.view", "restaurant", <RestaurantPage />)}
    />,
    <Route
      key="retail-home"
      path="/retail"
      element={gated("retail", ["pos.access", "sales.view", "inventory.view", "dashboard.view"], undefined, <DashboardPage />)}
    />,
    <Route
      key="gym-members-new"
      path="/gym/members/new"
      element={gated("gym", ["gym.manage", "gym.members.create"], "gym", <GymMemberFormPage />)}
    />,
    <Route
      key="gym-members-edit"
      path="/gym/members/:id/edit"
      element={gated("gym", ["gym.manage", "gym.members.update"], "gym", <GymMemberEditPage />)}
    />,
    <Route
      key="gym-members-detail"
      path="/gym/members/:id"
      element={gated("gym", "gym.view", "gym", <GymMemberDetailPage />)}
    />,
    <Route key="gym-members" path="/gym/members" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route key="gym-memberships" path="/gym/memberships" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route key="gym-plans" path="/gym/plans" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route key="gym-attendance" path="/gym/attendance" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route key="gym-classes" path="/gym/classes" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route key="gym-trainers" path="/gym/trainers" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route key="gym-workouts" path="/gym/workouts" element={gated("gym", "gym.view", "gym", <GymPage />)} />,
    <Route
      key="restaurant-kitchen"
      path="/restaurant/kitchen"
      element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantPage />)}
    />,
    <Route
      key="restaurant-tables"
      path="/restaurant/tables"
      element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantPage />)}
    />,
    <Route
      key="restaurant-menu"
      path="/restaurant/menu"
      element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantPage />)}
    />,
    <Route
      key="cafeteria-kitchen"
      path="/cafeteria/kitchen"
      element={gated("cafeteria", "restaurant.view", "restaurant", <RestaurantPage />)}
    />,
    <Route
      key="cafeteria-tables"
      path="/cafeteria/tables"
      element={gated("cafeteria", "restaurant.view", "restaurant", <RestaurantPage />)}
    />,
    <Route
      key="pharmacy-medicines"
      path="/pharmacy/medicines"
      element={gated("pharmacy", "products.view", ["pharmacy", "inventory"], <ProductsPage />)}
    />,
    <Route
      key="pharmacy-batches"
      path="/pharmacy/batches"
      element={gated("pharmacy", "pharmacy.view", "pharmacy", <PharmacyPage />)}
    />,
    <Route
      key="pharmacy-expiry"
      path="/pharmacy/expiry"
      element={gated("pharmacy", "pharmacy.view", "pharmacy", <PharmacyPage />)}
    />,
    <Route
      key="pharmacy-prescriptions"
      path="/pharmacy/prescriptions"
      element={gated("pharmacy", "pharmacy.view", "pharmacy", <PharmacyPage />)}
    />,
    <Route key="hotel-types" path="/hotel/types" element={gated("hotel", "hotel.view", "hotel", <HotelPage />)} />,
    <Route
      key="hotel-reservations-new"
      path="/hotel/reservations/new"
      element={gated("hotel", ["hotel.manage", "hotel.front_desk", "hotel.reservations.create"], "hotel", <HotelReservationFormPage />)}
    />,
    <Route
      key="hotel-reservations-edit"
      path="/hotel/reservations/:id/edit"
      element={gated("hotel", ["hotel.manage", "hotel.front_desk", "hotel.reservations.update"], "hotel", <HotelReservationEditPage />)}
    />,
    <Route
      key="hotel-reservations-detail"
      path="/hotel/reservations/:id"
      element={gated("hotel", "hotel.view", "hotel", <HotelReservationDetailPage />)}
    />,
    <Route key="hotel-reservations" path="/hotel/reservations" element={gated("hotel", "hotel.view", "hotel", <HotelPage />)} />,
    <Route key="hotel-rooms" path="/hotel/rooms" element={gated("hotel", "hotel.view", "hotel", <HotelPage />)} />,
    <Route key="hotel-guests" path="/hotel/guests" element={gated("hotel", "hotel.view", "hotel", <HotelPage />)} />,
    <Route key="hotel-front-desk" path="/hotel/front-desk" element={gated("hotel", "hotel.view", "hotel", <HotelPage />)} />,
    <Route
      key="hotel-housekeeping"
      path="/hotel/housekeeping"
      element={gated("hotel", "hotel.view", "hotel", <HotelPage />)}
    />,
    <Route
      key="property-units-new"
      path="/property/units/new"
      element={gated("property", ["property_management.manage", "property_management.masters.create"], "property_management", <PropertyUnitFormPage />)}
    />,
    <Route
      key="property-units-edit"
      path="/property/units/:id/edit"
      element={gated("property", ["property_management.manage", "property_management.masters.update"], "property_management", <PropertyUnitEditPage />)}
    />,
    <Route
      key="property-units-detail"
      path="/property/units/:id"
      element={gated("property", "property_management.view", "property_management", <PropertyUnitDetailPage />)}
    />,
    <Route
      key="property-units"
      path="/property/units"
      element={gated("property", "property_management.view", "property_management", <PropertyPage />)}
    />,
    <Route
      key="property-properties"
      path="/property/properties"
      element={gated("property", "property_management.view", "property_management", <PropertyPage />)}
    />,
    <Route
      key="property-maintenance"
      path="/property/maintenance"
      element={gated("property", ["property_management.view", "property_management.maintenance"], "property_management", <PropertyPage />)}
    />,
    <Route
      key="futsal-bookings"
      path="/futsal/bookings"
      element={gated("futsal", "futsal.view", "futsal", <FutsalPage />)}
    />,
    <Route key="futsal-teams" path="/futsal/teams" element={gated("futsal", "futsal.view", "futsal", <FutsalPage />)} />,
    <Route
      key="futsal-ledger"
      path="/futsal/ledger"
      element={gated("futsal", "futsal.finance", "futsal", <FutsalPage />)}
    />,
    <Route
      key="property-housing"
      path="/property/housing"
      element={gated("property", "housing_rental.view", "housing_rental", <HousingPage />)}
    />,
    <Route
      key="property-office"
      path="/property/office"
      element={gated("property", "office_rental.view", "office_rental", <OfficePage />)}
    />,
  ];
}

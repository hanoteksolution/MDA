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
  ProjectManagementPage,
  TravelAgencyPage,
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
import {
  RestaurantMenuItemDetailPage,
  RestaurantMenuItemEditPage,
  RestaurantMenuItemFormPage,
} from "@/modules/restaurant/pages/RestaurantMenuItemPages";
import {
  ProjectWbsDetailPage,
  ProjectWbsEditPage,
  ProjectWbsListPage,
  ProjectWbsNewPage,
} from "@/modules/projects/pages/ProjectWbsPages";
import {
  ProjectBudgetDetailPage,
  ProjectBudgetEditPage,
  ProjectBudgetListPage,
  ProjectBudgetNewPage,
} from "@/modules/projects/pages/ProjectBudgetPages";
import {
  ProjectTaskDetailPage,
  ProjectTaskEditPage,
  ProjectTaskListPage,
  ProjectTaskNewPage,
} from "@/modules/projects/pages/ProjectTaskPages";
import {
  ProjectOperationDetailPage,
  ProjectOperationFormPage,
  ProjectOperationsListPage,
} from "@/modules/projects/pages/ProjectOperationsPages";
import {
  ProjectMilestoneDetailPage,
  ProjectMilestoneEditPage,
  ProjectMilestoneListPage,
  ProjectMilestoneNewPage,
} from "@/modules/projects/pages/ProjectMilestonePages";
import { ProjectConstructionDetailPage, ProjectConstructionPage } from "@/modules/projects/pages/ProjectConstructionPage";
import {
  ProjectBoqDetailPage,
  ProjectBoqEditPage,
  ProjectBoqListPage,
  ProjectBoqNewPage,
} from "@/modules/projects/pages/ProjectBoqPages";
import {
  TravelBookingDetailPage,
  TravelBookingEditPage,
  TravelBookingListPage,
  TravelBookingNewPage,
} from "@/modules/travel/pages/TravelBookingPages";
import {
  TravelPackageDetailPage,
  TravelPackageEditPage,
  TravelPackageListPage,
  TravelPackageNewPage,
} from "@/modules/travel/pages/TravelPackagePages";
import {
  TravelTravelerDetailPage,
  TravelTravelerEditPage,
  TravelTravelerListPage,
  TravelTravelerNewPage,
} from "@/modules/travel/pages/TravelTravelerPages";
import {
  TravelVisaDetailPage,
  TravelVisaEditPage,
  TravelVisaListPage,
  TravelVisaNewPage,
} from "@/modules/travel/pages/TravelVisaPages";
import { TravelDestinationPage } from "@/modules/travel/pages/TravelDestinationPage";
import {
  TravelActivityPages, TravelDocumentPages, TravelDriverPages, TravelInsurancePages,
  TravelItineraryPages, TravelPaymentPages, TravelQuotationPages, TravelRefundPages, TravelExpensePages,
  TravelTransferPages, TravelVehiclePages,
} from "@/modules/travel/pages/TravelExtendedPages";
import { TravelFieldPage, TravelReportsPage } from "@/modules/travel/pages/TravelFieldPage";
import { ProjectWorkerDetailPage, ProjectWorkforcePage } from "@/modules/projects/pages/ProjectWorkforcePages";
import { ProjectInventoryPage } from "@/modules/projects/pages/ProjectInventoryPage";
import { ProjectMobileFieldPage } from "@/modules/projects/pages/ProjectMobileFieldPage";
import { ProjectReportsPage } from "@/modules/projects/pages/ProjectReportsPage";
import {
  ProjectDetailPage,
  ProjectEditPage,
  ProjectFormNewPage,
  ProjectListPage,
} from "@/modules/projects/pages/ProjectPages";

const TRAVEL_EXTENDED_RESOURCES = [
  ["insurance", "travel.insurance", TravelInsurancePages],
  ["vehicles", "travel.vehicles", TravelVehiclePages],
  ["drivers", "travel.drivers", TravelDriverPages],
  ["transfers", "travel.transfers", TravelTransferPages],
  ["itineraries", "travel.itineraries", TravelItineraryPages],
  ["activities", "travel.activities", TravelActivityPages],
  ["quotations", "travel.quotations", TravelQuotationPages],
  ["documents", "travel.documents", TravelDocumentPages],
  ["payments", "travel.payments", TravelPaymentPages],
  ["refunds", "travel.refunds", TravelRefundPages],
  ["expenses", "travel.expenses", TravelExpensePages],
] as const;
import {
  RestaurantFloorDetailPage,
  RestaurantFloorEditPage,
  RestaurantFloorFormPage,
  RestaurantIngredientDetailPage,
  RestaurantIngredientEditPage,
  RestaurantIngredientFormPage,
  RestaurantModifierDetailPage,
  RestaurantModifierEditPage,
  RestaurantModifierFormPage,
  RestaurantRecipeDetailPage,
  RestaurantRecipeEditPage,
  RestaurantRecipeFormPage,
  RestaurantStationDetailPage,
  RestaurantStationEditPage,
  RestaurantStationFormPage,
} from "@/modules/restaurant/pages/RestaurantOpsPages";

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
  project: <ProjectManagementPage />,
  travel: <TravelAgencyPage />,
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
  project: { permission: "projects.view", module: "project_management" },
  travel: { permission: "travel.bookings.view", module: "travel_agency" },
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
      key="project-home"
      path="/project"
      element={gated("project", "projects.view", "project_management", <ProjectManagementPage />)}
    />,
    <Route
      key="travel-home"
      path="/travel"
      element={gated("travel", "travel.bookings.view", "travel_agency", <TravelAgencyPage />)}
    />,
    <Route
      key="project-projects"
      path="/project/projects"
      element={gated("project", "projects.view", "project_management", <ProjectListPage />)}
    />,
    <Route
      key="project-projects-new"
      path="/project/projects/new"
      element={gated("project", "projects.create", "project_management", <ProjectFormNewPage />)}
    />,
    <Route
      key="project-projects-edit"
      path="/project/projects/:id/edit"
      element={gated("project", "projects.update", "project_management", <ProjectEditPage />)}
    />,
    <Route
      key="project-projects-detail"
      path="/project/projects/:id"
      element={gated("project", "projects.view", "project_management", <ProjectDetailPage />)}
    />,
    <Route
      key="project-budgets"
      path="/project/budgets"
      element={gated("project", "project.budget.view", "project_management", <ProjectBudgetListPage />)}
    />,
    <Route
      key="project-budgets-new"
      path="/project/budgets/new"
      element={gated("project", "project.budget.create", "project_management", <ProjectBudgetNewPage />)}
    />,
    <Route
      key="project-budgets-edit"
      path="/project/budgets/:id/edit"
      element={gated("project", "project.budget.update", "project_management", <ProjectBudgetEditPage />)}
    />,
    <Route
      key="project-budgets-detail"
      path="/project/budgets/:id"
      element={gated("project", "project.budget.view", "project_management", <ProjectBudgetDetailPage />)}
    />,
    <Route
      key="project-wbs"
      path="/project/wbs"
      element={gated("project", "project.wbs.view", "project_management", <ProjectWbsListPage />)}
    />,
    <Route
      key="project-wbs-new"
      path="/project/wbs/new"
      element={gated("project", "project.wbs.create", "project_management", <ProjectWbsNewPage />)}
    />,
    <Route
      key="project-wbs-edit"
      path="/project/wbs/:id/edit"
      element={gated("project", "project.wbs.update", "project_management", <ProjectWbsEditPage />)}
    />,
    <Route
      key="project-wbs-detail"
      path="/project/wbs/:id"
      element={gated("project", "project.wbs.view", "project_management", <ProjectWbsDetailPage />)}
    />,
    <Route
      key="project-tasks"
      path="/project/tasks"
      element={gated("project", "project.tasks.view", "project_management", <ProjectTaskListPage />)}
    />,
    <Route
      key="project-tasks-new"
      path="/project/tasks/new"
      element={gated("project", "project.tasks.create", "project_management", <ProjectTaskNewPage />)}
    />,
    <Route
      key="project-tasks-edit"
      path="/project/tasks/:id/edit"
      element={gated("project", "project.tasks.update", "project_management", <ProjectTaskEditPage />)}
    />,
    <Route
      key="project-tasks-detail"
      path="/project/tasks/:id"
      element={gated("project", "project.tasks.view", "project_management", <ProjectTaskDetailPage />)}
    />,
    <Route
      key="project-milestones"
      path="/project/milestones"
      element={gated("project", "project.milestones.view", "project_management", <ProjectMilestoneListPage />)}
    />,
    <Route
      key="project-milestones-new"
      path="/project/milestones/new"
      element={gated("project", "project.milestones.create", "project_management", <ProjectMilestoneNewPage />)}
    />,
    <Route
      key="project-milestones-edit"
      path="/project/milestones/:id/edit"
      element={gated("project", "project.milestones.update", "project_management", <ProjectMilestoneEditPage />)}
    />,
    <Route
      key="project-milestones-detail"
      path="/project/milestones/:id"
      element={gated("project", "project.milestones.view", "project_management", <ProjectMilestoneDetailPage />)}
    />,
    <Route
      key="project-workforce"
      path="/project/workforce"
      element={gated("project", "project.workers.view", "project_management", <ProjectWorkforcePage />)}
    />,
    <Route
      key="project-worker-detail"
      path="/project/workforce/:id"
      element={gated("project", "project.workers.view", "project_management", <ProjectWorkerDetailPage />)}
    />,
    <Route
      key="project-construction"
      path="/project/construction"
      element={gated("project", "projects.view", "project_management", <ProjectConstructionPage />)}
    />,
    <Route
      key="project-construction-detail"
      path="/project/construction/:kind/:id"
      element={gated("project", "projects.view", "project_management", <ProjectConstructionDetailPage />)}
    />,
    <Route
      key="project-boq"
      path="/project/boq"
      element={gated("project", "project.boq.view", "project_management", <ProjectBoqListPage />)}
    />,
    <Route key="project-inventory" path="/project/allocations" element={gated("project", "project.inventory.view", "project_management", <ProjectInventoryPage />)} />,
    <Route key="project-field" path="/project/field" element={gated("project", "project.tasks.view", "project_management", <ProjectMobileFieldPage />)} />,
    <Route key="project-portfolio-reports" path="/project/portfolio" element={gated("project", "projects.view", "project_management", <ProjectReportsPage />)} />,
    <Route
      key="project-boq-new"
      path="/project/boq/new"
      element={gated("project", "project.boq.create", "project_management", <ProjectBoqNewPage />)}
    />,
    <Route
      key="project-boq-edit"
      path="/project/boq/:id/edit"
      element={gated("project", "project.boq.update", "project_management", <ProjectBoqEditPage />)}
    />,
    <Route
      key="project-boq-detail"
      path="/project/boq/:id"
      element={gated("project", "project.boq.view", "project_management", <ProjectBoqDetailPage />)}
    />,
    ...([
      ["procurement", "project.materials"],
      ["equipment", "project.equipment"],
      ["expenses", "project.expenses"],
      ["change-orders", "project.change_orders"],
      ["site-reports", "project.site_reports"],
      ["quality", "project.quality"],
      ["safety", "project.safety"],
      ["risks", "project.risks"],
      ["issues", "project.issues"],
      ["billing", "project.invoices"],
    ].flatMap(([operation, permission]) => [
      <Route key={`project-${operation}`} path={`/project/${operation}`} element={gated("project", `${permission}.view`, "project_management", <ProjectOperationsListPage />)} />,
      <Route key={`project-${operation}-new`} path={`/project/${operation}/new`} element={gated("project", `${permission}.create`, "project_management", <ProjectOperationFormPage />)} />,
      <Route key={`project-${operation}-edit`} path={`/project/${operation}/:id/edit`} element={gated("project", `${permission}.update`, "project_management", <ProjectOperationFormPage />)} />,
      <Route key={`project-${operation}-detail`} path={`/project/${operation}/:id`} element={gated("project", `${permission}.view`, "project_management", <ProjectOperationDetailPage />)} />,
    ])),
    <Route
      key="travel-bookings"
      path="/travel/bookings"
      element={gated("travel", "travel.bookings.view", "travel_agency", <TravelBookingListPage />)}
    />,
    <Route key="travel-bookings-new" path="/travel/bookings/new" element={gated("travel", "travel.bookings.create", "travel_agency", <TravelBookingNewPage />)} />,
    <Route key="travel-bookings-detail" path="/travel/bookings/:id" element={gated("travel", "travel.bookings.view", "travel_agency", <TravelBookingDetailPage />)} />,
    <Route key="travel-bookings-edit" path="/travel/bookings/:id/edit" element={gated("travel", "travel.bookings.update", "travel_agency", <TravelBookingEditPage />)} />,
    <Route key="travel-packages" path="/travel/packages" element={gated("travel", "travel.packages.view", "travel_agency", <TravelPackageListPage />)} />,
    <Route key="travel-packages-new" path="/travel/packages/new" element={gated("travel", "travel.packages.create", "travel_agency", <TravelPackageNewPage />)} />,
    <Route key="travel-packages-detail" path="/travel/packages/:id" element={gated("travel", "travel.packages.view", "travel_agency", <TravelPackageDetailPage />)} />,
    <Route key="travel-packages-edit" path="/travel/packages/:id/edit" element={gated("travel", "travel.packages.update", "travel_agency", <TravelPackageEditPage />)} />,
    <Route key="travel-travelers" path="/travel/travelers" element={gated("travel", "travel.travelers.view", "travel_agency", <TravelTravelerListPage />)} />,
    <Route key="travel-travelers-new" path="/travel/travelers/new" element={gated("travel", "travel.travelers.create", "travel_agency", <TravelTravelerNewPage />)} />,
    <Route key="travel-travelers-detail" path="/travel/travelers/:id" element={gated("travel", "travel.travelers.view", "travel_agency", <TravelTravelerDetailPage />)} />,
    <Route key="travel-travelers-edit" path="/travel/travelers/:id/edit" element={gated("travel", "travel.travelers.update", "travel_agency", <TravelTravelerEditPage />)} />,
    <Route key="travel-visas" path="/travel/visas" element={gated("travel", "travel.visas.view", "travel_agency", <TravelVisaListPage />)} />,
    <Route key="travel-visas-new" path="/travel/visas/new" element={gated("travel", "travel.visas.create", "travel_agency", <TravelVisaNewPage />)} />,
    <Route key="travel-visas-detail" path="/travel/visas/:id" element={gated("travel", "travel.visas.view", "travel_agency", <TravelVisaDetailPage />)} />,
    <Route key="travel-visas-edit" path="/travel/visas/:id/edit" element={gated("travel", "travel.visas.update", "travel_agency", <TravelVisaEditPage />)} />,
    <Route key="travel-destinations" path="/travel/destinations" element={gated("travel", "travel.destinations.view", "travel_agency", <TravelDestinationPage />)} />,
    <Route key="travel-field" path="/travel/field" element={gated("travel", "travel.bookings.view", "travel_agency", <TravelFieldPage />)} />,
    <Route key="travel-reports" path="/travel/reports" element={gated("travel", "reports.view", undefined, <TravelReportsPage />)} />,
    ...TRAVEL_EXTENDED_RESOURCES.flatMap(([resource, permission, Pages]) => [
      <Route key={`travel-${resource}`} path={`/travel/${resource}`} element={gated("travel", `${permission}.view`, "travel_agency", <Pages.List />)} />,
      <Route key={`travel-${resource}-new`} path={`/travel/${resource}/new`} element={gated("travel", `${permission}.create`, "travel_agency", <Pages.New />)} />,
      <Route key={`travel-${resource}-detail`} path={`/travel/${resource}/:id`} element={gated("travel", `${permission}.view`, "travel_agency", <Pages.Detail />)} />,
      <Route key={`travel-${resource}-edit`} path={`/travel/${resource}/:id/edit`} element={gated("travel", `${permission}.update`, "travel_agency", <Pages.Edit />)} />,
    ]),
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
      key="restaurant-menu-item-new"
      path="/restaurant/menu/items/new"
      element={gated("restaurant", ["restaurant.manage", "restaurant.menu.create"], "restaurant", <RestaurantMenuItemFormPage />)}
    />,
    <Route
      key="restaurant-menu-item-edit"
      path="/restaurant/menu/items/:id/edit"
      element={gated("restaurant", ["restaurant.manage", "restaurant.menu.update"], "restaurant", <RestaurantMenuItemEditPage />)}
    />,
    <Route
      key="restaurant-menu-item-detail"
      path="/restaurant/menu/items/:id"
      element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantMenuItemDetailPage />)}
    />,
    <Route key="restaurant-floor-new" path="/restaurant/floors/new" element={gated("restaurant", ["restaurant.manage", "restaurant.tables.create"], "restaurant", <RestaurantFloorFormPage />)} />,
    <Route key="restaurant-floor-edit" path="/restaurant/floors/:id/edit" element={gated("restaurant", ["restaurant.manage", "restaurant.tables.update"], "restaurant", <RestaurantFloorEditPage />)} />,
    <Route key="restaurant-floor-detail" path="/restaurant/floors/:id" element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantFloorDetailPage />)} />,
    <Route key="restaurant-station-new" path="/restaurant/stations/new" element={gated("restaurant", ["restaurant.manage", "restaurant.kitchen"], "restaurant", <RestaurantStationFormPage />)} />,
    <Route key="restaurant-station-edit" path="/restaurant/stations/:id/edit" element={gated("restaurant", ["restaurant.manage", "restaurant.kitchen"], "restaurant", <RestaurantStationEditPage />)} />,
    <Route key="restaurant-station-detail" path="/restaurant/stations/:id" element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantStationDetailPage />)} />,
    <Route key="restaurant-modifier-new" path="/restaurant/modifiers/new" element={gated("restaurant", ["restaurant.manage", "restaurant.menu.create"], "restaurant", <RestaurantModifierFormPage />)} />,
    <Route key="restaurant-modifier-edit" path="/restaurant/modifiers/:id/edit" element={gated("restaurant", ["restaurant.manage", "restaurant.menu.update"], "restaurant", <RestaurantModifierEditPage />)} />,
    <Route key="restaurant-modifier-detail" path="/restaurant/modifiers/:id" element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantModifierDetailPage />)} />,
    <Route key="restaurant-ingredient-new" path="/restaurant/ingredients/new" element={gated("restaurant", ["restaurant.manage", "inventory.manage", "products.manage"], "restaurant", <RestaurantIngredientFormPage />)} />,
    <Route key="restaurant-ingredient-edit" path="/restaurant/ingredients/:id/edit" element={gated("restaurant", ["restaurant.manage", "inventory.manage", "products.manage"], "restaurant", <RestaurantIngredientEditPage />)} />,
    <Route key="restaurant-ingredient-detail" path="/restaurant/ingredients/:id" element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantIngredientDetailPage />)} />,
    <Route key="restaurant-recipe-new" path="/restaurant/recipes/new" element={gated("restaurant", ["restaurant.manage", "restaurant.menu.update"], "restaurant", <RestaurantRecipeFormPage />)} />,
    <Route key="restaurant-recipe-edit" path="/restaurant/recipes/:id/edit" element={gated("restaurant", ["restaurant.manage", "restaurant.menu.update"], "restaurant", <RestaurantRecipeEditPage />)} />,
    <Route key="restaurant-recipe-detail" path="/restaurant/recipes/:id" element={gated("restaurant", "restaurant.view", "restaurant", <RestaurantRecipeDetailPage />)} />,
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

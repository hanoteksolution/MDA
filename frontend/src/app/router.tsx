import { BrowserRouter, HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { isTauri } from "@/utils/platform";
import { AppShell } from "@/layouts/AppShell/AppShell";
import { AuthLayout, ProtectedRoute } from "@/layouts/AuthLayout/AuthLayout";
import { PermissionGuard } from "@/components/auth/PermissionGuard";
import { SetupPage } from "@/pages/auth/SetupPage";
import { OnboardingPage } from "@/pages/auth/OnboardingPage";
import { ConnectionPage } from "@/pages/auth/ConnectionPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import {
  ProductsPage,
  ProductFormPage,
  ProductEditPage,
  CategoriesPage,
  InventoryDashboardPage,
  StockPage,
  AdjustmentsPage,
  WarehousesPage,
} from "@/app/routes/phase2";
import {
  SettingsPage,
  AdminPage,
  PosPage,
  WaiterPerformancePage,
  PurchasesPage,
  SalesPage,
  DailyOpsPage,
  ReceiptManagementPage,
  ExpensesPage,
  TrashPage,
  CustomersPage,
  SuppliersPage,
  FinancePage,
  ReportsPage,
  StaffPerformancePage,
  PlatformShopsPage,
  PlatformSubscriptionsPage,
  PlatformTenantsPage,
  PlatformTenantDetailPage,
  PlatformShopDetailPage,
  PlatformDemosPage,
  FutsalPage,
  PharmacyPage,
  GymPage,
  RestaurantPage,
  HotelPage,
  PropertyPage,
  HousingPage,
  OfficePage,
} from "@/app/routes/modules";
import {
  CustomerFormPage,
  CustomerEditPage,
  SupplierFormPage,
  SupplierEditPage,
  PurchaseFormPage,
  PurchaseEditPage,
  UserFormPage,
  UserEditPage,
  RoleFormPage,
  RoleEditPage,
  BranchFormPage,
  BranchEditPage,
} from "@/app/routes/forms";
import {
  InvoiceFormPage,
  InvoiceEditPage,
  QuotationFormPage,
  QuotationEditPage,
} from "@/app/routes/sales";

const Router = isTauri() ? HashRouter : BrowserRouter;

export function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/setup" element={<SetupPage />} />
          <Route path="/onboard" element={<OnboardingPage />} />
          <Route path="/connection" element={<ConnectionPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>

        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route
            path="/dashboard"
            element={
              <PermissionGuard permission="dashboard.view">
                <DashboardPage />
              </PermissionGuard>
            }
          />

          {/* Products */}
          <Route
            path="/products"
            element={
              <PermissionGuard permission="products.view" module="inventory">
                <ProductsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/products/new"
            element={
              <PermissionGuard permission="products.create" module="inventory">
                <ProductFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/products/:id/edit"
            element={
              <PermissionGuard permission="products.update" module="inventory">
                <ProductEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/categories"
            element={
              <PermissionGuard permission="products.view" module="inventory">
                <CategoriesPage />
              </PermissionGuard>
            }
          />

          {/* Inventory */}
          <Route
            path="/inventory"
            element={
              <PermissionGuard permission="inventory.view" module="inventory">
                <InventoryDashboardPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/inventory/stock"
            element={
              <PermissionGuard permission="inventory.view" module="inventory">
                <StockPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/inventory/adjustments"
            element={
              <PermissionGuard permission="inventory.adjust" module="inventory">
                <AdjustmentsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/inventory/warehouses"
            element={
              <PermissionGuard permission="inventory.view" module="inventory">
                <WarehousesPage />
              </PermissionGuard>
            }
          />

          {/* Operations */}
          <Route
            path="/pos"
            element={
              <PermissionGuard permission="pos.access" module="pos">
                <PosPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/purchases"
            element={
              <PermissionGuard permission="purchases.view" module="purchases">
                <PurchasesPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/purchases/new"
            element={
              <PermissionGuard permission="purchases.create" module="purchases">
                <PurchaseFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/purchases/:id/edit"
            element={
              <PermissionGuard permission="purchases.update" module="purchases">
                <PurchaseEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/sales"
            element={
              <PermissionGuard permission="sales.view" module="sales">
                <SalesPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/daily-ops"
            element={
              <PermissionGuard permission="sales.view" module="sales">
                <DailyOpsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/receipts"
            element={
              <PermissionGuard permission="sales.view" module="sales">
                <ReceiptManagementPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/expenses"
            element={
              <PermissionGuard permission={["finance.view", "sales.view"]}>
                <ExpensesPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/trash"
            element={
              <PermissionGuard permission="trash.view">
                <TrashPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/waiter-performance"
            element={
              <PermissionGuard permission={["pos.access", "sales.view"]} module="pos">
                <WaiterPerformancePage />
              </PermissionGuard>
            }
          />
          <Route
            path="/sales/invoices/new"
            element={
              <PermissionGuard permission="sales.create">
                <InvoiceFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/sales/invoices/:id/edit"
            element={
              <PermissionGuard permission="sales.update">
                <InvoiceEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/sales/quotations/new"
            element={
              <PermissionGuard permission="sales.create">
                <QuotationFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/sales/quotations/:id/edit"
            element={
              <PermissionGuard permission="sales.update">
                <QuotationEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/customers"
            element={
              <PermissionGuard permission="customers.view" module="sales">
                <CustomersPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/customers/new"
            element={
              <PermissionGuard permission="customers.create" module="sales">
                <CustomerFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/customers/:id/edit"
            element={
              <PermissionGuard permission="customers.update" module="sales">
                <CustomerEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/suppliers"
            element={
              <PermissionGuard permission="suppliers.view" module="purchases">
                <SuppliersPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/suppliers/new"
            element={
              <PermissionGuard permission="suppliers.create" module="purchases">
                <SupplierFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/suppliers/:id/edit"
            element={
              <PermissionGuard permission="suppliers.update" module="purchases">
                <SupplierEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/finance"
            element={
              <PermissionGuard permission="finance.view">
                <FinancePage />
              </PermissionGuard>
            }
          />
          <Route
            path="/futsal"
            element={
              <PermissionGuard permission="futsal.view" module="futsal">
                <FutsalPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/pharmacy"
            element={
              <PermissionGuard permission="pharmacy.view" module="pharmacy">
                <PharmacyPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/gym"
            element={
              <PermissionGuard permission="gym.view" module="gym">
                <GymPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/restaurant"
            element={
              <PermissionGuard permission="restaurant.view" module="restaurant">
                <RestaurantPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/hotel"
            element={
              <PermissionGuard permission="hotel.view" module="hotel">
                <HotelPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/property"
            element={
              <PermissionGuard permission="property_management.view" module="property_management">
                <PropertyPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/housing"
            element={
              <PermissionGuard permission="housing_rental.view" module="housing_rental">
                <HousingPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/office"
            element={
              <PermissionGuard permission="office_rental.view" module="office_rental">
                <OfficePage />
              </PermissionGuard>
            }
          />
          <Route
            path="/reports"
            element={
              <PermissionGuard permission="reports.view">
                <ReportsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/staff-performance"
            element={
              <PermissionGuard permission="staff.performance.view">
                <StaffPerformancePage />
              </PermissionGuard>
            }
          />
          <Route
            path="/platform/tenants"
            element={
              <PermissionGuard permission="platform.view">
                <PlatformTenantsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/platform/tenants/:groupId"
            element={
              <PermissionGuard permission="platform.view">
                <PlatformTenantDetailPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/platform/shops/:shopId"
            element={
              <PermissionGuard permission="platform.view">
                <PlatformShopDetailPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/platform/demos"
            element={
              <PermissionGuard permission="platform.view">
                <PlatformDemosPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/platform"
            element={
              <PermissionGuard permission="platform.view">
                <PlatformShopsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/platform/subscriptions"
            element={
              <PermissionGuard permission="subscriptions.manage">
                <PlatformSubscriptionsPage />
              </PermissionGuard>
            }
          />

          {/* Administration */}
          <Route
            path="/admin"
            element={
              <PermissionGuard permission={["users.view", "roles.view"]}>
                <AdminPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/admin/users/new"
            element={
              <PermissionGuard permission="users.create">
                <UserFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/admin/users/:id/edit"
            element={
              <PermissionGuard permission="users.update">
                <UserEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/admin/roles/new"
            element={
              <PermissionGuard permission="roles.create">
                <RoleFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/admin/roles/:id/edit"
            element={
              <PermissionGuard permission="roles.update">
                <RoleEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/settings"
            element={
              <PermissionGuard permission="settings.view">
                <SettingsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/settings/branches/new"
            element={
              <PermissionGuard permission="branches.create">
                <BranchFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/settings/branches/:id/edit"
            element={
              <PermissionGuard permission="branches.update">
                <BranchEditPage />
              </PermissionGuard>
            }
          />
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/layouts/AppShell/AppShell";
import { AuthLayout, ProtectedRoute } from "@/layouts/AuthLayout/AuthLayout";
import { PermissionGuard } from "@/components/auth/PermissionGuard";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import {
  ProductsPage,
  ProductFormPage,
  ProductEditPage,
  InventoryDashboardPage,
  StockPage,
  AdjustmentsPage,
  WarehousesPage,
} from "@/app/routes/phase2";
import {
  SettingsPage,
  AdminPage,
  PosPage,
  PurchasesPage,
  SalesPage,
  CustomersPage,
  SuppliersPage,
  FinancePage,
  ReportsPage,
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

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AuthLayout />}>
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
              <PermissionGuard permission="products.view">
                <ProductsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/products/new"
            element={
              <PermissionGuard permission="products.create">
                <ProductFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/products/:id/edit"
            element={
              <PermissionGuard permission="products.update">
                <ProductEditPage />
              </PermissionGuard>
            }
          />

          {/* Inventory */}
          <Route
            path="/inventory"
            element={
              <PermissionGuard permission="inventory.view">
                <InventoryDashboardPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/inventory/stock"
            element={
              <PermissionGuard permission="inventory.view">
                <StockPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/inventory/adjustments"
            element={
              <PermissionGuard permission="inventory.adjust">
                <AdjustmentsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/inventory/warehouses"
            element={
              <PermissionGuard permission="inventory.view">
                <WarehousesPage />
              </PermissionGuard>
            }
          />

          {/* Operations */}
          <Route
            path="/pos"
            element={
              <PermissionGuard permission="pos.access">
                <PosPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/purchases"
            element={
              <PermissionGuard permission="purchases.view">
                <PurchasesPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/purchases/new"
            element={
              <PermissionGuard permission="purchases.create">
                <PurchaseFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/purchases/:id/edit"
            element={
              <PermissionGuard permission="purchases.update">
                <PurchaseEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/sales"
            element={
              <PermissionGuard permission="sales.view">
                <SalesPage />
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
              <PermissionGuard permission="sales.create">
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
              <PermissionGuard permission="sales.create">
                <QuotationEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/customers"
            element={
              <PermissionGuard permission="customers.view">
                <CustomersPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/customers/new"
            element={
              <PermissionGuard permission="customers.create">
                <CustomerFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/customers/:id/edit"
            element={
              <PermissionGuard permission="customers.update">
                <CustomerEditPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/suppliers"
            element={
              <PermissionGuard permission="suppliers.view">
                <SuppliersPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/suppliers/new"
            element={
              <PermissionGuard permission="suppliers.create">
                <SupplierFormPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/suppliers/:id/edit"
            element={
              <PermissionGuard permission="suppliers.update">
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
            path="/reports"
            element={
              <PermissionGuard permission="reports.view">
                <ReportsPage />
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
    </BrowserRouter>
  );
}

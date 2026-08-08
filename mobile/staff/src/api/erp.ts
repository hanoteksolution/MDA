import { apiRequest } from "./client";

export interface Page<T> {
  results: T[];
  count: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
}

export function money(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

export function fetchDashboardKpis(period = "today") {
  return apiRequest<Record<string, unknown>>(`/dashboard/kpis/?period=${period}`);
}

export function fetchRecentSales() {
  return apiRequest<{ results: Record<string, unknown>[]; count: number }>("/dashboard/recent-sales/");
}

export function fetchLowStockDashboard() {
  return apiRequest<{ results: Record<string, unknown>[]; count: number }>("/dashboard/low-stock/");
}

export function fetchDashboardWidgets() {
  return apiRequest<{ results: Record<string, unknown>[]; count: number }>("/dashboard/widgets/");
}

export function searchProducts(q: string) {
  const qs = q ? `?q=${encodeURIComponent(q)}&limit=20` : "?limit=20";
  return apiRequest<Record<string, unknown>[]>(`/products/search/${qs}`);
}

export function posCheckout(payload: Record<string, unknown>) {
  return apiRequest<Record<string, unknown>>("/pos/checkout/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchSalesSummary() {
  return apiRequest<Record<string, unknown>>("/sales/summary/");
}

export function fetchInvoices() {
  return apiRequest<Page<Record<string, unknown>>>("/sales/invoices/?page_size=30");
}

export function fetchInventorySummary() {
  return apiRequest<Record<string, unknown>>("/inventory/summary/");
}

export function fetchInventoryList() {
  return apiRequest<Page<Record<string, unknown>>>("/inventory/?page_size=40");
}

export function fetchLowStock() {
  return apiRequest<Page<Record<string, unknown>>>("/inventory/low-stock/?page_size=30");
}

export function fetchPurchaseSummary() {
  return apiRequest<Record<string, unknown>>("/purchases/summary/");
}

export function fetchPurchaseOrders() {
  return apiRequest<Page<Record<string, unknown>>>("/purchases/?page_size=30");
}

export function fetchCustomers() {
  return apiRequest<Page<Record<string, unknown>>>("/customers/?page_size=40");
}

export function fetchCustomerSummary() {
  return apiRequest<Record<string, unknown>>("/customers/summary/");
}

export function fetchSuppliers() {
  return apiRequest<Page<Record<string, unknown>>>("/suppliers/?page_size=40");
}

export function fetchFinanceSummary(period = "month") {
  return apiRequest<Record<string, unknown>>(`/finance/summary/?period=${period}`);
}

export function fetchBusinessUnits() {
  return apiRequest<Page<Record<string, unknown>>>("/finance/business-units/?is_active=true&page_size=50");
}

export function fetchProfitLoss(businessUnitId?: string) {
  const qs = businessUnitId ? `?business_unit_id=${encodeURIComponent(businessUnitId)}` : "";
  return apiRequest<Record<string, unknown>>(`/finance/reports/profit-loss/${qs}`);
}

export function fetchAccountingEquation() {
  return apiRequest<Record<string, unknown>>("/finance/equation/");
}

export function fetchReportCatalog() {
  return apiRequest<Record<string, unknown>[]>("/reports/catalog/");
}

export function fetchReportData(category: string, report: string) {
  return apiRequest<Record<string, unknown>>(
    `/reports/data/?category=${encodeURIComponent(category)}&report=${encodeURIComponent(report)}`
  );
}

export function fetchCompany() {
  return apiRequest<Record<string, unknown>>("/settings/company/");
}

export function fetchBranches() {
  return apiRequest<Record<string, unknown>[]>("/settings/branches/");
}

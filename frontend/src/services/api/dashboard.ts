import type { ApiResponse } from "@/types/models";
import type { DashboardKPIs } from "@/types/models";
import { apiRequest } from "./http";

export interface DashboardTransaction {
  id: string;
  customer: string;
  amount: number;
  status: string;
  date: string;
}

export interface DashboardLowStock {
  id: string;
  product: string;
  sku: string;
  current: number;
  minimum: number;
  warehouse: string;
}

export interface DashboardTopProduct {
  id: string;
  name: string;
  sku: string;
  sold: number;
  revenue: number;
}

export interface DashboardCharts {
  sales_trend: { month: string; sales: number; revenue: number }[];
  revenue: { month: string; revenue: number }[];
  profit: { month: string; profit: number; expenses: number }[];
}

export const dashboardApi = {
  kpis: (period = "today") =>
    apiRequest<ApiResponse<DashboardKPIs>>(`/dashboard/kpis/?period=${period}`),

  recentSales: () =>
    apiRequest<ApiResponse<{ results: DashboardTransaction[]; count: number }>>("/dashboard/recent-sales/"),

  lowStock: () =>
    apiRequest<ApiResponse<{ results: DashboardLowStock[]; count: number }>>("/dashboard/low-stock/"),

  topProducts: (period = "month") =>
    apiRequest<ApiResponse<DashboardTopProduct[]>>(`/dashboard/top-products/?period=${period}`),

  charts: () => apiRequest<ApiResponse<DashboardCharts>>("/dashboard/charts/"),
};

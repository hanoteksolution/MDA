import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface ReportResult {
  columns: string[];
  rows: Record<string, string | number>[];
}

export interface SalesReportPrintData {
  date_from: string;
  date_to: string;
  kpis: {
    total_sales: number;
    total_orders: number;
    total_customers: number;
    total_profit: number;
  };
  hourly_sales: { hour: string; value: number }[];
  sales_by_category: { label: string; revenue: number; pct: number }[];
  top_products: {
    index: number;
    name: string;
    sku: string;
    sold: number;
    revenue: number;
    profit: number;
  }[];
  summary: {
    total_sales: number;
    total_cost: number;
    total_profit: number;
    profit_margin: number;
    discounts: number;
    returns: number;
    tax_collected: number;
  };
}

export const reportsApi = {
  data: (params: {
    category: string;
    report: string;
    date_from?: string;
    date_to?: string;
  }) => apiRequest<ApiResponse<ReportResult>>(`/reports/data/${qs(params)}`),

  salesPrint: (params: { date_from?: string; date_to?: string } = {}) =>
    apiRequest<ApiResponse<SalesReportPrintData>>(`/reports/sales-print/${qs(params)}`),

  chart: (category: string) =>
    apiRequest<ApiResponse<{ month: string; revenue?: number; profit?: number; expenses?: number }[]>>(
      `/reports/chart/?category=${category}`
    ),
};

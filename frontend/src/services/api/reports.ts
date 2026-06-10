import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface ReportResult {
  columns: string[];
  rows: Record<string, string | number>[];
}

export const reportsApi = {
  data: (params: {
    category: string;
    report: string;
    date_from?: string;
    date_to?: string;
  }) => apiRequest<ApiResponse<ReportResult>>(`/reports/data/${qs(params)}`),

  chart: (category: string) =>
    apiRequest<ApiResponse<{ month: string; revenue?: number; profit?: number; expenses?: number }[]>>(
      `/reports/chart/?category=${category}`
    ),
};

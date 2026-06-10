import type { ApiResponse } from "@/types/models";
import { apiRequest } from "./http";

export interface FinanceKPIs {
  revenue: number;
  expenses: number;
  net_profit: number;
  cash_collected: number;
  cash_balance: number;
}

export interface FinanceAccount {
  id: string;
  name: string;
  type: string;
  balance: number;
}

export interface FinanceActivity {
  id: string;
  label: string;
  amount: number;
  type: "in" | "out";
  date: string;
}

export interface FinanceExpense {
  id: string;
  description: string;
  category: string;
  date: string;
  amount: number;
  status: string;
}

export interface FinanceSummary {
  kpis: FinanceKPIs;
  activity: FinanceActivity[];
  accounts: FinanceAccount[];
  expenses: FinanceExpense[];
  chart: { month: string; profit: number; expenses: number }[];
}

export const financeApi = {
  summary: (period = "month") =>
    apiRequest<ApiResponse<FinanceSummary>>(`/finance/summary/?period=${period}`),
};

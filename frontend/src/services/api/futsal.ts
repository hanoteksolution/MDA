import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest } from "./http";

export interface FutsalSummary {
  courts: number;
  teams: number;
  players: number;
  bookings_today: number;
  hours_today: number;
  bookings_month: number;
  income_month: number;
  expense_month: number;
  profit_month: number;
}

export interface FutsalCourt {
  id: string;
  name: string;
  code: string;
  branch_id: string;
  branch_name: string;
  hourly_rate: number;
  is_active: boolean;
  notes: string;
}

export interface FutsalTeam {
  id: string;
  name: string;
  branch_id: string;
  captain_name: string;
  contact_phone: string;
  player_count: number;
  is_active: boolean;
  notes: string;
}

export interface FutsalPlayer {
  id: string;
  full_name: string;
  team_id: string | null;
  team_name: string;
  branch_id: string;
  phone: string;
  jersey_number: number | null;
  is_active: boolean;
  notes: string;
}

export interface FutsalBooking {
  id: string;
  court_id: string;
  court_name: string;
  branch_id: string;
  team_id: string | null;
  team_name: string;
  customer_id: string | null;
  customer_name: string;
  title: string;
  start_at: string;
  end_at: string;
  hours: number;
  hourly_rate: number;
  amount: number;
  amount_paid: number;
  status: string;
  notes: string;
}

export interface FutsalLedgerEntry {
  id: string;
  branch_id: string;
  entry_type: "income" | "expense";
  category: string;
  amount: number;
  entry_date: string;
  description: string;
  booking_id: string | null;
}

function qs(params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") q.set(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const futsalApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<FutsalSummary>>(`/futsal/summary/${qs({ branch_id: branchId })}`),

  courts: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<FutsalCourt>>(`/futsal/courts/${qs({ page, branch_id: branchId })}`),

  createCourt: (data: Partial<FutsalCourt>) =>
    apiRequest<ApiResponse<FutsalCourt>>("/futsal/courts/", { method: "POST", body: JSON.stringify(data) }),

  teams: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<FutsalTeam>>(`/futsal/teams/${qs({ page, branch_id: branchId })}`),

  createTeam: (data: Partial<FutsalTeam>) =>
    apiRequest<ApiResponse<FutsalTeam>>("/futsal/teams/", { method: "POST", body: JSON.stringify(data) }),

  players: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<FutsalPlayer>>(`/futsal/players/${qs({ page, branch_id: branchId })}`),

  createPlayer: (data: Partial<FutsalPlayer>) =>
    apiRequest<ApiResponse<FutsalPlayer>>("/futsal/players/", { method: "POST", body: JSON.stringify(data) }),

  bookings: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<FutsalBooking>>(`/futsal/bookings/${qs({ page, branch_id: branchId })}`),

  createBooking: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<FutsalBooking>>("/futsal/bookings/", { method: "POST", body: JSON.stringify(data) }),

  ledger: (page = 1, branchId?: string, entryType?: string) =>
    apiRequest<ApiListResponse<FutsalLedgerEntry>>(
      `/futsal/ledger/${qs({ page, branch_id: branchId, entry_type: entryType })}`
    ),

  createLedger: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<FutsalLedgerEntry>>("/futsal/ledger/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

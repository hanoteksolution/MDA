import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface HousingSummary {
  tenants: number;
  leases_active: number;
  leases_draft: number;
  residential_units: number;
  units_occupied: number;
  units_vacant: number;
  charges_pending: number;
  charges_overdue: number;
  rent_pending_amount: number;
  deposits_held: number;
}

export interface HousingTenant {
  id: string;
  branch_id: string | null;
  customer_id: string | null;
  full_name: string;
  phone: string;
  email: string;
  id_number: string;
  notes: string;
  is_active: boolean;
}

export interface LeaseCharge {
  id: string;
  lease_id: string;
  branch_id: string;
  charge_type: string;
  status: string;
  description: string;
  amount: number;
  period_start: string | null;
  period_end: string | null;
  due_date: string | null;
  invoice_id: string | null;
  invoice_number?: string | null;
  posted_at: string | null;
}

export interface HousingLease {
  id: string;
  lease_number: string;
  branch_id: string;
  unit_id: string;
  unit_code: string;
  building_name: string;
  housing_tenant_id: string;
  tenant_name: string;
  tenant_phone: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  rent_amount: number;
  deposit_amount: number;
  deposit_held: boolean;
  notes: string;
  activated_at: string | null;
  terminated_at: string | null;
  charges?: LeaseCharge[];
  charge_count?: number;
}

export const housingApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<HousingSummary>>(
      `/housing/summary/${qs({ branch_id: branchId })}`
    ),

  tenants: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<HousingTenant>>(
      `/housing/tenants/${qs({ page, branch_id: branchId })}`
    ),

  createTenant: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<HousingTenant>>("/housing/tenants/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  leases: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<HousingLease>>(
      `/housing/leases/${qs({ page, branch_id: branchId, status })}`
    ),

  createLease: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<HousingLease>>("/housing/leases/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  activate: (id: string) =>
    apiRequest<ApiResponse<HousingLease>>(`/housing/leases/${id}/activate/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  terminate: (id: string) =>
    apiRequest<ApiResponse<HousingLease>>(`/housing/leases/${id}/terminate/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  postRent: (id: string) =>
    apiRequest<ApiResponse<LeaseCharge>>(`/housing/leases/${id}/charges/`, {
      method: "POST",
      body: JSON.stringify({ post_rent: true }),
    }),

  lease: (id: string) =>
    apiRequest<ApiResponse<HousingLease>>(`/housing/leases/${id}/`),

  invoiceCharge: (
    chargeId: string,
    data?: { payment_method?: string; payment_reference?: string }
  ) =>
    apiRequest<ApiResponse<LeaseCharge>>(`/housing/charges/${chargeId}/invoice/`, {
      method: "POST",
      body: JSON.stringify(data || { payment_method: "on_account" }),
    }),

  markPaid: (
    chargeId: string,
    data?: { payment_method?: string; payment_reference?: string }
  ) =>
    apiRequest<ApiResponse<LeaseCharge>>(`/housing/charges/${chargeId}/paid/`, {
      method: "POST",
      body: JSON.stringify(data || { payment_method: "cash" }),
    }),
};

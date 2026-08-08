import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface OfficeSummary {
  tenants: number;
  leases_active: number;
  leases_draft: number;
  office_units: number;
  units_occupied: number;
  units_vacant: number;
  charges_pending: number;
  charges_overdue: number;
  rent_pending_amount: number;
  deposits_held: number;
}

export interface OfficeTenant {
  id: string;
  branch_id: string | null;
  customer_id: string | null;
  company_name: string;
  registration_number: string;
  contact_name: string;
  phone: string;
  email: string;
  notes: string;
  is_active: boolean;
}

export interface OfficeLeaseCharge {
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

export interface OfficeLease {
  id: string;
  lease_number: string;
  branch_id: string;
  unit_id: string;
  unit_code: string;
  building_name: string;
  office_tenant_id: string;
  company_name: string;
  contact_name: string;
  tenant_phone: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  rent_amount: number;
  service_charge: number;
  monthly_total: number;
  deposit_amount: number;
  deposit_held: boolean;
  parking_slots: number;
  furnished: boolean;
  internet_included: boolean;
  electricity_included: boolean;
  notes: string;
  activated_at: string | null;
  terminated_at: string | null;
  charges?: OfficeLeaseCharge[];
  charge_count?: number;
}

export const officeApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<OfficeSummary>>(
      `/office/summary/${qs({ branch_id: branchId })}`
    ),

  tenants: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<OfficeTenant>>(
      `/office/tenants/${qs({ page, branch_id: branchId })}`
    ),

  leases: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<OfficeLease>>(
      `/office/leases/${qs({ page, branch_id: branchId, status })}`
    ),

  createLease: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<OfficeLease>>("/office/leases/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  activate: (id: string) =>
    apiRequest<ApiResponse<OfficeLease>>(`/office/leases/${id}/activate/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  terminate: (id: string) =>
    apiRequest<ApiResponse<OfficeLease>>(`/office/leases/${id}/terminate/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  postRent: (id: string) =>
    apiRequest<ApiResponse<OfficeLeaseCharge>>(`/office/leases/${id}/charges/`, {
      method: "POST",
      body: JSON.stringify({ post_rent: true }),
    }),

  lease: (id: string) =>
    apiRequest<ApiResponse<OfficeLease>>(`/office/leases/${id}/`),

  invoiceCharge: (
    chargeId: string,
    data?: { payment_method?: string; payment_reference?: string }
  ) =>
    apiRequest<ApiResponse<OfficeLeaseCharge>>(`/office/charges/${chargeId}/invoice/`, {
      method: "POST",
      body: JSON.stringify(data || { payment_method: "on_account" }),
    }),

  markPaid: (
    chargeId: string,
    data?: { payment_method?: string; payment_reference?: string }
  ) =>
    apiRequest<ApiResponse<OfficeLeaseCharge>>(`/office/charges/${chargeId}/paid/`, {
      method: "POST",
      body: JSON.stringify(data || { payment_method: "cash" }),
    }),
};

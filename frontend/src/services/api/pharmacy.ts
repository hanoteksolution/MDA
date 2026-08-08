import type { ApiResponse } from "@/types/models";
import type { ApiListResponse } from "@/types/models/catalog";
import { apiRequest, qs } from "./http";

export interface PharmacyBatch {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  category_id?: string | null;
  category_name?: string;
  warehouse_id: string;
  warehouse_name: string;
  batch_number: string;
  manufacturing_date: string | null;
  expiry_date: string | null;
  days_to_expiry: number | null;
  status: "ok" | "expiring" | "expired";
  quantity: number;
  cost_price: number | null;
  is_active: boolean;
  notes: string;
}

export interface PharmacyCategory {
  id: string;
  name: string;
  batch_count: number;
  quantity: number;
  product_count: number;
}

export interface PharmacySummary {
  batch_count: number;
  total_quantity: number;
  expired_count: number;
  expiring_count: number;
  expiry_alert_days: number;
  categories?: PharmacyCategory[];
  features?: {
    batches?: boolean;
    prescriptions?: boolean;
    expiry_alerts?: boolean;
  };
  prescriptions_active?: number;
  prescriptions_dispensed?: number;
  prescriptions_total?: number;
}

export interface PrescriptionLine {
  id: string;
  product_id: string | null;
  category_id?: string | null;
  category_name?: string;
  drug_name: string;
  dosage: string;
  frequency: string;
  duration_days: number | null;
  quantity: number;
  quantity_dispensed?: number;
  quantity_remaining?: number;
  instructions: string;
  sort_order: number;
}

export interface Prescription {
  id: string;
  rx_number: string;
  patient_name: string;
  patient_phone: string;
  customer_id: string | null;
  prescribed_by: string;
  status: "draft" | "active" | "dispensed" | "cancelled";
  prescribed_at: string | null;
  dispensed_at: string | null;
  dispensed_by_id: string | null;
  branch_id: string | null;
  notes: string;
  line_count: number;
  lines: PrescriptionLine[];
}

export const pharmacyApi = {
  summary: () => apiRequest<ApiResponse<PharmacySummary>>("/pharmacy/summary/"),

  categories: () =>
    apiRequest<ApiResponse<PharmacyCategory[]>>("/pharmacy/categories/"),

  batches: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<PharmacyBatch>>(`/pharmacy/batches/${qs(params)}`),

  expiring: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<PharmacyBatch>>(`/pharmacy/batches/expiring/${qs(params)}`),

  createBatch: (data: {
    product_id: string;
    warehouse_id: string;
    quantity: number;
    batch_number?: string;
    expiry_date?: string;
    manufacturing_date?: string;
    cost_price?: number;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<PharmacyBatch>>("/pharmacy/batches/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  fefoPreview: (params: { product_id: string; warehouse_id: string; quantity?: number }) =>
    apiRequest<
      ApiResponse<
        { batch_id: string; batch_number: string; expiry_date: string | null; quantity: number }[]
      >
    >(`/pharmacy/batches/fefo-preview/${qs(params)}`),

  prescriptions: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Prescription>>(`/pharmacy/prescriptions/${qs(params)}`),

  createPrescription: (data: {
    patient_name: string;
    patient_phone?: string;
    prescribed_by?: string;
    prescribed_at?: string;
    notes?: string;
    drug_name?: string;
    product_id?: string;
    dosage?: string;
    frequency?: string;
    quantity?: number;
    instructions?: string;
    lines?: {
      drug_name: string;
      product_id?: string;
      dosage?: string;
      frequency?: string;
      quantity?: number;
      instructions?: string;
      duration_days?: number;
    }[];
  }) =>
    apiRequest<ApiResponse<Prescription>>("/pharmacy/prescriptions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  dispensePrescription: (
    id: string,
    data: {
      notes?: string;
      warehouse_id?: string;
      lines?: { id: string; quantity: number }[];
      fill_quantities?: Record<string, number>;
    } = {}
  ) =>
    apiRequest<ApiResponse<Prescription>>(`/pharmacy/prescriptions/${id}/dispense/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

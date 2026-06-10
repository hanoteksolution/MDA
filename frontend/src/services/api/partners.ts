import type { ApiResponse } from "@/types/models";
import type {
  ApiListResponse,
  Customer,
  CustomerSummary,
  PurchaseOrder,
  PurchaseSummary,
  Supplier,
  SupplierSummary,
} from "@/types/models/partners";
import { apiRequest, qs } from "./http";

export const customersApi = {
  list: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Customer>>(`/customers/${qs(params)}`),

  get: (id: string) => apiRequest<ApiResponse<Customer>>(`/customers/${id}/`),

  summary: () => apiRequest<ApiResponse<CustomerSummary>>("/customers/summary/"),

  create: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Customer>>("/customers/", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Customer>>(`/customers/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) =>
    apiRequest<ApiResponse<null>>(`/customers/${id}/`, { method: "DELETE" }),
};

export const suppliersApi = {
  list: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Supplier>>(`/suppliers/${qs(params)}`),

  get: (id: string) => apiRequest<ApiResponse<Supplier>>(`/suppliers/${id}/`),

  summary: () => apiRequest<ApiResponse<SupplierSummary>>("/suppliers/summary/"),

  create: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Supplier>>("/suppliers/", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Supplier>>(`/suppliers/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) =>
    apiRequest<ApiResponse<null>>(`/suppliers/${id}/`, { method: "DELETE" }),
};

export const purchasesApi = {
  list: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<PurchaseOrder>>(`/purchases/${qs(params)}`),

  get: (id: string) => apiRequest<ApiResponse<PurchaseOrder>>(`/purchases/${id}/`),

  summary: () => apiRequest<ApiResponse<PurchaseSummary>>("/purchases/summary/"),

  create: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<PurchaseOrder>>("/purchases/", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<PurchaseOrder>>(`/purchases/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) =>
    apiRequest<ApiResponse<null>>(`/purchases/${id}/`, { method: "DELETE" }),
};

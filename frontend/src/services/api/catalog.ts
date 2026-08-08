import type { ApiResponse } from "@/types/models";
import type {
  ApiListResponse,
  AttributeDefinition,
  Brand,
  Category,
  InventoryAdjustment,
  InventoryItem,
  InventorySummary,
  PaginatedResponse,
  Product,
  ProductFormData,
  Unit,
  Warehouse,
} from "@/types/models/catalog";
import { apiRequest, apiUpload, qs } from "./http";

export const productsApi = {
  list: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Product>>(`/products/${qs(params)}`),

  search: (q: string, params: { limit?: number; category?: string } = {}) =>
    apiRequest<ApiResponse<Product[]>>(
      `/products/search/${qs({ q, limit: params.limit ?? 40, category: params.category })}`
    ),

  get: (id: string) => apiRequest<ApiResponse<Product>>(`/products/${id}/`),

  create: (data: ProductFormData) =>
    apiRequest<ApiResponse<Product>>("/products/", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: Partial<ProductFormData>) =>
    apiRequest<ApiResponse<Product>>(`/products/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) =>
    apiRequest<ApiResponse<null>>(`/products/${id}/`, { method: "DELETE" }),

  uploadImage: (file: File) =>
    apiUpload<ApiResponse<{ url: string; path: string }>>("/products/upload-image/", file),

  attributes: () =>
    apiRequest<ApiResponse<AttributeDefinition[]>>("/products/attributes/"),

  applicableAttributes: (params: { category_id?: string; business_type_id?: string } = {}) =>
    apiRequest<ApiResponse<AttributeDefinition[]>>(
      `/products/attributes/applicable/${qs(params)}`
    ),

  createAttribute: (data: Partial<AttributeDefinition> & { code: string; name: string }) =>
    apiRequest<ApiResponse<AttributeDefinition>>("/products/attributes/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  assignCategoryAttribute: (
    categoryId: string,
    data: { definition_id: string; is_required?: boolean | null; sort_order?: number }
  ) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/products/categories/${categoryId}/attributes/`,
      { method: "PUT", body: JSON.stringify(data) }
    ),

  categories: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Category>>(`/categories/${qs({ page_size: 100, ...params })}`),

  createCategory: (data: string | { name: string; description?: string; is_active?: boolean }) =>
    apiRequest<ApiResponse<Category>>("/categories/", {
      method: "POST",
      body: JSON.stringify(typeof data === "string" ? { name: data } : data),
    }),

  updateCategory: (
    id: string,
    data: { name?: string; description?: string; is_active?: boolean; parent_id?: string | null }
  ) =>
    apiRequest<ApiResponse<Category>>(`/categories/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteCategory: (id: string) =>
    apiRequest<ApiResponse<null>>(`/categories/${id}/`, { method: "DELETE" }),

  brands: () => apiRequest<ApiListResponse<Brand>>("/brands/?page_size=100"),

  createBrand: (name: string) =>
    apiRequest<ApiResponse<Brand>>("/brands/", { method: "POST", body: JSON.stringify({ name }) }),

  units: () => apiRequest<ApiResponse<Unit[]>>("/units/"),

  createUnit: (name: string) =>
    apiRequest<ApiResponse<Unit>>("/units/", {
      method: "POST",
      body: JSON.stringify({ name, abbreviation: name.slice(0, 3).toLowerCase() }),
    }),
};

export const inventoryApi = {
  list: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<InventoryItem>>(`/inventory/${qs(params)}`),

  summary: () => apiRequest<ApiResponse<InventorySummary>>("/inventory/summary/"),

  lowStock: () => apiRequest<ApiListResponse<InventoryItem>>("/inventory/low-stock/?page_size=50"),

  outOfStock: () => apiRequest<ApiListResponse<InventoryItem>>("/inventory/out-of-stock/?page_size=50"),

  adjustments: () => apiRequest<ApiListResponse<InventoryAdjustment>>("/inventory/adjustments/"),

  createAdjustment: (data: {
    warehouse_id: string;
    reason: string;
    items: { product_id: string; quantity_after: number }[];
  }) =>
    apiRequest<ApiResponse<InventoryAdjustment>>("/inventory/adjustments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  warehouses: () => apiRequest<ApiListResponse<Warehouse>>("/warehouses/?page_size=100"),

  createWarehouse: (data: Partial<Warehouse>) =>
    apiRequest<ApiResponse<Warehouse>>("/warehouses/", { method: "POST", body: JSON.stringify(data) }),

  transfers: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Record<string, unknown>>>(`/inventory/transfers/${qs(params)}`),

  createTransfer: (data: {
    source_warehouse_id: string;
    destination_warehouse_id: string;
    branch_id?: string;
    notes?: string;
    lines?: { product_id: string; quantity: number }[];
  }) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/inventory/transfers/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  confirmTransfer: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/inventory/transfers/${id}/confirm/`, {
      method: "POST",
    }),

  cancelTransfer: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/inventory/transfers/${id}/cancel/`, {
      method: "POST",
    }),
};

export type { PaginatedResponse };

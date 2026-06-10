import type { ApiResponse } from "@/types/models";
import type {
  ApiListResponse,
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

  get: (id: string) => apiRequest<ApiResponse<Product>>(`/products/${id}/`),

  create: (data: ProductFormData) =>
    apiRequest<ApiResponse<Product>>("/products/", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: Partial<ProductFormData>) =>
    apiRequest<ApiResponse<Product>>(`/products/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) =>
    apiRequest<ApiResponse<null>>(`/products/${id}/`, { method: "DELETE" }),

  uploadImage: (file: File) =>
    apiUpload<ApiResponse<{ url: string; path: string }>>("/products/upload-image/", file),

  categories: () => apiRequest<ApiListResponse<Category>>("/categories/?page_size=100"),

  createCategory: (name: string) =>
    apiRequest<ApiResponse<Category>>("/categories/", { method: "POST", body: JSON.stringify({ name }) }),

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
};

export type { PaginatedResponse };

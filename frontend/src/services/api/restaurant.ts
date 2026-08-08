import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface RestaurantSummary {
  categories: number;
  menu_items: number;
  tables: number;
  tables_occupied: number;
  orders_open: number;
  orders_today: number;
}

export interface MenuCategory {
  id: string;
  name: string;
  branch_id: string;
  branch_name: string;
  sort_order: number;
  is_active: boolean;
  notes: string;
}

export interface MenuItem {
  id: string;
  category_id: string;
  category_name: string;
  branch_id: string;
  product_id: string | null;
  name: string;
  sku: string;
  description: string;
  unit_price: number;
  is_available: boolean;
  sort_order: number;
}

export interface DiningTable {
  id: string;
  branch_id: string;
  branch_name: string;
  code: string;
  label: string;
  capacity: number;
  status: "free" | "occupied" | "reserved";
  is_active: boolean;
  notes: string;
}

export interface OrderLine {
  id: string;
  menu_item_id: string;
  product_id: string | null;
  name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  status: string;
  notes: string;
}

export interface RestaurantOrder {
  id: string;
  order_number: string;
  branch_id: string;
  table_id: string | null;
  table_code: string | null;
  status: string;
  service_type: string;
  waiter_user_id: string | null;
  waiter_name: string;
  guest_count: number;
  subtotal: number;
  notes: string;
  opened_at: string | null;
  closed_at: string | null;
  lines?: OrderLine[];
  line_count?: number;
}

export const restaurantApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<RestaurantSummary>>(
      `/restaurant/summary/${qs({ branch_id: branchId })}`
    ),

  categories: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<MenuCategory>>(
      `/restaurant/categories/${qs({ page, branch_id: branchId })}`
    ),

  createCategory: (data: { name: string; branch_id: string; sort_order?: number }) =>
    apiRequest<ApiResponse<MenuCategory>>("/restaurant/categories/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  items: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<MenuItem>>(
      `/restaurant/items/${qs({ page, branch_id: branchId })}`
    ),

  createItem: (data: {
    name: string;
    branch_id: string;
    category_id: string;
    unit_price?: number;
    sku?: string;
  }) =>
    apiRequest<ApiResponse<MenuItem>>("/restaurant/items/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  tables: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<DiningTable>>(
      `/restaurant/tables/${qs({ page, branch_id: branchId })}`
    ),

  createTable: (data: {
    code: string;
    branch_id: string;
    label?: string;
    capacity?: number;
  }) =>
    apiRequest<ApiResponse<DiningTable>>("/restaurant/tables/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  orders: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<RestaurantOrder>>(
      `/restaurant/orders/${qs({ page, branch_id: branchId })}`
    ),

  createOrder: (data: {
    branch_id: string;
    table_id?: string;
    waiter_name?: string;
    guest_count?: number;
    lines?: { menu_item_id: string; quantity?: number }[];
  }) =>
    apiRequest<ApiResponse<RestaurantOrder>>("/restaurant/orders/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateOrderStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  order: (id: string) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/`),

  orderForPos: (id: string) =>
    apiRequest<
      ApiResponse<{
        order: {
          id: string;
          order_number: string;
          table_id: string | null;
          table_code: string | null;
          waiter_name: string;
          subtotal: number;
          status: string;
        };
        items: { product_id: string; quantity: number; unit_price: number; name: string; sku: string }[];
        notes: string;
      }>
    >(`/restaurant/orders/${id}/pos/`),
};

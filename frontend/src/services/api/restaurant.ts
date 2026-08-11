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
  floor_id?: string | null;
}

export interface RestaurantFloor {
  id: string;
  branch_id: string;
  branch_name: string;
  name: string;
  code: string;
  sort_order: number;
  is_active: boolean;
  notes: string;
}

export interface KitchenStation {
  id: string;
  branch_id: string;
  branch_name: string;
  name: string;
  code: string;
  sort_order: number;
  is_active: boolean;
  notes: string;
}

export interface ModifierGroup {
  id: string;
  branch_id: string;
  branch_name: string;
  name: string;
  code: string;
  required: boolean;
  min_select: number;
  max_select: number;
  sort_order: number;
  is_active: boolean;
  notes: string;
}

export interface Modifier {
  id: string;
  branch_id: string;
  group_id: string;
  group_name: string;
  name: string;
  code: string;
  price_delta: number;
  sort_order: number;
  is_active: boolean;
  notes: string;
}

export interface Ingredient {
  id: string;
  branch_id: string;
  product_id: string | null;
  name: string;
  code: string;
  unit: string;
  unit_cost: number;
  is_active: boolean;
  notes: string;
}

export interface RecipeIngredient {
  id: string;
  ingredient_id: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  unit_cost: number;
  notes: string;
}

export interface Recipe {
  id: string;
  branch_id: string;
  menu_item_id: string;
  menu_item_name: string;
  name: string;
  version: string;
  yield_qty: number;
  waste_percent: number;
  is_active: boolean;
  notes: string;
  total_cost: number;
  ingredients?: RecipeIngredient[];
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

  updateCategory: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<MenuCategory>>(`/restaurant/categories/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteCategory: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/categories/${id}/`, {
      method: "DELETE",
    }),

  updateItem: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<MenuItem>>(`/restaurant/items/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  item: (id: string) =>
    apiRequest<ApiResponse<MenuItem>>(`/restaurant/items/${id}/`),

  deleteItem: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/items/${id}/`, {
      method: "DELETE",
    }),

  updateTable: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<DiningTable>>(`/restaurant/tables/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteTable: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/tables/${id}/`, {
      method: "DELETE",
    }),

  floors: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<RestaurantFloor>>(
      `/restaurant/floors/${qs({ page, branch_id: branchId })}`
    ),
  createFloor: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<RestaurantFloor>>("/restaurant/floors/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateFloor: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<RestaurantFloor>>(`/restaurant/floors/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  floor: (id: string) =>
    apiRequest<ApiResponse<RestaurantFloor>>(`/restaurant/floors/${id}/`),
  deleteFloor: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/floors/${id}/`, {
      method: "DELETE",
    }),

  stations: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<KitchenStation>>(
      `/restaurant/stations/${qs({ page, branch_id: branchId })}`
    ),
  createStation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<KitchenStation>>("/restaurant/stations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateStation: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<KitchenStation>>(`/restaurant/stations/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  station: (id: string) =>
    apiRequest<ApiResponse<KitchenStation>>(`/restaurant/stations/${id}/`),
  deleteStation: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/stations/${id}/`, {
      method: "DELETE",
    }),

  modifierGroups: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<ModifierGroup>>(
      `/restaurant/modifier-groups/${qs({ page, branch_id: branchId })}`
    ),
  createModifierGroup: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ModifierGroup>>("/restaurant/modifier-groups/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  modifiers: (page = 1, branchId?: string, groupId?: string) =>
    apiRequest<ApiListResponse<Modifier>>(
      `/restaurant/modifiers/${qs({ page, branch_id: branchId, group_id: groupId })}`
    ),
  createModifier: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Modifier>>("/restaurant/modifiers/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  modifier: (id: string) =>
    apiRequest<ApiResponse<Modifier>>(`/restaurant/modifiers/${id}/`),
  updateModifier: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Modifier>>(`/restaurant/modifiers/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteModifier: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/modifiers/${id}/`, {
      method: "DELETE",
    }),

  ingredients: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<Ingredient>>(
      `/restaurant/ingredients/${qs({ page, branch_id: branchId })}`
    ),
  createIngredient: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Ingredient>>("/restaurant/ingredients/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  ingredient: (id: string) =>
    apiRequest<ApiResponse<Ingredient>>(`/restaurant/ingredients/${id}/`),
  updateIngredient: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Ingredient>>(`/restaurant/ingredients/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteIngredient: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/ingredients/${id}/`, {
      method: "DELETE",
    }),

  recipes: (page = 1, branchId?: string, menuItemId?: string) =>
    apiRequest<ApiListResponse<Recipe>>(
      `/restaurant/recipes/${qs({ page, branch_id: branchId, menu_item_id: menuItemId })}`
    ),
  createRecipe: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Recipe>>("/restaurant/recipes/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  recipe: (id: string) =>
    apiRequest<ApiResponse<Recipe>>(`/restaurant/recipes/${id}/`),
  updateRecipe: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Recipe>>(`/restaurant/recipes/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteRecipe: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/recipes/${id}/`, {
      method: "DELETE",
    }),
  addRecipeIngredient: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Recipe>>(`/restaurant/recipes/${id}/ingredients/`, {
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
  submitOrder: (id: string) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/submit/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  cancelOrder: (id: string) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  voidOrder: (id: string) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/void/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  refundOrder: (id: string) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/refund/`, {
      method: "POST",
      body: JSON.stringify({}),
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

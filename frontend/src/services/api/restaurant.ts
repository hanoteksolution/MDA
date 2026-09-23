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
  orders_preparing?: number;
  orders_ready?: number;
  orders_completed_today?: number;
  orders_cancelled_today?: number;
  todays_sales?: number;
  todays_orders_paid?: number;
  average_order_value?: number;
}

export interface CafeteriaProfile {
  id: string;
  branch_id: string;
  business_name: string;
  trading_name: string;
  currency: string;
  timezone: string;
  language: string;
  order_prefix: string;
  invoice_prefix: string;
  kitchen_barista_mode: string;
  table_service_enabled: boolean;
  takeaway_enabled: boolean;
  delivery_enabled: boolean;
  reservations_enabled: boolean;
  tips_enabled: boolean;
  service_charge_enabled: boolean;
  loyalty_enabled: boolean;
  recipe_deduction_enabled: boolean;
  negative_stock_allowed: boolean;
  default_warehouse_id: string | null;
  receipt_header: string;
  receipt_footer: string;
}

export interface BaristaTicket {
  id: string;
  order_number: string;
  queue_number: string;
  priority: string;
  status: string;
  service_type: string;
  waiter_name: string;
  barista_user_id: string | null;
  subtotal: number;
  opened_at: string | null;
  elapsed_seconds: number;
  board_column: string;
  lines: {
    id: string;
    name: string;
    quantity: number;
    notes: string;
    modifiers?: { name: string; price_delta: number }[];
  }[];
}

export interface BaristaQueue {
  columns: { NEW: BaristaTicket[]; PREPARING: BaristaTicket[]; READY: BaristaTicket[] };
  counts: Record<string, number>;
  generated_at: string;
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

export interface MenuCustomizePayload {
  menu_item: MenuItem | null;
  variants: {
    id: string;
    name: string;
    price_adjustment: number;
    is_default?: boolean;
    is_available?: boolean;
  }[];
  modifier_groups: {
    id: string;
    name: string;
    min_select: number;
    max_select: number;
    is_required?: boolean;
    modifiers: { id: string; name: string; price_delta: number }[];
  }[];
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
        items: { product_id: string; quantity: number; unit_price: number; name?: string; sku?: string }[];
        notes?: string;
      }>
    >(`/restaurant/orders/${id}/pos/`),

  cafeteriaProfile: (branchId: string) =>
    apiRequest<ApiResponse<CafeteriaProfile | null>>(
      `/restaurant/cafeteria-profile/${qs({ branch_id: branchId })}`
    ),
  saveCafeteriaProfile: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<CafeteriaProfile>>("/restaurant/cafeteria-profile/", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  baristaQueue: (branchId?: string, stationId?: string) =>
    apiRequest<ApiResponse<BaristaQueue>>(
      `/restaurant/barista/queue/${qs({ branch_id: branchId, station_id: stationId })}`
    ),
  baristaAction: (orderId: string, action: "accept" | "start" | "ready" | "complete") =>
    apiRequest<ApiResponse<BaristaTicket>>(
      `/restaurant/barista/tickets/${orderId}/${action}/`,
      { method: "POST", body: JSON.stringify({}) }
    ),
  wasteList: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<Record<string, unknown>>>(
      `/restaurant/waste/${qs({ page, branch_id: branchId })}`
    ),
  createWaste: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/restaurant/waste/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  approveWaste: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/waste/${id}/approve/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  itemVariants: (itemId: string) =>
    apiRequest<ApiResponse<Record<string, unknown>[]>>(
      `/restaurant/items/${itemId}/variants/`
    ),
  createVariant: (itemId: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/restaurant/items/${itemId}/variants/`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  activateRecipe: (id: string) =>
    apiRequest<ApiResponse<Recipe>>(`/restaurant/recipes/${id}/activate/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  recipeCosting: (id: string) =>
    apiRequest<ApiResponse<Recipe>>(`/restaurant/recipes/${id}/costing/`),

  itemCustomizeByProduct: (productId: string) =>
    apiRequest<ApiResponse<MenuCustomizePayload>>(
      `/restaurant/items/by-product/${productId}/customize/`
    ),

  updateOrderCharges: (
    id: string,
    data: { tip_amount?: number; service_charge_amount?: number }
  ) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  addOrderLine: (
    orderId: string,
    data: {
      menu_item_id: string;
      quantity?: number;
      variant_id?: string;
      modifiers?: { modifier_id: string; quantity?: number }[];
      unit_price?: number;
      notes?: string;
    }
  ) =>
    apiRequest<ApiResponse<RestaurantOrder>>(`/restaurant/orders/${orderId}/lines/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listPromotions: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<Record<string, unknown>>>(
      `/restaurant/promotions/${qs({ page, branch_id: branchId })}`
    ),
  createPromotion: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/restaurant/promotions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updatePromotion: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/promotions/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  archivePromotion: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/promotions/${id}/`, {
      method: "DELETE",
    }),
  resolvePromotion: (data: { code: string; branch_id?: string; amount?: number }) =>
    apiRequest<
      ApiResponse<{
        promotion: Record<string, unknown> | null;
        discount_amount: number;
      }>
    >("/restaurant/promotions/resolve/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listCombos: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<Record<string, unknown>>>(
      `/restaurant/combos/${qs({ page, branch_id: branchId })}`
    ),
  createCombo: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/restaurant/combos/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCombo: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/combos/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  archiveCombo: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/combos/${id}/`, {
      method: "DELETE",
    }),
  loyaltyProgram: (branchId?: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/restaurant/loyalty/program/${qs({ branch_id: branchId })}`
    ),
  updateLoyaltyProgram: (branchId: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/restaurant/loyalty/program/${qs({ branch_id: branchId })}`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),
  enrollLoyalty: (data: { program_id: string; customer_id: string }) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/restaurant/loyalty/enroll/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listReservations: (page = 1, branchId?: string, status?: string) =>
    apiRequest<ApiListResponse<Record<string, unknown>>>(
      `/restaurant/reservations/${qs({ page, branch_id: branchId, status })}`
    ),
  createReservation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/restaurant/reservations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateReservationStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/restaurant/reservations/${id}/status/`,
      { method: "POST", body: JSON.stringify({ status }) }
    ),
  listShifts: (page = 1, branchId?: string) =>
    apiRequest<ApiListResponse<Record<string, unknown>>>(
      `/restaurant/shifts/${qs({ page, branch_id: branchId })}`
    ),
  createShift: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/restaurant/shifts/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  shiftAction: (id: string, action: "open" | "close") =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/restaurant/shifts/${id}/${action}/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

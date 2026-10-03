export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiListResponse<T> {
  success: boolean;
  message: string;
  data: PaginatedResponse<T>;
}

export interface Category {
  id: string;
  name: string;
  parent_id: string | null;
  description: string;
  is_active: boolean;
}

export interface Brand {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
}

export interface Unit {
  id: string;
  name: string;
  abbreviation: string;
  is_active: boolean;
}

export interface ProductAttributeValue {
  definition_id: string;
  code: string;
  name: string;
  data_type: string;
  value: string | number | boolean | string[] | null;
  option_id?: string | null;
  is_pos_visible?: boolean;
}

export interface AttributeDefinition {
  id: string;
  code: string;
  name: string;
  description: string;
  data_type: string;
  is_required: boolean;
  is_searchable: boolean;
  is_filterable: boolean;
  is_pos_visible: boolean;
  is_reportable: boolean;
  is_active: boolean;
  sort_order: number;
  tenant_id: string | null;
  is_system: boolean;
  source?: string;
  options: { id: string; value: string; label: string; sort_order: number; is_active: boolean }[];
}

export interface Product {
  id: string;
  sku: string;
  barcode: string;
  name: string;
  category_id: string;
  category_name: string;
  brand_id: string | null;
  brand_name: string | null;
  unit_id: string;
  unit_name: string;
  cost_price: number;
  selling_price: number;
  minimum_stock: number;
  description: string;
  image: string;
  is_active: boolean;
  requires_prescription?: boolean;
  module_code?: string;
  total_stock?: number;
  warehouse_id?: string | null;
  warehouse_name?: string | null;
  attributes?: ProductAttributeValue[];
  created_at: string;
}

export interface Warehouse {
  id: string;
  name: string;
  code: string;
  branch_id: string;
  branch_name: string;
  address: string;
  is_active: boolean;
  is_default: boolean;
}

export interface InventoryItem {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  product_image?: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: number;
  reserved_quantity: number;
  damaged_quantity: number;
  returned_quantity: number;
  available_quantity: number;
  minimum_stock: number;
  is_low_stock: boolean;
  is_out_of_stock: boolean;
}

export interface InventorySummary {
  total_items: number;
  total_quantity: number;
  inventory_value: number;
  low_stock_count: number;
  out_of_stock_count: number;
}

export interface InventoryAdjustment {
  id: string;
  adjustment_number: string;
  warehouse_id: string;
  warehouse_name: string;
  branch_id: string;
  reason: string;
  status: string;
  items_count: number;
  created_at: string;
}

export interface ProductFormData {
  sku?: string;
  barcode?: string;
  name: string;
  category_id: string;
  brand_id?: string;
  unit_id?: string;
  cost_price: number;
  selling_price: number;
  minimum_stock: number;
  description?: string;
  image?: string;
  is_active?: boolean;
  requires_prescription?: boolean;
  module_code?: string;
  initial_stock?: number;
  stock?: number;
  warehouse_id?: string;
  attributes?: { definition_id?: string; code?: string; value: unknown }[] | Record<string, unknown>;
}

// --- Branch Phase 3: branch aggregation, cross-branch availability, ledger history ---

export interface BranchStockDashboard {
  branch_id: string;
  total_skus: number;
  inventory_value: number;
  low_stock_count: number;
  out_of_stock_count: number;
  reserved_quantity: number;
  recent_movements_count: number;
}

/** Quantities may arrive as decimal strings; render them with Number(). */
export interface WarehouseAvailability {
  warehouse_id: string;
  warehouse_name: string;
  on_hand: number | string;
  reserved: number | string;
  available: number | string;
}

export interface BranchAvailability {
  branch_id: string;
  branch_name: string;
  on_hand: number;
  reserved: number;
  available: number;
  in_transit: number;
  warehouses?: WarehouseAvailability[];
}

export interface OtherBranchAvailability {
  branch_id: string;
  branch_name: string;
  available: number;
  branch_code?: string;
  on_hand?: number;
  reserved?: number;
  in_transit?: number;
  /** null when the caller may not see that branch's warehouses. */
  warehouses?: WarehouseAvailability[] | null;
}

export interface OpenTransferSummary {
  id: string;
  request_number: string;
  status: string;
  source_branch_name: string;
  destination_branch_name: string;
  quantity_requested: number | string;
  direction: "incoming" | "outgoing";
}

export interface ProductAvailability {
  product_id: string;
  product_sku: string;
  product_name: string;
  current_branch: BranchAvailability;
  /** Empty when the caller lacks inventory.cross_branch_view — not an error. */
  other_branches: OtherBranchAvailability[];
  open_transfers?: OpenTransferSummary[];
}

export interface StockMovementRecord {
  id: string;
  movement_type: string;
  product_id: string;
  product_sku: string;
  warehouse_id: string;
  warehouse_name: string;
  branch_id: string | null;
  location_id: string | null;
  location_name: string | null;
  destination_warehouse_id: string | null;
  quantity: number;
  unit_cost: number | null;
  reference_type: string;
  reference_id: string | null;
  performed_by: string | null;
  notes: string;
  created_at: string;
}

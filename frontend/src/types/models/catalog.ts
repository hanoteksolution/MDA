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
  total_stock?: number;
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
  sku: string;
  barcode?: string;
  name: string;
  category_id: string;
  brand_id?: string;
  unit_id: string;
  cost_price: number;
  selling_price: number;
  minimum_stock: number;
  description?: string;
  image?: string;
  is_active?: boolean;
  initial_stock?: number;
  warehouse_id?: string;
}

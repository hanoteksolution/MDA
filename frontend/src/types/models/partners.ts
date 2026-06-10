import type { ApiListResponse, PaginatedResponse } from "@/types/models/catalog";

export type CustomerType = "retail" | "wholesale" | "corporate";
export type PurchaseOrderStatus = "draft" | "ordered" | "received" | "cancelled";

export interface Customer {
  id: string;
  customer_code: string;
  full_name: string;
  email: string;
  phone: string;
  address: string;
  customer_type: CustomerType;
  credit_limit: number;
  outstanding_balance: number;
  branch_id: string | null;
  branch_name: string | null;
  is_active: boolean;
  total_orders: number;
  created_at: string;
}

export interface Supplier {
  id: string;
  supplier_code: string;
  company_name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  payment_terms: number;
  outstanding_balance: number;
  is_active: boolean;
  total_orders: number;
  created_at: string;
}

export interface PurchaseOrderItem {
  id?: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  quantity_ordered: number;
  quantity_received?: number;
  unit_cost: number;
  line_total?: number;
}

export interface PurchaseOrder {
  id: string;
  order_number: string;
  supplier_id: string;
  supplier_name: string;
  branch_id: string;
  branch_name: string;
  status: PurchaseOrderStatus;
  order_date: string;
  expected_date: string | null;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  notes: string;
  ordered_by: string | null;
  item_count: number;
  items?: PurchaseOrderItem[];
  created_at: string;
}

export interface CustomerSummary {
  total: number;
  active: number;
  credit_outstanding: number;
}

export interface SupplierSummary {
  total: number;
  active: number;
  payables: number;
}

export interface PurchaseSummary {
  open_orders: number;
  pending_receipt: number;
  total_orders: number;
  month_total: number;
}

export type { ApiListResponse, PaginatedResponse };

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
  supplier_address?: string;
  supplier_phone?: string;
  supplier_email?: string;
  supplier_payment_terms?: number;
  branch_id: string;
  branch_name: string;
  branch_address?: string;
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

export interface CustomerReportPrintData {
  report_id: string;
  report_date: string;
  generated_by: string;
  branch: string | null;
  growth_year: number;
  kpis: {
    total: number;
    active: number;
    corporate: number;
    retail: number;
    wholesale: number;
    with_credit: number;
    outstanding: number;
    new_customers: number;
  };
  distribution: { label: string; count: number; pct: number }[];
  monthly_growth: { month: string; value: number }[];
  directory: {
    index: number;
    name: string;
    code: string;
    phone: string;
    email: string;
    type: string;
    credit_limit: number;
    balance: number;
    last_transaction: string;
    status: string;
    is_active: boolean;
  }[];
  financial_summary: {
    total_credit_limit: number;
    total_outstanding: number;
    avg_customer_value: number;
    highest_balance: number;
  };
  contact_summary: {
    with_email: number;
    with_phone: number;
    with_both: number;
    missing_info: number;
  };
  top_by_sales: { rank: number; name: string; amount: number; pct: number }[];
  top_by_profit: { rank: number; name: string; amount: number; pct: number }[];
  top_by_outstanding: { rank: number; name: string; amount: number; pct: number }[];
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

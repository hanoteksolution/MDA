import type { ApiResponse } from "@/types/models";
import type { ApiListResponse } from "@/types/models/catalog";
import type { PosReceipt } from "./pos";
import { apiRequest, qs } from "./http";

export type SaleDocStatus =
  | "draft"
  | "sent"
  | "paid"
  | "overdue"
  | "on_hold"
  | "cancelled"
  | "accepted"
  | "rejected"
  | "expired";

export interface SaleLineItem {
  id?: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  quantity: number;
  unit_price: number;
  line_total?: number;
}

export interface Invoice {
  id: string;
  number: string;
  customer_id: string;
  customer_name: string;
  branch_id: string;
  branch_name: string;
  status: SaleDocStatus;
  issue_date: string;
  due_date: string | null;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  balance_due?: number;
  is_paid?: boolean;
  payment_method?: string | null;
  waiter_name?: string;
  served_by_user_id?: string | null;
  notes: string;
  date: string;
  item_count: number;
  items?: SaleLineItem[];
  created_at: string;
}

export interface Quotation {
  id: string;
  number: string;
  customer_id: string;
  customer_name: string;
  branch_id: string;
  branch_name: string;
  status: SaleDocStatus;
  valid_until: string | null;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  notes: string;
  date: string;
  item_count: number;
  items?: SaleLineItem[];
  created_at: string;
}

export interface DeliveryNoteItem {
  name: string;
  sku?: string;
  quantity_ordered: number;
  quantity_delivered: number;
  unit: string;
}

export interface DeliveryNote {
  delivery_number: string;
  order_number: string;
  invoice_number: string;
  invoice_id: string;
  delivery_date: string;
  sales_person: string;
  vehicle_no: string;
  customer_name: string;
  customer_address: string;
  customer_phone: string;
  company: {
    name: string;
    phone: string;
    email: string;
    website: string;
    address: string;
  };
  branch: {
    name: string;
    code: string;
    address: string;
  };
  items: DeliveryNoteItem[];
}

export interface SalesSummary {
  today_sales: number;
  month_sales: number;
  open_invoices: number;
  quotations_count: number;
}

export interface DailyOpsProduct {
  product_id: string;
  name: string;
  sku: string;
  quantity: number;
  revenue: number;
}

export interface DailyOpsUnpaid {
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  customer_id: string;
  status: string;
  payment_method: string;
  waiter_name: string;
  total_amount: number;
  amount_paid: number;
  balance_due: number;
  items: { name: string; quantity: number; line_total: number }[];
}

export interface DailyExpense {
  id: string;
  description: string;
  category: string;
  amount: number;
  notes: string;
  expense_date: string;
  branch_id?: string;
  branch_name?: string;
  created_by?: string;
  created_at?: string;
}

export interface ExpenseListData {
  results: DailyExpense[];
  count: number;
  total_amount: number;
}

export type TrashKind = "invoice" | "quotation" | "expense" | "receipt";

export interface TrashItem {
  id: string;
  kind: TrashKind | string;
  number?: string;
  title?: string;
  customer_name?: string;
  category?: string;
  amount?: number;
  total_amount?: number;
  status?: string;
  date?: string;
  issue_date?: string;
  branch_name?: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
  notes?: string;
}

export interface DailyOpsData {
  date: string;
  summary: {
    invoices_count: number;
    paid_total: number;
    unpaid_count: number;
    unpaid_total: number;
    products_count: number;
    expense_total: number;
  };
  products_sold: DailyOpsProduct[];
  unpaid_receipts: DailyOpsUnpaid[];
  expenses: DailyExpense[];
  activity_dates?: string[];
}

export interface CustomerMonthlyAccount {
  customer_id: string;
  customer_name: string;
  year: number;
  month: number;
  period_label: string;
  summary: {
    receipts_count: number;
    total_amount: number;
    total_paid: number;
    total_due: number;
  };
  waiters: { name: string; amount_due: number }[];
  products: { name: string; sku: string; quantity: number; amount: number }[];
  receipts: {
    invoice_id: string;
    invoice_number: string;
    issue_date: string;
    status: string;
    payment_method: string;
    waiter_name: string;
    total_amount: number;
    amount_paid: number;
    balance_due: number;
    items: { name: string; sku: string; quantity: number; line_total: number }[];
  }[];
}

export const salesApi = {
  summary: () => apiRequest<ApiResponse<SalesSummary>>("/sales/summary/"),

  dailyOps: (date?: string) =>
    apiRequest<ApiResponse<DailyOpsData>>(
      `/sales/daily-ops/${date ? `?date=${encodeURIComponent(date)}` : ""}`
    ),

  customerMonthly: (params: { customer_id: string; year?: number; month?: number }) => {
    const q = new URLSearchParams({ customer_id: params.customer_id });
    if (params.year) q.set("year", String(params.year));
    if (params.month) q.set("month", String(params.month));
    return apiRequest<ApiResponse<CustomerMonthlyAccount>>(`/sales/customer-monthly/?${q}`);
  },

  expenses: (params: Record<string, string | undefined> = {}) =>
    apiRequest<ApiResponse<ExpenseListData>>(`/sales/expenses/${qs(params)}`),

  createExpense: (data: {
    description: string;
    amount: number;
    category?: string;
    expense_date?: string;
    notes?: string;
    branch_id?: string;
  }) =>
    apiRequest<ApiResponse<DailyExpense>>("/sales/expenses/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateExpense: (
    id: string,
    data: {
      description?: string;
      amount?: number;
      category?: string;
      expense_date?: string;
      notes?: string;
      branch_id?: string;
    }
  ) =>
    apiRequest<ApiResponse<DailyExpense>>(`/sales/expenses/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteExpense: (id: string) =>
    apiRequest<ApiResponse<null>>(`/sales/expenses/${id}/`, { method: "DELETE" }),

  trash: (params: Record<string, string | undefined> = {}) =>
    apiRequest<ApiResponse<TrashItem[]>>(`/sales/trash/${qs(params)}`),

  restoreTrash: (kind: string, id: string) =>
    apiRequest<ApiResponse<unknown>>(`/sales/trash/${kind}/${id}/restore/`, { method: "POST" }),

  purgeTrash: (kind: string, id: string) =>
    apiRequest<ApiResponse<null>>(`/sales/trash/${kind}/${id}/purge/`, { method: "DELETE" }),

  invoices: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Invoice>>(`/sales/invoices/${qs(params)}`),

  getInvoice: (id: string) => apiRequest<ApiResponse<Invoice>>(`/sales/invoices/${id}/`),

  getInvoiceReceipt: (id: string) =>
    apiRequest<ApiResponse<PosReceipt>>(`/sales/invoices/${id}/receipt/`),

  getInvoiceDeliveryNote: (id: string) =>
    apiRequest<ApiResponse<DeliveryNote>>(`/sales/invoices/${id}/delivery-note/`),

  createInvoice: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Invoice>>("/sales/invoices/", { method: "POST", body: JSON.stringify(data) }),

  updateInvoice: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Invoice>>(`/sales/invoices/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  deleteInvoice: (id: string) =>
    apiRequest<ApiResponse<null>>(`/sales/invoices/${id}/`, { method: "DELETE" }),

  markInvoicePaid: (id: string, data: { payment_method?: string } = {}) =>
    apiRequest<ApiResponse<Invoice>>(`/sales/invoices/${id}/mark-paid/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  markInvoiceUnpaid: (id: string) =>
    apiRequest<ApiResponse<Invoice>>(`/sales/invoices/${id}/mark-unpaid/`, { method: "POST" }),

  quotations: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Quotation>>(`/sales/quotations/${qs(params)}`),

  getQuotation: (id: string) => apiRequest<ApiResponse<Quotation>>(`/sales/quotations/${id}/`),

  createQuotation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Quotation>>("/sales/quotations/", { method: "POST", body: JSON.stringify(data) }),

  updateQuotation: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Quotation>>(`/sales/quotations/${id}/`, { method: "PUT", body: JSON.stringify(data) }),

  deleteQuotation: (id: string) =>
    apiRequest<ApiResponse<null>>(`/sales/quotations/${id}/`, { method: "DELETE" }),
};

export type { ApiListResponse };

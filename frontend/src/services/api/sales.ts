import type { ApiResponse } from "@/types/models";
import type { ApiListResponse } from "@/types/models/catalog";
import type { PosReceipt } from "./pos";
import { apiRequest, qs } from "./http";

export type SaleDocStatus = "draft" | "sent" | "paid" | "overdue" | "cancelled" | "accepted" | "rejected" | "expired";

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

export const salesApi = {
  summary: () => apiRequest<ApiResponse<SalesSummary>>("/sales/summary/"),

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

  quotations: (params: Record<string, string | number | undefined> = {}) =>
    apiRequest<ApiListResponse<Quotation>>(`/sales/quotations/${qs(params)}`),

  getQuotation: (id: string) => apiRequest<ApiResponse<Quotation>>(`/sales/quotations/${id}/`),

  createQuotation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Quotation>>("/sales/quotations/", { method: "POST", body: JSON.stringify(data) }),

  updateQuotation: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Quotation>>(`/sales/quotations/${id}/`, { method: "PUT", body: JSON.stringify(data) }),
};

export type { ApiListResponse };

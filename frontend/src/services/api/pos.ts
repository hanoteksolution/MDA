import type { ApiResponse } from "@/types/models";
import { apiRequest } from "./http";

export type PaymentMethod =
  | "cash"
  | "card"
  | "mobile"
  | "bank"
  | "split"
  | "on_account"
  | "charge_to_room";

export interface PosMerchant {
  id: string;
  label: string;
  company_name: string;
  merchant_number: string;
  provider: "cash" | "card" | "mobile" | "bank";
  is_default: boolean;
}

export interface PosWaiter {
  id: string;
  name: string;
  user_id?: string;
  is_active?: boolean;
}

export interface PosProfile {
  merchants: PosMerchant[];
  waiters?: PosWaiter[];
  default_payment_method: PaymentMethod;
  receipt_footer: string;
  return_policy?: string;
  code?: string;
  capabilities?: Record<string, boolean>;
  enabled_modules?: string[];
}

export interface PosReceiptItem {
  name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  image?: string;
}

export interface PosPaymentGuideEntry {
  label: string;
  number: string;
}

export interface PosReceipt {
  invoice_number: string;
  invoice_id: string;
  status?: string;
  is_paid?: boolean;
  date: string;
  time: string;
  datetime_display?: string;
  cashier: string;
  waiter?: string;
  terminal: string;
  customer_name: string;
  customer_address?: string;
  customer_phone?: string;
  customer_email?: string;
  company: {
    name: string;
    legal_name: string;
    tax_id: string;
    email?: string;
    phone: string;
    address: string;
    logo?: string;
  };
  branch: {
    name: string;
    code: string;
    phone: string;
    address: string;
  };
  merchant: PosMerchant | null;
  merchant_reference?: string;
  payment_reference?: string;
  payment_guide?: PosPaymentGuideEntry[];
  items: PosReceiptItem[];
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  tax_rate?: number;
  total_amount: number;
  payment_method: string;
  payment_method_label?: string;
  amount_tendered: number | null;
  change: number | null;
  footer: string;
  return_policy?: string;
  verification_path?: string;
  loyalty_points_earned?: number;
  loyalty_points_total?: number;
}

export interface PosCheckoutPayload {
  customer_id?: string;
  branch_id?: string;
  items: { product_id: string; quantity: number; unit_price: number }[];
  discount_pct: number;
  discount_amount?: number;
  tax_rate: number;
  payment_method: PaymentMethod;
  payments?: { method: PaymentMethod; amount: number; reference?: string }[];
  merchant_id?: string;
  amount_tendered?: number;
  payment_reference?: string;
  waiter_id?: string;
  waiter_name?: string;
  notes?: string;
  /** Resumed on-hold invoice — converts it in place, keeping the receipt number. */
  hold_invoice_id?: string;
  idempotency_key?: string;
  /** Explicit cashier shift; defaults to the current user's open session. */
  cashier_session_id?: string;
  /** Open restaurant floor ticket to mark paid after checkout. */
  restaurant_order_id?: string;
  /** Open hotel folio — posts F&B to guest room (charge-to-room). */
  hotel_folio_id?: string;
  hotel_reservation_id?: string;
  /** Active pharmacy prescription covering Rx-required cart lines. */
  prescription_id?: string;
}

export interface CashierSession {
  id: string;
  branch_id: string;
  cashier_id: string;
  cashier_name: string;
  opened_at: string;
  closed_at: string | null;
  opening_float: number;
  closing_cash_counted: number | null;
  expected_cash: number | null;
  cash_variance: number | null;
  total_sales: number;
  total_refunds: number;
  status: "open" | "closed";
  notes: string;
}

export interface SaleRefundItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface SaleRefund {
  id: string;
  refund_number: string;
  original_invoice_id: string;
  original_invoice_number: string;
  branch_id: string;
  cashier_session_id: string | null;
  reason: string;
  total_amount: number;
  processed_by_id: string | null;
  created_at: string;
  items?: SaleRefundItem[];
}

export interface PosRefundPayload {
  invoice_id: string;
  items: { product_id: string; quantity: number }[];
  reason?: string;
  cashier_session_id?: string;
}

export interface PosRefundResult {
  refund: SaleRefund;
  invoice: { id: string; number: string; amount_refunded: number; total_amount: number };
}

export interface PosCheckoutResult {
  invoice: { id: string; number: string; total_amount: number };
  receipt: PosReceipt;
}

export interface PosWaiterSaleItem {
  name: string;
  sku: string;
  quantity: number;
  line_total: number;
}

export interface PosWaiterSale {
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  status: string;
  payment_method: string;
  payment_method_label: string;
  total_amount: number;
  amount_paid: number;
  balance_due: number;
  issue_date: string;
  waiter_name: string;
  waiter_id?: string;
  items: PosWaiterSaleItem[];
}

export interface WaiterPerformanceRow {
  waiter_id: string;
  waiter_name: string;
  user_id?: string | null;
  receipts_count: number;
  paid_count: number;
  unpaid_count: number;
  on_account_count: number;
  total_served: number;
  paid_total: number;
  unpaid_total: number;
  items_sold: number;
}

export interface WaiterPerformanceData {
  date_from: string;
  date_to: string;
  summary: {
    waiters_count: number;
    receipts_count: number;
    paid_total: number;
    unpaid_total: number;
    on_account_count: number;
    total_served: number;
  };
  waiters: WaiterPerformanceRow[];
  receipts: PosWaiterSale[];
}

export const posApi = {
  profile: () => apiRequest<ApiResponse<PosProfile>>("/pos/profile/"),

  saveProfile: (data: PosProfile) =>
    apiRequest<ApiResponse<PosProfile>>("/pos/profile/", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  checkout: (data: PosCheckoutPayload) =>
    apiRequest<ApiResponse<PosCheckoutResult>>("/pos/checkout/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listHolds: (params: { branch_id?: string; search?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.branch_id) q.set("branch_id", params.branch_id);
    if (params.search) q.set("search", params.search);
    const qs = q.toString();
    return apiRequest<ApiResponse<import("./sales").Invoice[]>>(
      `/pos/holds/${qs ? `?${qs}` : ""}`
    );
  },

  createHold: (data: PosCheckoutPayload & { label?: string }) =>
    apiRequest<ApiResponse<import("./sales").Invoice>>("/pos/holds/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Allocate next sequential order/hold slip number (counts toward printed total). */
  allocateReceiptNumber: (data: { kind?: "order" | "hold" | "invoice"; branch_id?: string } = {}) =>
    apiRequest<
      ApiResponse<{
        number: string;
        serial: number;
        kind: string;
        total_issued: number;
        branch_id: string;
        branch_code: string;
      }>
    >("/pos/receipt-number/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Peek current issued count without allocating. */
  receiptNumberStats: (params: { kind?: "order" | "hold" | "invoice"; branch_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.kind) q.set("kind", params.kind);
    if (params.branch_id) q.set("branch_id", params.branch_id);
    const qs = q.toString();
    return apiRequest<
      ApiResponse<{
        kind: string;
        total_issued: number;
        next_serial: number;
        branch_id: string;
        branch_code: string;
      }>
    >(`/pos/receipt-number/${qs ? `?${qs}` : ""}`);
  },

  waiterSales: (params: {
    waiter_id?: string;
    user_id?: string;
    branch_id?: string;
    days?: number;
    date_from?: string;
    date_to?: string;
    waiter_name?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.waiter_id) q.set("waiter_id", params.waiter_id);
    if (params.user_id) q.set("user_id", params.user_id);
    if (params.branch_id) q.set("branch_id", params.branch_id);
    if (params.days) q.set("days", String(params.days));
    if (params.date_from) q.set("date_from", params.date_from);
    if (params.date_to) q.set("date_to", params.date_to);
    if (params.waiter_name) q.set("waiter_name", params.waiter_name);
    const qs = q.toString();
    return apiRequest<ApiResponse<PosWaiterSale[]>>(`/pos/waiter-sales/${qs ? `?${qs}` : ""}`);
  },

  waiterPerformance: (params: {
    branch_id?: string;
    date_from?: string;
    date_to?: string;
    waiter_id?: string;
    waiter_name?: string;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.branch_id) q.set("branch_id", params.branch_id);
    if (params.date_from) q.set("date_from", params.date_from);
    if (params.date_to) q.set("date_to", params.date_to);
    if (params.waiter_id) q.set("waiter_id", params.waiter_id);
    if (params.waiter_name) q.set("waiter_name", params.waiter_name);
    const qs = q.toString();
    return apiRequest<ApiResponse<WaiterPerformanceData>>(
      `/pos/waiter-performance/${qs ? `?${qs}` : ""}`
    );
  },

  listSessions: (params: { branch_id?: string; status?: "open" | "closed" } = {}) => {
    const q = new URLSearchParams();
    if (params.branch_id) q.set("branch_id", params.branch_id);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return apiRequest<ApiResponse<CashierSession[]>>(`/pos/sessions/${qs ? `?${qs}` : ""}`);
  },

  currentSession: (params: { branch_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.branch_id) q.set("branch_id", params.branch_id);
    const qs = q.toString();
    return apiRequest<ApiResponse<CashierSession | null>>(
      `/pos/sessions/current/${qs ? `?${qs}` : ""}`
    );
  },

  openSession: (data: { branch_id?: string; opening_float?: number; notes?: string } = {}) =>
    apiRequest<ApiResponse<CashierSession>>("/pos/sessions/open/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  closeSession: (data: {
    session_id: string;
    closing_cash_counted: number;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<CashierSession>>("/pos/sessions/close/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  refund: (data: PosRefundPayload) =>
    apiRequest<ApiResponse<PosRefundResult>>("/pos/refunds/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

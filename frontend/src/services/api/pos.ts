import type { ApiResponse } from "@/types/models";
import { apiRequest } from "./http";

export type PaymentMethod = "cash" | "card" | "mobile" | "bank" | "split";

export interface PosMerchant {
  id: string;
  label: string;
  company_name: string;
  merchant_number: string;
  provider: "cash" | "card" | "mobile" | "bank";
  is_default: boolean;
}

export interface PosProfile {
  merchants: PosMerchant[];
  default_payment_method: PaymentMethod;
  receipt_footer: string;
  return_policy?: string;
}

export interface PosReceiptItem {
  name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  image?: string;
}

export interface PosReceipt {
  invoice_number: string;
  invoice_id: string;
  date: string;
  time: string;
  datetime_display?: string;
  cashier: string;
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
  merchant_id?: string;
  amount_tendered?: number;
  payment_reference?: string;
  notes?: string;
}

export interface PosCheckoutResult {
  invoice: { id: string; number: string; total_amount: number };
  receipt: PosReceipt;
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
};

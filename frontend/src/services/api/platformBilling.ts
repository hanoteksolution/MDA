import type { ApiResponse } from "@/types/models";
import { platformCloudRequest } from "@/services/api/sync";

/** Platform Admin → Billing (`/api/v1/platform/billing/*`). Elevated users only; money values are decimal strings. */

export interface BillingPage<T> {
  count: number;
  page: number;
  page_size: number;
  results: T[];
}

export interface MoneyTotal {
  currency: string;
  amount: string;
}

export interface BillingOverview {
  tenants: { total: number; demo: number; without_subscription: number };
  subscriptions: {
    total: number;
    active: number;
    trial: number;
    expired: number;
    suspended: number;
    unassigned: number;
    expiring_soon: number;
    overdue: number;
  };
  payments: { pending: number; failed: number; review: number; confirmed: number };
  reconciliation_open: number;
  revenue: { verified: MoneyTotal[]; manual_unposted: MoneyTotal[]; note: string };
  can_recover: boolean;
}

export interface BillingSubscriptionRow {
  id: string;
  reference_code: string;
  tenant_id: string | null;
  tenant_name: string | null;
  tenant_slug: string | null;
  workspace: string | null;
  plan_code: string;
  plan_name: string;
  status: string;
  billing_status: string;
  monthly_fee: string | null;
  started_at: string | null;
  expires_at: string | null;
  next_billing_at: string | null;
  days_until_expiry: number | null;
  last_paid_at: string | null;
  last_payment_amount: string | null;
  last_payment_at: string | null;
  is_usable: boolean;
}

export interface BillingPaymentRow {
  id: string;
  payment_reference: string;
  subscription_id: string;
  reference_code: string;
  tenant_id: string | null;
  tenant_name: string | null;
  plan_name: string;
  kind: "checkout" | "manual";
  amount: string;
  currency: string | null;
  status: string;
  created_at: string;
  confirmed_at: string | null;
  auto_renewed: boolean;
  external_transaction_id: string;
  failure_reason: string;
  invoice_number: string | null;
  intent_status: string | null;
}

export interface BillingInvoiceRow {
  id: string;
  invoice_number: string;
  payment_id: string;
  payment_reference: string;
  tenant_id: string | null;
  tenant_name: string | null;
  plan_name: string;
  status: string;
  issue_date: string | null;
  due_date: string | null;
  total_amount: string;
  amount_paid: string;
  currency: string | null;
  payment_status: string;
}

export interface BillingReconciliationRow {
  id: string;
  kind: string;
  kind_label: string;
  status: string;
  tenant_id: string | null;
  tenant_name: string | null;
  payment_reference: string | null;
  provider_status: string;
  provider_amount: string | null;
  ledger_status: string;
  ledger_amount: string | null;
  detail: string;
  created_at: string;
  resolved_at: string | null;
  resolution_note: string;
}

export interface BillingPlanRow {
  id: string;
  code: string;
  name: string;
  monthly_price: string;
  max_users: number;
  max_branches: number;
  description: string;
  is_active: boolean;
  modules: string[];
  subscriptions: number;
}

export interface BillingTimelineEvent {
  at: string | null;
  event: string;
  label: string;
  amount?: string | null;
  by?: string | null;
}

export interface TenantBillingDetail {
  tenant: { id: string; name: string; slug: string; status: string; workspace: string | null; contact_email: string; is_demo: boolean };
  subscription: (BillingSubscriptionRow & { billing_period_days: number; grace_period_days: number; warning_days: number }) | null;
  plan: { code: string; name: string; monthly_price: string; max_users: number; max_branches: number } | null;
  timeline: BillingTimelineEvent[];
  invoices: BillingInvoiceRow[];
  payments: BillingPaymentRow[];
  renewal_history: { at: string | null; event: string; reason: string | null; by: string | null; expires_at: string | null }[];
  reconciliation: BillingReconciliationRow[];
  audit: { id: string; at: string | null; action: string; module: string; entity_type: string; user: string | null; event: string | null }[];
  can_recover: boolean;
}

export type BillingQuery = Record<string, string | number | undefined>;

function qs(params: BillingQuery = {}): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const platformBillingApi = {
  overview: () => platformCloudRequest<ApiResponse<BillingOverview>>("/platform/billing/overview/"),
  subscriptions: (params?: BillingQuery) =>
    platformCloudRequest<ApiResponse<BillingPage<BillingSubscriptionRow>>>(`/platform/billing/subscriptions/${qs(params)}`),
  payments: (params?: BillingQuery) =>
    platformCloudRequest<ApiResponse<BillingPage<BillingPaymentRow>>>(`/platform/billing/payments/${qs(params)}`),
  invoices: (params?: BillingQuery) =>
    platformCloudRequest<ApiResponse<BillingPage<BillingInvoiceRow>>>(`/platform/billing/invoices/${qs(params)}`),
  reconciliation: (params?: BillingQuery) =>
    platformCloudRequest<ApiResponse<BillingPage<BillingReconciliationRow>>>(`/platform/billing/reconciliation/${qs(params)}`),
  plans: () => platformCloudRequest<ApiResponse<BillingPlanRow[]>>("/platform/billing/plans/"),
  tenant: (tenantId: string) =>
    platformCloudRequest<ApiResponse<TenantBillingDetail>>(`/platform/billing/tenants/${tenantId}/`),
  /** Exceptional Super Admin recovery. Never records a payment. */
  recover: (subscriptionId: string, reason: string) =>
    platformCloudRequest<ApiResponse<BillingSubscriptionRow>>(`/platform/billing/subscriptions/${subscriptionId}/recover/`, {
      method: "POST",
      body: JSON.stringify({ reason, confirm: true }),
    }),
};

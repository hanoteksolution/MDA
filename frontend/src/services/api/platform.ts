import type { ApiResponse } from "@/types/models";
import { platformCloudRequest } from "@/services/api/sync";
import { apiRequest } from "./http";

export interface StaffEvaluation {
  id: string;
  staff_id: string;
  rating: number;
  notes: string;
  period: string;
  period_start: string;
  evaluator_id: string;
  evaluator_name: string;
  updated_at: string;
}

export interface StaffPerformanceRow {
  user_id: string;
  username: string;
  full_name: string;
  role: string;
  branch: string;
  tenant_id?: string;
  shop_name?: string;
  sales_count: number;
  total_sales: number;
  cash_collected: number;
  average_sale: number;
  login_sessions: number;
  evaluation?: StaffEvaluation | null;
}

export interface PlatformShopGroupRow {
  id: string;
  name: string;
  slug: string;
  contact_email: string;
  contact_phone: string;
  shop_count: number;
  tenant_count?: number;
  is_active: boolean;
  managers?: {
    id: string;
    username: string;
    full_name: string;
    email: string;
    role: string;
  }[];
  totals?: {
    shops: number;
    active_shops: number;
    total_sales: number;
    revenue: number;
    users: number;
  };
  shops?: PlatformTenantRow[];
  period?: string;
}

export interface PlatformShopProduct {
  id: string;
  name: string;
  sku: string;
  quantity: number;
  unit_price: number;
}

export interface PlatformShopSale {
  id: string;
  invoice_number: string;
  customer_name: string;
  status: string;
  total_amount: number;
  issue_date: string | null;
  cashier: string;
}

export interface PlatformShopOverview {
  tenant: {
    id: string;
    name: string;
    slug: string;
    is_active: boolean;
    contact_email: string;
    contact_phone?: string;
    shop_group_id?: string | null;
    shop_group_name?: string | null;
    last_synced_at?: string | null;
    sync_secret?: string;
  };
  subscription: PlatformTenantRow["subscription"];
  company?: { id: string; name: string } | null;
  branch?: { id: string; name: string; code: string } | null;
  kpis: {
    total_sales?: number;
    revenue?: number;
    cash_collected?: number;
    profit?: number;
    [key: string]: unknown;
  };
  staff_performance: StaffPerformanceRow[];
  catalog: {
    products_count: number;
    stock_units: number;
    stock_value: number;
    low_stock: number;
    products?: PlatformShopProduct[];
  };
  recent_sales?: PlatformShopSale[];
  users: {
    id: string;
    username: string;
    full_name: string;
    email?: string;
    role: string;
    is_active: boolean;
  }[];
  waiters?: { id: string; name: string; user_id?: string | null; is_active?: boolean }[];
}


export interface PlatformUserOption {
  id: string;
  username: string;
  full_name: string;
  email: string;
  role: string | null;
}

export interface PlatformPlanRow {
  code: string;
  name: string;
  monthly_price: number;
  max_users: number;
  max_branches: number;
  description?: string;
  is_active?: boolean;
}

export interface PlatformSubscriptionRow {
  id: string;
  reference_code: string;
  tenant_id: string | null;
  tenant_name: string | null;
  contact_user: PlatformUserOption | null;
  plan: string;
  plan_code: string;
  status: string;
  monthly_price: number;
  monthly_fee: number;
  custom_monthly_fee: number | null;
  started_at: string;
  expires_at: string | null;
  last_paid_at: string | null;
  billing_period_days: number;
  warning_days: number;
  grace_period_days: number;
  alert_title: string;
  alert_message_template: string;
  days_until_expiry: number | null;
  is_usable: boolean;
  is_payment_current: boolean;
  needs_payment_alert: boolean;
  notes: string;
}

export interface SubscriptionPaymentInfo {
  payment_id: string;
  payment_reference: string;
  payment_status: string;
  amount: number;
  merchant_number: string;
  company_name: string;
  provider_label: string;
  ussd_code: string;
  qr_payload: string;
  qr_image_url: string;
  instructions_title: string;
  instructions: string[];
  contact_phone: string;
  auto_renew_enabled: boolean;
  dialog_title_override?: string;
  dialog_message_override?: string;
}

export interface SubscriptionPaymentConfig {
  company_name: string;
  merchant_number: string;
  ussd_template: string;
  qr_image_url: string;
  qr_payload_template: string;
  provider_label: string;
  instructions_title: string;
  instructions: string[];
  contact_phone: string;
  dialog_title_override: string;
  dialog_message_override: string;
  auto_renew_enabled: boolean;
}

export interface SubscriptionPaymentRow {
  id: string;
  subscription_id: string;
  payment_reference: string;
  amount: number;
  merchant_number: string;
  payer_phone: string;
  external_transaction_id: string;
  status: string;
  period_key: string;
  confirmed_at: string | null;
  auto_renewed: boolean;
  notes: string;
  tenant_name: string | null;
  reference_code: string;
}

export interface SubscriptionAlert {
  subscription_id: string;
  reference_code: string;
  tenant_id: string | null;
  tenant_name: string | null;
  contact_user_id: string | null;
  contact_user_name: string | null;
  plan: string;
  plan_code: string;
  status: string;
  monthly_fee: number;
  expires_at: string | null;
  last_paid_at: string | null;
  days_until_expiry: number | null;
  warning_days: number;
  grace_period_days: number;
  grace_days_remaining: number | null;
  is_payment_current: boolean;
  severity: "warning" | "critical";
  title: string;
  message: string;
  alert_title?: string;
  alert_message_template?: string;
  payment?: SubscriptionPaymentInfo;
}

export interface PlatformTenantRow {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  contact_email: string;
  shop_group_id?: string | null;
  shop_group_name?: string | null;
  subscription: {
    id?: string;
    reference_code?: string;
    plan: string;
    status: string;
    monthly_price: number;
    monthly_fee?: number;
    expires_at: string | null;
    is_usable: boolean;
    needs_payment_alert?: boolean;
  } | null;
  kpis: {
    total_sales: number;
    revenue: number;
    cash_collected: number;
    profit: number;
  };
}

export const ALERT_TEMPLATE_PLACEHOLDERS =
  "{shop_name}, {plan}, {monthly_fee}, {days_left}, {grace_days}, {expires_at}, {reference}, {contact_user}, {status}, {last_paid_at}";

export const platformApi = {
  tenants: (period = "month") =>
    platformCloudRequest<ApiResponse<PlatformTenantRow[]>>(`/platform/tenants/?period=${period}`),

  tenant: (id: string, period = "month") =>
    platformCloudRequest<ApiResponse<Record<string, unknown>>>(`/platform/tenants/${id}/?period=${period}`),

  updateShop: (id: string, data: Record<string, unknown>) =>
    platformCloudRequest<ApiResponse<Record<string, unknown>>>(`/platform/tenants/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteShop: (id: string) =>
    platformCloudRequest<ApiResponse<null>>(`/platform/tenants/${id}/`, {
      method: "DELETE",
    }),

  tenantUsers: (tenantId: string) =>
    platformCloudRequest<ApiResponse<PlatformUserOption[]>>(`/platform/tenants/${tenantId}/users/`),

  createTenantUser: (
    tenantId: string,
    data: {
      username: string;
      password: string;
      email?: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      role_slug?: string;
    }
  ) =>
    platformCloudRequest<ApiResponse<PlatformUserOption>>(`/platform/tenants/${tenantId}/users/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  createShop: (data: Record<string, unknown>) =>
    platformCloudRequest<ApiResponse<Record<string, unknown>>>("/platform/tenants/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSubscription: (tenantId: string, data: Record<string, unknown>) =>
    platformCloudRequest<ApiResponse<Record<string, unknown>>>(`/platform/tenants/${tenantId}/subscription/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  plans: () =>
    platformCloudRequest<ApiResponse<PlatformPlanRow[]>>("/platform/plans/"),

  createPlan: (data: {
    name: string;
    code?: string;
    monthly_price: number;
    max_users?: number;
    max_branches?: number;
    description?: string;
  }) =>
    platformCloudRequest<ApiResponse<PlatformPlanRow>>("/platform/plans/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  subscriptions: (unassignedOnly = false) =>
    platformCloudRequest<ApiResponse<PlatformSubscriptionRow[]>>(
      `/platform/subscriptions/${unassignedOnly ? "?unassigned=1" : ""}`
    ),

  subscription: (id: string) =>
    platformCloudRequest<ApiResponse<PlatformSubscriptionRow>>(`/platform/subscriptions/${id}/`),

  createSubscription: (data: Record<string, unknown>) =>
    platformCloudRequest<ApiResponse<PlatformSubscriptionRow>>("/platform/subscriptions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSubscriptionRecord: (id: string, data: Record<string, unknown>) =>
    platformCloudRequest<ApiResponse<PlatformSubscriptionRow>>(`/platform/subscriptions/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteSubscription: (id: string) =>
    platformCloudRequest<ApiResponse<null>>(`/platform/subscriptions/${id}/`, {
      method: "DELETE",
    }),

  assignSubscription: (subscriptionId: string, tenantId: string) =>
    platformCloudRequest<ApiResponse<PlatformSubscriptionRow>>(`/platform/subscriptions/${subscriptionId}/assign/`, {
      method: "POST",
      body: JSON.stringify({ tenant_id: tenantId }),
    }),

  renewSubscription: (subscriptionId: string, notes = "") =>
    platformCloudRequest<ApiResponse<PlatformSubscriptionRow>>(`/platform/subscriptions/${subscriptionId}/renew/`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  subscriptionAlerts: () =>
    platformCloudRequest<ApiResponse<SubscriptionAlert[]>>("/platform/subscriptions/alerts/"),

  mySubscriptionAlert: () =>
    apiRequest<ApiResponse<SubscriptionAlert | null>>("/platform/subscriptions/my-alert/"),

  getSubscriptionPaymentConfig: () =>
    platformCloudRequest<ApiResponse<SubscriptionPaymentConfig>>(
      "/platform/subscriptions/payment-config/"
    ),

  saveSubscriptionPaymentConfig: (data: Partial<SubscriptionPaymentConfig>) =>
    platformCloudRequest<ApiResponse<SubscriptionPaymentConfig>>(
      "/platform/subscriptions/payment-config/",
      { method: "PUT", body: JSON.stringify(data) }
    ),

  uploadSubscriptionQr: async (file: File) => {
    const { ensureConnectionLoaded, getCloudApiBase } = await import("@/config/connection");
    const { hasCloudSession } = await import("./cloudHttp");
    const { isTauri } = await import("@/utils/platform");
    const { apiUpload } = await import("./http");

    if (isTauri()) {
      await ensureConnectionLoaded();
      const base = getCloudApiBase();
      if (base && hasCloudSession()) {
        const { getCloudAccessToken } = await import("./cloudHttp");
        const token = getCloudAccessToken();
        const formData = new FormData();
        formData.append("image", file);
        const res = await fetch(`${base.replace(/\/$/, "")}/platform/subscriptions/payment-config/upload-qr/`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.message || "QR upload failed");
        }
        return res.json() as Promise<
          ApiResponse<{ url: string; config: SubscriptionPaymentConfig }>
        >;
      }
    }
    return apiUpload<ApiResponse<{ url: string; config: SubscriptionPaymentConfig }>>(
      "/platform/subscriptions/payment-config/upload-qr/",
      file
    );
  },

  reportSubscriptionPayment: (
    subscriptionId: string,
    data: { payer_phone?: string; notes?: string } = {}
  ) =>
    platformCloudRequest<
      ApiResponse<{ payment: SubscriptionPaymentRow; alert: SubscriptionAlert }>
    >(`/platform/subscriptions/${subscriptionId}/report-payment/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  subscriptionPaymentStatus: (subscriptionId: string) =>
    platformCloudRequest<
      ApiResponse<{
        payment: SubscriptionPaymentRow | null;
        subscription: PlatformSubscriptionRow;
        alert: SubscriptionAlert | null;
      }>
    >(`/platform/subscriptions/${subscriptionId}/payment-status/`),

  pendingSubscriptionPayments: () =>
    platformCloudRequest<ApiResponse<SubscriptionPaymentRow[]>>(
      "/platform/subscriptions/pending-payments/"
    ),

  confirmSubscriptionPayment: (
    paymentId: string,
    data: { external_transaction_id?: string; payer_phone?: string; notes?: string } = {}
  ) =>
    platformCloudRequest<
      ApiResponse<{ payment: SubscriptionPaymentRow; subscription: PlatformSubscriptionRow }>
    >(`/platform/payments/${paymentId}/confirm/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  shopGroups: (params: { enrich?: boolean; period?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.enrich) q.set("enrich", "1");
    if (params.period) q.set("period", params.period);
    const qs = q.toString();
    return platformCloudRequest<ApiResponse<PlatformShopGroupRow[]>>(
      `/platform/shop-groups/${qs ? `?${qs}` : ""}`
    );
  },

  shopGroup: (id: string, period = "month") =>
    platformCloudRequest<ApiResponse<PlatformShopGroupRow>>(
      `/platform/shop-groups/${id}/?period=${period}`
    ),

  createShopGroup: (data: { name: string; contact_email?: string; contact_phone?: string }) =>
    platformCloudRequest<ApiResponse<PlatformShopGroupRow>>("/platform/shop-groups/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  tenantDetail: (id: string, period = "month") =>
    platformCloudRequest<ApiResponse<PlatformShopOverview>>(
      `/platform/tenants/${id}/?period=${period}`
    ),
};
export const staffPerformanceApi = {
  list: (params: {
    period?: string;
    branch_id?: string;
    tenant_id?: string;
    all_shops?: boolean;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.period) q.set("period", params.period);
    if (params.branch_id) q.set("branch_id", params.branch_id);
    if (params.tenant_id) q.set("tenant_id", params.tenant_id);
    if (params.all_shops) q.set("all_shops", "1");
    const qs = q.toString();
    return apiRequest<ApiResponse<StaffPerformanceRow[]>>(
      `/reports/staff-performance/${qs ? `?${qs}` : ""}`
    );
  },

  saveEvaluation: (
    userId: string,
    data: { period: string; rating: number; notes?: string }
  ) =>
    apiRequest<ApiResponse<StaffEvaluation>>(`/reports/staff-performance/${userId}/evaluation/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

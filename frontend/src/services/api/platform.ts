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
  is_active: boolean;
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

  tenantUsers: (tenantId: string) =>
    platformCloudRequest<ApiResponse<PlatformUserOption[]>>(`/platform/tenants/${tenantId}/users/`),

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

  shopGroups: () =>
    platformCloudRequest<ApiResponse<PlatformShopGroupRow[]>>("/platform/shop-groups/"),

  createShopGroup: (data: { name: string; contact_email?: string; contact_phone?: string }) =>
    platformCloudRequest<ApiResponse<PlatformShopGroupRow>>("/platform/shop-groups/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
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

import type { ApiResponse } from "@/types/models";
import { apiRequest } from "./http";

export interface SyncRunResult {
  status: string;
  synced_at: string;
  message?: string;
  mode?: string;
  pushed?: { invoices: number; customers: number; inventory: number; waiters?: number };
  pulled?: Record<string, number>;
  subscription?: SubscriptionStatus;
}

export interface SyncConfig {
  cloud_api_base: string;
  tenant_slug: string;
  sync_secret: string;
  device_id: string;
  last_sync_at: string;
  last_pull_at?: string;
  last_status: string;
  last_message: string;
  initial_pull_done?: boolean;
}

export interface SubscriptionStatusAlert {
  subscription_id: string;
  reference_code: string;
  tenant_id?: string | null;
  tenant_name?: string | null;
  plan: string;
  plan_code?: string;
  status: string;
  monthly_fee: number;
  expires_at: string | null;
  last_paid_at?: string | null;
  days_until_expiry: number | null;
  warning_days?: number;
  grace_period_days: number;
  grace_days_remaining: number | null;
  is_payment_current?: boolean;
  is_usable?: boolean;
  severity: "warning" | "critical";
  title: string;
  message: string;
  payment?: {
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
  };
}

export interface SubscriptionStatus {
  has_subscription: boolean;
  locked: boolean;
  show_alert: boolean;
  is_usable: boolean;
  alert: SubscriptionStatusAlert | null;
  evaluated_on: string;
  source: string;
  last_pull_at?: string;
}

export const syncApi = {
  config: () => apiRequest<ApiResponse<SyncConfig>>("/sync/config/"),

  saveConfig: (data: Partial<SyncConfig>) =>
    apiRequest<ApiResponse<SyncConfig>>("/sync/config/", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  run: () =>
    apiRequest<ApiResponse<SyncRunResult>>("/sync/run/", {
      method: "POST",
    }),

  subscriptionStatus: () =>
    apiRequest<ApiResponse<SubscriptionStatus>>("/sync/subscription-status/"),

  reportPayment: (data: { payer_phone?: string; notes?: string } = {}) =>
    apiRequest<
      ApiResponse<{
        payment: {
          id: string;
          status: string;
          payment_reference: string;
          auto_renewed?: boolean;
        };
        alert?: SubscriptionStatusAlert;
        is_payment_current?: boolean;
        subscription_usable?: boolean;
      }>
    >("/sync/report-payment/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  paymentStatus: () =>
    apiRequest<
      ApiResponse<{
        payment: {
          id: string;
          status: string;
          payment_reference: string;
          auto_renewed?: boolean;
        } | null;
        alert?: SubscriptionStatusAlert;
        is_payment_current?: boolean;
        subscription_usable?: boolean;
      }>
    >("/sync/payment-status/"),
};

/** Platform APIs: browser uses same-origin API; desktop uses cloud when configured. */
export async function platformCloudRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const { ensureConnectionLoaded, getCloudApiBase } = await import("@/config/connection");
  const { hasCloudSession, cloudApiRequest } = await import("./cloudHttp");
  const { isTauri } = await import("@/utils/platform");

  if (isTauri()) {
    await ensureConnectionLoaded();
    const base = getCloudApiBase();
    if (base) {
      if (hasCloudSession()) {
        return cloudApiRequest<T>(endpoint, options);
      }
      throw new Error(
        "Cloud admin sign-in required. Open Settings → Connection and click \"Sign in to cloud\"."
      );
    }
  }

  // Web browser on cloud server, or desktop local DB — use normal logged-in session
  return apiRequest<T>(endpoint, options);
}

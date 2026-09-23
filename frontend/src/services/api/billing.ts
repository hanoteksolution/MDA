import { apiRequest } from "@/services/api/http";

interface Envelope<T> {
  data: T;
  message?: string;
}

export type SubscriptionStatus = "trial" | "active" | "expired" | "suspended";
export type SubscriptionPaymentStatus = "pending" | "confirmed" | "failed" | "expired" | "review";

export interface CurrentSubscription {
  reference: string;
  plan_id: string;
  plan_name: string;
  status: SubscriptionStatus;
  started_at: string | null;
  expires_at: string | null;
  next_billing_date: string | null;
  days_until_expiry: number | null;
  grace_period_days: number;
  billing_period_days: number;
  is_usable: boolean;
  last_paid_at: string | null;
  monthly_fee: string;
  currency: string;
}

export interface BillingPlan {
  id: string;
  code: string;
  name: string;
  description: string;
  monthly_price: string;
  max_users: number;
  max_branches: number;
  is_current: boolean;
  action: "renew" | "change";
  available: boolean;
  reason: string;
}

export interface SubscriptionPaymentItem {
  id: string;
  reference: string;
  kind: "renew" | "new_plan" | "legacy";
  plan_id: string | null;
  plan_name: string | null;
  amount: string;
  currency: string;
  status: SubscriptionPaymentStatus;
  failure_reason: string;
  invoice_number: string | null;
  payment_reference: string;
  payment_expires_at: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface BillingOverview {
  subscription: CurrentSubscription | null;
  plans: BillingPlan[];
  payments: SubscriptionPaymentItem[];
  online_payment: boolean;
  billing_cycles?: string[];
}

/**
 * Tenant Billing & Subscription. Read-only plus "start checkout": the server activates or renews
 * only after the payment provider's verified confirmation — there is no client "mark paid" call.
 */
export const billingApi = {
  overview: () => apiRequest<Envelope<BillingOverview>>("/billing/subscription/"),
  checkout: (planId: string, idempotencyKey: string) =>
    apiRequest<Envelope<SubscriptionPaymentItem>>("/billing/subscription/checkout/", {
      method: "POST",
      body: JSON.stringify({ plan_id: planId, idempotency_key: idempotencyKey }),
    }),
  payment: (id: string) => apiRequest<Envelope<SubscriptionPaymentItem>>(`/billing/subscription/payments/${id}/`),
};

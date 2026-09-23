import { apiRequest } from "@/services/api/http";
import { platformCloudRequest } from "@/services/api/sync";

/**
 * Integrations API (SMS + payments). Mirrors `backend/api/v1/integrations/`.
 *
 * Nothing returned here contains a secret: credentials are only ever described by
 * `has_secret` + `masked_tail`. Secrets travel one way — up, in `credentials.create` /
 * `credentials.rotate` — and are never read back.
 */

interface Envelope<T> {
  data: T;
  message?: string;
}

export interface IntegrationCredential {
  id: string;
  label: string;
  has_secret: boolean;
  masked_tail: string;
  rotated_at: string | null;
}

export type SmsProviderType = "MOCK" | "CUSTOM_HTTP";
export type PaymentProviderType = "MOCK";

export interface SmsProvider {
  id: string;
  name: string;
  provider_type: SmsProviderType;
  branch_id: string | null;
  sender_id: string;
  credential_id: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  is_default: boolean;
}

export interface SmsProviderInput {
  name: string;
  provider_type: SmsProviderType;
  branch_id?: string | null;
  sender_id?: string;
  credential_id?: string | null;
  config?: Record<string, unknown>;
  is_active?: boolean;
  is_default?: boolean;
}

export interface SmsTemplate {
  id: string;
  code: string;
  name: string;
  body: string;
  is_active: boolean;
}

export type SmsLogStatus = "QUEUED" | "RETRYING" | "SENT" | "FAILED";

export interface SmsLog {
  id: string;
  branch_id: string | null;
  provider_id: string | null;
  to: string;
  sender_id: string;
  body: string;
  status: SmsLogStatus;
  provider_reference: string;
  attempts: number;
  next_retry_at: string | null;
  sent_at: string | null;
  error: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
}

export interface PaymentProvider {
  id: string;
  name: string;
  provider_type: PaymentProviderType;
  branch_id: string | null;
  credential_id: string | null;
  webhook_credential_id: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  webhook_path: string;
}

export interface PaymentProviderInput {
  name: string;
  provider_type: PaymentProviderType;
  branch_id?: string | null;
  credential_id?: string | null;
  webhook_credential_id?: string | null;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export type PaymentIntentStatus = "created" | "pending" | "succeeded" | "failed" | "expired";

export interface PaymentIntent {
  id: string;
  invoice_id: string;
  branch_id: string;
  provider_id: string;
  idempotency_key: string;
  amount: string;
  currency: string;
  method: string;
  status: PaymentIntentStatus;
  provider_reference: string;
  expires_at: string | null;
  failure_reason: string;
  payment_id: string | null;
  settled_at: string | null;
  created_at: string;
}

export type WebhookEventStatus =
  | "received"
  | "processed"
  | "ignored"
  | "rejected"
  | "invalid"
  | "error";

export interface PaymentWebhookEvent {
  id: string;
  provider_id: string;
  event_id: string;
  signature_valid: boolean;
  status: WebhookEventStatus;
  reason: string;
  intent_id: string | null;
  received_at: string;
  processed_at: string | null;
}

export type ReconciliationKind =
  | "status_mismatch"
  | "amount_mismatch"
  | "missing_payment"
  | "missing_journal"
  | "late_success"
  | "unapplied_payment";

export interface ReconciliationRecord {
  id: string;
  branch_id: string;
  provider_id: string;
  intent_id: string;
  kind: ReconciliationKind;
  status: "open" | "resolved";
  provider_status: string;
  provider_amount: string | null;
  ledger_status: string;
  ledger_amount: string | null;
  detail: string;
  resolved_at: string | null;
  resolution_note: string;
  created_at: string;
}

export interface ReconciliationSummary {
  checked: number;
  mismatches: number;
  [key: string]: unknown;
}


// ─── SMS reseller billing ─────────────────────────────────────────────────────

export interface SmsPackage {
  id: string;
  name: string;
  code: string;
  sms_quantity: number;
  price: string;
  currency: string;
  validity_days: number | null;
  description: string;
  is_active: boolean;
}

export type SmsPackageInput = Omit<SmsPackage, "id">;

export type SmsPurchaseStatus = "pending" | "credited" | "failed" | "expired" | "review";

export interface SmsPurchase {
  id: string;
  package_id: string;
  package_name: string;
  sms_quantity: number;
  price: string;
  currency: string;
  validity_days: number | null;
  status: SmsPurchaseStatus;
  payment_reference: string;
  failure_reason: string;
  credited_at: string | null;
  created_at: string;
}

export type SmsCreditKind = "purchase" | "adjust_credit" | "adjust_debit" | "reserve" | "release" | "expire";

export interface SmsCreditEntry {
  id: string;
  kind: SmsCreditKind;
  units: number;
  balance_after: number;
  purchase_id: string | null;
  sms_log_id: string | null;
  expires_at: string | null;
  reason: string;
  created_at: string;
}

export interface SmsBillingSummary {
  balance: number;
  reserved: number;
  used_30d: number;
  used_total: number;
  purchased_total: number;
  next_expiry: { units: number; expires_at: string }[];
  enforced: boolean;
  payments_available?: boolean;
}

export interface SmsTenantBalance {
  tenant_id: string;
  tenant_name: string;
  balance: number;
  purchased: number;
  used: number;
  pending_purchases: number;
  review_purchases: number;
}

const json = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
const patch = (body: unknown): RequestInit => ({ method: "PATCH", body: JSON.stringify(body) });

function query(params?: Record<string, string | undefined>): string {
  const q = Object.entries(params ?? {})
    .filter(([, v]) => v)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v as string)}`)
    .join("&");
  return q ? `?${q}` : "";
}

/** Tenant operations (Settings → Integrations). Provider configuration is not reachable from here. */
export const integrationsApi = {
  sms: {
    templates: () => apiRequest<Envelope<SmsTemplate[]>>("/integrations/sms-templates/"),
    createTemplate: (input: { code: string; name?: string; body: string }) =>
      apiRequest<Envelope<SmsTemplate>>("/integrations/sms-templates/", json(input)),
    logs: (params?: { status?: string }) =>
      apiRequest<Envelope<SmsLog[]>>(`/integrations/sms-logs/${query(params)}`),
    /** Queues a real message through the branch's active provider (there is no dry-run endpoint). */
    send: (input: { to: string; body?: string; template_code?: string; branch_id?: string; context?: Record<string, string> }) =>
      apiRequest<Envelope<SmsLog>>("/integrations/sms/send/", json(input)),
  },
  smsBilling: {
    packages: () => apiRequest<Envelope<SmsPackage[]>>("/integrations/sms-billing/packages/"),
    summary: () => apiRequest<Envelope<SmsBillingSummary>>("/integrations/sms-billing/summary/"),
    ledger: () => apiRequest<Envelope<SmsCreditEntry[]>>("/integrations/sms-billing/ledger/"),
    purchases: () => apiRequest<Envelope<SmsPurchase[]>>("/integrations/sms-billing/purchases/"),
    purchase: (id: string) => apiRequest<Envelope<SmsPurchase>>(`/integrations/sms-billing/purchases/${id}/`),
    /** Starts a payment. Credits arrive only after the provider's verified confirmation. */
    buy: (packageId: string, idempotencyKey: string) =>
      apiRequest<Envelope<SmsPurchase>>("/integrations/sms-billing/purchases/", json({ package_id: packageId, idempotency_key: idempotencyKey })),
  },
  payments: {
    intents: (params?: { status?: string; invoice_id?: string }) =>
      apiRequest<Envelope<PaymentIntent[]>>(`/integrations/payments/intents/${query(params)}`),
    intent: (id: string) =>
      apiRequest<Envelope<PaymentIntent>>(`/integrations/payments/intents/${id}/`),
  },
};

/**
 * Platform Admin → Integrations. Provider infrastructure for one tenant; the backend admits only
 * global platform administrators and requires the tenant to be named on every call.
 */
export function platformIntegrationsApi(tenantId: string) {
  // Same transport as the other Platform Admin screens (cloud API from the desktop shell).
  const base = "/platform/integrations";
  const t = (params?: Record<string, string | undefined>) => query({ tenant_id: tenantId, ...params });
  return {
    branches: () => platformCloudRequest<Envelope<{ id: string; name: string; code: string }[]>>(`${base}/branches/${t()}`),
    credentials: {
      list: () => platformCloudRequest<Envelope<IntegrationCredential[]>>(`${base}/credentials/${t()}`),
      create: (input: { label: string; secret: string }) =>
        platformCloudRequest<Envelope<IntegrationCredential>>(`${base}/credentials/${t()}`, json(input)),
      rotate: (id: string, input: { secret?: string; label?: string }) =>
        platformCloudRequest<Envelope<IntegrationCredential>>(`${base}/credentials/${id}/${t()}`, patch(input)),
    },
    sms: {
      providers: () => platformCloudRequest<Envelope<SmsProvider[]>>(`${base}/sms-providers/${t()}`),
      createProvider: (input: SmsProviderInput) =>
        platformCloudRequest<Envelope<SmsProvider>>(`${base}/sms-providers/${t()}`, json(input)),
      updateProvider: (id: string, input: Partial<SmsProviderInput>) =>
        platformCloudRequest<Envelope<SmsProvider>>(`${base}/sms-providers/${id}/${t()}`, patch(input)),
    },
    payments: {
      providers: () => platformCloudRequest<Envelope<PaymentProvider[]>>(`${base}/payment-providers/${t()}`),
      createProvider: (input: PaymentProviderInput) =>
        platformCloudRequest<Envelope<PaymentProvider>>(`${base}/payment-providers/${t()}`, json(input)),
      updateProvider: (id: string, input: Partial<PaymentProviderInput>) =>
        platformCloudRequest<Envelope<PaymentProvider>>(`${base}/payment-providers/${id}/${t()}`, patch(input)),
      webhookEvents: (params?: { status?: string }) =>
        platformCloudRequest<Envelope<PaymentWebhookEvent[]>>(`${base}/payments/webhook-events/${t(params)}`),
      reconciliation: (params?: { status?: string }) =>
        platformCloudRequest<Envelope<ReconciliationRecord[]>>(`${base}/payments/reconciliation/${t(params)}`),
      runReconciliation: (input?: { provider_id?: string }) =>
        platformCloudRequest<Envelope<ReconciliationSummary>>(`${base}/payments/reconcile/${t()}`, json(input ?? {})),
      resolveReconciliation: (id: string, note: string) =>
        platformCloudRequest<Envelope<ReconciliationRecord>>(`${base}/payments/reconciliation/${id}/resolve/${t()}`, json({ note })),
    },
  };
}

export type PlatformIntegrationsApi = ReturnType<typeof platformIntegrationsApi>;

/** Platform Admin → SMS billing: packages, billing provider, balances and audited adjustments. */
export const platformSmsBillingApi = {
  packages: () => platformCloudRequest<Envelope<SmsPackage[]>>("/platform/integrations/sms-billing/packages/"),
  createPackage: (input: Partial<SmsPackageInput>) =>
    platformCloudRequest<Envelope<SmsPackage>>("/platform/integrations/sms-billing/packages/", json(input)),
  updatePackage: (id: string, input: Partial<SmsPackageInput>) =>
    platformCloudRequest<Envelope<SmsPackage>>(`/platform/integrations/sms-billing/packages/${id}/`, patch(input)),
  settings: () =>
    platformCloudRequest<Envelope<{ payment_provider_id: string | null; payment_provider_name: string | null; payment_provider_tenant_id: string | null }>>(
      "/platform/integrations/sms-billing/settings/"
    ),
  saveSettings: (paymentProviderId: string | null) =>
    platformCloudRequest<Envelope<{ payment_provider_id: string | null; payment_provider_name: string | null }>>(
      "/platform/integrations/sms-billing/settings/", { method: "PUT", body: JSON.stringify({ payment_provider_id: paymentProviderId }) }
    ),
  balances: () => platformCloudRequest<Envelope<SmsTenantBalance[]>>("/platform/integrations/sms-billing/balances/"),
  ledger: (tenantId: string) =>
    platformCloudRequest<Envelope<{ summary: SmsBillingSummary; entries: SmsCreditEntry[]; purchases: SmsPurchase[] }>>(
      `/platform/integrations/sms-billing/ledger/${query({ tenant_id: tenantId })}`
    ),
  adjust: (tenantId: string, input: { units: number; reason: string; expires_at?: string }) =>
    platformCloudRequest<Envelope<SmsCreditEntry>>(`/platform/integrations/sms-billing/adjustments/${query({ tenant_id: tenantId })}`, json(input)),
};

/**
 * Pure logic for the Integrations screens — permissions, masking, form validation, status
 * presentation, filtering/pagination. No React, no network, so it is fully unit-testable.
 *
 * Validation here mirrors the backend (`api/v1/integrations/*`, `providers/custom_http.py`,
 * `services/sms_service.py`) to give early feedback. The backend stays authoritative.
 */
import type {
  IntegrationCredential,
  PaymentIntent,
  PaymentIntentStatus,
  PaymentProvider,
  PaymentProviderInput,
  ReconciliationKind,
  ReconciliationRecord,
  SmsLog,
  SmsLogStatus,
  SmsProvider,
  SmsProviderInput,
  SmsProviderType,
  WebhookEventStatus,
  SmsCreditKind,
  SmsPurchaseStatus,
} from "@/services/api/integrations";

// ─── permissions ────────────────────────────────────────────────────────────────

export interface IntegrationCaps {
  /** integrations.view — providers, templates, SMS logs, credential list. */
  view: boolean;
  /** integrations.manage — create/edit providers, templates, credentials. */
  manage: boolean;
  /** integrations.sms.send — test SMS. */
  sendSms: boolean;
  /** integrations.payments.view — intents, webhook events, reconciliation. */
  paymentsView: boolean;
  /** integrations.payments.reconcile — run reconciliation / resolve records. */
  reconcile: boolean;
  /** Anything at all in the section. */
  any: boolean;
  sms: boolean;
  payments: boolean;
  /** Provider infrastructure (credentials, providers, webhooks, reconciliation) — Platform Admin only. */
  providers: boolean;
  /** Tenant operations (templates, message logs, test SMS, payment intents) — tenant Settings only. */
  operations: boolean;
  /** integrations.sms.billing.view — SMS packages, balance, usage, purchase history. */
  billingView: boolean;
  /** integrations.sms.billing.purchase — buy SMS packages. */
  billingPurchase: boolean;
}

/** Tenant Settings → Integrations: operations only. Provider configuration is never exposed here. */
export function integrationCaps(has: (permission: string) => boolean): IntegrationCaps {
  const view = has("integrations.view");
  const manage = has("integrations.manage");
  const sendSms = has("integrations.sms.send");
  const paymentsView = has("integrations.payments.view");
  const billingView = has("integrations.sms.billing.view");
  return {
    view,
    manage,
    sendSms,
    paymentsView,
    reconcile: false,
    sms: view || sendSms || billingView,
    payments: paymentsView,
    any: view || sendSms || paymentsView || billingView,
    providers: false,
    operations: true,
    billingView,
    billingPurchase: billingView && has("integrations.sms.billing.purchase"),
  };
}

/** Platform Admin → Integrations. The backend admits only global platform administrators. */
export function platformIntegrationCaps(): IntegrationCaps {
  return {
    view: true,
    manage: true,
    sendSms: false,
    paymentsView: true,
    reconcile: true,
    sms: true,
    payments: true,
    any: true,
    providers: true,
    operations: false,
    billingView: false,
    billingPurchase: false,
  };
}

// ─── credentials: masked display only ───────────────────────────────────────────

/** What we may show about a stored secret. Never the value — the API does not return it. */
export function describeCredential(cred: IntegrationCredential | undefined | null): string {
  if (!cred) return "No credential linked";
  if (!cred.has_secret) return `${cred.label} · no secret stored`;
  return cred.masked_tail ? `${cred.label} · ${cred.masked_tail}` : `${cred.label} · secret stored`;
}

export function credentialLabelFor(
  credentials: IntegrationCredential[],
  id: string | null | undefined
): string {
  if (!id) return "No credential linked";
  return describeCredential(credentials.find((c) => c.id === id));
}

const SECRET_KEY =
  /^(authorization|proxy-authorization|key|sig|signature|bearer|x-api-key)$|secret|token|passw(or)?d|api[-_]?key|apikey|access[-_]?key|private[-_]?key/i;
const HAS_PLACEHOLDER = /\{\w+\}/;
export const REDACTED = "••••••";

export function isSecretLikeKey(key: string): boolean {
  return SECRET_KEY.test(key.trim());
}

/**
 * Secret-looking entries whose value is a literal instead of a `{placeholder}`.
 * Real credentials belong in the encrypted credential store and are referenced as `{secret}`.
 */
export function findLiteralSecrets(section: Record<string, unknown> | undefined | null): string[] {
  const out: string[] = [];
  for (const [key, value] of Object.entries(section ?? {})) {
    if (typeof value === "object" && value !== null) {
      out.push(...findLiteralSecrets(value as Record<string, unknown>));
    } else if (isSecretLikeKey(key) && String(value ?? "").trim() && !HAS_PLACEHOLDER.test(String(value))) {
      out.push(key);
    }
  }
  return out;
}

/** Copy of a config that is safe to render: literal secret-like values are replaced. */
export function redactConfig(config: Record<string, unknown> | undefined | null): Record<string, unknown> {
  const walk = (node: Record<string, unknown>): Record<string, unknown> => {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(node)) {
      if (typeof value === "object" && value !== null && !Array.isArray(value)) {
        out[key] = walk(value as Record<string, unknown>);
      } else if (isSecretLikeKey(key) && String(value ?? "").trim() && !HAS_PLACEHOLDER.test(String(value))) {
        out[key] = REDACTED;
      } else {
        out[key] = value;
      }
    }
    return out;
  };
  return walk(config ?? {});
}

// ─── key/value rows (headers, body mapping, metadata) ───────────────────────────

export interface KvRow {
  key: string;
  value: string;
}

export function recordToRows(record: unknown): KvRow[] {
  if (!record || typeof record !== "object" || Array.isArray(record)) return [];
  return Object.entries(record as Record<string, unknown>).map(([key, value]) => ({
    key,
    value: typeof value === "string" ? value : JSON.stringify(value),
  }));
}

export function rowsToRecord(rows: KvRow[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (key) out[key] = row.value;
  }
  return out;
}

export type FormErrors = Record<string, string>;

// ─── SMS provider form ──────────────────────────────────────────────────────────

export const SMS_PROVIDER_TYPES: { value: SmsProviderType; label: string; hint: string }[] = [
  { value: "CUSTOM_HTTP", label: "Custom HTTP gateway", hint: "Any provider with an HTTPS API — you supply the request template." },
  { value: "MOCK", label: "Mock (testing only)", hint: "Records messages locally; nothing is sent to a real network." },
];

export const MOCK_MODES = ["success", "timeout", "server_error", "malformed", "rejected"] as const;
export const PAYMENT_MOCK_MODES = ["success", "timeout", "server_error", "rejected"] as const;
export const SMS_PLACEHOLDERS = ["{to}", "{message}", "{sender}", "{secret}"] as const;

export interface SmsProviderForm {
  name: string;
  provider_type: SmsProviderType;
  branch_id: string;
  sender_id: string;
  credential_id: string;
  is_active: boolean;
  is_default: boolean;
  mock_mode: string;
  url: string;
  method: "POST" | "GET";
  body_format: "json" | "form";
  headers: KvRow[];
  body: KvRow[];
  success_statuses: string;
  reference_path: string;
  timeout_seconds: string;
}

export function emptySmsProviderForm(): SmsProviderForm {
  return {
    name: "",
    provider_type: "CUSTOM_HTTP",
    branch_id: "",
    sender_id: "",
    credential_id: "",
    is_active: true,
    is_default: false,
    mock_mode: "success",
    url: "",
    method: "POST",
    body_format: "json",
    headers: [{ key: "Authorization", value: "Bearer {secret}" }],
    body: [
      { key: "to", value: "{to}" },
      { key: "text", value: "{message}" },
      { key: "from", value: "{sender}" },
    ],
    success_statuses: "",
    reference_path: "",
    timeout_seconds: "10",
  };
}

export function smsFormFromProvider(p: SmsProvider): SmsProviderForm {
  const c = redactConfig(p.config); // a literal secret that slipped in is masked, then rejected on save
  return {
    ...emptySmsProviderForm(),
    name: p.name,
    provider_type: p.provider_type,
    branch_id: p.branch_id ?? "",
    sender_id: p.sender_id,
    credential_id: p.credential_id ?? "",
    is_active: p.is_active,
    is_default: p.is_default,
    mock_mode: String(c.mode ?? "success"),
    url: String(c.url ?? ""),
    method: String(c.method ?? "POST").toUpperCase() === "GET" ? "GET" : "POST",
    body_format: c.body_format === "form" ? "form" : "json",
    headers: recordToRows(c.headers),
    body: recordToRows(c.body),
    success_statuses: Array.isArray(c.success_statuses) ? c.success_statuses.join(", ") : "",
    reference_path: String(c.reference_path ?? ""),
    timeout_seconds: String(c.timeout_seconds ?? "10"),
  };
}

const PRIVATE_HOST =
  /^(localhost|.*\.local|.*\.internal|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|0\.0\.0\.0|\[?::1\]?$)/i;

export function parseStatusList(text: string): number[] | null {
  const parts = text.split(/[,\s]+/).filter(Boolean);
  const nums = parts.map(Number);
  if (nums.some((n) => !Number.isInteger(n) || n < 100 || n > 599)) return null;
  return nums;
}

export function validateSmsProviderForm(f: SmsProviderForm): FormErrors {
  const e: FormErrors = {};
  if (!f.name.trim()) e.name = "A name is required.";
  else if (f.name.trim().length > 120) e.name = "Name must be 120 characters or fewer.";
  if (f.sender_id.length > 32) e.sender_id = "Sender ID must be 32 characters or fewer.";
  if (f.provider_type === "MOCK") return e;

  let host = "";
  try {
    const u = new URL(f.url.trim());
    if (u.protocol !== "https:") e.url = "The URL must use https.";
    else host = u.hostname;
  } catch {
    e.url = "Enter a full https URL, e.g. https://gateway.example/send.";
  }
  if (!e.url && host && PRIVATE_HOST.test(host)) e.url = "The URL points to a private or internal address.";

  const timeout = Number(f.timeout_seconds);
  if (!Number.isFinite(timeout) || timeout < 1 || timeout > 30) {
    e.timeout_seconds = "Timeout must be between 1 and 30 seconds.";
  }
  if (f.success_statuses.trim() && !parseStatusList(f.success_statuses)) {
    e.success_statuses = "Use HTTP status codes separated by commas, e.g. 200, 201, 202.";
  }

  const headers = rowsToRecord(f.headers);
  const body = rowsToRecord(f.body);
  const bodyText = Object.values(body).join(" ");
  if (Object.keys(body).length === 0) e.body = "Map at least the recipient and message fields.";
  else if (!bodyText.includes("{to}") || !bodyText.includes("{message}")) {
    e.body = "The body must reference both {to} and {message}.";
  }

  const literal = [...findLiteralSecrets(headers), ...findLiteralSecrets(body)];
  if (literal.length) {
    e.headers = `Do not type secrets into the template (${literal.join(", ")}). Store them as a credential and use {secret}.`;
  }
  const usesSecret = [...Object.values(headers), ...Object.values(body)].some((v) => v.includes("{secret}"));
  if (usesSecret && !f.credential_id) e.credential_id = "The template uses {secret}: choose or create a credential.";
  return e;
}

export function buildSmsProviderInput(f: SmsProviderForm): SmsProviderInput {
  const base: SmsProviderInput = {
    name: f.name.trim(),
    provider_type: f.provider_type,
    branch_id: f.branch_id || null,
    sender_id: f.sender_id.trim(),
    credential_id: f.credential_id || null,
    is_active: f.is_active,
    is_default: f.is_default,
  };
  if (f.provider_type === "MOCK") return { ...base, config: { mode: f.mock_mode } };
  const config: Record<string, unknown> = {
    url: f.url.trim(),
    method: f.method,
    body_format: f.body_format,
    headers: rowsToRecord(f.headers),
    body: rowsToRecord(f.body),
    timeout_seconds: Number(f.timeout_seconds),
  };
  const statuses = f.success_statuses.trim() ? parseStatusList(f.success_statuses) : null;
  if (statuses?.length) config.success_statuses = statuses;
  if (f.reference_path.trim()) config.reference_path = f.reference_path.trim();
  return { ...base, config };
}

// ─── payment provider form ──────────────────────────────────────────────────────

export const PAYMENT_PROVIDER_TYPES: { value: "MOCK"; label: string; hint: string }[] = [
  { value: "MOCK", label: "Mock (testing only)", hint: "Deterministic test gateway. Real provider types appear here once their adapters ship." },
];

export interface PaymentProviderForm {
  name: string;
  provider_type: "MOCK";
  branch_id: string;
  credential_id: string;
  webhook_credential_id: string;
  is_active: boolean;
  mock_mode: string;
  metadata: KvRow[];
}

export function emptyPaymentProviderForm(): PaymentProviderForm {
  return {
    name: "",
    provider_type: "MOCK",
    branch_id: "",
    credential_id: "",
    webhook_credential_id: "",
    is_active: true,
    mock_mode: "success",
    metadata: [],
  };
}

export function paymentFormFromProvider(p: PaymentProvider): PaymentProviderForm {
  const { mode, ...rest } = redactConfig(p.config);
  return {
    ...emptyPaymentProviderForm(),
    name: p.name,
    provider_type: p.provider_type,
    branch_id: p.branch_id ?? "",
    credential_id: p.credential_id ?? "",
    webhook_credential_id: p.webhook_credential_id ?? "",
    is_active: p.is_active,
    mock_mode: String(mode ?? "success"),
    metadata: recordToRows(rest),
  };
}

export function validatePaymentProviderForm(f: PaymentProviderForm): FormErrors {
  const e: FormErrors = {};
  if (!f.name.trim()) e.name = "A name is required.";
  else if (f.name.trim().length > 120) e.name = "Name must be 120 characters or fewer.";
  const meta = rowsToRecord(f.metadata);
  const secretKeys = Object.keys(meta).filter((k) => isSecretLikeKey(k));
  if (secretKeys.length) {
    e.metadata = `Metadata is not encrypted — remove ${secretKeys.join(", ")} and store it as a credential instead.`;
  }
  if (f.credential_id && f.credential_id === f.webhook_credential_id) {
    e.webhook_credential_id = "Use a different secret for webhook signing than for API access.";
  }
  return e;
}

export function buildPaymentProviderInput(f: PaymentProviderForm): PaymentProviderInput {
  return {
    name: f.name.trim(),
    provider_type: f.provider_type,
    branch_id: f.branch_id || null,
    credential_id: f.credential_id || null,
    webhook_credential_id: f.webhook_credential_id || null,
    is_active: f.is_active,
    config: { ...rowsToRecord(f.metadata), mode: f.mock_mode },
  };
}

// ─── templates, credentials, test SMS ───────────────────────────────────────────

export interface TemplateForm {
  code: string;
  name: string;
  body: string;
}

const PLACEHOLDER = /\{(\w+)\}/g;
export const extractPlaceholders = (body: string): string[] =>
  Array.from(new Set(Array.from(body.matchAll(PLACEHOLDER), (m) => m[1])));

export function validateTemplateForm(f: TemplateForm): FormErrors {
  const e: FormErrors = {};
  if (!f.code.trim()) e.code = "A code is required.";
  else if (!/^[A-Za-z0-9_.-]{1,60}$/.test(f.code.trim())) {
    e.code = "Use letters, digits, dot, dash or underscore (max 60).";
  }
  if (f.name.trim().length > 120) e.name = "Name must be 120 characters or fewer.";
  if (!f.body.trim()) e.body = "The message body is required.";
  return e;
}

export function validateCredentialForm(f: { label: string; secret: string }): FormErrors {
  const e: FormErrors = {};
  if (!f.label.trim()) e.label = "A label is required.";
  if (!f.secret.trim()) e.secret = "A secret value is required.";
  return e;
}

/** Same normalisation and pattern as `SmsService._create_log`. */
export const normalizePhone = (raw: string): string => raw.replace(/[\s\-()]/g, "");
export const isValidPhone = (raw: string): boolean => /^\+?\d{6,15}$/.test(normalizePhone(raw));

export function validateTestSms(f: { to: string; body: string }): FormErrors {
  const e: FormErrors = {};
  if (!isValidPhone(f.to)) e.to = "Enter a number with 6–15 digits, optionally starting with +.";
  if (!f.body.trim()) e.body = "Enter a test message.";
  return e;
}

// ─── status presentation ────────────────────────────────────────────────────────

export type BadgeVariant = "default" | "secondary" | "success" | "warning" | "destructive" | "outline";
export interface StatusView {
  label: string;
  variant: BadgeVariant;
}

const SMS_STATUS: Record<SmsLogStatus, StatusView> = {
  QUEUED: { label: "Queued", variant: "secondary" },
  RETRYING: { label: "Retrying", variant: "warning" },
  SENT: { label: "Sent", variant: "success" },
  FAILED: { label: "Failed", variant: "destructive" },
};
const INTENT_STATUS: Record<PaymentIntentStatus, StatusView> = {
  created: { label: "Created", variant: "secondary" },
  pending: { label: "Pending", variant: "warning" },
  succeeded: { label: "Succeeded", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  expired: { label: "Expired", variant: "outline" },
};
const WEBHOOK_STATUS: Record<WebhookEventStatus, StatusView> = {
  received: { label: "Received", variant: "warning" },
  processed: { label: "Processed", variant: "success" },
  ignored: { label: "Ignored", variant: "secondary" },
  rejected: { label: "Rejected", variant: "destructive" },
  invalid: { label: "Invalid", variant: "destructive" },
  error: { label: "Error", variant: "destructive" },
};
const RECON_KIND: Record<ReconciliationKind, string> = {
  status_mismatch: "Status mismatch",
  amount_mismatch: "Amount mismatch",
  missing_payment: "Succeeded without a payment",
  missing_journal: "Payment without a journal entry",
  late_success: "Success after expiry/failure",
  unapplied_payment: "Money taken but not applied",
};

const fallback = (raw: string): StatusView => ({ label: raw || "Unknown", variant: "outline" });
export const smsStatusView = (s: string): StatusView => SMS_STATUS[s as SmsLogStatus] ?? fallback(s);
/** Rendered verbatim from the backend's `status` — the browser never derives or upgrades it. */
export const intentStatusView = (s: string): StatusView => INTENT_STATUS[s as PaymentIntentStatus] ?? fallback(s);
export const webhookStatusView = (s: string): StatusView => WEBHOOK_STATUS[s as WebhookEventStatus] ?? fallback(s);
export const reconciliationKindLabel = (k: string): string => RECON_KIND[k as ReconciliationKind] ?? k;
export const activeView = (active: boolean): StatusView =>
  active ? { label: "Enabled", variant: "success" } : { label: "Disabled", variant: "secondary" };

/** Transactions = intents the backend has settled into a payment. There is no separate endpoint. */
export const settledTransactions = (intents: PaymentIntent[]): PaymentIntent[] =>
  intents.filter((i) => i.status === "succeeded" && Boolean(i.payment_id));

export const formatMoney = (amount: string, currency: string): string => {
  const n = Number(amount);
  if (!Number.isFinite(n)) return `${amount} ${currency}`.trim();
  return `${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ${currency}`.trim();
};

export const shortId = (id: string | null | undefined): string => (id ? id.slice(0, 8) : "—");

// ─── client-side search / pagination ────────────────────────────────────────────

export function searchRows<T>(rows: T[], query: string, pick: (row: T) => (string | null | undefined)[]): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return rows;
  return rows.filter((r) => pick(r).some((v) => (v ?? "").toLowerCase().includes(q)));
}

export interface Page<T> {
  rows: T[];
  page: number;
  pageCount: number;
  total: number;
}

export function paginate<T>(rows: T[], page: number, size: number): Page<T> {
  const pageCount = Math.max(1, Math.ceil(rows.length / size));
  const safe = Math.min(Math.max(1, page), pageCount);
  return { rows: rows.slice((safe - 1) * size, safe * size), page: safe, pageCount, total: rows.length };
}

/** The API caps lists at 200 rows; tell the user when they may be looking at a truncated set. */
export const API_LIST_CAP = 200;
export const maybeTruncated = (count: number): boolean => count >= API_LIST_CAP;

// ─── overview ───────────────────────────────────────────────────────────────────

export interface OverviewSummary {
  smsProviders: number;
  smsActive: number;
  smsDefaultSet: boolean;
  smsFailed: number;
  smsRetrying: number;
  paymentProviders: number;
  paymentsActive: number;
  intentsPending: number;
  webhookProblems: number;
  openReconciliation: number;
}

export function summarize(input: {
  smsProviders: SmsProvider[];
  smsLogs: SmsLog[];
  paymentProviders: PaymentProvider[];
  intents: PaymentIntent[];
  events: { status: string }[];
  records: ReconciliationRecord[];
}): OverviewSummary {
  return {
    smsProviders: input.smsProviders.length,
    smsActive: input.smsProviders.filter((p) => p.is_active).length,
    smsDefaultSet: input.smsProviders.some((p) => p.is_default && p.is_active),
    smsFailed: input.smsLogs.filter((l) => l.status === "FAILED").length,
    smsRetrying: input.smsLogs.filter((l) => l.status === "RETRYING").length,
    paymentProviders: input.paymentProviders.length,
    paymentsActive: input.paymentProviders.filter((p) => p.is_active).length,
    intentsPending: input.intents.filter((i) => i.status === "pending" || i.status === "created").length,
    webhookProblems: input.events.filter((e) => ["rejected", "invalid", "error"].includes(e.status)).length,
    openReconciliation: input.records.filter((r) => r.status === "open").length,
  };
}

export function describeApiError(err: unknown, fallbackMessage = "Something went wrong."): string {
  if (err instanceof Error && err.message) return err.message;
  return fallbackMessage;
}

// ─── SMS reseller billing ───────────────────────────────────────────────────────

const PURCHASE_STATUS: Record<SmsPurchaseStatus, StatusView> = {
  pending: { label: "Awaiting payment", variant: "warning" },
  credited: { label: "Credited", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  expired: { label: "Expired", variant: "secondary" },
  review: { label: "Under review", variant: "warning" },
};

export function purchaseStatusView(status: SmsPurchaseStatus): StatusView {
  return PURCHASE_STATUS[status] ?? { label: status, variant: "outline" };
}

const CREDIT_KIND: Record<SmsCreditKind, string> = {
  purchase: "Package credited",
  adjust_credit: "Manual credit",
  adjust_debit: "Manual debit",
  reserve: "SMS sent",
  release: "SMS not delivered (returned)",
  expire: "Credits expired",
};

export const creditKindLabel = (kind: SmsCreditKind): string => CREDIT_KIND[kind] ?? kind;

export function formatPrice(price: string, currency: string): string {
  const n = Number(price);
  return Number.isFinite(n) ? `${currency} ${n.toFixed(2)}` : `${currency} ${price}`;
}

export const validityLabel = (days: number | null): string => (days ? `Valid ${days} day${days === 1 ? "" : "s"}` : "No expiry");

/** Platform package form → payload, with the backend's rules checked first. */
export function validatePackageForm(input: { name: string; code: string; sms_quantity: string; price: string; validity_days: string }): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!input.name.trim()) errors.name = "Name is required.";
  if (!input.code.trim()) errors.code = "Code is required.";
  if (!/^\d+$/.test(input.sms_quantity) || Number(input.sms_quantity) <= 0) errors.sms_quantity = "Enter a whole number above zero.";
  if (input.price.trim() === "" || !Number.isFinite(Number(input.price)) || Number(input.price) < 0) errors.price = "Enter a price of zero or more.";
  if (input.validity_days.trim() && (!/^\d+$/.test(input.validity_days) || Number(input.validity_days) <= 0)) errors.validity_days = "Days must be a positive whole number, or empty.";
  return errors;
}

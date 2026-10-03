import type { ApiResponse, AuthTokens, User } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface OnboardingBusinessType {
  id: string;
  code: string;
  name: string;
  description: string;
  default_modules: string[];
  is_active: boolean;
  sort_order: number;
}

export interface OnboardingPlan {
  code: string;
  name: string;
  monthly_price: number;
  max_users: number;
  max_branches: number;
  description: string;
  is_active: boolean;
  modules: string[];
}

export interface OnboardingCatalog {
  business_types: OnboardingBusinessType[];
  plans: OnboardingPlan[];
  modules: OnboardingModule[];
  base_domain: string;
  steps?: string[];
}

export interface OnboardingModule {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  dependencies: string[];
  is_core: boolean;
  supports_mobile: boolean;
  supports_pos: boolean;
  supports_inventory: boolean;
  supports_finance: boolean;
}

export interface SlugCheckResult {
  requested?: string;
  normalized?: string | null;
  slug?: string;
  available: boolean;
  reason: string | null;
  hostname: string | null;
  suggestions?: string[];
}

export interface OnboardingProvisionPayload {
  name: string;
  slug: string;
  business_type_code: string;
  plan_code: string;
  contact_email?: string;
  contact_phone?: string;
  country?: string;
  currency?: string;
  branch_name?: string;
  modules?: string[];
  owner: {
    username: string;
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
  };
}

export interface OnboardingProvisionResult extends Partial<AuthTokens> {
  tenant: Record<string, unknown>;
  subscription?: Record<string, unknown> | null;
  owner: Record<string, unknown>;
  branch: { id: string; name: string; code: string } | null;
  hostname: string;
  idempotent_replay?: boolean;
  user?: User;
}

export interface RegistrationResult {
  id: string;
  status: "pending_email" | "verified" | "provisioning" | "ready" | "failed_retryable" | "failed_final";
  subdomain: string;
  hostname: string;
  workspace_url: string;
  tls_ready?: boolean;
  tenant_id: string | null;
  message: string;
  failure_category?: string;
  stages?: { stage: string; status: string; message?: string }[];
}

export const onboardingApi = {
  catalog: () => apiRequest<ApiResponse<OnboardingCatalog>>("/public/catalog/"),

  checkSlug: (slug: string) =>
    apiRequest<ApiResponse<SlugCheckResult>>(
      `/public/workspaces/subdomain-availability/${qs({ subdomain: slug })}`
    ),

  provision: (data: OnboardingProvisionPayload) =>
    apiRequest<ApiResponse<OnboardingProvisionResult>>("/onboarding/provision/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  registrationStatus: (id: string) =>
    apiRequest<ApiResponse<RegistrationResult>>(`/public/registrations/${id}/status/`),

  register: (data: OnboardingProvisionPayload & { agreements: { terms_accepted: boolean; privacy_accepted: boolean } }, idempotencyKey: string) =>
    apiRequest<ApiResponse<RegistrationResult>>("/public/registrations/", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        subdomain: data.slug,
        business_type_code: data.business_type_code,
        plan_code: data.plan_code,
        modules: data.modules,
        company: {
          trading_name: data.name,
          contact_email: data.contact_email,
          contact_phone: data.contact_phone,
          country: data.country,
          currency: data.currency,
          branch_name: data.branch_name,
        },
        owner: data.owner,
        agreements: data.agreements,
      }),
    }),
};

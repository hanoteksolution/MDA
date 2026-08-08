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
  base_domain: string;
  steps: string[];
}

export interface SlugCheckResult {
  slug: string;
  available: boolean;
  reason: string;
  hostname: string | null;
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

export const onboardingApi = {
  catalog: () => apiRequest<ApiResponse<OnboardingCatalog>>("/onboarding/catalog/"),

  checkSlug: (slug: string) =>
    apiRequest<ApiResponse<SlugCheckResult>>(`/onboarding/slug-check/${qs({ slug })}`),

  provision: (data: OnboardingProvisionPayload) =>
    apiRequest<ApiResponse<OnboardingProvisionResult>>("/onboarding/provision/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

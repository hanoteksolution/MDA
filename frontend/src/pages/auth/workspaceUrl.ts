/** Frontend helpers for workspace URL UX. Backend remains authoritative. */

export const WORKSPACE_SLUG_MAX = 63;
export const WORKSPACE_SLUG_MIN = 2;
export const WORKSPACE_CHECK_DEBOUNCE_MS = 400;

export type WorkspaceUrlReason = "taken" | "reserved" | "invalid" | null;

export type WorkspaceUrlUiState =
  | "empty"
  | "checking"
  | "available"
  | "taken"
  | "reserved"
  | "invalid"
  | "error";

export type WorkspaceAvailability = {
  requested?: string;
  normalized: string | null;
  available: boolean;
  hostname: string | null;
  reason: WorkspaceUrlReason | string | null;
  suggestions: string[];
  slug?: string;
};

export function suggestFromCompanyName(name: string): string {
  return normalizeWorkspaceSlug(name);
}

export function normalizeWorkspaceSlug(value: string): string {
  // Mirrors the backend's normalize_tenant_slug: never trims a leading/trailing
  // hyphen, so a boundary hyphen surfaces as "invalid" instead of a silently
  // rewritten preview that then disagrees with the authoritative check.
  return value
    .toLowerCase()
    .trim()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .slice(0, WORKSPACE_SLUG_MAX);
}

export function workspaceHostname(slug: string, baseDomain: string): string {
  const normalized = normalizeWorkspaceSlug(slug);
  if (!normalized) return "";
  return `${normalized}.${baseDomain.replace(/^\./, "")}`;
}

export function workspaceHttpsUrl(slug: string, baseDomain: string): string {
  const host = workspaceHostname(slug, baseDomain);
  return host ? `https://${host}` : "";
}

export function deriveWorkspaceUiState(opts: {
  slug: string;
  checking: boolean;
  status: WorkspaceAvailability | null;
  networkError: boolean;
}): WorkspaceUrlUiState {
  if (!opts.slug) return "empty";
  if (opts.checking) return "checking";
  if (opts.networkError) return "error";
  if (!opts.status) return "empty";
  if (opts.status.available) return "available";
  const reason = opts.status.reason;
  if (reason === "taken") return "taken";
  if (reason === "reserved") return "reserved";
  if (reason === "invalid") return "invalid";
  return "invalid";
}

export function canContinueWorkspaceUrl(state: WorkspaceUrlUiState): boolean {
  return state === "available";
}

export function conflictSuggestions(details: Record<string, unknown> | undefined): string[] {
  const raw = details?.suggestions;
  if (!Array.isArray(raw)) return [];
  return raw.filter((item): item is string => typeof item === "string" && item.length > 0);
}

export function nextSlugFromCompanyName(opts: {
  companyName: string;
  slugTouched: boolean;
  currentSlug: string;
}): string {
  if (opts.slugTouched) return opts.currentSlug;
  return suggestFromCompanyName(opts.companyName);
}

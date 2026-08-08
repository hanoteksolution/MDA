import { getApiBase } from "@/config/api";

export type TenantHostMode = "platform" | "tenant" | "unknown" | "local";

export interface ResolvedTenantHost {
  mode: TenantHostMode;
  hostname: string;
  subdomain: string | null;
  reason?: string;
  base_domain: string;
  tenant: {
    id: string;
    name: string;
    slug: string;
    status: string;
    is_active: boolean;
    currency: string;
    language: string;
    timezone: string;
    business_type_code: string | null;
    business_type_name: string | null;
    branding: Record<string, unknown>;
  } | null;
}

const DEFAULT_BASE = "erp.safaritechno.com";

/** Current browser hostname without port. */
export function getBrowserHostname(): string {
  if (typeof window === "undefined") return "";
  return (window.location.hostname || "").toLowerCase();
}

export function getConfiguredBaseDomain(): string {
  const fromEnv = (import.meta.env.VITE_TENANT_BASE_DOMAIN as string | undefined)?.trim();
  return (fromEnv || DEFAULT_BASE).toLowerCase().replace(/^\.+|\.+$/g, "");
}

/**
 * Parse subdomain from hostname against the SaaS base domain.
 * Returns null on platform/apex/local hosts.
 */
export function extractSubdomainFromHost(
  hostname = getBrowserHostname(),
  baseDomain = getConfiguredBaseDomain()
): string | null {
  const host = hostname.toLowerCase().split(":")[0];
  if (!host || host === "localhost" || host === "127.0.0.1" || host === "tauri.localhost") {
    return null;
  }
  if (host === baseDomain || host === `www.${baseDomain}` || host === `api.${baseDomain}`) {
    return null;
  }
  const suffix = `.${baseDomain}`;
  if (!host.endsWith(suffix)) return null;
  const sub = host.slice(0, -suffix.length);
  if (!sub || sub.includes(".")) return null;
  return sub;
}

export function detectTenantHostMode(hostname = getBrowserHostname()): TenantHostMode {
  const host = hostname.toLowerCase();
  if (!host || host === "localhost" || host === "127.0.0.1" || host === "tauri.localhost") {
    return "local";
  }
  const sub = extractSubdomainFromHost(host);
  if (sub) return "tenant";
  const base = getConfiguredBaseDomain();
  if (host === base || host.endsWith(`.${base}`)) return "platform";
  return "unknown";
}

/** Public API: resolve branding for the current (or explicit) host. */
export async function resolveTenantHost(host?: string): Promise<ResolvedTenantHost> {
  const apiBase = getApiBase();
  const q = host ? `?host=${encodeURIComponent(host)}` : "";
  const res = await fetch(`${apiBase}/platform/resolve-host/${q}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const body = await res.json();
  if (!res.ok || body?.success === false) {
    return {
      mode: detectTenantHostMode(host || getBrowserHostname()),
      hostname: host || getBrowserHostname(),
      subdomain: extractSubdomainFromHost(host || getBrowserHostname()),
      base_domain: getConfiguredBaseDomain(),
      tenant: null,
      reason: body?.message || "resolve_failed",
    };
  }
  return body.data as ResolvedTenantHost;
}

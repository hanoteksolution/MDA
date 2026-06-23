import { getStoredApiBase, LOCAL_API_BASE } from "@/config/connection";
import { isTauri } from "@/utils/platform";

function normalizeBase(url: string): string {
  return url.replace(/\/$/, "");
}

/** Shop operations always use the local API on desktop. */
export function getApiBase(): string {
  if (isTauri()) {
    return LOCAL_API_BASE;
  }
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (configured?.trim()) {
    return normalizeBase(configured.trim());
  }
  return "/api/v1";
}

/** Cloud API for platform admin + sync (optional on desktop). */
export function getCloudApiBase(): string | null {
  return getStoredApiBase();
}

export function resolveMediaUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;

  const apiBase = getApiBase();
  const origin = apiBase.startsWith("http")
    ? apiBase.replace(/\/api\/v1$/, "")
    : window.location.origin;

  return `${origin}${path.startsWith("/") ? path : `/${path}`}`;
}

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
  const normalized = path.replace(/\\/g, "/").trim();
  if (!normalized) return undefined;
  if (
    normalized.startsWith("http://") ||
    normalized.startsWith("https://") ||
    normalized.startsWith("blob:") ||
    normalized.startsWith("data:")
  ) {
    return normalized;
  }

  const apiBase = getApiBase();
  const origin = apiBase.startsWith("http")
    ? apiBase.replace(/\/api\/v1$/, "")
    : window.location.origin;

  return `${origin}${normalized.startsWith("/") ? normalized : `/${normalized}`}`;
}

/** Stock/demo image hosts — treat as no image so UI shows upload empty state. */
export function isPlaceholderMediaUrl(path?: string | null): boolean {
  if (!path) return true;
  const lower = path.toLowerCase();
  return (
    lower.includes("picsum.photos") ||
    lower.includes("placeholder.com") ||
    lower.includes("placehold.co") ||
    lower.includes("via.placeholder")
  );
}

export function resolveProductImageUrl(path?: string | null): string | undefined {
  if (!path || isPlaceholderMediaUrl(path)) return undefined;
  return resolveMediaUrl(path);
}

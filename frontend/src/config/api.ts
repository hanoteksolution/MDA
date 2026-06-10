import { isTauri } from "@/utils/platform";

function normalizeBase(url: string): string {
  return url.replace(/\/$/, "");
}

/** API root, e.g. `/api/v1` (browser dev) or `http://127.0.0.1:8000/api/v1` (desktop). */
export function getApiBase(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (configured?.trim()) {
    return normalizeBase(configured.trim());
  }
  if (isTauri()) {
    return "http://127.0.0.1:8000/api/v1";
  }
  return "/api/v1";
}

/** Origin for uploaded media (`/media/...` paths from the API). */
export function resolveMediaUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;

  const apiBase = getApiBase();
  const origin = apiBase.startsWith("http")
    ? apiBase.replace(/\/api\/v1$/, "")
    : window.location.origin;

  return `${origin}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Default cloud API URL (domain or IP) — set at build time via VITE_PUBLIC_CLOUD_URL. */
function normalizeApiBase(url: string): string {
  const trimmed = url.trim().replace(/\/$/, "");
  return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
}

const configured = (import.meta.env.VITE_PUBLIC_CLOUD_URL as string | undefined)?.trim();

export const DEFAULT_CLOUD_API_BASE = normalizeApiBase(
  configured || "http://88.222.220.238:8010/api/v1"
);

export const PUBLIC_APP_URL = DEFAULT_CLOUD_API_BASE.replace(/\/api\/v1$/, "");

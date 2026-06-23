export const LOCAL_API_BASE = "http://127.0.0.1:8000/api/v1";

const CLOUD_STORAGE_KEY = "mda_cloud_api_base";

export interface HybridConnectionConfig {
  cloud_api_base: string;
  tenant_slug: string;
  sync_secret: string;
}

let memoryCloudBase: string | null = null;
let memoryConfig: HybridConnectionConfig | null = null;

export function getCloudApiBase(): string | null {
  if (memoryCloudBase) return memoryCloudBase;
  const value = localStorage.getItem(CLOUD_STORAGE_KEY);
  return value?.trim() || null;
}

export function setCloudApiBase(url: string | null): void {
  if (url?.trim()) {
    memoryCloudBase = url.trim().replace(/\/$/, "");
    localStorage.setItem(CLOUD_STORAGE_KEY, memoryCloudBase);
    return;
  }
  memoryCloudBase = null;
  localStorage.removeItem(CLOUD_STORAGE_KEY);
}

export function getHybridConfig(): HybridConnectionConfig | null {
  return memoryConfig;
}

export async function ensureConnectionLoaded(): Promise<HybridConnectionConfig | null> {
  return loadDesktopConnection();
}

export function isLocalApiBase(base: string): boolean {
  try {
    const normalized = base.startsWith("http") ? base : `http://${base}`;
    const host = new URL(normalized).hostname.toLowerCase();
    return host === "127.0.0.1" || host === "localhost";
  } catch {
    return true;
  }
}

export async function persistDesktopConnection(config: HybridConnectionConfig): Promise<void> {
  setCloudApiBase(config.cloud_api_base || null);
  memoryConfig = config;
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return;
  }
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("save_connection_config", { config });
}

export async function loadDesktopConnection(): Promise<HybridConnectionConfig | null> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    const cloud = getCloudApiBase();
    return cloud ? { cloud_api_base: cloud, tenant_slug: "", sync_secret: "" } : null;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const value = await invoke<HybridConnectionConfig>("get_connection_config");
    const normalized: HybridConnectionConfig = {
      cloud_api_base: (value.cloud_api_base || "").trim().replace(/\/$/, ""),
      tenant_slug: value.tenant_slug || "",
      sync_secret: value.sync_secret || "",
    };
    memoryConfig = normalized;
    if (normalized.cloud_api_base) {
      setCloudApiBase(normalized.cloud_api_base);
    }
    return normalized;
  } catch {
    const cloud = getCloudApiBase();
    return cloud ? { cloud_api_base: cloud, tenant_slug: "", sync_secret: "" } : null;
  }
}

/** @deprecated Use setCloudApiBase — kept for compatibility */
export function setStoredApiBase(url: string | null): void {
  setCloudApiBase(url);
}

/** @deprecated Use getCloudApiBase */
export function getStoredApiBase(): string | null {
  return getCloudApiBase();
}

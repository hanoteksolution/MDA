import type { ApiResponse } from "@/types/models";
import { apiRequest } from "./http";

export interface SyncRunResult {
  status: string;
  synced_at: string;
  message?: string;
  pushed?: { invoices: number; customers: number; inventory: number };
  pulled?: Record<string, number>;
}

export interface SyncConfig {
  cloud_api_base: string;
  tenant_slug: string;
  sync_secret: string;
  device_id: string;
  last_sync_at: string;
  last_pull_at?: string;
  last_status: string;
  last_message: string;
  initial_pull_done?: boolean;
}

export const syncApi = {
  config: () => apiRequest<ApiResponse<SyncConfig>>("/sync/config/"),

  saveConfig: (data: Partial<SyncConfig>) =>
    apiRequest<ApiResponse<SyncConfig>>("/sync/config/", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  run: () =>
    apiRequest<ApiResponse<SyncRunResult>>("/sync/run/", {
      method: "POST",
    }),
};

/** Platform APIs: browser uses same-origin API; desktop uses cloud when configured. */
export async function platformCloudRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const { ensureConnectionLoaded, getCloudApiBase } = await import("@/config/connection");
  const { hasCloudSession, cloudApiRequest } = await import("./cloudHttp");
  const { isTauri } = await import("@/utils/platform");

  if (isTauri()) {
    await ensureConnectionLoaded();
    const base = getCloudApiBase();
    if (base) {
      if (hasCloudSession()) {
        return cloudApiRequest<T>(endpoint, options);
      }
      throw new Error(
        "Cloud admin sign-in required. Open Settings → Connection and click \"Sign in to cloud\"."
      );
    }
  }

  // Web browser on cloud server, or desktop local DB — use normal logged-in session
  return apiRequest<T>(endpoint, options);
}

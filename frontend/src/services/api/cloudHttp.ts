import { getCloudApiBase } from "@/config/api";
import type { ApiResponse } from "@/types/models";

const CLOUD_ACCESS_KEY = "cloud_access_token";
const CLOUD_REFRESH_KEY = "cloud_refresh_token";

export function hasCloudSession(): boolean {
  return !!localStorage.getItem(CLOUD_ACCESS_KEY);
}

export function clearCloudSession(): void {
  localStorage.removeItem(CLOUD_ACCESS_KEY);
  localStorage.removeItem(CLOUD_REFRESH_KEY);
}

export async function cloudLogin(username: string, password: string): Promise<void> {
  const base = getCloudApiBase();
  if (!base) {
    throw new Error("Cloud server URL is not configured.");
  }
  const res = await fetch(`${base}/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.message || "Cloud login failed.");
  }
  const data = body.data ?? body;
  localStorage.setItem(CLOUD_ACCESS_KEY, data.access);
  if (data.refresh) {
    localStorage.setItem(CLOUD_REFRESH_KEY, data.refresh);
  }
}

export async function cloudApiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const base = getCloudApiBase();
  if (!base) {
    throw new Error("Cloud server is not configured.");
  }
  const token = localStorage.getItem(CLOUD_ACCESS_KEY);
  if (!token) {
    throw new Error("Cloud admin session required. Sign in to cloud from Settings → Connection.");
  }
  const url = `${base}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) {
      clearCloudSession();
    }
    throw new Error(body.message || `Cloud request failed (${res.status})`);
  }
  return body as T;
}

export type { ApiResponse };

import * as SecureStore from "expo-secure-store";

import { API_BASE } from "@/config/env";

const ACCESS_KEY = "mda_staff_access";
const REFRESH_KEY = "mda_staff_refresh";
const TENANT_KEY = "mda_staff_tenant";

export interface ApiEnvelope<T> {
  success: boolean;
  message?: string;
  code?: string;
  data?: T;
}

export async function getStoredTenant(): Promise<string | null> {
  return SecureStore.getItemAsync(TENANT_KEY);
}

export async function setStoredTenant(slug: string) {
  await SecureStore.setItemAsync(TENANT_KEY, slug);
}

export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_KEY);
}

export async function setTokens(access: string, refresh: string) {
  await SecureStore.setItemAsync(ACCESS_KEY, access);
  await SecureStore.setItemAsync(REFRESH_KEY, refresh);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
  if (!refresh) return null;
  const tenant = await getStoredTenant();
  const response = await fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(tenant ? { "X-Tenant-Slug": tenant } : {}),
    },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) return null;
  const body = (await response.json()) as ApiEnvelope<{ access: string; refresh?: string }>;
  const access = body.data?.access;
  if (!access) return null;
  await SecureStore.setItemAsync(ACCESS_KEY, access);
  if (body.data?.refresh) {
    await SecureStore.setItemAsync(REFRESH_KEY, body.data.refresh);
  }
  return access;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const tenant = await getStoredTenant();
  let token = await getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (tenant) headers["X-Tenant-Slug"] = tenant;

  let response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401 && retry) {
    token = await refreshAccessToken();
    if (!token) throw new Error("Session expired. Please sign in again.");
    headers.Authorization = `Bearer ${token}`;
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  }

  const body = (await response.json()) as ApiEnvelope<T> & T;
  if (!response.ok) {
    throw new Error(body.message || "Request failed");
  }
  return (body.data ?? body) as T;
}

export async function loginRequest(username: string, password: string, tenantSlug: string) {
  await setStoredTenant(tenantSlug);
  const response = await fetch(`${API_BASE}/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-Slug": tenantSlug,
    },
    body: JSON.stringify({ username, password }),
  });
  const body = (await response.json()) as ApiEnvelope<{
    access: string;
    refresh: string;
    user: { username: string };
  }>;
  if (!response.ok) {
    throw new Error(body.message || "Login failed");
  }
  if (!body.data?.access || !body.data.refresh) {
    throw new Error("Invalid login response");
  }
  await setTokens(body.data.access, body.data.refresh);
  return body.data;
}

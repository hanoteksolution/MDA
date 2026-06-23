import { getApiBase } from "@/config/api";
import { isTauri } from "@/utils/platform";

function apiUrl(endpoint: string): string {
  const base = getApiBase();
  return `${base}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
}

const PUBLIC_ENDPOINTS = ["/auth/login/", "/auth/refresh/", "/setup/"];
const AUTH_ROUTES = ["/login", "/forgot-password", "/setup"];

let logoutInProgress = false;
let refreshPromise: Promise<string | null> | null = null;

/** Decode JWT exp claim; returns true if missing or expired. */
export function isJwtExpired(token: string, bufferSeconds = 30): boolean {
  try {
    const segment = token.split(".")[1];
    if (!segment) return true;
    const payload = JSON.parse(atob(segment.replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof payload.exp !== "number") return false;
    return payload.exp * 1000 <= Date.now() + bufferSeconds * 1000;
  } catch {
    return true;
  }
}

export function clearAuthTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

/** Clear session and redirect to login (full page navigation). */
export function forceLogout(redirect = true) {
  if (logoutInProgress) return;
  logoutInProgress = true;
  clearAuthTokens();

  if (redirect) {
    const path = window.location.pathname;
    const onAuthPage = AUTH_ROUTES.some((r) => path.startsWith(r));
    if (!onAuthPage) {
      if (isTauri()) {
        window.location.hash = "#/login?expired=1";
      } else {
        window.location.replace("/login?expired=1");
      }
    }
  }

  logoutInProgress = false;
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh || isJwtExpired(refresh, 0)) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(apiUrl("/auth/refresh/"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then(async (res) => {
        if (!res.ok) return null;
        const data = await res.json();
        const access = data.access as string | undefined;
        if (!access) return null;
        localStorage.setItem("access_token", access);
        return access;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

export function qs(params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") q.set(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function apiUpload<T>(endpoint: string, file: File, fieldName = "image"): Promise<T> {
  const token = localStorage.getItem("access_token");
  const formData = new FormData();
  formData.append(fieldName, file);

  const response = await fetch(apiUrl(endpoint), {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "Upload failed");
  }
  return data as T;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  allowRetry = true
): Promise<T> {
  const isPublic = PUBLIC_ENDPOINTS.some((p) => endpoint.startsWith(p));

  let token = localStorage.getItem("access_token");
  if (!isPublic && token && isJwtExpired(token)) {
    token = await refreshAccessToken();
    if (!token) {
      forceLogout();
      throw new Error("Session expired. Please sign in again.");
    }
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(endpoint), {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      "Cannot reach the API server. Start it with: make run-backend (http://127.0.0.1:8000)"
    );
  }

  let data: { message?: string } & T;
  try {
    data = await response.json();
  } catch {
    if (response.status === 401 && !isPublic) {
      forceLogout();
      throw new Error("Session expired. Please sign in again.");
    }
    if (isPublic && response.status === 401) {
      throw new Error("Invalid username or password.");
    }
    if (response.status >= 500) {
      throw new Error(`Server error (${response.status}). Check API logs or try again.`);
    }
    throw new Error(
      response.ok
        ? "Unexpected server response."
        : `Request failed (${response.status}). The API may be unavailable.`
    );
  }

  if (response.status === 401 && !isPublic) {
    if (allowRetry) {
      const newToken = await refreshAccessToken();
      if (newToken) return apiRequest<T>(endpoint, options, false);
    }
    forceLogout();
    throw new Error(data.message || "Session expired. Please sign in again.");
  }

  if (!response.ok) {
    throw new Error(data.message || "Request failed");
  }

  return data;
}

/** Periodically refresh or logout when the access token expires. */
export function startSessionMonitor(intervalMs = 60_000): () => void {
  const tick = async () => {
    const access = localStorage.getItem("access_token");
    const refresh = localStorage.getItem("refresh_token");
    if (!access && !refresh) return;

    const onAuthPage = AUTH_ROUTES.some((r) => window.location.pathname.startsWith(r));
    if (onAuthPage) return;

    if (!access || isJwtExpired(access)) {
      const renewed = await refreshAccessToken();
      if (!renewed) forceLogout();
    }
  };

  tick();
  const id = setInterval(tick, intervalMs);
  return () => clearInterval(id);
}

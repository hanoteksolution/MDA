import { create } from "zustand";
import { api } from "@/services/api/client";
import { clearAuthTokens, forceLogout, isJwtExpired } from "@/services/api/http";
import { clearCloudSession, cloudLogin } from "@/services/api/cloudHttp";
import { ensureConnectionLoaded, getCloudApiBase, getHybridConfig } from "@/config/connection";
import { syncApi } from "@/services/api/sync";
import { requestCloudSync } from "@/components/desktop/syncEvents";
import { isTauri } from "@/utils/platform";
import type { User } from "@/types/models";

function isPlatformUser(user: User): boolean {
  return Boolean(
    user.is_platform_admin ||
      user.permissions?.includes("platform.view") ||
      user.permissions?.includes("platform.manage")
  );
}

async function tryAutoCloudLogin(username: string, password: string, user: User): Promise<void> {
  if (!isTauri() || !isPlatformUser(user)) return;
  await ensureConnectionLoaded();
  if (!getCloudApiBase()) return;
  try {
    await cloudLogin(username, password);
  } catch {
    // Cloud optional — local session remains valid
  }
}

function shopConnectionReady(): boolean {
  const cfg = getHybridConfig();
  return Boolean(cfg?.cloud_api_base && cfg.tenant_slug && cfg.sync_secret);
}

async function tryCloudShopProvision(username: string, password: string): Promise<{
  access: string;
  refresh: string;
  user: User;
}> {
  await cloudLogin(username, password);
  const cloudToken = localStorage.getItem("cloud_access_token");
  if (!cloudToken) {
    throw new Error("Cloud sign-in failed.");
  }

  try {
    const provision = await api.desktopProvision(username, password, cloudToken);
    clearCloudSession();
    try {
      await syncApi.run();
      requestCloudSync();
    } catch {
      // Provisioning succeeded; initial sync can retry in background
    }
    return provision.data;
  } catch (err) {
    clearCloudSession();
    throw err;
  }
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  clearError: () => void;
  sessionExpired: () => void;
}

function hasValidToken(): boolean {
  const token = localStorage.getItem("access_token");
  return !!token && !isJwtExpired(token);
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: hasValidToken(),
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      await ensureConnectionLoaded();

      const statusRes = await api.desktopUserStatus(username).catch(() => null);
      const localExists = Boolean(statusRes?.data.exists);
      const provisioned = Boolean(statusRes?.data.provisioned);
      const canCloudProvision = isTauri() && shopConnectionReady() && !provisioned;

      let session: { access: string; refresh: string; user: User } | null = null;

      if (localExists) {
        try {
          const local = await api.login(username, password);
          session = local.data;
        } catch {
          if (!canCloudProvision) throw new Error("Invalid credentials.");
        }
      }

      if (!session && canCloudProvision) {
        session = await tryCloudShopProvision(username, password);
      }

      if (!session) {
        throw new Error(
          canCloudProvision
            ? "Could not sign in. Use the username and password from your platform admin."
            : "Invalid credentials."
        );
      }

      localStorage.setItem("access_token", session.access);
      localStorage.setItem("refresh_token", session.refresh);
      await tryAutoCloudLogin(username, password, session.user);
      set({
        user: session.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Login failed",
        isLoading: false,
      });
      throw err;
    }
  },

  logout: async () => {
    const refresh = localStorage.getItem("refresh_token");
    try {
      if (refresh) await api.logout(refresh);
    } catch {
      // Ignore logout API errors — clear local session regardless
    } finally {
      clearAuthTokens();
      clearCloudSession();
      set({ user: null, isAuthenticated: false });
    }
  },

  sessionExpired: () => {
    clearAuthTokens();
    set({ user: null, isAuthenticated: false, isLoading: false, error: null });
    forceLogout();
  },

  loadUser: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ isAuthenticated: false, isLoading: false });
      return;
    }

    if (isJwtExpired(token)) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      forceLogout();
      return;
    }

    set({ isLoading: true });
    try {
      const response = await api.getMe();
      set({ user: response.data, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
      forceLogout();
    }
  },

  clearError: () => set({ error: null }),
}));

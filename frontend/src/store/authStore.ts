import { create } from "zustand";
import { api } from "@/services/api/client";
import { clearAuthTokens, forceLogout, isJwtExpired } from "@/services/api/http";
import type { User } from "@/types/models";

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
      const response = await api.login(username, password);
      localStorage.setItem("access_token", response.data.access);
      localStorage.setItem("refresh_token", response.data.refresh);
      set({
        user: response.data.user,
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

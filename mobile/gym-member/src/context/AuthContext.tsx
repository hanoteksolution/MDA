import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { fetchBootstrap, type MobileBootstrap, type MobileNav } from "@/api/bootstrap";
import { clearTokens, getAccessToken, loginRequest } from "@/api/client";
import { fetchHome, type GymHome } from "@/api/gym";
import { hasScreen } from "@/modules/registry";

interface AuthContextValue {
  loading: boolean;
  signedIn: boolean;
  home: GymHome | null;
  bootstrap: MobileBootstrap | null;
  mobileNav: MobileNav | null;
  enabledModules: string[];
  gymModuleEnabled: boolean;
  canShowScreen: (screenId: string) => boolean;
  signIn: (tenantSlug: string, username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshHome: () => Promise<void>;
  refreshBootstrap: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function gymWorkspaceEnabled(data: MobileBootstrap | null | undefined): boolean {
  return (data?.mobile_nav?.workspaces ?? []).some((w) => w.id === "gym_member");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);
  const [home, setHome] = useState<GymHome | null>(null);
  const [bootstrap, setBootstrap] = useState<MobileBootstrap | null>(null);

  const applyBootstrap = useCallback(async (data: MobileBootstrap) => {
    setBootstrap(data);
    if (!gymWorkspaceEnabled(data)) {
      setHome(null);
      return data;
    }
    try {
      setHome(await fetchHome());
    } catch {
      setHome(null);
    }
    return data;
  }, []);

  const refreshBootstrap = useCallback(async () => {
    const data = await fetchBootstrap();
    await applyBootstrap(data);
  }, [applyBootstrap]);

  const refreshHome = useCallback(async () => {
    if (!gymWorkspaceEnabled(bootstrap)) {
      setHome(null);
      return;
    }
    try {
      setHome(await fetchHome());
    } catch {
      setHome(null);
    }
  }, [bootstrap]);

  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessToken();
        if (token) {
          await refreshBootstrap();
          setSignedIn(true);
        }
      } catch {
        await clearTokens();
        setSignedIn(false);
        setBootstrap(null);
        setHome(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshBootstrap]);

  const signIn = useCallback(
    async (tenantSlug: string, username: string, password: string) => {
      await loginRequest(username, password, tenantSlug);
      await refreshBootstrap();
      setSignedIn(true);
    },
    [refreshBootstrap]
  );

  const signOut = useCallback(async () => {
    await clearTokens();
    setHome(null);
    setBootstrap(null);
    setSignedIn(false);
  }, []);

  const mobileNav = bootstrap?.mobile_nav ?? null;
  const enabledModules =
    bootstrap?.enabled_modules ??
    bootstrap?.mobile_nav?.enabled_modules ??
    bootstrap?.user?.enabled_modules ??
    [];
  const gymModuleEnabled = gymWorkspaceEnabled(bootstrap);

  const canShowScreen = useCallback(
    (screenId: string) => hasScreen(mobileNav?.screens, screenId),
    [mobileNav]
  );

  const value = useMemo(
    () => ({
      loading,
      signedIn,
      home,
      bootstrap,
      mobileNav,
      enabledModules,
      gymModuleEnabled,
      canShowScreen,
      signIn,
      signOut,
      refreshHome,
      refreshBootstrap,
    }),
    [
      loading,
      signedIn,
      home,
      bootstrap,
      mobileNav,
      enabledModules,
      gymModuleEnabled,
      canShowScreen,
      signIn,
      signOut,
      refreshHome,
      refreshBootstrap,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

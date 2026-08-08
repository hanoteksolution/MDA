import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  fetchStaffBootstrap,
  type MobileBootstrap,
  type MobileNav,
  type MobileNavWorkspace,
} from "@/api/bootstrap";
import { clearTokens, getAccessToken, loginRequest } from "@/api/client";

interface AuthContextValue {
  loading: boolean;
  signedIn: boolean;
  bootstrap: MobileBootstrap | null;
  mobileNav: MobileNav | null;
  moduleWorkspaces: MobileNavWorkspace[];
  signIn: (tenantSlug: string, username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshBootstrap: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);
  const [bootstrap, setBootstrap] = useState<MobileBootstrap | null>(null);

  const refreshBootstrap = useCallback(async () => {
    const data = await fetchStaffBootstrap();
    setBootstrap(data);
  }, []);

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
    setBootstrap(null);
    setSignedIn(false);
  }, []);

  const mobileNav = bootstrap?.mobile_nav ?? null;
  const moduleWorkspaces = (mobileNav?.workspaces ?? []).filter(
    (w) => w.audience === "staff" && w.id !== "staff_hub"
  );

  const value = useMemo(
    () => ({
      loading,
      signedIn,
      bootstrap,
      mobileNav,
      moduleWorkspaces,
      signIn,
      signOut,
      refreshBootstrap,
    }),
    [loading, signedIn, bootstrap, mobileNav, moduleWorkspaces, signIn, signOut, refreshBootstrap]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

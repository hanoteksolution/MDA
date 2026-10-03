import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, Lock, User, ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { LoginBrandingPanel } from "@/components/auth/LoginBrandingPanel";
import { useAuthStore } from "@/store/authStore";
import { postLoginPath } from "@/navigation/postLogin";
import { setupApi } from "@/services/api/setup";
import {
  ensureConnectionLoaded,
  getHybridConfig,
  isLocalApiBase,
} from "@/config/connection";
import { getApiBase } from "@/config/api";
import { isTauri } from "@/utils/platform";
import { SafariLogo } from "@/components/brand/SafariLogo";
import {
  resolveTenantHost,
  type ResolvedTenantHost,
} from "@/config/tenantHost";

const REMEMBER_KEY = "mda_remember_username";

function shopConnectionReady(): boolean {
  const cfg = getHybridConfig();
  return Boolean(cfg?.cloud_api_base && cfg.tenant_slug && cfg.sync_secret);
}

const formContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.2 },
  },
};

const formItem = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: "easeOut" as const },
  },
};

export function LoginPage() {
  const [apiTarget, setApiTarget] = useState("");
  const [checkingSetup, setCheckingSetup] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login, isLoading, error, clearError, isAuthenticated, user } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [sessionExpired, setSessionExpired] = useState(false);
  const [hostTenant, setHostTenant] = useState<ResolvedTenantHost | null>(null);
  // keep searchParams usage
  useEffect(() => {
    setSessionExpired(searchParams.get("expired") === "1");
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    resolveTenantHost()
      .then((resolved) => {
        if (!cancelled) setHostTenant(resolved);
      })
      .catch(() => {
        /* ignore branding errors */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const withTimeout = <T,>(promise: Promise<T>, ms: number) =>
      Promise.race([
        promise,
        new Promise<never>((_, reject) => {
          window.setTimeout(() => reject(new Error("API timeout")), ms);
        }),
      ]);

    const checkSetup = async (attempt = 0) => {
      try {
        await ensureConnectionLoaded();
        if (cancelled) return;
        setApiTarget(getApiBase());
        const res = await withTimeout(setupApi.status(), 5000);
        if (cancelled) return;
        if (res.data.needs_setup) {
          // Desktop: cloud shop path — connection → login → provision (skip local Setup).
          if (isTauri()) {
            if (!shopConnectionReady()) {
              navigate("/connection", { replace: true });
              return;
            }
            setCheckingSetup(false);
            return;
          }
          navigate("/setup", { replace: true });
          return;
        }
        setCheckingSetup(false);
      } catch {
        if (cancelled) return;
        if (attempt < 3) {
          window.setTimeout(() => {
            void checkSetup(attempt + 1);
          }, 400);
          return;
        }
        setApiTarget(getApiBase());
        setCheckingSetup(false);
      }
    };

    void checkSetup();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    const saved = localStorage.getItem(REMEMBER_KEY);
    if (saved) {
      setUsername(saved);
      setRememberMe(true);
    }
  }, []);

  useEffect(() => {
    if (sessionExpired) clearError();
  }, [sessionExpired, clearError]);

  useEffect(() => {
    if (isAuthenticated && user) {
      navigate(postLoginPath(user), { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (rememberMe) {
      localStorage.setItem(REMEMBER_KEY, username);
    } else {
      localStorage.removeItem(REMEMBER_KEY);
    }

    try {
      await login(username, password);
      navigate(postLoginPath(useAuthStore.getState().user), { replace: true });
    } catch {
      try {
        const res = await setupApi.status();
        if (res.data.needs_setup && !isTauri()) {
          navigate("/setup", { replace: true });
        } else if (res.data.needs_setup && isTauri() && !shopConnectionReady()) {
          navigate("/connection", { replace: true });
        }
      } catch {
        // stay on login with store error
      }
    }
  };

  if (!isTauri() && hostTenant?.mode === "unknown" && hostTenant.reason === "unknown_subdomain") {
    const host = hostTenant.hostname;
    const apex = hostTenant.base_domain;
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background px-4 text-center">
        <SafariLogo size="md" />
        <div className="max-w-md space-y-3">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Workspace not found</h1>
          <p className="text-muted-foreground">
            There is no Safari ERP workspace at <span className="break-all font-mono text-foreground">{host}</span>.
            Check the address, or create a workspace with this name.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/onboard"
            className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Create a workspace
          </Link>
          <a
            href={`https://${apex}/login`}
            className="rounded-xl border border-border px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Go to {apex}
          </a>
        </div>
      </main>
    );
  }

  if (checkingSetup) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background" role="status">
        <SafariLogo size="md" />
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent motion-reduce:animate-none" aria-hidden />
        <span className="sr-only">Loading…</span>
      </div>
    );
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <LoginBrandingPanel
        productName={hostTenant?.tenant?.name || undefined}
        productTagline={
          hostTenant?.tenant
            ? hostTenant.tenant.business_type_name || "Business portal"
            : undefined
        }
        headline={
          hostTenant?.tenant
            ? `Sign in to ${hostTenant.tenant.name}`
            : undefined
        }
        description={
          hostTenant?.tenant
            ? `Secure access for ${hostTenant.tenant.name} staff. Your session is bound to this business domain.`
            : undefined
        }
      />

      <main className="flex min-w-0 flex-col bg-background">
        <div className="safari-brand-rule h-1 w-full lg:hidden" aria-hidden />
        <div className="flex flex-1 flex-col justify-center px-4 py-10 sm:px-10 lg:px-14 xl:px-20">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mx-auto w-full max-w-md"
          >
            {/* Narrow screens: the branding panel is hidden, keep the logo visible. */}
            <div className="mb-8 lg:hidden">
              <SafariLogo size="md" />
              {hostTenant?.tenant?.name ? (
                <p className="mt-4 text-sm font-semibold text-brand-soft-foreground">
                  {hostTenant.tenant.name}
                </p>
              ) : null}
            </div>

            <div className="mb-8">
              <h2 className="text-3xl font-bold tracking-tight text-foreground">Welcome back</h2>
              <p className="mt-2 text-muted-foreground">
                {hostTenant?.tenant
                  ? `Sign in to ${hostTenant.tenant.name}`
                  : isTauri() && shopConnectionReady()
                  ? "Sign in with your cloud shop account. This PC will work offline after the first login."
                  : "Sign in to your Safari ERP workspace"}
              </p>
              {isTauri() && apiTarget && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Server:{" "}
                  <span className="font-mono text-foreground">{apiTarget}</span>
                  {" · "}
                  <Link to="/connection" className="text-primary hover:underline">
                    Change
                  </Link>
                  {isLocalApiBase(apiTarget) && (
                    <span className="block mt-1 text-amber-600">
                      First shop sign-in verifies your account on the live server, copies your role and
                      permissions locally, then downloads shop data. Use a shop user (Admin / Cashier),
                      not a multi-shop manager. Later sign-ins use this PC only; Sync keeps both sides updated.
                    </span>
                  )}
                </p>
              )}
            </div>

            <div className="rounded-2xl border border-border bg-brand-surface p-6 shadow-[0_1px_2px_hsl(var(--foreground)/0.04),0_12px_32px_-12px_hsl(var(--brand-primary)/0.18)] sm:p-8">
              <motion.form
                variants={formContainer}
                initial="hidden"
                animate="show"
                onSubmit={handleSubmit}
                className="space-y-5"
              >
                {/* Username */}
                <motion.div variants={formItem} className="space-y-2">
                  <Label htmlFor="username" className="text-foreground">
                    Username
                  </Label>
                  <div className="relative">
                    <User className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                    <Input
                      id="username"
                      value={username}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
                      placeholder="Enter your username"
                      className="pl-11"
                      required
                      autoFocus
                      autoComplete="username"
                    />
                  </div>
                </motion.div>

                {/* Password */}
                <motion.div variants={formItem} className="space-y-2">
                  <Label htmlFor="password" className="text-foreground">
                    Password
                  </Label>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                      placeholder="Enter your password"
                      className="pl-11 pr-12"
                      required
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                      aria-controls="password"
                      className="absolute right-1.5 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-lg text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" aria-hidden />
                      ) : (
                        <Eye className="h-4 w-4" aria-hidden />
                      )}
                    </button>
                  </div>
                </motion.div>

                {/* Remember + Forgot */}
                <motion.div
                  variants={formItem}
                  className="flex flex-wrap items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="remember"
                      checked={rememberMe}
                      onCheckedChange={(checked) => setRememberMe(checked === true)}
                    />
                    <Label
                      htmlFor="remember"
                      className="cursor-pointer text-sm font-normal text-muted-foreground"
                    >
                      Remember me
                    </Label>
                  </div>
                  <Link
                    to="/forgot-password"
                    className="rounded text-sm font-medium text-primary transition-colors hover:text-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    Forgot password?
                  </Link>
                </motion.div>

                {/* Session expired notice */}
                {sessionExpired && (
                  <div
                    role="status"
                    className="rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-foreground"
                  >
                    <p className="font-medium">Your session has expired</p>
                    <p className="mt-0.5 text-muted-foreground">Please sign in again to continue.</p>
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div
                    role="alert"
                    className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                  >
                    {error}
                  </div>
                )}

                {/* Submit */}
                <motion.div variants={formItem}>
                  <Button
                    type="submit"
                    size="lg"
                    loading={isLoading}
                    className="w-full group"
                  >
                    {!isLoading && (
                      <>
                        Sign in
                        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1 motion-reduce:transition-none" aria-hidden />
                      </>
                    )}
                  </Button>
                </motion.div>
              </motion.form>
            </div>

            {!isTauri() && (
              <p className="mt-6 text-center text-sm text-muted-foreground">
                New to Safari ERP?{" "}
                <Link
                  to="/onboard"
                  className="rounded font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Create a workspace
                </Link>
              </p>
            )}

            <div className="mt-8 flex flex-col items-center gap-1 border-t border-border pt-6 text-muted-foreground">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-brand-deep" aria-hidden />
                <span className="text-xs">Encrypted sign-in · tenant-isolated workspace</span>
              </div>
              {import.meta.env.DEV && (
                <p className="text-[11px] text-muted-foreground/70">
                  Dev demo: run <code className="text-[10px]">make seed-demo</code>
                </p>
              )}
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}

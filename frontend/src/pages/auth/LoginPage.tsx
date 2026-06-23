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
import { setupApi } from "@/services/api/setup";
import { ensureConnectionLoaded, isLocalApiBase } from "@/config/connection";
import { getApiBase } from "@/config/api";
import { isTauri } from "@/utils/platform";
import { cn } from "@/utils/cn";

const REMEMBER_KEY = "mda_remember_username";

const formContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.2 },
  },
};

const formItem = {
  hidden: { opacity: 0, x: 20 },
  show: {
    opacity: 1,
    x: 0,
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
  const { login, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionExpired = searchParams.get("expired") === "1";

  useEffect(() => {
    let cancelled = false;

    const checkSetup = async (attempt = 0) => {
      try {
        await ensureConnectionLoaded();
        setApiTarget(getApiBase());
        const res = await setupApi.status();
        if (cancelled) return;
        if (res.data.needs_setup) {
          navigate("/setup", { replace: true });
          return;
        }
        setCheckingSetup(false);
      } catch {
        if (cancelled) return;
        if (attempt < 8) {
          window.setTimeout(() => {
            void checkSetup(attempt + 1);
          }, 500);
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
      navigate("/dashboard", { replace: true });
    } catch {
      try {
        const res = await setupApi.status();
        if (res.data.needs_setup) {
          navigate("/setup", { replace: true });
        }
      } catch {
        // stay on login with store error
      }
    }
  };

  if (checkingSetup) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Left — 60% branding */}
      <div className="lg:w-[60%] order-2 lg:order-1">
        <LoginBrandingPanel />
      </div>

      {/* Right — 40% form */}
      <div className="relative flex lg:w-[40%] order-1 lg:order-2 flex-col justify-center bg-background px-6 py-10 sm:px-10 lg:px-12 xl:px-16">
        {/* Subtle gradient accent */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-emerald-500/5 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-emerald-500/5 blur-3xl" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 mx-auto w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600">
              <span className="text-base font-black text-white">M</span>
            </div>
            <span className="text-lg font-bold text-foreground">MDA Retail ERP</span>
          </div>

          <div className="mb-8">
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-3xl font-bold tracking-tight text-foreground"
            >
              Welcome back
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="mt-2 text-muted-foreground"
            >
              Sign in to access your enterprise dashboard
            </motion.p>
            {isTauri() && apiTarget && (
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.18 }}
                className="mt-3 text-xs text-muted-foreground"
              >
                Server:{" "}
                <span className="font-mono text-foreground">{apiTarget}</span>
                {" · "}
                <Link to="/connection" className="text-primary hover:underline">
                  Change
                </Link>
                {isLocalApiBase(apiTarget) && (
                  <span className="block mt-1 text-amber-600">
                    First shop sign-in verifies your account on the live server, copies your role and
                    permissions locally, then downloads shop data. Later sign-ins use this PC only.
                  </span>
                )}
              </motion.p>
            )}
          </div>

          {/* Glass card form */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.4 }}
            className="glass-card rounded-2xl p-8"
          >
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
                  <User className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
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
                  <Lock className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="pl-11 pr-11"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </motion.div>

              {/* Remember + Forgot */}
              <motion.div
                variants={formItem}
                className="flex items-center justify-between"
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
                  className="text-sm font-medium text-primary hover:text-primary-hover transition-colors"
                >
                  Forgot password?
                </Link>
              </motion.div>

              {/* Session expired notice */}
              {sessionExpired && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-foreground"
                >
                  <p className="font-medium">Your session has expired</p>
                  <p className="mt-0.5 text-muted-foreground">Please sign in again to continue.</p>
                </motion.div>
              )}

              {/* Error */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                >
                  {error}
                </motion.div>
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
                      Sign in to Dashboard
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </>
                  )}
                </Button>
              </motion.div>
            </motion.form>
          </motion.div>

          {/* Enterprise trust footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="mt-8 space-y-4"
          >
            <div className="flex flex-col items-center justify-center gap-1 text-muted-foreground">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <span className="text-xs">
                  Secured with enterprise-grade JWT authentication
                </span>
              </div>
              {import.meta.env.DEV && (
                <p className="text-[11px] text-muted-foreground/70">
                  Dev demo: run <code className="text-[10px]">make seed-demo</code>
                </p>
              )}
            </div>

            <div className="flex items-center justify-center gap-6 border-t border-border pt-6">
              {["SOC 2 Ready", "GDPR Compliant", "99.9% Uptime"].map((badge) => (
                <span
                  key={badge}
                  className={cn(
                    "text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60"
                  )}
                >
                  {badge}
                </span>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}

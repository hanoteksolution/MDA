import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  Globe,
  Layers,
  Store,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField } from "@/components/forms/FormField";
import { LoginBrandingPanel } from "@/components/auth/LoginBrandingPanel";
import {
  onboardingApi,
  type OnboardingBusinessType,
  type OnboardingPlan,
} from "@/services/api/onboarding";
import { useAuthStore } from "@/store/authStore";
import { clearBrandingCache } from "@/documents/branding";
import { cn } from "@/utils/cn";
import { isTauri } from "@/utils/platform";

const STEPS = [
  { id: "business", label: "Business", icon: Building2 },
  { id: "type", label: "Type", icon: Store },
  { id: "subdomain", label: "Subdomain", icon: Globe },
  { id: "plan", label: "Plan", icon: Layers },
  { id: "owner", label: "Account", icon: User },
] as const;

type StepId = (typeof STEPS)[number]["id"];

function slugify(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const [step, setStep] = useState<StepId>("business");
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [businessTypes, setBusinessTypes] = useState<OnboardingBusinessType[]>([]);
  const [plans, setPlans] = useState<OnboardingPlan[]>([]);
  const [baseDomain, setBaseDomain] = useState("erp.safaritechno.com");

  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [businessTypeCode, setBusinessTypeCode] = useState("retail");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [slugStatus, setSlugStatus] = useState<{
    available: boolean;
    reason: string;
    hostname: string | null;
  } | null>(null);
  const [planCode, setPlanCode] = useState("starter");
  const [branchName, setBranchName] = useState("Main Branch");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
      return;
    }
    if (isTauri()) {
      navigate("/connection", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    onboardingApi
      .catalog()
      .then((res) => {
        setBusinessTypes(res.data.business_types || []);
        setPlans(res.data.plans || []);
        setBaseDomain(res.data.base_domain || "erp.safaritechno.com");
        if (res.data.business_types?.[0]?.code) {
          setBusinessTypeCode(res.data.business_types[0].code);
        }
        if (res.data.plans?.[0]?.code) {
          setPlanCode(res.data.plans[0].code);
        }
      })
      .catch(() => setError("Could not load onboarding options."))
      .finally(() => setLoadingCatalog(false));
  }, []);

  useEffect(() => {
    if (!slugTouched && name) {
      setSlug(slugify(name));
    }
  }, [name, slugTouched]);

  useEffect(() => {
    if (!slug || step !== "subdomain") {
      setSlugStatus(null);
      return;
    }
    const handle = window.setTimeout(() => {
      onboardingApi
        .checkSlug(slug)
        .then((res) =>
          setSlugStatus({
            available: res.data.available,
            reason: res.data.reason,
            hostname: res.data.hostname,
          })
        )
        .catch(() =>
          setSlugStatus({ available: false, reason: "Could not check subdomain.", hostname: null })
        );
    }, 350);
    return () => window.clearTimeout(handle);
  }, [slug, step]);

  const stepIndex = useMemo(() => STEPS.findIndex((s) => s.id === step), [step]);

  const validateStep = useCallback((): string | null => {
    if (step === "business") {
      if (!name.trim()) return "Business name is required.";
      if (!contactEmail.trim()) return "Contact email is required.";
    }
    if (step === "type" && !businessTypeCode) return "Select a business type.";
    if (step === "subdomain") {
      if (!slug.trim()) return "Subdomain is required.";
      if (slugStatus && !slugStatus.available) return slugStatus.reason || "Subdomain unavailable.";
    }
    if (step === "plan" && !planCode) return "Select a plan.";
    if (step === "owner") {
      if (!username.trim()) return "Username is required.";
      if (!email.trim()) return "Email is required.";
      if (password.length < 8) return "Password must be at least 8 characters.";
      if (password !== confirmPassword) return "Passwords do not match.";
    }
    return null;
  }, [
    step,
    name,
    contactEmail,
    businessTypeCode,
    slug,
    slugStatus,
    planCode,
    username,
    email,
    password,
    confirmPassword,
  ]);

  const goNext = () => {
    const err = validateStep();
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    if (stepIndex < STEPS.length - 1) {
      setStep(STEPS[stepIndex + 1].id);
    }
  };

  const goBack = () => {
    setError(null);
    if (stepIndex > 0) setStep(STEPS[stepIndex - 1].id);
  };

  const handleProvision = async () => {
    const err = validateStep();
    if (err) {
      setError(err);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await onboardingApi.provision({
        name: name.trim(),
        slug: slug.trim(),
        business_type_code: businessTypeCode,
        plan_code: planCode,
        contact_email: contactEmail.trim(),
        contact_phone: contactPhone.trim(),
        branch_name: branchName.trim() || "Main Branch",
        owner: {
          username: username.trim(),
          email: email.trim(),
          password,
          phone: contactPhone.trim(),
        },
      });

      if (res.data.access && res.data.refresh && res.data.user) {
        localStorage.setItem("access_token", res.data.access);
        localStorage.setItem("refresh_token", res.data.refresh);
        clearBrandingCache();
        useAuthStore.setState({
          user: res.data.user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
        navigate("/dashboard", { replace: true });
        return;
      }
      navigate("/login", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provisioning failed.");
    } finally {
      setSaving(false);
    }
  };

  if (loadingCatalog) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <LoginBrandingPanel
        productName="MDA Retail"
        productTagline="Self-serve onboarding"
        headline="Launch your shop in minutes"
        description="Pick your business type, claim a subdomain, choose a plan, and start selling."
      />

      <div className="flex flex-col justify-center px-6 py-10 sm:px-12">
        <div className="mx-auto w-full max-w-lg">
          <div className="mb-8">
            <p className="text-sm font-medium text-primary">Create your shop</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">Onboarding</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </div>

          <ol className="mb-8 flex flex-wrap gap-2">
            {STEPS.map((s, idx) => {
              const Icon = s.icon;
              const active = s.id === step;
              const done = idx < stepIndex;
              return (
                <li
                  key={s.id}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                    active && "bg-primary/10 text-primary",
                    done && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
                    !active && !done && "bg-muted text-muted-foreground"
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                  {s.label}
                </li>
              );
            })}
          </ol>

          <motion.div
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {step === "business" && (
              <>
                <FormField label="Business name" required>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Fresh Mart"
                    autoFocus
                  />
                </FormField>
                <FormField label="Contact email" required>
                  <Input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => {
                      setContactEmail(e.target.value);
                      if (!email) setEmail(e.target.value);
                    }}
                    placeholder="owner@shop.com"
                  />
                </FormField>
                <FormField label="Contact phone">
                  <Input
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="61xxxxxxx"
                  />
                </FormField>
              </>
            )}

            {step === "type" && (
              <div className="grid gap-2 sm:grid-cols-2">
                {businessTypes.map((bt) => (
                  <button
                    key={bt.code}
                    type="button"
                    onClick={() => setBusinessTypeCode(bt.code)}
                    className={cn(
                      "rounded-xl border px-3 py-3 text-left transition-colors",
                      businessTypeCode === bt.code
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-muted/40"
                    )}
                  >
                    <p className="text-sm font-medium">{bt.name}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {(bt.default_modules || []).join(" · ") || "Core modules"}
                    </p>
                  </button>
                ))}
              </div>
            )}

            {step === "subdomain" && (
              <>
                <FormField
                  label="Subdomain"
                  required
                  hint={slugStatus?.hostname || `Will be ${slug || "your-shop"}.${baseDomain}`}
                  error={slugStatus && !slugStatus.available ? slugStatus.reason : undefined}
                >
                  <div className="flex items-center gap-2">
                    <Input
                      value={slug}
                      onChange={(e) => {
                        setSlugTouched(true);
                        setSlug(slugify(e.target.value));
                      }}
                      placeholder="freshmart"
                      className="font-mono"
                    />
                    <span className="shrink-0 text-xs text-muted-foreground">.{baseDomain}</span>
                  </div>
                </FormField>
                {slugStatus?.available && (
                  <p className="text-xs text-emerald-600">Subdomain is available.</p>
                )}
              </>
            )}

            {step === "plan" && (
              <div className="space-y-2">
                {plans.map((plan) => (
                  <button
                    key={plan.code}
                    type="button"
                    onClick={() => setPlanCode(plan.code)}
                    className={cn(
                      "flex w-full items-start justify-between rounded-xl border px-4 py-3 text-left transition-colors",
                      planCode === plan.code
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-muted/40"
                    )}
                  >
                    <div>
                      <p className="text-sm font-semibold">{plan.name}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {plan.max_users} users · {plan.max_branches} branches
                        {plan.modules?.length ? ` · ${plan.modules.length} modules` : ""}
                      </p>
                    </div>
                    <p className="text-sm font-medium">${plan.monthly_price}/mo</p>
                  </button>
                ))}
              </div>
            )}

            {step === "owner" && (
              <>
                <FormField label="First branch name">
                  <Input value={branchName} onChange={(e) => setBranchName(e.target.value)} />
                </FormField>
                <FormField label="Owner username" required>
                  <Input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </FormField>
                <FormField label="Owner email" required>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                  />
                </FormField>
                <FormField label="Password" required hint="At least 8 characters">
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </FormField>
                <FormField label="Confirm password" required>
                  <Input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </FormField>
              </>
            )}
          </motion.div>

          {error && (
            <p className="mt-4 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <div className="mt-6 flex items-center justify-between gap-2">
            <Button type="button" variant="secondary" onClick={goBack} disabled={stepIndex === 0 || saving}>
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            {step === "owner" ? (
              <Button type="button" onClick={() => void handleProvision()} disabled={saving}>
                {saving ? "Provisioning…" : "Create shop"}
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="button" onClick={goNext}>
                Continue
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

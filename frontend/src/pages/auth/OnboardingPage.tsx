import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  BedDouble,
  Building2,
  Check,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Coffee,
  Dumbbell,
  FlaskConical,
  Globe,
  GraduationCap,
  HardHat,
  Home,
  LayoutGrid,
  Layers,
  Package,
  PackageCheck,
  Pill,
  Plane,
  Search,
  ShoppingBag,
  Store,
  Truck,
  User,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField } from "@/components/forms/FormField";
import { LoginBrandingPanel } from "@/components/auth/LoginBrandingPanel";
import { SafariLogo } from "@/components/brand/SafariLogo";
import {
  onboardingApi,
  type OnboardingBusinessType,
  type OnboardingModule,
  type OnboardingPlan,
} from "@/services/api/onboarding";
import { useAuthStore } from "@/store/authStore";
import { postLoginPath } from "@/navigation/postLogin";
import { cn } from "@/utils/cn";
import { isTauri } from "@/utils/platform";
import { ApiClientError } from "@/services/api/http";
import { WorkspaceUrlField } from "@/pages/auth/WorkspaceUrlField";
import {
  WORKSPACE_CHECK_DEBOUNCE_MS,
  canContinueWorkspaceUrl,
  conflictSuggestions,
  deriveWorkspaceUiState,
  nextSlugFromCompanyName,
  normalizeWorkspaceSlug,
  workspaceHttpsUrl,
  type WorkspaceAvailability,
} from "@/pages/auth/workspaceUrl";
import {
  PROVISIONING_STAGES,
  summarizeProvisioningStages,
  type ProvisioningStageSummary,
} from "@/pages/auth/provisioningStages";

const STEPS = [
  { id: "business", label: "Company", icon: Building2 },
  { id: "type", label: "Industry", icon: Store },
  { id: "modules", label: "Modules", icon: LayoutGrid },
  { id: "plan", label: "Plan", icon: Layers },
  { id: "subdomain", label: "Workspace URL", icon: Globe },
  { id: "owner", label: "Owner & branch", icon: User },
  { id: "review", label: "Review", icon: ClipboardCheck },
] as const;

type StepId = (typeof STEPS)[number]["id"];

const INDUSTRY_ICONS: Record<string, LucideIcon> = {
  retail: ShoppingBag,
  supermarket: Store,
  pharmacy: Pill,
  cafeteria: Coffee,
  restaurant: UtensilsCrossed,
  electronics: Package,
  gym: Dumbbell,
  hotel: BedDouble,
  property: Home,
  school: GraduationCap,
  travel: Plane,
  project: HardHat,
  futsal: FlaskConical,
};

const MODULE_ICONS: Record<string, LucideIcon> = {
  pos: Store,
  inventory: Package,
  sales: ShoppingBag,
  purchases: PackageCheck,
  restaurant: UtensilsCrossed,
  pharmacy: Pill,
  gym: Dumbbell,
  hotel: BedDouble,
  finance: Layers,
  customers: User,
  suppliers: Truck,
  property_management: Home,
  housing_rental: Home,
  office_rental: Building2,
  school: GraduationCap,
  travel: Plane,
  projects: HardHat,
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [step, setStep] = useState<StepId>("business");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [businessTypes, setBusinessTypes] = useState<OnboardingBusinessType[]>([]);
  const [plans, setPlans] = useState<OnboardingPlan[]>([]);
  const [modules, setModules] = useState<OnboardingModule[]>([]);
  const [selectedModules, setSelectedModules] = useState<string[]>([]);
  const [baseDomain, setBaseDomain] = useState("erp.safaritechno.com");
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [businessTypeCode, setBusinessTypeCode] = useState("");
  const [planCode, setPlanCode] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [slugChecking, setSlugChecking] = useState(false);
  const [slugNetworkError, setSlugNetworkError] = useState(false);
  const [slugStatus, setSlugStatus] = useState<WorkspaceAvailability | null>(null);
  const [createdWorkspace, setCreatedWorkspace] = useState<{
    name: string;
    url: string;
    loginUrl: string;
    tlsReady: boolean;
    stages: ProvisioningStageSummary[];
  } | null>(null);
  const [branchName, setBranchName] = useState("Main Branch");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreementsAccepted, setAgreementsAccepted] = useState(false);
  const [idempotencyKey] = useState(() => crypto.randomUUID());
  const [moduleQuery, setModuleQuery] = useState("");
  const [moduleFilter, setModuleFilter] = useState<"all" | "recommended" | "selected">("all");

  const stepIndex = STEPS.findIndex((item) => item.id === step);
  const selectedType = businessTypes.find((item) => item.code === businessTypeCode);

  /** Plans that actually expose modules (excludes orphan/custom empty plans). */
  const selectablePlans = useMemo(
    () =>
      [...plans]
        .filter((p) => (p.modules?.length || 0) > 0)
        .sort((a, b) => a.monthly_price - b.monthly_price),
    [plans]
  );

  const selectedPlan =
    selectablePlans.find((item) => item.code === planCode) || selectablePlans[0];

  const moduleByCode = useMemo(() => {
    const map = new Map<string, OnboardingModule>();
    modules.forEach((m) => map.set(m.code, m));
    return map;
  }, [modules]);

  /** Industry defaults — not limited by plan so users can always multi-select. */
  const recommendedSet = useMemo(
    () => new Set(selectedType?.default_modules || []),
    [selectedType]
  );

  const resolveModuleName = (code: string) => moduleByCode.get(code)?.name || code.replace(/_/g, " ");

  const cheapestPlanCovering = (codes: string[]): OnboardingPlan | null => {
    if (!selectablePlans.length) return null;
    const needed = codes.filter(Boolean);
    if (!needed.length) return selectablePlans[0];
    const covering = selectablePlans.filter((p) =>
      needed.every((code) => p.modules.includes(code))
    );
    return covering[0] || selectablePlans[selectablePlans.length - 1] || null;
  };

  const syncPlanForModules = (codes: string[]) => {
    const cover = cheapestPlanCovering(codes);
    if (cover && cover.code !== planCode) setPlanCode(cover.code);
  };

  useEffect(() => {
    if (isAuthenticated) navigate(postLoginPath(useAuthStore.getState().user), { replace: true });
    else if (isTauri()) navigate("/connection", { replace: true });
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    onboardingApi
      .catalog()
      .then(({ data }) => {
        const nextTypes = data.business_types || [];
        const nextPlans = (data.plans || [])
          .filter((p) => (p.modules?.length || 0) > 0)
          .sort((a, b) => a.monthly_price - b.monthly_price);
        const nextModules = data.modules || [];
        setBusinessTypes(nextTypes);
        setPlans(data.plans || []);
        setModules(nextModules);
        setBaseDomain(data.base_domain || "erp.safaritechno.com");
        const type = nextTypes[0];
        const defaults = type?.default_modules?.length
          ? [...type.default_modules]
          : nextModules.slice(0, 3).map((m) => m.code);
        setSelectedModules(defaults);
        if (type) setBusinessTypeCode(type.code);
        const cover =
          nextPlans.find((p) => defaults.every((c) => p.modules.includes(c))) || nextPlans[0];
        if (cover) setPlanCode(cover.code);
      })
      .catch(() => setError("We couldn't load setup options. Please refresh and try again."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!slugTouched) {
      setSlug(nextSlugFromCompanyName({ companyName: name, slugTouched, currentSlug: slug }));
    }
  }, [name, slugTouched]);

  useEffect(() => {
    if (step !== "subdomain" || !slug) {
      setSlugStatus(null);
      setSlugChecking(false);
      setSlugNetworkError(false);
      return;
    }
    let cancelled = false;
    setSlugChecking(true);
    setSlugNetworkError(false);
    const timer = window.setTimeout(() => {
      onboardingApi
        .checkSlug(slug)
        .then(({ data }) => {
          if (cancelled) return;
          setSlugStatus({
            requested: data.requested,
            normalized: data.normalized ?? data.slug ?? slug,
            available: data.available,
            reason: data.reason,
            hostname: data.hostname,
            suggestions: data.suggestions || [],
            slug: data.slug,
          });
        })
        .catch(() => {
          if (cancelled) return;
          setSlugNetworkError(true);
          setSlugStatus(null);
        })
        .finally(() => {
          if (!cancelled) setSlugChecking(false);
        });
    }, WORKSPACE_CHECK_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [slug, step]);

  // Keep plan aligned with selected modules whenever the set changes.
  useEffect(() => {
    if (!selectablePlans.length || !selectedModules.length) return;
    const cover = cheapestPlanCovering(selectedModules);
    if (cover && cover.code !== planCode) setPlanCode(cover.code);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModules.join("|"), selectablePlans.map((p) => p.code).join("|")]);

  const chooseType = (type: OnboardingBusinessType) => {
    setBusinessTypeCode(type.code);
    const next =
      type.default_modules?.length > 0
        ? [...type.default_modules]
        : modules.slice(0, 3).map((m) => m.code);
    setSelectedModules(next);
    syncPlanForModules(next);
    setError(null);
  };

  const toggleModule = (module: OnboardingModule) => {
    if (selectedModules.includes(module.code)) {
      const requiredBy = modules.filter(
        (item) =>
          selectedModules.includes(item.code) &&
          item.dependencies.includes(module.code) &&
          item.code !== module.code
      );
      if (requiredBy.length) {
        setError(
          `${module.name} is required by ${requiredBy.map((m) => m.name).join(", ")}.`
        );
        return;
      }
      if (selectedModules.length <= 1) {
        setError("Keep at least one module selected for your workspace.");
        return;
      }
      const next = selectedModules.filter((code) => code !== module.code);
      setSelectedModules(next);
      syncPlanForModules(next);
    } else {
      const withDeps = Array.from(new Set([module.code, ...module.dependencies]));
      const next = Array.from(new Set([...selectedModules, ...withDeps]));
      setSelectedModules(next);
      syncPlanForModules(next);
    }
    setError(null);
  };

  const applyRecommended = () => {
    const next = Array.from(recommendedSet);
    if (!next.length) return;
    setSelectedModules(next);
    syncPlanForModules(next);
    setError(null);
  };

  const selectAllModules = () => {
    const next = modules.map((m) => m.code);
    setSelectedModules(next);
    syncPlanForModules(next);
    setError(null);
  };

  const visibleModules = useMemo(() => {
    const q = moduleQuery.trim().toLowerCase();
    return modules
      .filter((m) => {
        if (moduleFilter === "recommended") return recommendedSet.has(m.code);
        if (moduleFilter === "selected") return selectedModules.includes(m.code);
        return true;
      })
      .filter((m) => {
        if (!q) return true;
        return (
          m.name.toLowerCase().includes(q) ||
          m.code.toLowerCase().includes(q) ||
          m.category.toLowerCase().includes(q) ||
          (m.description || "").toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        const rank = (m: OnboardingModule) => {
          if (recommendedSet.has(m.code)) return 0;
          if (selectedModules.includes(m.code)) return 1;
          return 2;
        };
        const d = rank(a) - rank(b);
        if (d !== 0) return d;
        return a.name.localeCompare(b.name);
      });
  }, [modules, moduleQuery, moduleFilter, recommendedSet, selectedModules]);

  const modulesByCategory = useMemo(() => {
    const groups = new Map<string, OnboardingModule[]>();
    visibleModules.forEach((m) => {
      const key = m.category || "General";
      const list = groups.get(key) || [];
      list.push(m);
      groups.set(key, list);
    });
    return Array.from(groups.entries());
  }, [visibleModules]);

  const fieldError = (key: string) => fieldErrors[key] || undefined;

  const clearFieldError = (key: string) => {
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  };

  const workspaceUrlState = deriveWorkspaceUiState({
    slug,
    checking: slugChecking,
    status: slugStatus,
    networkError: slugNetworkError,
  });

  const applyWorkspaceSlug = (value: string) => {
    clearFieldError("subdomain");
    setSlugTouched(true);
    setSlug(normalizeWorkspaceSlug(value));
  };

  const validate = () => {
    if (step === "business" && (!name.trim() || !contactEmail.trim()))
      return "Business name and contact email are required.";
    if (step === "type" && !businessTypeCode) return "Choose your industry.";
    if (step === "modules" && !selectedModules.length) return "Choose at least one module.";
    if (step === "plan") {
      if (!selectedPlan) return "Choose a plan.";
      const missing = selectedModules.filter((code) => !selectedPlan.modules.includes(code));
      if (missing.length) {
        return `${selectedPlan.name} doesn't include ${missing.map(resolveModuleName).join(", ")}.`;
      }
    }
    if (step === "subdomain" && !canContinueWorkspaceUrl(workspaceUrlState)) {
      if (workspaceUrlState === "taken") return "This workspace URL is already taken.";
      if (workspaceUrlState === "reserved") return "This workspace URL is reserved.";
      if (workspaceUrlState === "checking") return "Wait until the workspace URL is confirmed.";
      if (workspaceUrlState === "error") return "We couldn't check this URL. Try again in a moment.";
      return "Choose an available workspace URL.";
    }
    if (step === "owner") {
      if (!username.trim() || !email.trim()) return "Owner username and email are required.";
      if (password.length < 8) return "Password must contain at least 8 characters.";
      if (password !== confirmPassword) return "Passwords do not match.";
      if (!agreementsAccepted) return "Accept the Terms and Privacy Policy to continue.";
    }
    return null;
  };

  const next = () => {
    const message = validate();
    if (message) return setError(message);
    setError(null);
    setFieldErrors({});
    setStep(STEPS[stepIndex + 1].id);
  };

  const back = () => {
    setError(null);
    setFieldErrors({});
    if (stepIndex > 0) setStep(STEPS[stepIndex - 1].id);
  };

  const goTo = (target: StepId) => {
    setError(null);
    setFieldErrors({});
    setStep(target);
  };

  const submit = async () => {
    const message = validate();
    if (message) return setError(message);
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      const response = await onboardingApi.register(
        {
          name: name.trim(),
          slug,
          business_type_code: businessTypeCode,
          plan_code: selectedPlan?.code || planCode,
          modules: selectedModules,
          contact_email: contactEmail.trim(),
          contact_phone: contactPhone.trim(),
          branch_name: branchName.trim() || "Main Branch",
          owner: {
            username: username.trim(),
            email: email.trim(),
            password,
            phone: contactPhone.trim(),
          },
          agreements: { terms_accepted: true, privacy_accepted: true },
        },
        idempotencyKey
      );
      if (response.data.status === "ready") {
        const workspaceUrl = response.data.workspace_url.replace(/\/$/, "");
        setCreatedWorkspace({
          name: name.trim(),
          url: workspaceUrl,
          loginUrl: `${workspaceUrl}/login?welcome=1`,
          tlsReady: response.data.tls_ready !== false,
          stages: summarizeProvisioningStages(response.data.stages),
        });
        return;
      } else {
        setError("Check your email to verify your address. You can safely leave this page.");
      }
    } catch (reason) {
      if (reason instanceof ApiClientError) {
        const mapped: Record<string, string> = {};
        for (const [key, messages] of Object.entries(reason.fieldErrors)) {
          if (messages[0]) mapped[key] = messages[0];
        }
        setFieldErrors(mapped);
        setError(reason.message || "Please correct the highlighted fields.");
        if (reason.status === 409 || reason.code === "SUBDOMAIN_TAKEN") {
          const suggestions = conflictSuggestions(reason.details);
          setSlugStatus({
            normalized: slug,
            available: false,
            hostname: null,
            reason: "taken",
            suggestions,
          });
          setStep("subdomain");
        } else if (mapped["owner.username"] || mapped["owner.email"] || mapped["owner.password"]) {
          setStep("owner");
        } else if (mapped.subdomain) {
          setStep("subdomain");
        } else if (mapped.modules) {
          setStep("modules");
        } else if (mapped.plan_code) {
          setStep("plan");
        }
      } else {
        setError(
          reason instanceof Error
            ? reason.message
            : "We couldn't create your workspace. Please try again."
        );
      }
    } finally {
      setSaving(false);
    }
  };

  if (createdWorkspace) {
    return (
      <div className="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <LoginBrandingPanel
          headline="Your workspace is ready"
          description="Open the address below and sign in with the owner account you just created. The address stays the same if you rename the company."
        />
        <main className="flex min-w-0 flex-col bg-background">
          <div className="safari-brand-rule h-1 w-full lg:hidden" aria-hidden />
          <div className="flex flex-1 flex-col justify-center px-4 py-10 sm:px-8 xl:px-14">
            <div className="mx-auto w-full max-w-lg">
              <SafariLogo size="sm" className="mb-8 lg:hidden" />
              <section
                aria-labelledby="workspace-created-title"
                className="rounded-2xl border border-border bg-brand-surface p-6 shadow-[0_1px_2px_hsl(var(--foreground)/0.04),0_12px_32px_-12px_hsl(var(--brand-primary)/0.18)] sm:p-8"
              >
                <p className="inline-flex items-center gap-2 rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-soft-foreground">
                  <CheckCircle2 className="h-4 w-4 text-success" aria-hidden />
                  Workspace created successfully
                </p>
                <h1
                  id="workspace-created-title"
                  className="mt-4 break-words text-2xl font-bold tracking-tight text-foreground"
                >
                  {createdWorkspace.name}
                </h1>

                <div className="mt-6 rounded-xl border border-border bg-muted/40 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Workspace URL
                  </p>
                  <a
                    href={createdWorkspace.loginUrl}
                    className="mt-1 block break-all rounded font-mono text-sm font-semibold text-brand-deep hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {createdWorkspace.url}
                  </a>
                </div>

                {createdWorkspace.stages.length ? (
                  <ul className="mt-6 grid gap-2 sm:grid-cols-2" aria-label="Completed setup steps">
                    {createdWorkspace.stages.map((stage) => (
                      <StageRow key={stage.id} label={stage.label} status={stage.status} />
                    ))}
                  </ul>
                ) : null}

                {!createdWorkspace.tlsReady ? (
                  <p className="mt-6 rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-foreground">
                    The secure certificate for this address is still being issued. If the workspace
                    doesn&apos;t open yet, wait a minute and try again.
                  </p>
                ) : null}

                <Button
                  type="button"
                  size="lg"
                  className="mt-6 w-full"
                  onClick={() => window.location.assign(createdWorkspace.loginUrl)}
                >
                  Open Workspace <ArrowRight className="h-4 w-4" aria-hidden />
                </Button>
              </section>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background" role="status">
        <SafariLogo size="md" />
        <div
          className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent motion-reduce:animate-none"
          aria-hidden
        />
        <span className="sr-only">Loading setup options…</span>
      </div>
    );
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <LoginBrandingPanel
        headline="Build the workspace your business deserves"
        description="Choose your industry, combine the modules you need, and launch a secure workspace on its own address in minutes."
      />
      <main className="flex min-w-0 flex-col bg-background">
        <div className="safari-brand-rule h-1 w-full lg:hidden" aria-hidden />
        <div className="flex flex-1 flex-col justify-center px-4 py-8 sm:px-8 xl:px-14">
        <div className="mx-auto w-full max-w-3xl">
          <SafariLogo size="sm" className="mb-6 lg:hidden" />
          <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Create your workspace
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Already registered?{" "}
                <Link
                  to="/login"
                  className="rounded font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Sign in
                </Link>
              </p>
            </div>
            <p className="text-sm text-muted-foreground" aria-live="polite">
              Step <strong className="text-foreground">{stepIndex + 1}</strong> of {STEPS.length}
              <span className="sm:hidden"> · {STEPS[stepIndex].label}</span>
            </p>
          </header>

          <div
            className="mb-5 h-1.5 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Setup progress"
            aria-valuemin={1}
            aria-valuemax={STEPS.length}
            aria-valuenow={stepIndex + 1}
          >
            <div
              className="h-full rounded-full bg-brand-primary transition-all duration-500 motion-reduce:transition-none"
              style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
            />
          </div>

          <ol aria-label="Setup steps" className="mb-6 hidden grid-cols-7 gap-2 sm:grid">
            {STEPS.map((item, index) => {
              const Icon = item.icon;
              const active = item.id === step;
              const done = index < stepIndex;
              return (
                <li
                  key={item.id}
                  aria-current={active ? "step" : undefined}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-xl border px-1 py-2 text-center text-[10px] font-semibold leading-tight transition-colors",
                    active && "border-brand-primary bg-brand-soft text-brand-soft-foreground",
                    done && "border-border bg-brand-surface text-brand-soft-foreground",
                    !active && !done && "border-transparent bg-muted text-muted-foreground"
                  )}
                >
                  {done ? <Check className="h-4 w-4" aria-hidden /> : <Icon className="h-4 w-4" aria-hidden />}
                  {item.label}
                  {done ? <span className="sr-only"> (completed)</span> : null}
                </li>
              );
            })}
          </ol>

          {saving ? (
            <ProvisioningPanel
              name={name.trim()}
              hostname={slug ? `${slug}.${baseDomain}` : baseDomain}
            />
          ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
              className="min-h-[420px] rounded-2xl border border-border bg-brand-surface p-5 shadow-[0_1px_2px_hsl(var(--foreground)/0.04),0_12px_32px_-12px_hsl(var(--brand-primary)/0.16)] sm:p-7"
            >
              {step === "business" && (
                <Step
                  title="Tell us about your business"
                  subtitle="We'll tailor your workspace around these details."
                >
                  <FormField label="Business or trading name" htmlFor="onb-company-name" required>
                    <Input
                      id="onb-company-name"
                      autoComplete="organization"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Fresh Market"
                      autoFocus
                    />
                  </FormField>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField label="Contact email" htmlFor="onb-contact-email" required>
                      <Input
                        id="onb-contact-email"
                        autoComplete="email"
                        type="email"
                        value={contactEmail}
                        onChange={(e) => {
                          setContactEmail(e.target.value);
                          if (!email) setEmail(e.target.value);
                        }}
                        placeholder="owner@company.com"
                      />
                    </FormField>
                    <FormField label="Phone number" htmlFor="onb-contact-phone">
                      <Input
                        id="onb-contact-phone"
                        type="tel"
                        autoComplete="tel"
                        value={contactPhone}
                        onChange={(e) => setContactPhone(e.target.value)}
                        placeholder="Your business number"
                      />
                    </FormField>
                  </div>
                </Step>
              )}

              {step === "type" && (
                <Step
                  title="What kind of business do you run?"
                  subtitle="Pick an industry — we'll recommend modules. You can add more on the next steps."
                >
                  <div className="grid max-h-[460px] gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
                    {businessTypes.map((type) => {
                      const Icon = INDUSTRY_ICONS[type.code] || Store;
                      const selected = businessTypeCode === type.code;
                      const modNames = (type.default_modules || []).map(resolveModuleName);
                      return (
                        <button
                          key={type.code}
                          type="button"
                          onClick={() => chooseType(type)}
                          aria-pressed={selected}
                          className={cn(
                            "group relative overflow-hidden rounded-2xl border p-4 text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                            selected
                              ? "border-brand-primary bg-brand-soft ring-1 ring-brand-primary/30"
                              : "border-border bg-brand-surface hover:-translate-y-0.5 hover:border-brand-primary/50 hover:shadow-md motion-reduce:hover:translate-y-0"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <span
                              className={cn(
                                "grid h-11 w-11 shrink-0 place-items-center rounded-xl transition-colors",
                                selected
                                  ? "bg-brand-primary text-brand-primary-foreground"
                                  : "bg-muted text-muted-foreground group-hover:bg-brand-soft group-hover:text-brand-soft-foreground"
                              )}
                            >
                              <Icon className="h-5 w-5" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center justify-between gap-2">
                                <strong className="text-[15px] tracking-tight">{type.name}</strong>
                                {selected ? (
                                  <CheckCircle2 className="h-5 w-5 shrink-0 text-brand-primary" aria-hidden />
                                ) : null}
                              </span>
                              <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                                {type.description ||
                                  `${modNames.length} recommended modules for a fast start`}
                              </span>
                            </span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {modNames.length ? (
                              modNames.slice(0, 5).map((label) => (
                                <span
                                  key={label}
                                  className={cn(
                                    "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                                    selected
                                      ? "bg-brand-surface text-brand-soft-foreground"
                                      : "bg-muted text-muted-foreground"
                                  )}
                                >
                                  {label}
                                </span>
                              ))
                            ) : (
                              <span className="text-[11px] text-muted-foreground">
                                Custom module mix
                              </span>
                            )}
                            {modNames.length > 5 ? (
                              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                                +{modNames.length - 5} more
                              </span>
                            ) : null}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </Step>
              )}

              {step === "modules" && (
                <Step
                  title="Build your perfect workspace"
                  subtitle={`Recommended for ${selectedType?.name || "your industry"} — tap any modules you need. You can select as many as you like.`}
                >
                  <div className="mb-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-brand-primary/20 bg-brand-soft px-4 py-3 text-sm text-brand-soft-foreground">
                      <span className="flex items-center gap-2">
                        <PackageCheck className="h-4 w-4" aria-hidden />
                        <strong>{selectedModules.length}</strong> selected
                        <span className="text-muted-foreground">
                          · {recommendedSet.size} recommended
                          {selectedPlan ? ` · fits ${selectedPlan.name}` : ""}
                        </span>
                      </span>
                      <span className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={applyRecommended}
                          className="rounded-lg px-2 py-1 text-xs font-semibold hover:bg-brand-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          Use recommended
                        </button>
                        <button
                          type="button"
                          onClick={selectAllModules}
                          className="rounded-lg px-2 py-1 text-xs font-semibold hover:bg-brand-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          Select all
                        </button>
                      </span>
                    </div>

                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                      <div className="relative flex-1">
                        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                        <Input
                          value={moduleQuery}
                          onChange={(e) => setModuleQuery(e.target.value)}
                          placeholder="Search modules…"
                          aria-label="Search modules"
                          className="h-11 rounded-xl pl-9"
                        />
                      </div>
                      <div className="flex rounded-xl border border-border bg-muted p-1" role="group" aria-label="Filter modules">
                        {(
                          [
                            ["all", "All"],
                            ["recommended", "Recommended"],
                            ["selected", "Selected"],
                          ] as const
                        ).map(([id, label]) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => setModuleFilter(id)}
                            aria-pressed={moduleFilter === id}
                            className={cn(
                              "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                              moduleFilter === id
                                ? "bg-brand-surface text-brand-soft-foreground shadow-sm"
                                : "text-muted-foreground hover:text-foreground"
                            )}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {selectedModules.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {selectedModules.map((code) => (
                          <button
                            key={code}
                            type="button"
                            onClick={() => {
                              const mod = moduleByCode.get(code);
                              if (mod) toggleModule(mod);
                            }}
                            aria-label={`Remove ${resolveModuleName(code)}`}
                            className="inline-flex items-center gap-1 rounded-full border border-brand-primary/25 bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand-soft-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            {resolveModuleName(code)}
                            <span aria-hidden>×</span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="max-h-[380px] space-y-5 overflow-y-auto pr-1">
                    {modulesByCategory.map(([category, rows]) => (
                      <div key={category}>
                        <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                          {category}
                        </p>
                        <div className="grid gap-3 sm:grid-cols-2">
                          {rows.map((module) => (
                            <ModuleCard
                              key={module.code}
                              module={module}
                              selected={selectedModules.includes(module.code)}
                              recommended={recommendedSet.has(module.code)}
                              onClick={() => toggleModule(module)}
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                    {!modulesByCategory.length ? (
                      <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                        No modules match your filters.
                      </p>
                    ) : null}
                  </div>
                </Step>
              )}

              {step === "plan" && (
                <Step
                  title="Choose the right foundation"
                  subtitle="We've matched a plan to your module mix. You can pick a higher plan for more capacity."
                >
                  <div className="space-y-3">
                    {selectablePlans.map((plan) => {
                      const selected = (selectedPlan?.code || planCode) === plan.code;
                      const missing = selectedModules.filter((code) => !plan.modules.includes(code));
                      const covers = missing.length === 0;
                      const suggested =
                        cheapestPlanCovering(selectedModules)?.code === plan.code;
                      return (
                        <button
                          key={plan.code}
                          type="button"
                          onClick={() => {
                            if (!covers) {
                              setError(
                                `${plan.name} doesn't include ${missing
                                  .map(resolveModuleName)
                                  .join(", ")}. Choose a higher plan or remove those modules.`
                              );
                              return;
                            }
                            setPlanCode(plan.code);
                            setError(null);
                          }}
                          aria-pressed={selected}
                          className={cn(
                            "flex w-full items-center justify-between gap-4 rounded-2xl border p-4 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                            selected
                              ? "border-brand-primary bg-brand-soft ring-1 ring-brand-primary/30"
                              : covers
                                ? "border-border bg-brand-surface hover:border-brand-primary/50 hover:shadow-md"
                                : "border-border bg-brand-surface opacity-60"
                          )}
                        >
                          <span>
                            <span className="flex flex-wrap items-center gap-2">
                              <strong className="block text-[15px]">{plan.name}</strong>
                              {suggested ? (
                                <span className="rounded-full bg-brand-primary px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-brand-primary-foreground">
                                  Best match
                                </span>
                              ) : null}
                            </span>
                            <span className="mt-1 block text-xs text-muted-foreground">
                              {plan.max_users} users · {plan.max_branches} branches ·{" "}
                              {plan.modules.length} modules
                            </span>
                            {!covers ? (
                              <span className="mt-2 block text-xs text-amber-700 dark:text-amber-300">
                                Missing: {missing.map(resolveModuleName).join(", ")}
                              </span>
                            ) : plan.description ? (
                              <span className="mt-2 block text-xs text-muted-foreground">
                                {plan.description}
                              </span>
                            ) : null}
                          </span>
                          <span className="text-right">
                            <strong className="text-lg">${plan.monthly_price}</strong>
                            <span className="block text-[10px] text-muted-foreground">per month</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </Step>
              )}

              {step === "subdomain" && (
                <Step
                  title="Claim your workspace URL"
                  subtitle="This is the address your team will use. It will not change when you rename the company."
                >
                  <WorkspaceUrlField
                    slug={slug}
                    baseDomain={baseDomain}
                    state={workspaceUrlState}
                    status={slugStatus}
                    fieldError={fieldError("subdomain")}
                    onChange={applyWorkspaceSlug}
                    onSelectSuggestion={applyWorkspaceSlug}
                  />
                </Step>
              )}

              {step === "owner" && (
                <Step
                  title="Create your owner account"
                  subtitle="These credentials control your new tenant workspace."
                >
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField label="First branch" htmlFor="onb-branch" hint="Your default branch. You can add more later.">
                      <Input id="onb-branch" value={branchName} onChange={(e) => setBranchName(e.target.value)} />
                    </FormField>
                    <FormField
                      label="Owner username"
                      htmlFor="onb-owner-username"
                      required
                      error={fieldError("owner.username")}
                    >
                      <Input
                        id="onb-owner-username"
                        value={username}
                        onChange={(e) => {
                          clearFieldError("owner.username");
                          setUsername(e.target.value);
                        }}
                        autoComplete="username"
                        aria-invalid={Boolean(fieldError("owner.username"))}
                        className={cn(
                          fieldError("owner.username") &&
                            "border-destructive focus-visible:ring-destructive"
                        )}
                      />
                    </FormField>
                    <FormField label="Owner email" htmlFor="onb-owner-email" required error={fieldError("owner.email")}>
                      <Input
                        id="onb-owner-email"
                        type="email"
                        value={email}
                        onChange={(e) => {
                          clearFieldError("owner.email");
                          setEmail(e.target.value);
                        }}
                        autoComplete="email"
                        aria-invalid={Boolean(fieldError("owner.email"))}
                        className={cn(
                          fieldError("owner.email") && "border-destructive focus-visible:ring-destructive"
                        )}
                      />
                    </FormField>
                    <div />
                    <FormField
                      label="Password"
                      htmlFor="onb-owner-password"
                      required
                      hint="At least 8 characters"
                      error={fieldError("owner.password")}
                    >
                      <Input
                        id="onb-owner-password"
                        type="password"
                        value={password}
                        onChange={(e) => {
                          clearFieldError("owner.password");
                          setPassword(e.target.value);
                        }}
                        autoComplete="new-password"
                        aria-invalid={Boolean(fieldError("owner.password"))}
                        className={cn(
                          fieldError("owner.password") &&
                            "border-destructive focus-visible:ring-destructive"
                        )}
                      />
                    </FormField>
                    <FormField label="Confirm password" htmlFor="onb-owner-password-confirm" required>
                      <Input
                        id="onb-owner-password-confirm"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        autoComplete="new-password"
                      />
                    </FormField>
                  </div>
                  <label className="mt-2 flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={agreementsAccepted}
                      onChange={(e) => setAgreementsAccepted(e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-brand-primary"
                    />
                    I agree to the Terms of Service and Privacy Policy.
                  </label>
                </Step>
              )}

              {step === "review" && (
                <Step
                  title="Review and create"
                  subtitle="Check the details below. Nothing is created until you press Create workspace."
                >
                  <dl className="divide-y divide-border rounded-2xl border border-border">
                    <ReviewRow label="Company" onEdit={() => goTo("business")}>
                      <span className="font-semibold text-foreground">{name.trim()}</span>
                      <span className="block text-muted-foreground">
                        {[contactEmail.trim(), contactPhone.trim()].filter(Boolean).join(" · ")}
                      </span>
                    </ReviewRow>
                    <ReviewRow label="Industry" onEdit={() => goTo("type")}>
                      {selectedType?.name || "—"}
                    </ReviewRow>
                    <ReviewRow label="Modules" onEdit={() => goTo("modules")}>
                      <span className="font-semibold text-foreground">{selectedModules.length} selected</span>
                      <span className="block text-muted-foreground">
                        {selectedModules.map(resolveModuleName).join(", ")}
                      </span>
                    </ReviewRow>
                    <ReviewRow label="Plan" onEdit={() => goTo("plan")}>
                      {selectedPlan ? `${selectedPlan.name} · $${selectedPlan.monthly_price}/month` : "—"}
                    </ReviewRow>
                    <ReviewRow label="Workspace URL" onEdit={() => goTo("subdomain")}>
                      <span className="break-all font-mono text-brand-deep">
                        {workspaceHttpsUrl(slug, baseDomain)}
                      </span>
                    </ReviewRow>
                    <ReviewRow label="First branch" onEdit={() => goTo("owner")}>
                      {branchName.trim() || "Main Branch"}
                    </ReviewRow>
                    <ReviewRow label="Owner" onEdit={() => goTo("owner")}>
                      <span className="font-semibold text-foreground">{username.trim()}</span>
                      <span className="block text-muted-foreground">{email.trim()}</span>
                    </ReviewRow>
                  </dl>
                </Step>
              )}
            </motion.div>
          </AnimatePresence>
          )}

          {error ? (
            <p
              role="alert"
              className="mt-4 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
            >
              {error}
            </p>
          ) : null}

          {!saving ? (
            <div className="mt-5 flex items-center justify-between gap-3">
              <Button type="button" variant="secondary" onClick={back} disabled={stepIndex === 0}>
                <ArrowLeft className="h-4 w-4" aria-hidden /> Back
              </Button>
              {step === "review" ? (
                <Button type="button" onClick={() => void submit()}>
                  Create workspace
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={next}
                  disabled={step === "subdomain" && !canContinueWorkspaceUrl(workspaceUrlState)}
                >
                  Continue <ArrowRight className="h-4 w-4" aria-hidden />
                </Button>
              )}
            </div>
          ) : null}
        </div>
        </div>
      </main>
    </div>
  );
}

function Step({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold tracking-tight">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function ModuleCard({
  module,
  selected,
  recommended,
  onClick,
}: {
  module: OnboardingModule;
  selected: boolean;
  recommended: boolean;
  onClick: () => void;
}) {
  const Icon = MODULE_ICONS[module.code] || LayoutGrid;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "relative rounded-2xl border p-4 text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        selected
          ? "border-brand-primary bg-brand-soft ring-1 ring-brand-primary/30"
          : "border-border bg-brand-surface hover:-translate-y-0.5 hover:border-brand-primary/50 hover:shadow-md motion-reduce:hover:translate-y-0"
      )}
    >
      {recommended ? (
        <span className="absolute right-3 top-3 rounded-full bg-brand-deep/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-brand-deep">
          Recommended
        </span>
      ) : null}
      <span className="flex items-start gap-3">
        <span
          className={cn(
            "grid h-10 w-10 shrink-0 place-items-center rounded-xl",
            selected ? "bg-brand-primary text-brand-primary-foreground" : "bg-muted text-muted-foreground"
          )}
        >
          <Icon className="h-5 w-5" />
        </span>
        <span className="min-w-0 flex-1 pr-10">
          <span className="flex items-center justify-between gap-2">
            <strong className="text-sm">{module.name}</strong>
            <span
              className={cn(
                "grid h-5 w-5 shrink-0 place-items-center rounded-md border",
                selected
                  ? "border-brand-primary bg-brand-primary text-brand-primary-foreground"
                  : "border-input bg-brand-surface"
              )}
            >
              {selected ? <Check className="h-3.5 w-3.5" /> : null}
            </span>
          </span>
          <span className="mt-1 block text-xs leading-5 text-muted-foreground">
            {module.description || "Enable this capability in your workspace."}
          </span>
        </span>
      </span>
      <span className="mt-3 flex flex-wrap gap-1.5">
        <Tag>{module.category || "Module"}</Tag>
        {module.supports_mobile ? <Tag blue>Mobile</Tag> : null}
        {module.supports_pos ? <Tag>POS</Tag> : null}
      </span>
    </button>
  );
}

function Tag({ children, blue = false }: { children: React.ReactNode; blue?: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide",
        blue
          ? "bg-brand-deep/10 text-brand-deep"
          : "bg-muted text-muted-foreground"
      )}
    >
      {children}
    </span>
  );
}

function ReviewRow({
  label,
  onEdit,
  children,
}: {
  label: string;
  onEdit: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-4 py-3 text-sm">
      <div className="min-w-0 flex-1 sm:flex sm:gap-4">
        <dt className="shrink-0 text-xs font-semibold uppercase tracking-wide text-muted-foreground sm:w-32 sm:pt-0.5">
          {label}
        </dt>
        <dd className="mt-1 min-w-0 break-words sm:mt-0">{children}</dd>
      </div>
      <button
        type="button"
        onClick={onEdit}
        aria-label={`Edit ${label.toLowerCase()}`}
        className="shrink-0 rounded-md px-2 py-1 text-xs font-semibold text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        Edit
      </button>
    </div>
  );
}

/**
 * Shown while the registration request is in flight. Provisioning runs inside
 * that request, so there is no per-stage progress to report yet: the list says
 * what the server will do, and completion is shown only from its response.
 */
function ProvisioningPanel({ name, hostname }: { name: string; hostname: string }) {
  return (
    <section
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="rounded-2xl border border-border bg-brand-surface p-6 shadow-[0_1px_2px_hsl(var(--foreground)/0.04),0_12px_32px_-12px_hsl(var(--brand-primary)/0.16)] sm:p-8"
    >
      <div className="flex items-start gap-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-brand-soft">
          <span
            className="h-6 w-6 animate-spin rounded-full border-2 border-brand-primary border-t-transparent motion-reduce:animate-none"
            aria-hidden
          />
        </span>
        <div className="min-w-0">
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Creating {name || "your workspace"}
          </h2>
          <p className="mt-1 break-words text-sm text-muted-foreground">
            Setting up <span className="font-mono text-brand-deep">{hostname}</span>. This usually
            takes a few seconds — please keep this page open.
          </p>
        </div>
      </div>

      <p className="mt-8 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        What we&apos;re setting up
      </p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {PROVISIONING_STAGES.map((stage) => (
          <StageRow key={stage.id} label={stage.label} status="pending" />
        ))}
      </ul>
      <p className="mt-6 text-xs text-muted-foreground">
        Each step is confirmed by the server when your workspace is ready.
      </p>
    </section>
  );
}

function StageRow({ label, status }: { label: string; status: string }) {
  const done = status === "succeeded";
  const failed = status === "failed";
  return (
    <li className="flex items-center gap-2.5 rounded-xl border border-border bg-muted/30 px-3 py-2 text-sm">
      {done ? (
        <CheckCircle2 className="h-4 w-4 shrink-0 text-success" aria-hidden />
      ) : (
        <Circle
          className={cn("h-4 w-4 shrink-0", failed ? "text-destructive" : "text-muted-foreground/60")}
          aria-hidden
        />
      )}
      <span className={done ? "text-foreground" : "text-muted-foreground"}>{label}</span>
      <span className="sr-only">{done ? " — done" : failed ? " — failed" : " — pending"}</span>
    </li>
  );
}

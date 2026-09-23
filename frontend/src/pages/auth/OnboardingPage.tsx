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
  Sparkles,
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
  type WorkspaceAvailability,
} from "@/pages/auth/workspaceUrl";

const STEPS = [
  { id: "business", label: "Business", icon: Building2 },
  { id: "type", label: "Industry", icon: Store },
  { id: "modules", label: "Modules", icon: LayoutGrid },
  { id: "plan", label: "Plan", icon: Layers },
  { id: "subdomain", label: "Workspace", icon: Globe },
  { id: "owner", label: "Account", icon: User },
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
      <div className="grid min-h-dvh bg-slate-50 lg:grid-cols-[.86fr_1.14fr] dark:bg-slate-950">
        <LoginBrandingPanel
          productName="Safari ERP"
          productTagline="Your business, intelligently connected"
          headline="Your workspace is ready"
          description="Open the address you approved. The hostname never changes unless you start a dedicated domain-change workflow."
        />
        <section className="relative flex flex-col justify-center px-5 py-10 sm:px-10">
          <div className="mx-auto w-full max-w-lg rounded-[1.75rem] border border-slate-200/80 bg-white p-8 shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4" /> Workspace created successfully
            </div>
            <h1 className="text-2xl font-bold tracking-tight">{createdWorkspace.name}</h1>
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Your workspace
            </p>
            <p className="mt-1 break-all font-mono text-sm font-semibold text-emerald-700 dark:text-emerald-300">
              {createdWorkspace.url}
            </p>
            <Button
              type="button"
              className="mt-6 w-full bg-emerald-600 hover:bg-emerald-500"
              onClick={() => window.location.assign(createdWorkspace.loginUrl)}
            >
              Open Workspace <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </section>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center bg-slate-950">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="grid min-h-dvh bg-slate-50 lg:grid-cols-[.86fr_1.14fr] dark:bg-slate-950">
      <LoginBrandingPanel
        productName="Safari ERP"
        productTagline="Your business, intelligently connected"
        headline="Build the workspace your business deserves"
        description="Choose your industry, combine the modules you need, and launch a secure tenant workspace in minutes."
      />
      <section className="relative flex flex-col justify-center overflow-hidden px-5 py-10 sm:px-10 xl:px-16">
        <div className="pointer-events-none absolute -right-24 top-0 h-80 w-80 rounded-full bg-emerald-200/40 blur-3xl dark:bg-emerald-900/10" />
        <div className="pointer-events-none absolute -left-16 bottom-10 h-56 w-56 rounded-full bg-teal-200/30 blur-3xl dark:bg-teal-900/10" />
        <div className="relative mx-auto w-full max-w-3xl">
          <header className="mb-7 flex items-start justify-between gap-5">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-emerald-200/80 bg-emerald-50/90 px-3 py-1 text-xs font-semibold text-emerald-700 shadow-sm dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                <Sparkles className="h-3.5 w-3.5" /> Guided setup
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                Create your workspace
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Already registered?{" "}
                <Link to="/login" className="font-semibold text-emerald-600 hover:underline">
                  Sign in
                </Link>
              </p>
            </div>
            <div className="hidden rounded-2xl border border-slate-200/80 bg-white/90 px-4 py-3 text-right shadow-sm backdrop-blur sm:block dark:border-slate-800 dark:bg-slate-900">
              <p className="text-xs text-muted-foreground">Setup progress</p>
              <p className="text-lg font-bold text-emerald-600">
                {Math.round(((stepIndex + 1) / STEPS.length) * 100)}%
              </p>
            </div>
          </header>

          <div className="mb-5 h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-emerald-400 to-teal-400 transition-all duration-500"
              style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
            />
          </div>

          <ol className="mb-6 grid grid-cols-3 gap-2 sm:grid-cols-6">
            {STEPS.map((item, index) => {
              const Icon = item.icon;
              const active = item.id === step;
              const done = index < stepIndex;
              return (
                <li
                  key={item.id}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-xl border px-1 py-2 text-[10px] font-semibold transition-all",
                    active &&
                      "border-emerald-400 bg-emerald-50 text-emerald-700 shadow-sm dark:bg-emerald-950",
                    done &&
                      "border-emerald-200 bg-white text-emerald-700 dark:border-emerald-900 dark:bg-slate-900",
                    !active &&
                      !done &&
                      "border-transparent bg-slate-100 text-muted-foreground dark:bg-slate-900"
                  )}
                >
                  {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                  {item.label}
                </li>
              );
            })}
          </ol>

          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
              className="min-h-[420px] rounded-[1.75rem] border border-slate-200/80 bg-white/95 p-5 shadow-xl shadow-slate-200/40 backdrop-blur sm:p-7 dark:border-slate-800 dark:bg-slate-900/95 dark:shadow-none"
            >
              {step === "business" && (
                <Step
                  title="Tell us about your business"
                  subtitle="We'll tailor your workspace around these details."
                >
                  <FormField label="Business or trading name" required>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Fresh Market"
                      autoFocus
                    />
                  </FormField>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField label="Contact email" required>
                      <Input
                        type="email"
                        value={contactEmail}
                        onChange={(e) => {
                          setContactEmail(e.target.value);
                          if (!email) setEmail(e.target.value);
                        }}
                        placeholder="owner@company.com"
                      />
                    </FormField>
                    <FormField label="Phone number">
                      <Input
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
                          className={cn(
                            "group relative overflow-hidden rounded-2xl border p-4 text-left transition-all duration-200",
                            selected
                              ? "border-emerald-400 bg-gradient-to-br from-emerald-50 via-white to-teal-50 shadow-lg shadow-emerald-100/70 dark:from-emerald-950 dark:via-slate-900 dark:to-slate-900 dark:shadow-none"
                              : "border-slate-200 bg-white hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-950"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <span
                              className={cn(
                                "grid h-11 w-11 shrink-0 place-items-center rounded-xl transition-colors",
                                selected
                                  ? "bg-emerald-500 text-white shadow-md shadow-emerald-500/30"
                                  : "bg-slate-100 text-slate-600 group-hover:bg-emerald-100 group-hover:text-emerald-700 dark:bg-slate-800"
                              )}
                            >
                              <Icon className="h-5 w-5" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center justify-between gap-2">
                                <strong className="text-[15px] tracking-tight">{type.name}</strong>
                                {selected ? (
                                  <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
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
                                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200"
                                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
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
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800">
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
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-emerald-200/70 bg-gradient-to-r from-emerald-50 to-teal-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900 dark:from-emerald-950 dark:to-slate-900 dark:text-emerald-100">
                      <span className="flex items-center gap-2">
                        <PackageCheck className="h-4 w-4" />
                        <strong>{selectedModules.length}</strong> selected
                        <span className="text-emerald-700/80 dark:text-emerald-300/80">
                          · {recommendedSet.size} recommended
                          {selectedPlan ? ` · fits ${selectedPlan.name}` : ""}
                        </span>
                      </span>
                      <span className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={applyRecommended}
                          className="rounded-lg px-2 py-1 text-xs font-semibold hover:bg-white/60 dark:hover:bg-slate-800/60"
                        >
                          Use recommended
                        </button>
                        <button
                          type="button"
                          onClick={selectAllModules}
                          className="rounded-lg px-2 py-1 text-xs font-semibold hover:bg-white/60 dark:hover:bg-slate-800/60"
                        >
                          Select all
                        </button>
                      </span>
                    </div>

                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                      <div className="relative flex-1">
                        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          value={moduleQuery}
                          onChange={(e) => setModuleQuery(e.target.value)}
                          placeholder="Search modules…"
                          className="h-11 rounded-xl pl-9"
                        />
                      </div>
                      <div className="flex rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-950">
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
                            className={cn(
                              "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                              moduleFilter === id
                                ? "bg-white text-emerald-700 shadow-sm dark:bg-slate-800 dark:text-emerald-300"
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
                            className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                          >
                            {resolveModuleName(code)}
                            <span className="text-emerald-500">×</span>
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
                      <p className="rounded-2xl border border-dashed border-slate-200 p-8 text-center text-sm text-muted-foreground dark:border-slate-700">
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
                          className={cn(
                            "flex w-full items-center justify-between rounded-2xl border p-4 text-left transition-all",
                            selected
                              ? "border-emerald-400 bg-gradient-to-r from-emerald-50 to-teal-50 shadow-md dark:from-emerald-950 dark:to-slate-900"
                              : covers
                                ? "border-slate-200 hover:shadow-md dark:border-slate-700"
                                : "border-slate-200 opacity-55 dark:border-slate-700"
                          )}
                        >
                          <span>
                            <span className="flex flex-wrap items-center gap-2">
                              <strong className="block text-[15px]">{plan.name}</strong>
                              {suggested ? (
                                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
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
                    <FormField label="First branch">
                      <Input value={branchName} onChange={(e) => setBranchName(e.target.value)} />
                    </FormField>
                    <FormField
                      label="Owner username"
                      required
                      error={fieldError("owner.username")}
                    >
                      <Input
                        value={username}
                        onChange={(e) => {
                          clearFieldError("owner.username");
                          setUsername(e.target.value);
                        }}
                        autoComplete="username"
                        aria-invalid={Boolean(fieldError("owner.username"))}
                        className={cn(
                          fieldError("owner.username") &&
                            "border-red-400 focus-visible:ring-red-400"
                        )}
                      />
                    </FormField>
                    <FormField label="Owner email" required error={fieldError("owner.email")}>
                      <Input
                        type="email"
                        value={email}
                        onChange={(e) => {
                          clearFieldError("owner.email");
                          setEmail(e.target.value);
                        }}
                        autoComplete="email"
                        aria-invalid={Boolean(fieldError("owner.email"))}
                        className={cn(
                          fieldError("owner.email") && "border-red-400 focus-visible:ring-red-400"
                        )}
                      />
                    </FormField>
                    <div />
                    <FormField
                      label="Password"
                      required
                      hint="At least 8 characters"
                      error={fieldError("owner.password")}
                    >
                      <Input
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
                            "border-red-400 focus-visible:ring-red-400"
                        )}
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
                  </div>
                  <label className="mt-2 flex items-start gap-3 rounded-xl border bg-slate-50 p-3 text-sm text-muted-foreground dark:bg-slate-950">
                    <input
                      type="checkbox"
                      checked={agreementsAccepted}
                      onChange={(e) => setAgreementsAccepted(e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-emerald-600"
                    />
                    I agree to the Terms of Service and Privacy Policy.
                  </label>
                </Step>
              )}
            </motion.div>
          </AnimatePresence>

          {error ? (
            <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
              {error}
            </p>
          ) : null}

          <div className="mt-5 flex items-center justify-between">
            <Button type="button" variant="secondary" onClick={back} disabled={stepIndex === 0 || saving}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            {step === "owner" ? (
              <Button
                type="button"
                onClick={() => void submit()}
                disabled={saving}
                className="bg-emerald-600 hover:bg-emerald-500"
              >
                {saving ? "Creating workspace…" : "Create workspace"}
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={next}
                disabled={step === "subdomain" && !canContinueWorkspaceUrl(workspaceUrlState)}
                className="bg-emerald-600 hover:bg-emerald-500"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </section>
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
        "relative rounded-2xl border p-4 text-left transition-all duration-200",
        selected
          ? "border-emerald-400 bg-gradient-to-br from-emerald-50 to-teal-50 shadow-md shadow-emerald-100 ring-1 ring-emerald-300/60 dark:from-emerald-950 dark:to-slate-900 dark:shadow-none dark:ring-emerald-700"
          : "border-slate-200 hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md dark:border-slate-700"
      )}
    >
      {recommended ? (
        <span className="absolute right-3 top-3 rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          Recommended
        </span>
      ) : null}
      <span className="flex items-start gap-3">
        <span
          className={cn(
            "grid h-10 w-10 shrink-0 place-items-center rounded-xl",
            selected ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-500 dark:bg-slate-800"
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
                  ? "border-emerald-500 bg-emerald-500 text-white"
                  : "border-slate-300 bg-white dark:border-slate-600 dark:bg-slate-900"
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
          ? "bg-blue-50 text-blue-600 dark:bg-blue-950"
          : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
      )}
    >
      {children}
    </span>
  );
}

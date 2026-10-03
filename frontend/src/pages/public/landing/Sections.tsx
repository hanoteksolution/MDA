import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowRightLeft,
  BarChart3,
  Boxes,
  Building2,
  Check,
  Dumbbell,
  FolderKanban,
  GraduationCap,
  Home,
  Landmark,
  MoreHorizontal,
  Pill,
  Plane,
  ShoppingCart,
  Store,
  Trophy,
  UtensilsCrossed,
  BedDouble,
  Users,
  type LucideIcon,
} from "lucide-react";
import { SafariLogo } from "@/components/brand/SafariLogo";
import { cn } from "@/utils/cn";
import { btnPrimary, btnSecondary, container, focusRing } from "./ui";

function SectionHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-primary">{eyebrow}</p>
        <h2 className="mt-3 max-w-2xl text-balance text-3xl font-extrabold tracking-tight text-brand-ink sm:text-4xl">{title}</h2>
      </div>
      {children ? <p className="max-w-md text-base leading-7 text-brand-ink/70">{children}</p> : null}
    </div>
  );
}

const iconBox = "grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-brand-soft text-brand-primary";

/* ---------- Industry strip ---------- */
const INDUSTRIES: { label: string; Icon: LucideIcon }[] = [
  { label: "Retail", Icon: Store },
  { label: "Restaurant", Icon: UtensilsCrossed },
  { label: "Pharmacy", Icon: Pill },
  { label: "Property", Icon: Building2 },
  { label: "Services", Icon: Users },
  { label: "and more...", Icon: MoreHorizontal },
];

export function IndustryStrip() {
  return (
    <section id="industries" className="scroll-mt-20 border-y border-brand-primary/10 bg-brand-surface">
      <div className={cn(container, "flex flex-col gap-4 py-6 lg:flex-row lg:items-center lg:gap-10")}>
        <p className="text-[11px] font-bold uppercase leading-tight tracking-[0.18em] text-brand-ink/60">
          Built for<br />real businesses
        </p>
        <ul className="flex flex-wrap gap-2.5">
          {INDUSTRIES.map(({ label, Icon }) => (
            <li key={label} className="flex items-center gap-2 rounded-full border border-brand-primary/15 bg-brand-soft/50 px-4 py-2 text-sm font-medium text-brand-ink">
              <Icon className="h-4 w-4 text-brand-primary" aria-hidden /> {label}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------- Capabilities ---------- */
const CAPABILITIES: { Icon: LucideIcon; title: string; body: string }[] = [
  { Icon: Boxes, title: "Inventory & POS", body: "Live stock, purchasing, sales and counter operations in one workspace." },
  { Icon: BarChart3, title: "Finance & reporting", body: "Ledgers, cash flow and business reporting stay connected to every transaction." },
  { Icon: Building2, title: "Built for your industry", body: "Enable only the modules your retail, restaurant, pharmacy, property or service business needs." },
];

export function Capabilities() {
  return (
    <section id="solutions" className="scroll-mt-20 py-16 lg:py-24">
      <div className={container}>
        <SectionHeader eyebrow="A platform that adapts" title="Start focused. Add capability as you grow.">
          Choose the tools you need today, and enable more as your business expands. Everything works together in one secure workspace.
        </SectionHeader>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {CAPABILITIES.map(({ Icon, title, body }) => (
            <a
              key={title}
              href="#modules"
              className={cn(
                "group flex items-start gap-4 rounded-2xl border border-brand-primary/10 bg-brand-surface p-5 shadow-sm shadow-brand-primary/5 transition hover:border-brand-primary/30 hover:shadow-lg hover:shadow-brand-primary/10 motion-safe:hover:-translate-y-0.5",
                focusRing
              )}
            >
              <span className={iconBox}><Icon className="h-6 w-6" aria-hidden /></span>
              <span className="min-w-0 flex-1">
                <span className="block text-lg font-bold text-brand-ink">{title}</span>
                <span className="mt-1.5 block text-sm leading-6 text-brand-ink/70">{body}</span>
              </span>
              <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-soft text-brand-primary transition group-hover:bg-brand-primary group-hover:text-brand-primary-foreground">
                <ArrowRight className="h-4 w-4" aria-hidden />
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Everything connected ---------- */
const FLOW: { Icon: LucideIcon; title: string; body: string }[] = [
  { Icon: Boxes, title: "Inventory", body: "Stock by branch and warehouse, purchasing and receiving." },
  { Icon: ShoppingCart, title: "Sales", body: "POS and sales that draw down the same stock." },
  { Icon: Landmark, title: "Finance", body: "Ledgers and journals tied to each transaction." },
  { Icon: BarChart3, title: "Reporting", body: "Reports built from the same connected records." },
];

export function Connected() {
  return (
    <section className="bg-brand-soft/50 py-16 lg:py-24">
      <div className={container}>
        <SectionHeader eyebrow="Everything connected" title="One record from stock room to balance sheet.">
          No re-keying between tools. Each step feeds the next, so your numbers agree everywhere.
        </SectionHeader>
        <ol className="mt-10 grid gap-4 md:grid-cols-4 md:gap-0">
          {FLOW.map(({ Icon, title, body }, i) => (
            <li key={title} className="relative md:px-2">
              <div className="h-full rounded-2xl border border-brand-primary/10 bg-brand-surface p-5 shadow-sm shadow-brand-primary/5">
                <div className="flex items-center gap-3">
                  <span className={iconBox}><Icon className="h-6 w-6" aria-hidden /></span>
                  <span className="text-xs font-bold text-brand-primary/70" aria-hidden>0{i + 1}</span>
                </div>
                <h3 className="mt-4 text-lg font-bold text-brand-ink">{title}</h3>
                <p className="mt-1.5 text-sm leading-6 text-brand-ink/70">{body}</p>
              </div>
              {i < FLOW.length - 1 && (
                <span className="absolute -right-3 top-1/2 z-10 hidden h-6 w-6 -translate-y-1/2 place-items-center rounded-full border border-brand-primary/20 bg-brand-surface text-brand-primary md:grid" aria-hidden>
                  <ArrowRight className="h-3.5 w-3.5" />
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ---------- Multi-branch ---------- */
const BRANCH_POINTS = [
  "Branch-specific stock levels",
  "A POS for each branch",
  "Sales tracked per branch",
  "Stock transfers between branches",
  "Consolidated reporting across the company",
];
const BRANCHES = ["Bakaaro", "KM4", "Hodan"];

export function MultiBranch() {
  return (
    <section className="py-16 lg:py-24">
      <div className={cn(container, "grid items-center gap-12 lg:grid-cols-2")}>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-primary">Multi-branch</p>
          <h2 className="mt-3 text-balance text-3xl font-extrabold tracking-tight text-brand-ink sm:text-4xl">Built for multi-branch operations.</h2>
          <p className="mt-4 max-w-lg text-base leading-7 text-brand-ink/70">
            Run every shop under one company. Each branch keeps its own stock and sales, while you see the whole business in one place.
          </p>
          <ul className="mt-7 space-y-3">
            {BRANCH_POINTS.map((p) => (
              <li key={p} className="flex items-start gap-3 text-sm font-medium text-brand-ink">
                <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-primary/10 text-brand-primary">
                  <Check className="h-3 w-3" aria-hidden />
                </span>
                {p}
              </li>
            ))}
          </ul>
        </div>

        <div
          className="relative overflow-hidden rounded-3xl border border-brand-primary/10 bg-gradient-to-br from-brand-soft via-brand-surface to-brand-soft p-6 sm:p-10"
          role="img"
          aria-label="Diagram: one company containing the Bakaaro, KM4 and Hodan branches, with transfers between branches"
        >
          <div className="pointer-events-none absolute -right-12 -top-12 h-48 w-48 rounded-full bg-brand-primary/15 blur-3xl" aria-hidden />
          <div className="pointer-events-none absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-brand-secondary/15 blur-3xl" aria-hidden />
          <div className="relative mx-auto flex max-w-sm flex-col items-center">
            <div className="flex items-center gap-3 rounded-2xl border border-brand-primary/20 bg-brand-surface px-5 py-3.5 shadow-lg shadow-brand-primary/10">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-primary text-brand-primary-foreground"><Building2 className="h-5 w-5" /></span>
              <span className="text-sm font-bold text-brand-ink">Your company<br /><span className="font-medium text-brand-ink/60">Consolidated view</span></span>
            </div>
            <div className="h-6 w-px bg-brand-primary/30" aria-hidden />
            <div className="h-px w-[66%] bg-brand-primary/30" aria-hidden />
            <div className="grid w-full grid-cols-3 gap-3">
              {BRANCHES.map((b) => (
                <div key={b} className="flex flex-col items-center">
                  <div className="h-5 w-px bg-brand-primary/30" aria-hidden />
                  <div className="w-full rounded-xl border border-brand-primary/15 bg-brand-surface p-3 text-center shadow-sm">
                    <span className="mx-auto grid h-9 w-9 place-items-center rounded-lg bg-brand-soft text-brand-primary"><Store className="h-4 w-4" /></span>
                    <p className="mt-2 text-sm font-bold text-brand-ink">{b}</p>
                    <p className="text-[10px] text-brand-ink/60">Stock · POS · Sales</p>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-6 flex items-center gap-2 rounded-full border border-brand-primary/15 bg-brand-surface px-3.5 py-1.5 text-xs font-semibold text-brand-soft-foreground">
              <ArrowRightLeft className="h-3.5 w-3.5 text-brand-primary" aria-hidden /> Transfers between branches
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------- Modules ---------- */
const MODULES: { Icon: LucideIcon; label: string }[] = [
  { Icon: Store, label: "Retail & POS" },
  { Icon: UtensilsCrossed, label: "Restaurant & cafeteria" },
  { Icon: Pill, label: "Pharmacy" },
  { Icon: Home, label: "Property & rentals" },
  { Icon: GraduationCap, label: "School" },
  { Icon: BedDouble, label: "Hotel" },
  { Icon: Dumbbell, label: "Gym" },
  { Icon: Trophy, label: "Futsal" },
  { Icon: FolderKanban, label: "Project management" },
  { Icon: Plane, label: "Travel agency" },
];

export function Modules() {
  return (
    <section id="modules" className="scroll-mt-20 bg-brand-soft/50 py-16 lg:py-24">
      <div className={container}>
        <SectionHeader eyebrow="Industry modules" title="Turn on only what your business needs.">
          Retail, inventory, sales, purchases and finance form the core. Add industry modules on top.
        </SectionHeader>
        <ul className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {MODULES.map(({ Icon, label }) => (
            <li key={label} className="flex items-center gap-3 rounded-xl border border-brand-primary/10 bg-brand-surface p-3.5 shadow-sm shadow-brand-primary/5 transition hover:border-brand-primary/30">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand-primary"><Icon className="h-5 w-5" aria-hidden /></span>
              <span className="text-sm font-semibold leading-tight text-brand-ink">{label}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------- Final CTA ---------- */
export function FinalCta() {
  return (
    <section id="pricing" className="scroll-mt-20 py-16 lg:py-24">
      <div className={container}>
        <div className="relative overflow-hidden rounded-3xl bg-brand-ink px-6 py-14 text-center sm:px-12 lg:py-20">
          <div className="pointer-events-none absolute -left-16 -top-24 h-72 w-72 rounded-full bg-brand-primary/50 blur-3xl" aria-hidden />
          <div className="pointer-events-none absolute -bottom-28 right-0 h-72 w-72 rounded-full bg-brand-accent/30 blur-3xl" aria-hidden />
          <div className="pointer-events-none absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-brand-secondary/20 blur-3xl" aria-hidden />
          <div className="relative">
            <h2 className="mx-auto max-w-2xl text-balance text-3xl font-extrabold tracking-tight text-brand-surface sm:text-4xl">
              Ready to run your business with clarity?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-brand-surface/75">
              Choose your plan, select the modules you need, and create your workspace.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link to="/register" className={cn(btnPrimary, "bg-brand-surface text-brand-ink shadow-black/20 hover:bg-brand-soft")}>
                Start free <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link to="/register" className={cn(btnSecondary, "border-brand-surface/30 bg-transparent text-brand-surface hover:bg-brand-surface/10 hover:border-brand-surface/50")}>
                View pricing
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------- Footer ---------- */
const linkCls = cn("rounded text-sm text-brand-ink/70 transition hover:text-brand-primary", focusRing);

export function LandingFooter() {
  return (
    <footer id="resources" className="scroll-mt-20 border-t border-brand-primary/10 bg-brand-surface">
      <div className={cn(container, "grid gap-10 py-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]")}>
        <div>
          <SafariLogo size="sm" />
          <p className="mt-4 max-w-xs text-sm leading-6 text-brand-ink/70">
            One workspace for operations, finance, customers and industry workflows.
          </p>
        </div>
        <nav aria-label="Product">
          <p className="text-sm font-bold text-brand-ink">Product</p>
          <ul className="mt-3 space-y-2.5">
            <li><a className={linkCls} href="#solutions">Solutions</a></li>
            <li><a className={linkCls} href="#modules">Modules</a></li>
            <li><a className={linkCls} href="#pricing">Pricing</a></li>
          </ul>
        </nav>
        <nav aria-label="Industries">
          <p className="text-sm font-bold text-brand-ink">Industries</p>
          <ul className="mt-3 space-y-2.5">
            {["Retail", "Restaurant", "Pharmacy", "Property"].map((i) => (
              <li key={i}><a className={linkCls} href="#modules">{i}</a></li>
            ))}
          </ul>
        </nav>
        <nav aria-label="Get started">
          <p className="text-sm font-bold text-brand-ink">Get started</p>
          <ul className="mt-3 space-y-2.5">
            <li><Link className={linkCls} to="/register">Create your workspace</Link></li>
            <li><Link className={linkCls} to="/login">Sign in</Link></li>
            <li><Link className={linkCls} to="/forgot-password">Reset password</Link></li>
          </ul>
        </nav>
      </div>
      <div className="border-t border-brand-primary/10">
        <p className={cn(container, "py-5 text-xs text-brand-ink/60")}>© 2026 Safari ERP</p>
      </div>
    </footer>
  );
}

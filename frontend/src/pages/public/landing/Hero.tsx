import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, Check, LayoutGrid, ShieldCheck, Zap, type LucideIcon } from "lucide-react";
import { cn } from "@/utils/cn";
import { HeroVisual } from "./DashboardPreview";
import { btnPrimary, btnSecondary, container } from "./ui";

const BENEFITS: { Icon: LucideIcon; lines: [string, string] }[] = [
  { Icon: Zap, lines: ["Get started", "in minutes"] },
  { Icon: BarChart3, lines: ["All modules", "in one workspace"] },
  { Icon: ShieldCheck, lines: ["Secure &", "scalable"] },
];

export function Hero() {
  return (
    <section className="relative overflow-x-clip bg-gradient-to-b from-brand-surface via-brand-soft/60 to-brand-surface">
      <div className={cn(container, "grid items-center gap-10 pb-10 pt-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-6 lg:pb-16 lg:pt-16")}>
        <div className="relative z-10">
          <p className="inline-flex items-center gap-2 rounded-full border border-brand-primary/20 bg-brand-soft px-3.5 py-1.5 text-xs font-semibold text-brand-soft-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-primary" aria-hidden />
            All-in-one ERP for growing businesses
          </p>

          <h1 className="mt-6 text-balance text-[2.6rem] font-extrabold leading-[1.05] tracking-tight text-brand-ink sm:text-6xl lg:text-5xl xl:text-[3.9rem]">
            Run your whole
            <br />
            business{" "}
            <span className="bg-gradient-to-r from-brand-primary via-brand-primary to-brand-accent bg-clip-text text-transparent">
              with clarity.
            </span>
          </h1>

          <p className="mt-6 max-w-xl text-base leading-7 text-brand-ink/70 sm:text-lg sm:leading-8">
            Safari ERP brings operations, finance, customers and industry workflows together—securely isolated for your company and ready in minutes.
          </p>

          <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {BENEFITS.map(({ Icon, lines }) => (
              <li key={lines[0]} className="flex items-center gap-3">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand-primary">
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                <span className="text-sm font-semibold leading-tight text-brand-ink">
                  {lines[0]}
                  <br />
                  <span className="font-medium text-brand-ink/70">{lines[1]}</span>
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link to="/register" className={cn(btnPrimary, "px-6 py-3.5 text-base")}>
              Create your workspace <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <a href="#modules" className={cn(btnSecondary, "px-6 py-3.5 text-base")}>
              <LayoutGrid className="h-4 w-4 text-brand-primary" aria-hidden /> Explore modules
            </a>
          </div>

          <ul className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-brand-ink/70">
            {["No credit card required", "Flexible plans", "Cancel anytime"].map((t) => (
              <li key={t} className="flex items-center gap-1.5">
                <Check className="h-4 w-4 text-brand-primary" aria-hidden /> {t}
              </li>
            ))}
          </ul>
        </div>

        <HeroVisual />
      </div>
    </section>
  );
}

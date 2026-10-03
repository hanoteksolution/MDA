import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Building2, GitBranch, LayoutGrid, ShieldCheck, type LucideIcon } from "lucide-react";
import { SafariLogo } from "@/components/brand/SafariLogo";
import { SAFARI_BRAND } from "@/design-system/brand";

const CAPABILITIES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: LayoutGrid,
    title: "One platform, every module",
    body: "POS, inventory, purchases, finance and industry modules in a single workspace.",
  },
  {
    icon: GitBranch,
    title: "Built for multiple branches",
    body: "Branch-level stock, transfers and reporting with a consolidated view.",
  },
  {
    icon: ShieldCheck,
    title: "Isolated, secure workspaces",
    body: "Every company gets its own workspace address and tenant-scoped data.",
  },
];

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

/**
 * Safari-branded side panel shared by Login, Onboarding and Setup (desktop
 * widths only — narrow screens show the logo above the form instead).
 */
export function LoginBrandingPanel({
  productName,
  productTagline,
  headline,
  description,
  children,
}: {
  /** Tenant/workspace name when signing in on a tenant host. */
  productName?: string;
  productTagline?: string;
  headline?: string;
  description?: string;
  /** Optional replacement for the capability list (e.g. onboarding summary). */
  children?: ReactNode;
} = {}) {
  const title = headline || "Run your whole business from one workspace.";
  const body =
    description ||
    "Safari ERP connects sales, stock, finance and your branches — so your team works from the same numbers, every day.";

  return (
    <aside className="relative hidden h-full min-h-dvh flex-col overflow-hidden border-r border-border/70 bg-brand-soft lg:flex">
      <div className="safari-brand-rule h-1 w-full" aria-hidden />
      {/* Quiet brand wash — kept well below text contrast. */}
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden
        style={{
          background:
            "radial-gradient(60% 45% at 0% 0%, hsl(var(--brand-primary) / 0.10), transparent 70%), radial-gradient(45% 35% at 100% 100%, hsl(var(--brand-secondary) / 0.08), transparent 70%)",
        }}
      />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 flex flex-1 flex-col px-10 py-10 xl:px-14 xl:py-12"
      >
        <motion.div variants={item}>
          <SafariLogo size="lg" />
        </motion.div>

        <div className="my-auto max-w-lg py-12">
          {productName ? (
            <motion.p
              variants={item}
              className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-primary/20 bg-brand-surface/80 px-3 py-1 text-xs font-semibold text-brand-soft-foreground"
            >
              <Building2 className="h-3.5 w-3.5" aria-hidden />
              {productName}
              {productTagline ? (
                <span className="font-normal text-muted-foreground">· {productTagline}</span>
              ) : null}
            </motion.p>
          ) : (
            <motion.p
              variants={item}
              className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-brand-primary"
            >
              {SAFARI_BRAND.product}
            </motion.p>
          )}
          <motion.h1
            variants={item}
            className="text-3xl font-bold leading-tight tracking-tight text-brand-ink xl:text-4xl"
          >
            {title}
          </motion.h1>
          <motion.p variants={item} className="mt-4 text-base leading-relaxed text-muted-foreground">
            {body}
          </motion.p>

          <motion.div variants={item} className="mt-10">
            {children ?? (
              <ul className="space-y-5">
                {CAPABILITIES.map(({ icon: Icon, title: capTitle, body: capBody }) => (
                  <li key={capTitle} className="flex gap-4">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-brand-primary/15 bg-brand-surface text-brand-primary shadow-sm">
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                    <span>
                      <span className="block text-sm font-semibold text-brand-ink">{capTitle}</span>
                      <span className="mt-0.5 block text-sm text-muted-foreground">{capBody}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        </div>

        <motion.p variants={item} className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} {SAFARI_BRAND.company}
        </motion.p>
      </motion.div>
    </aside>
  );
}

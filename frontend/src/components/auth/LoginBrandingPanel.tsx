import { motion } from "framer-motion";
import { Shield, Zap, Globe, Award } from "lucide-react";
import { DashboardPreviewMockup } from "./DashboardPreviewMockup";

const trustBadges = [
  { icon: Shield, label: "256-bit Encryption" },
  { icon: Zap, label: "Offline-First POS" },
  { icon: Globe, label: "Multi-Branch Ready" },
  { icon: Award, label: "Enterprise Grade" },
];

const clients = ["RetailCo", "PharmaPlus", "TechMart", "FreshGrocer"];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export function LoginBrandingPanel() {
  return (
    <div className="relative flex flex-col justify-between overflow-hidden bg-secondary px-8 py-10 lg:px-14 lg:py-12 xl:px-16">
      {/* Background layers */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950" />
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-emerald-500/20 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-teal-500/15 blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 flex flex-col flex-1"
      >
        {/* Logo & headline */}
        <motion.div variants={item} className="mb-8 lg:mb-10">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-500/30">
              <span className="text-lg font-black text-white">M</span>
            </div>
            <div>
              <p className="text-sm font-semibold tracking-widest text-emerald-400 uppercase">
                MDA Retail
              </p>
              <p className="text-xs text-white/50">Enterprise ERP & POS</p>
            </div>
          </div>
        </motion.div>

        <motion.div variants={item} className="mb-6 lg:mb-8">
          <h1 className="text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-5xl xl:text-[3.25rem] xl:leading-[1.1]">
            Run your entire{" "}
            <span className="text-gradient from-emerald-300 to-emerald-500 bg-gradient-to-r bg-clip-text text-transparent">
              retail operation
            </span>{" "}
            from one platform.
          </h1>
          <p className="mt-4 max-w-lg text-base leading-relaxed text-white/60 lg:text-lg">
            POS, inventory, purchases, finance, and analytics — built for
            multi-branch retailers who demand speed, reliability, and control.
          </p>
        </motion.div>

        {/* Trust badges */}
        <motion.div variants={item} className="mb-8 flex flex-wrap gap-3">
          {trustBadges.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-sm"
            >
              <Icon className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-xs font-medium text-white/70">{label}</span>
            </div>
          ))}
        </motion.div>

        {/* Dashboard preview */}
        <motion.div variants={item} className="flex-1 flex items-center">
          <DashboardPreviewMockup />
        </motion.div>

        {/* Social proof */}
        <motion.div variants={item} className="mt-8 lg:mt-10 pt-6 border-t border-white/10">
          <p className="mb-4 text-xs font-medium uppercase tracking-widest text-white/40">
            Trusted by leading retailers
          </p>
          <div className="flex flex-wrap items-center gap-6">
            {clients.map((name) => (
              <span
                key={name}
                className="text-sm font-semibold text-white/25 hover:text-white/40 transition-colors"
              >
                {name}
              </span>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}

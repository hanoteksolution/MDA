import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, Boxes, Building2, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";

const capabilities = [
  { Icon: Boxes, title: "Inventory & POS", body: "Live stock, purchasing, sales and counter operations in one workspace." },
  { Icon: BarChart3, title: "Finance & reporting", body: "Ledgers, cash flow and business reporting stay connected to every transaction." },
  { Icon: Building2, title: "Built for your industry", body: "Enable only the modules your retail, restaurant, pharmacy, property or service business needs." },
];

export function LandingPage() {
  return (
    <main className="min-h-dvh bg-slate-950 text-white">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-8">
        <Link to="/" className="flex items-center gap-3 font-semibold tracking-tight">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-400 text-slate-950">S</span>
          Safari ERP
        </Link>
        <div className="flex items-center gap-3 text-sm">
          <a href="#solutions" className="hidden text-slate-300 hover:text-white sm:block">Solutions</a>
          <a href="#pricing" className="hidden text-slate-300 hover:text-white sm:block">Pricing</a>
          <Link to="/login" className="rounded-xl px-4 py-2 text-slate-200 hover:bg-white/10">Sign in</Link>
          <Link to="/register" className="rounded-xl bg-emerald-400 px-4 py-2 font-semibold text-slate-950 hover:bg-emerald-300">Start free</Link>
        </div>
      </nav>

      <section className="relative overflow-hidden px-6 pb-24 pt-20 lg:px-8 lg:pt-28">
        <div className="absolute inset-x-0 top-0 -z-0 mx-auto h-96 max-w-4xl rounded-full bg-emerald-500/15 blur-3xl" />
        <div className="relative mx-auto max-w-5xl text-center">
          <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-200">
            <Sparkles className="h-4 w-4" /> One workspace. Modules that fit your business.
          </div>
          <h1 className="text-balance text-5xl font-semibold tracking-tight sm:text-7xl">Run your whole business with clarity.</h1>
          <p className="mx-auto mt-7 max-w-2xl text-lg leading-8 text-slate-300">Safari ERP brings operations, finance, customers and industry workflows together—securely isolated for your company and ready in minutes.</p>
          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <Link to="/register" className="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-400 px-6 py-3.5 font-semibold text-slate-950 hover:bg-emerald-300">Create your workspace <ArrowRight className="h-4 w-4" /></Link>
            <a href="#solutions" className="rounded-2xl border border-white/15 bg-white/5 px-6 py-3.5 font-semibold hover:bg-white/10">Explore modules</a>
          </div>
          <div className="mt-12 flex flex-wrap justify-center gap-x-8 gap-y-3 text-sm text-slate-400">
            <span className="flex gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" />14-day trial</span>
            <span className="flex gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" />No card required</span>
            <span className="flex gap-2"><ShieldCheck className="h-4 w-4 text-emerald-400" />Tenant-isolated data</span>
          </div>
        </div>
      </section>

      <section id="solutions" className="border-y border-white/10 bg-white/[0.03] px-6 py-24 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-emerald-400">A platform that adapts</p>
          <h2 className="mt-3 max-w-2xl text-3xl font-semibold sm:text-4xl">Start focused. Add capability as you grow.</h2>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {capabilities.map(({ Icon, title, body }) => (
              <article key={title} className="rounded-3xl border border-white/10 bg-slate-900 p-7">
                <Icon className="h-7 w-7 text-emerald-400" />
                <h3 className="mt-6 text-xl font-semibold">{title}</h3>
                <p className="mt-3 leading-7 text-slate-400">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="px-6 py-24 text-center lg:px-8">
        <h2 className="text-3xl font-semibold">A simpler way to get started</h2>
        <p className="mx-auto mt-4 max-w-xl text-slate-400">Choose the plan and modules that match your operation during setup. Your workspace stays uniquely yours.</p>
        <Link to="/register" className="mt-8 inline-flex rounded-2xl bg-white px-6 py-3 font-semibold text-slate-950 hover:bg-slate-100">See plans and start free</Link>
      </section>

      <footer className="border-t border-white/10 px-6 py-8 text-center text-sm text-slate-500">© 2026 Safari ERP · Privacy · Terms · Support</footer>
    </main>
  );
}

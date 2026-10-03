import {
  BarChart3,
  Bell,
  Boxes,
  ChevronDown,
  Headphones,
  Laptop,
  LayoutDashboard,
  Monitor,
  Network,
  Package,
  Receipt,
  Search,
  Settings,
  ShoppingCart,
  Smartphone,
  TrendingUp,
  Truck,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/utils/cn";

const SIDEBAR: { label: string; Icon: LucideIcon }[] = [
  { label: "Dashboard", Icon: LayoutDashboard },
  { label: "Sales", Icon: ShoppingCart },
  { label: "Inventory", Icon: Boxes },
  { label: "Purchases", Icon: Truck },
  { label: "Expenses", Icon: Receipt },
  { label: "Finance", Icon: Wallet },
  { label: "Customers", Icon: Users },
  { label: "Reports", Icon: BarChart3 },
  { label: "Settings", Icon: Settings },
];

const STATS = [
  { label: "Total Sales", value: "$2,450", delta: "+12%", up: true, Icon: TrendingUp, tone: "bg-emerald-500/10 text-emerald-600" },
  { label: "Stock Items", value: "1,284", delta: "+6%", up: true, Icon: Package, tone: "bg-brand-deep/10 text-brand-deep" },
  { label: "Customers", value: "892", delta: "+18%", up: true, Icon: Users, tone: "bg-brand-primary/10 text-brand-primary" },
  { label: "Expenses", value: "$320", delta: "-4%", up: false, Icon: Receipt, tone: "bg-orange-500/10 text-orange-600" },
];

const PRODUCTS: { name: string; sold: number; Icon: LucideIcon }[] = [
  { name: "Phone", sold: 42, Icon: Smartphone },
  { name: "Television", sold: 28, Icon: Monitor },
  { name: "Laptop", sold: 24, Icon: Laptop },
  { name: "Earbuds", sold: 20, Icon: Headphones },
];

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];

function SalesChart() {
  return (
    <svg viewBox="0 0 400 130" className="h-full w-full" role="img" aria-label="Sample sales trend rising over seven months">
      <defs>
        <linearGradient id="lp-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--brand-primary))" stopOpacity="0.28" />
          <stop offset="100%" stopColor="hsl(var(--brand-primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[20, 55, 90].map((y) => (
        <line key={y} x1="0" x2="400" y1={y} y2={y} stroke="hsl(var(--brand-primary))" strokeOpacity="0.1" />
      ))}
      <path
        d="M0 100 C40 92 60 78 100 84 S160 104 200 84 S260 44 300 58 S360 34 400 40 L400 130 L0 130 Z"
        fill="url(#lp-area)"
      />
      <path
        d="M0 100 C40 92 60 78 100 84 S160 104 200 84 S260 44 300 58 S360 34 400 40"
        fill="none"
        stroke="hsl(var(--brand-primary))"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="300" cy="58" r="5" fill="hsl(var(--brand-surface))" stroke="hsl(var(--brand-primary))" strokeWidth="2.5" />
    </svg>
  );
}

/**
 * Marketing-only preview of the Safari ERP dashboard. Static and lightweight:
 * it is not the real dashboard, and every figure is sample data.
 */
export function DashboardPreview() {
  return (
    <div
      className="overflow-hidden rounded-2xl border border-brand-primary/15 bg-brand-surface shadow-2xl shadow-brand-primary/20"
      role="img"
      aria-label="Preview of the Safari ERP dashboard showing sales, stock, customers, expenses, a sales chart and top products (sample data)"
    >
      {/* App bar */}
      <div className="flex items-center gap-3 border-b border-brand-primary/10 px-4 py-2.5">
        <span className="text-[11px] font-bold tracking-tight text-brand-ink">SAFARI ERP</span>
        <div className="ml-2 hidden h-7 flex-1 items-center gap-2 rounded-lg bg-brand-soft px-2.5 text-[10px] text-brand-ink/50 sm:flex">
          <Search className="h-3 w-3" aria-hidden /> Search anything…
        </div>
        <div className="ml-auto flex items-center gap-2.5">
          <span className="flex items-center gap-1 rounded-lg border border-brand-primary/15 px-2 py-1 text-[10px] font-medium text-brand-ink">
            Bakaaro Branch <ChevronDown className="h-3 w-3" aria-hidden />
          </span>
          <Bell className="h-3.5 w-3.5 text-brand-ink/60" aria-hidden />
          <span className="grid h-6 w-6 place-items-center rounded-full bg-gradient-to-br from-brand-primary to-brand-accent text-[9px] font-bold text-white">A</span>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside className="hidden w-[132px] shrink-0 flex-col gap-0.5 bg-brand-ink p-2.5 sm:flex" aria-hidden>
          {SIDEBAR.map(({ label, Icon }, i) => (
            <span
              key={label}
              className={cn(
                "flex items-center gap-2 rounded-md px-2 py-1.5 text-[10px] font-medium",
                i === 0 ? "bg-brand-primary text-brand-primary-foreground" : "text-brand-surface/70"
              )}
            >
              <Icon className="h-3 w-3" /> {label}
            </span>
          ))}
        </aside>

        {/* Main */}
        <div className="min-w-0 flex-1 space-y-3 bg-brand-soft/40 p-3.5">
          <div>
            <p className="text-[13px] font-bold text-brand-ink">Good morning, Ahmed</p>
            <p className="text-[10px] text-brand-ink/60">Here’s what’s happening at Bakaaro Branch today.</p>
          </div>

          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {STATS.map(({ label, value, delta, up, Icon, tone }) => (
              <div key={label} className="rounded-xl border border-brand-primary/10 bg-brand-surface p-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-medium text-brand-ink/60">{label}</span>
                  <span className={cn("grid h-5 w-5 place-items-center rounded-md", tone)}>
                    <Icon className="h-2.5 w-2.5" />
                  </span>
                </div>
                <p className="mt-1 text-[15px] font-bold leading-none text-brand-ink">{value}</p>
                <p className={cn("mt-1 text-[9px] font-semibold", up ? "text-emerald-600" : "text-rose-500")}>{delta}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-2 md:grid-cols-[1.6fr_1fr]">
            <div className="rounded-xl border border-brand-primary/10 bg-brand-surface p-3">
              <p className="text-[10px] font-bold text-brand-ink">Sales Overview</p>
              <div className="relative mt-2 h-[104px]">
                <SalesChart />
                <span className="absolute left-[62%] top-0 rounded-md bg-brand-ink px-1.5 py-1 text-[9px] font-semibold leading-tight text-brand-surface">
                  $2,450 <span className="text-emerald-400">+12%</span>
                </span>
              </div>
              <div className="mt-1 flex justify-between text-[8px] text-brand-ink/45" aria-hidden>
                {MONTHS.map((m) => <span key={m}>{m}</span>)}
              </div>
            </div>

            <div className="hidden rounded-xl border border-brand-primary/10 bg-brand-surface p-3 md:block">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold text-brand-ink">Top Products</p>
                <span className="text-[9px] font-medium text-brand-primary">View all</span>
              </div>
              <ul className="mt-2 space-y-2">
                {PRODUCTS.map(({ name, sold, Icon }) => (
                  <li key={name} className="flex items-center gap-2 text-[10px]">
                    <span className="grid h-6 w-6 place-items-center rounded-md bg-brand-soft text-brand-primary">
                      <Icon className="h-3 w-3" />
                    </span>
                    <span className="flex-1 truncate font-medium text-brand-ink">{name}</span>
                    <span className="text-brand-ink/50">{sold} sold</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const floatCard =
  "absolute z-10 flex items-center gap-3 rounded-2xl border border-brand-primary/10 bg-brand-surface px-4 py-3 shadow-xl shadow-brand-primary/15 landing-float";

/** Dashboard preview with soft glow, dot grid and three floating feature cards. */
export function HeroVisual() {
  return (
    <div className="relative mx-auto w-full max-w-[680px] lg:mx-0 lg:max-w-none">
      {/* Glows + dot grid */}
      <div className="pointer-events-none absolute -right-10 -top-10 h-72 w-72 rounded-full bg-brand-primary/25 blur-3xl" aria-hidden />
      <div className="pointer-events-none absolute -left-8 top-1/3 h-56 w-56 rounded-full bg-brand-accent/15 blur-3xl" aria-hidden />
      <div className="pointer-events-none absolute -bottom-10 right-1/4 h-56 w-56 rounded-full bg-brand-secondary/20 blur-3xl" aria-hidden />
      <div
        className="pointer-events-none absolute -right-4 top-24 hidden h-40 w-32 opacity-60 sm:block"
        style={{ backgroundImage: "radial-gradient(hsl(var(--brand-primary) / 0.35) 1.4px, transparent 1.4px)", backgroundSize: "14px 14px" }}
        aria-hidden
      />

      <div className="relative py-10 sm:px-6 lg:py-14">
        <div className="lg:[transform:perspective(2000px)_rotateY(-8deg)_rotateX(3deg)]">
          <DashboardPreview />
        </div>

        <div className={cn(floatCard, "-top-1 right-0 hidden sm:flex")}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-soft text-brand-primary"><Network className="h-5 w-5" /></span>
          <p className="text-sm font-bold leading-tight text-brand-ink">Multi-branch<br /><span className="font-medium text-brand-ink/60">management</span></p>
        </div>
        <div className={cn(floatCard, "-bottom-1 left-0 [animation-delay:-2s] sm:-left-2")}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-500/10 text-emerald-600"><BarChart3 className="h-5 w-5" /></span>
          <p className="text-sm font-bold leading-tight text-brand-ink">Real-time insights<br /><span className="font-medium text-brand-ink/60">for better decisions</span></p>
        </div>
        <div className={cn(floatCard, "-bottom-4 right-2 hidden [animation-delay:-4s] md:flex")}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-orange-500/10 text-orange-600"><Package className="h-5 w-5" /></span>
          <p className="text-sm font-bold leading-tight text-brand-ink">Live stock<br /><span className="font-medium text-brand-ink/60">across branches</span></p>
        </div>
      </div>
      <p className="text-center text-[11px] text-brand-ink/50 lg:text-left">Preview with sample data.</p>
    </div>
  );
}

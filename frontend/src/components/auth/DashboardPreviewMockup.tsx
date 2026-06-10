import { motion } from "framer-motion";
import {
  BarChart3,
  Package,
  ShoppingCart,
  TrendingUp,
  Wallet,
} from "lucide-react";

const kpis = [
  { label: "Revenue", value: "$284K", icon: Wallet, trend: "+12.4%" },
  { label: "Sales", value: "1,842", icon: ShoppingCart, trend: "+8.2%" },
  { label: "Products", value: "12.4K", icon: Package, trend: "+2.1%" },
  { label: "Profit", value: "$68K", icon: TrendingUp, trend: "+15.7%" },
];

const chartBars = [40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88];

export function DashboardPreviewMockup() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40, rotateX: 8 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
      className="relative w-full max-w-2xl perspective-1000"
    >
      <div className="absolute -inset-4 rounded-3xl bg-gradient-to-r from-emerald-500/20 to-teal-500/10 blur-2xl animate-pulse-soft" />

      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        className="relative overflow-hidden rounded-2xl border border-white/20 bg-white/10 p-1 shadow-2xl shadow-black/20 backdrop-blur-2xl"
      >
        <div className="rounded-xl bg-slate-900/90 p-5">
          {/* Window chrome */}
          <div className="mb-4 flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="h-3 w-3 rounded-full bg-red-400/80" />
              <span className="h-3 w-3 rounded-full bg-amber-400/80" />
              <span className="h-3 w-3 rounded-full bg-emerald-400/80" />
            </div>
            <div className="ml-4 flex-1 rounded-lg bg-white/5 px-4 py-1.5 text-xs text-white/40">
              app.mda-erp.com/dashboard
            </div>
          </div>

          <div className="flex gap-4">
            {/* Mini sidebar */}
            <div className="hidden sm:flex w-14 shrink-0 flex-col gap-2 rounded-lg bg-white/5 p-2">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className={`h-8 rounded-lg ${i === 0 ? "bg-emerald-500/30" : "bg-white/5"}`}
                />
              ))}
            </div>

            {/* Main content */}
            <div className="flex-1 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="h-3 w-24 rounded bg-white/20" />
                  <div className="mt-2 h-5 w-40 rounded bg-white/30" />
                </div>
                <div className="h-8 w-24 rounded-lg bg-emerald-500/30" />
              </div>

              {/* KPI row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                {kpis.map((kpi, i) => (
                  <motion.div
                    key={kpi.label}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.6 + i * 0.1 }}
                    className="rounded-xl border border-white/10 bg-white/5 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <kpi.icon className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-[10px] font-medium text-emerald-400">{kpi.trend}</span>
                    </div>
                    <p className="mt-2 text-[10px] text-white/50">{kpi.label}</p>
                    <p className="text-sm font-bold text-white">{kpi.value}</p>
                  </motion.div>
                ))}
              </div>

              {/* Chart */}
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="mb-3 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-medium text-white/70">Sales Trend</span>
                </div>
                <div className="flex items-end gap-1.5 h-20">
                  {chartBars.map((height, i) => (
                    <motion.div
                      key={i}
                      initial={{ height: 0 }}
                      animate={{ height: `${height}%` }}
                      transition={{ delay: 0.8 + i * 0.05, duration: 0.5 }}
                      className="flex-1 rounded-t bg-gradient-to-t from-emerald-600 to-emerald-400 opacity-80"
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

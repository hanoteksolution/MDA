import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Clock, Heart, Zap, FileText, PauseCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";
import type { HeldSale, RecentSale } from "../hooks/usePosCart";

interface PosBottomWidgetsProps {
  recentSales: RecentSale[];
  favoriteProducts: Product[];
  heldSales: HeldSale[];
  onAddProduct: (p: Product) => void;
  onHoldSale: () => void;
  onClearCart: () => void;
  onOpenDrafts: () => void;
}

function WidgetCard({
  title,
  icon,
  children,
  index,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      className="ds-card-premium relative overflow-hidden rounded-2xl border-border/60 p-4 shadow-sm"
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent" />
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
      </div>
      {children}
    </motion.div>
  );
}

export function PosBottomWidgets({
  recentSales,
  favoriteProducts,
  heldSales,
  onAddProduct,
  onHoldSale,
  onClearCart,
  onOpenDrafts,
}: PosBottomWidgetsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="grid shrink-0 grid-cols-1 gap-3 border-t border-border/70 bg-gradient-to-t from-muted/30 to-transparent p-4 lg:grid-cols-3"
    >
      <WidgetCard title="Recently Sold" icon={<Clock className="h-3.5 w-3.5" />} index={0}>
        {recentSales.length === 0 ? (
          <p className="py-3 text-xs text-muted-foreground">No recent sales yet</p>
        ) : (
          <ul className="max-h-24 space-y-2 overflow-y-auto scrollbar-thin">
            {recentSales.slice(0, 5).map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-2 rounded-lg px-2 py-1 text-xs hover:bg-muted/40">
                <span className="truncate font-medium text-foreground">{s.name}</span>
                <span className="shrink-0 font-bold tabular-nums text-primary">
                  {formatCurrency(s.total)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </WidgetCard>

      <WidgetCard title="Favorites" icon={<Heart className="h-3.5 w-3.5" />} index={1}>
        {favoriteProducts.length === 0 ? (
          <p className="py-3 text-xs text-muted-foreground">Star products to pin them here</p>
        ) : (
          <ul className="max-h-24 space-y-1 overflow-y-auto scrollbar-thin">
            {favoriteProducts.slice(0, 5).map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onAddProduct(p)}
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition-colors hover:bg-primary/10"
                >
                  <span className="truncate font-medium">{p.name}</span>
                  <span className="shrink-0 font-semibold tabular-nums text-primary">
                    {formatCurrency(p.selling_price)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </WidgetCard>

      <WidgetCard title="Quick Actions" icon={<Zap className="h-3.5 w-3.5" />} index={2}>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="h-10 justify-start gap-2 rounded-xl text-xs font-semibold"
            onClick={onClearCart}
          >
            <RotateCcw className="h-4 w-4 text-primary" />
            New Sale
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="h-10 justify-start gap-2 rounded-xl text-xs font-semibold"
            onClick={onHoldSale}
          >
            <PauseCircle className="h-4 w-4 text-amber-600" />
            Hold Sale
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="relative h-10 justify-start gap-2 rounded-xl text-xs font-semibold"
            onClick={onOpenDrafts}
          >
            <FileText className="h-4 w-4 text-sky-600" />
            Drafts
            {heldSales.length > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground shadow-md">
                {heldSales.length}
              </span>
            )}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="h-10 justify-start gap-2 rounded-xl text-xs font-semibold"
            onClick={onOpenDrafts}
            disabled={heldSales.length === 0}
          >
            <Clock className="h-4 w-4 text-violet-600" />
            Resume
          </Button>
        </div>
      </WidgetCard>
    </motion.div>
  );
}

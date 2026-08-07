import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShoppingCart,
  User,
  Trash2,
  Plus,
  Minus,
  Lock,
  Percent,
  StickyNote,
  DollarSign,
  Printer,
  PauseCircle,
  UtensilsCrossed,
  ClipboardList,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { resolveMediaUrl } from "@/config/api";
import { cn, formatCurrency } from "@/utils/cn";
import { appDialog } from "@/components/feedback/AppDialog";
import type { PosWaiter } from "@/services/api/pos";
import type { CartLine, DiscountMode } from "../hooks/usePosCart";
import { printOrderSlip } from "../receipt/printCartSlip";
import { PosCartQuickCreateDialog, type PosQuickCreateMode } from "./PosCartQuickCreateDialog";

interface PosCartPanelProps {
  cart: CartLine[];
  itemCount: number;
  subtotal: number;
  discount: number;
  discountPct: number;
  discountAmount: number;
  discountMode: DiscountMode;
  onDiscountPctChange: (pct: number) => void;
  onDiscountAmountChange: (amount: number) => void;
  tax: number;
  taxRate: number;
  grandTotal: number;
  orderNotes: string;
  onNotesChange: (v: string) => void;
  customerId: string;
  customerName: string;
  onCustomerChange: (id: string) => void;
  customers: { id: string; name: string }[];
  waiters: PosWaiter[];
  waiterId: string;
  onWaiterChange: (id: string) => void;
  branchName?: string;
  branchCode?: string;
  branchId?: string;
  onCreateCustomer?: (data: { full_name: string; phone?: string }) => Promise<void>;
  onCreateWaiter?: (name: string) => Promise<void>;
  onUpdateQty: (id: string, delta: number) => void;
  onRemove: (id: string) => void;
  onOpenCheckout: () => void;
  onHold: () => void;
  onViewWaiterSales?: () => void;
}

export function PosCartPanel({
  cart,
  itemCount,
  subtotal,
  discount,
  discountPct,
  discountAmount,
  discountMode,
  onDiscountPctChange,
  onDiscountAmountChange,
  tax,
  taxRate,
  grandTotal,
  orderNotes,
  onNotesChange,
  customerId,
  customerName,
  onCustomerChange,
  customers,
  waiters,
  waiterId,
  onWaiterChange,
  branchName,
  branchCode,
  branchId,
  onCreateCustomer,
  onCreateWaiter,
  onUpdateQty,
  onRemove,
  onOpenCheckout,
  onHold,
  onViewWaiterSales,
}: PosCartPanelProps) {
  const hasCart = cart.length > 0;
  const hasWaiter = Boolean(waiterId);
  const activeWaiters = waiters.filter((w) => w.is_active !== false);
  const [printing, setPrinting] = useState(false);
  const [quickCreate, setQuickCreate] = useState<PosQuickCreateMode | null>(null);
  const waiterName = waiters.find((w) => w.id === waiterId)?.name;

  const requireWaiter = async (action: string) => {
    if (hasWaiter) return true;
    await appDialog.alert(`Select a waiter before you can ${action}.`, {
      title: "Waiter required",
      tone: "danger",
    });
    return false;
  };

  const handlePrint = async () => {
    if (!(await requireWaiter("print a receipt"))) return;
    setPrinting(true);
    try {
      await printOrderSlip({
        customerName,
        waiterName,
        branchName,
        branchCode,
        branchId,
        cart,
        subtotal,
        discount,
        tax,
        taxRate,
        grandTotal,
        notes: orderNotes,
      });
    } finally {
      setPrinting(false);
    }
  };

  const handleHold = async () => {
    if (!(await requireWaiter("hold this sale"))) return;
    onHold();
  };

  const handleCheckout = async () => {
    if (!(await requireWaiter("checkout"))) return;
    onOpenCheckout();
  };

  const discountLabel =
    discountMode === "percent" && discountPct > 0
      ? `Discount (${Number(discountPct.toFixed(discountPct % 1 === 0 ? 0 : 2))}%)`
      : discount > 0
        ? "Discount"
        : null;

  return (
    <div className="pos-cart-panel relative z-[2] flex h-full min-h-0 flex-col overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-primary/[0.06] to-transparent" />

      <div className="relative flex shrink-0 items-center justify-between border-b border-border/50 px-3 py-2 xl:px-4 xl:py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-emerald-600 text-primary-foreground shadow-[0_8px_20px_hsl(var(--primary)/0.28)] xl:h-10 xl:w-10 xl:rounded-2xl">
            <ShoppingCart className="h-4 w-4" strokeWidth={2.25} />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-foreground">Current sale</h2>
            <p className="hidden text-[11px] text-muted-foreground 2xl:block">Review items before checkout</p>
          </div>
        </div>
        <Badge className="border-0 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold tabular-nums text-primary">
          {itemCount} {itemCount === 1 ? "item" : "items"}
        </Badge>
      </div>

      <div className="relative shrink-0 space-y-1 border-b border-border/50 px-3 py-1.5 xl:space-y-1.5 xl:px-4 xl:py-2">
        <div className="flex items-center gap-2">
          <div className="flex flex-1 items-center gap-2 rounded-xl border border-border/50 bg-background/70 px-2.5 py-1 shadow-[inset_0_1px_0_hsl(var(--background))] xl:gap-3 xl:rounded-2xl xl:px-3 xl:py-1.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary xl:h-8 xl:w-8 xl:rounded-xl">
              <User className="h-3.5 w-3.5 xl:h-4 xl:w-4" />
            </div>
            <Select value={customerId} onValueChange={onCustomerChange}>
              <SelectTrigger className="h-8 flex-1 border-0 bg-transparent px-0 text-sm shadow-none focus:ring-0 xl:h-9">
                <SelectValue placeholder="Walk-in Customer" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="walkin">Walk-in Customer</SelectItem>
                {customers.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {onCreateCustomer && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="h-9 w-9 shrink-0 rounded-xl p-0"
              onClick={() => setQuickCreate("customer")}
              title="Add customer"
            >
              <Plus className="h-4 w-4" />
            </Button>
          )}
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex flex-1 items-center gap-2 rounded-xl border bg-background/70 px-2.5 py-1 xl:gap-3 xl:rounded-2xl xl:px-3 xl:py-1.5",
                hasWaiter ? "border-border/50" : "border-amber-500/40 ring-1 ring-amber-500/20"
              )}
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 xl:h-8 xl:w-8 xl:rounded-xl">
                <UtensilsCrossed className="h-3.5 w-3.5 xl:h-4 xl:w-4" />
              </div>
              <Select
                value={waiterId || undefined}
                onValueChange={(v) => onWaiterChange(v)}
              >
                <SelectTrigger className="h-8 flex-1 border-0 bg-transparent px-0 text-sm shadow-none focus:ring-0 xl:h-9">
                  <SelectValue placeholder="Select waiter (required)" />
                </SelectTrigger>
                <SelectContent>
                  {activeWaiters.map((w) => (
                    <SelectItem key={w.id} value={w.id}>
                      {w.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {onCreateWaiter && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-9 w-9 shrink-0 rounded-xl p-0"
                onClick={() => setQuickCreate("waiter")}
                title="Add waiter"
              >
                <Plus className="h-4 w-4" />
              </Button>
            )}
            {onViewWaiterSales && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-9 shrink-0 rounded-xl px-2.5"
                onClick={() => {
                  if (!waiterId) {
                    void requireWaiter("view unpaid products");
                    return;
                  }
                  onViewWaiterSales();
                }}
                title="View waiter unpaid products"
              >
                <ClipboardList className="h-4 w-4" />
              </Button>
            )}
          </div>
          {!hasWaiter && (
            <p className="px-1 text-[10px] font-medium leading-tight text-amber-700 dark:text-amber-400 xl:text-[11px]">
              Waiter required for print, hold, and checkout.
            </p>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2 scrollbar-thin xl:px-4 xl:py-3">
        <AnimatePresence mode="popLayout">
          {cart.map((item, i) => (
            <motion.div
              key={item.id}
              layout
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12, height: 0 }}
              transition={{ delay: i * 0.02 }}
              className="mb-2 overflow-hidden rounded-xl border border-border/50 bg-card/90 p-2.5 shadow-[0_1px_2px_hsl(var(--foreground)/0.04)] transition-shadow hover:shadow-[0_8px_20px_hsl(var(--foreground)/0.06)] xl:mb-2.5 xl:rounded-2xl xl:p-3"
            >
              <div className="flex gap-2.5 xl:gap-3">
                <div className="h-10 w-10 shrink-0 overflow-hidden rounded-lg border border-border/40 bg-muted/40 xl:h-12 xl:w-12 xl:rounded-xl">
                  {item.image ? (
                    <img src={resolveMediaUrl(item.image)} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary/10 to-primary/5">
                      <ShoppingCart className="h-4 w-4 text-primary/60" />
                    </div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-semibold tracking-tight">{item.name}</p>
                  <p className="font-mono text-[10px] text-muted-foreground">{item.sku}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {formatCurrency(item.price)} each
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 shrink-0 p-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => onRemove(item.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <div className="mt-2 flex items-center justify-between xl:mt-3">
                <div className="flex items-center overflow-hidden rounded-xl border border-border/50 bg-muted/20">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 rounded-none p-0 hover:bg-muted/60 xl:h-8 xl:w-8"
                    onClick={() => onUpdateQty(item.id, -1)}
                  >
                    <Minus className="h-3.5 w-3.5" />
                  </Button>
                  <span className="w-8 text-center text-sm font-semibold tabular-nums xl:w-9">{item.qty}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 rounded-none p-0 hover:bg-muted/60 xl:h-8 xl:w-8"
                    onClick={() => onUpdateQty(item.id, 1)}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <span className="text-sm font-bold tabular-nums tracking-tight text-foreground xl:text-[15px]">
                  {formatCurrency(item.price * item.qty)}
                </span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Adjustments scroll with cart so Print/Hold/Checkout stay pinned */}
        <div className="mt-2 space-y-1.5 border-t border-border/40 pt-2 xl:mt-3 xl:space-y-2 xl:pt-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Adjustments
          </p>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-1.5 rounded-xl border border-border/50 bg-background/70 px-2.5 py-0.5">
              <Percent className="h-3.5 w-3.5 shrink-0 text-primary/80" />
              <Input
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={discountPct ? Number(discountPct.toFixed(2)) : ""}
                placeholder="0"
                onChange={(e) =>
                  onDiscountPctChange(Math.min(100, Math.max(0, parseFloat(e.target.value) || 0)))
                }
                className="h-8 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
              />
              <span className="shrink-0 text-[11px] text-muted-foreground">%</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-xl border border-border/50 bg-background/70 px-2.5 py-0.5">
              <DollarSign className="h-3.5 w-3.5 shrink-0 text-primary/80" />
              <Input
                type="number"
                min={0}
                step={0.01}
                value={discountAmount ? Number(discountAmount.toFixed(2)) : ""}
                placeholder="0.00"
                onChange={(e) =>
                  onDiscountAmountChange(Math.max(0, parseFloat(e.target.value) || 0))
                }
                className="h-8 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
              />
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-background/70 px-2.5 py-0.5">
            <StickyNote className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <Input
              value={orderNotes}
              onChange={(e) => onNotesChange(e.target.value)}
              placeholder="Order notes..."
              className="h-8 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
            />
          </div>
        </div>
      </div>

      {/* Sticky footer: totals + actions always visible on laptops */}
      <div className="pos-cart-footer shrink-0 border-t border-border/50 bg-card/95 backdrop-blur-md">
        <div className="space-y-1 border-t border-border/40 bg-background/40 px-3 py-2 xl:space-y-1.5 xl:px-4 xl:py-2.5">
          <div className="flex justify-between text-[13px]">
            <span className="text-muted-foreground">Subtotal</span>
            <span className="font-medium tabular-nums">{formatCurrency(subtotal)}</span>
          </div>
          {discountLabel && (
            <div className="flex justify-between text-[13px] text-emerald-600 dark:text-emerald-400">
              <span>{discountLabel}</span>
              <span className="font-medium tabular-nums">−{formatCurrency(discount)}</span>
            </div>
          )}
          <div className="flex justify-between text-[13px]">
            <span className="text-muted-foreground">VAT ({Math.round(taxRate * 100)}%)</span>
            <span className="font-medium tabular-nums">{formatCurrency(tax)}</span>
          </div>
          <div className="flex items-baseline justify-between rounded-xl border border-primary/15 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent px-3 py-2 xl:rounded-2xl xl:px-4 xl:py-2.5">
            <span className="text-sm font-semibold tracking-tight">Total</span>
            <motion.span
              key={grandTotal}
              initial={{ scale: 1.05, opacity: 0.75 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-lg font-bold tabular-nums tracking-tight text-primary xl:text-xl 2xl:text-[1.65rem]"
            >
              {formatCurrency(grandTotal)}
            </motion.span>
          </div>
        </div>

        <div className="pos-cart-actions space-y-1.5 p-3 pt-2 xl:space-y-2 xl:p-4 xl:pt-2">
          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant="secondary"
              className="h-9 gap-2 rounded-xl xl:h-10 xl:rounded-2xl"
              disabled={!hasCart || printing || !hasWaiter}
              onClick={handlePrint}
            >
              <Printer className="h-4 w-4" />
              Print
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="h-9 gap-2 rounded-xl border-amber-500/20 bg-amber-500/5 text-amber-700 hover:bg-amber-500/10 dark:text-amber-400 xl:h-10 xl:rounded-2xl"
              disabled={!hasCart || !hasWaiter}
              onClick={() => void handleHold()}
            >
              <PauseCircle className="h-4 w-4" />
              Hold
            </Button>
          </div>
          <Button
            size="lg"
            className={cn(
              "h-11 w-full gap-2 rounded-xl text-sm font-semibold tracking-tight xl:h-12 xl:rounded-2xl xl:text-[15px] 2xl:h-14",
              "bg-gradient-to-r from-primary via-primary to-emerald-600 shadow-[0_12px_32px_hsl(var(--primary)/0.28)]",
              "transition-all hover:shadow-[0_16px_40px_hsl(var(--primary)/0.34)] hover:brightness-[1.03]",
              "disabled:opacity-50 disabled:shadow-none"
            )}
            disabled={!hasCart || !hasWaiter}
            onClick={() => void handleCheckout()}
          >
            <Lock className="h-4 w-4" />
            Checkout · {formatCurrency(grandTotal)}
          </Button>
        </div>
      </div>

      <PosCartQuickCreateDialog
        mode={quickCreate}
        onClose={() => setQuickCreate(null)}
        onCreateCustomer={onCreateCustomer}
        onCreateWaiter={onCreateWaiter}
      />
    </div>
  );
}

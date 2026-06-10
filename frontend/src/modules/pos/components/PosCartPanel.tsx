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
  Sparkles,
  DollarSign,
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
import type { CartLine } from "../hooks/usePosCart";

interface PosCartPanelProps {
  cart: CartLine[];
  itemCount: number;
  subtotal: number;
  discount: number;
  discountPct: number;
  discountAmount: number;
  onDiscountPctChange: (pct: number) => void;
  onDiscountAmountChange: (amount: number) => void;
  tax: number;
  taxRate: number;
  grandTotal: number;
  orderNotes: string;
  onNotesChange: (v: string) => void;
  customerId: string;
  onCustomerChange: (id: string) => void;
  customers: { id: string; name: string }[];
  onUpdateQty: (id: string, delta: number) => void;
  onRemove: (id: string) => void;
  onOpenCheckout: () => void;
}

export function PosCartPanel({
  cart,
  itemCount,
  subtotal,
  discount,
  discountPct,
  discountAmount,
  onDiscountPctChange,
  onDiscountAmountChange,
  tax,
  taxRate,
  grandTotal,
  orderNotes,
  onNotesChange,
  customerId,
  onCustomerChange,
  customers,
  onUpdateQty,
  onRemove,
  onOpenCheckout,
}: PosCartPanelProps) {
  const hasCart = cart.length > 0;

  return (
    <div className="relative z-[2] flex h-full flex-col border-l border-border/50 bg-gradient-to-b from-card/95 via-card to-muted/30 shadow-[-12px_0_40px_rgba(0,0,0,0.08)] backdrop-blur-xl">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-primary/[0.07] to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 left-0 w-px bg-gradient-to-b from-primary/30 via-border/50 to-transparent" />

      {/* Header */}
      <div className="relative flex shrink-0 items-center justify-between border-b border-border/70 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-emerald-600 text-primary-foreground shadow-lg shadow-primary/25">
            <ShoppingCart className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight text-foreground">Current Sale</h2>
            <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Sparkles className="h-3 w-3 text-primary" />
              Terminal POS-001
            </p>
          </div>
        </div>
        <Badge className="border-0 bg-primary/10 px-2.5 py-1 font-bold tabular-nums text-primary">
          {itemCount} {itemCount === 1 ? "item" : "items"}
        </Badge>
      </div>

      {/* Customer */}
      <div className="relative shrink-0 border-b border-border/70 bg-muted/25 px-5 py-3.5">
        <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-card/80 px-3 py-2 shadow-sm backdrop-blur-sm">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <User className="h-4 w-4" />
          </div>
          <Select value={customerId} onValueChange={onCustomerChange}>
            <SelectTrigger className="h-9 flex-1 border-0 bg-transparent px-0 shadow-none focus:ring-0">
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
      </div>

      {/* Cart lines */}
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 scrollbar-thin">
        {!hasCart ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex h-full flex-col items-center justify-center py-16 text-center"
          >
            <div className="relative mb-4">
              <div className="absolute inset-0 rounded-3xl bg-primary/20 blur-xl" />
              <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl border border-border/60 bg-gradient-to-br from-muted/80 to-card shadow-inner">
                <ShoppingCart className="h-9 w-9 text-muted-foreground/60" />
              </div>
            </div>
            <p className="text-base font-semibold text-foreground">Cart is empty</p>
            <p className="mt-1.5 max-w-[220px] text-xs leading-relaxed text-muted-foreground">
              Select products from the catalog or scan a barcode to start a new sale
            </p>
          </motion.div>
        ) : (
          <AnimatePresence mode="popLayout">
            {cart.map((item, i) => (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16, height: 0 }}
                transition={{ delay: i * 0.03 }}
                className="mb-3 overflow-hidden rounded-2xl border border-border/70 bg-card/90 p-3 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="flex gap-3">
                  <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl border border-border/50 bg-muted shadow-sm">
                    {item.image ? (
                      <img
                        src={resolveMediaUrl(item.image)}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary/15 to-primary/5">
                        <ShoppingCart className="h-4 w-4 text-primary/70" />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{item.name}</p>
                    <p className="font-mono text-[10px] text-muted-foreground">{item.sku}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {formatCurrency(item.price)} each
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 shrink-0 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => onRemove(item.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center overflow-hidden rounded-xl border border-border/70 bg-muted/30 shadow-inner">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-9 w-9 rounded-none p-0 hover:bg-muted"
                      onClick={() => onUpdateQty(item.id, -1)}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <span className="w-10 text-center text-sm font-bold tabular-nums">{item.qty}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-9 w-9 rounded-none p-0 hover:bg-muted"
                      onClick={() => onUpdateQty(item.id, 1)}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <span className="text-base font-bold tabular-nums text-foreground">
                    {formatCurrency(item.price * item.qty)}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Adjustments */}
      <div className="shrink-0 space-y-3 border-t border-border/70 bg-muted/15 px-5 py-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Discount</p>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/60 px-3 py-1">
            <Percent className="h-4 w-4 shrink-0 text-primary" />
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
              className="h-9 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
            />
            <span className="shrink-0 text-xs font-medium text-muted-foreground">%</span>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/60 px-3 py-1">
            <DollarSign className="h-4 w-4 shrink-0 text-primary" />
            <Input
              type="number"
              min={0}
              step={0.01}
              value={discountAmount ? Number(discountAmount.toFixed(2)) : ""}
              placeholder="0.00"
              onChange={(e) =>
                onDiscountAmountChange(Math.max(0, parseFloat(e.target.value) || 0))
              }
              className="h-9 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
            />
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-border/50 bg-card/60 px-3 py-1">
          <StickyNote className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Input
            value={orderNotes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="Order notes..."
            className="h-9 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
          />
        </div>
      </div>

      {/* Summary */}
      <div className="shrink-0 space-y-2 border-t border-border/70 bg-card/50 px-5 py-4 backdrop-blur-sm">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Subtotal</span>
          <span className="font-medium tabular-nums">{formatCurrency(subtotal)}</span>
        </div>
        {discount > 0 && (
          <div className="flex justify-between text-sm text-success">
            <span>
              Discount
              {discountPct > 0 && ` (${Number(discountPct.toFixed(1))}%)`}
            </span>
            <span className="font-medium tabular-nums">−{formatCurrency(discount)}</span>
          </div>
        )}
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">VAT ({Math.round(taxRate * 100)}%)</span>
          <span className="font-medium tabular-nums">{formatCurrency(tax)}</span>
        </div>
        <div className="flex items-baseline justify-between rounded-2xl border border-primary/15 bg-gradient-to-br from-primary/15 via-primary/5 to-transparent px-4 py-3.5 shadow-inner">
          <span className="text-sm font-bold text-foreground">Grand Total</span>
          <motion.span
            key={grandTotal}
            initial={{ scale: 1.08, opacity: 0.7 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-2xl font-extrabold tabular-nums tracking-tight text-primary"
          >
            {formatCurrency(grandTotal)}
          </motion.span>
        </div>
      </div>

      {/* Checkout */}
      <div className="shrink-0 p-5 pt-0">
        <Button
          size="lg"
          className={cn(
            "h-14 w-full gap-2 text-base font-bold",
            "bg-gradient-to-r from-primary to-emerald-600 shadow-xl shadow-primary/30",
            "transition-all hover:shadow-2xl hover:shadow-primary/35 hover:brightness-105",
            "disabled:opacity-50 disabled:shadow-none"
          )}
          disabled={!hasCart}
          onClick={onOpenCheckout}
        >
          <Lock className="h-5 w-5" />
          Checkout · {formatCurrency(grandTotal)}
        </Button>
      </div>
    </div>
  );
}

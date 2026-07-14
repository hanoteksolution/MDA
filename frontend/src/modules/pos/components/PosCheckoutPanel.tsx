import { useEffect, useMemo, useState } from "react";
import {
  X,
  Banknote,
  Smartphone,
  Loader2,
  CheckCircle2,
  Lock,
  FileText,
  Printer,
  CalendarClock,
  Sparkles,
} from "lucide-react";
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
import {
  posApi,
  type PaymentMethod,
  type PosProfile,
  type PosReceipt,
  type PosWaiter,
} from "@/services/api/pos";
import { PosReceiptView } from "./PosReceiptView";
import { printOrderSlip } from "../receipt/printCartSlip";
import type { CartLine } from "../hooks/usePosCart";

type CheckoutPayment = Extract<PaymentMethod, "cash" | "mobile" | "on_account">;

const PAYMENT_OPTIONS: {
  id: CheckoutPayment;
  label: string;
  short: string;
  icon: typeof Banknote;
  description: string;
}[] = [
  {
    id: "cash",
    label: "Cash",
    short: "Cash",
    icon: Banknote,
    description: "Accept cash and give change",
  },
  {
    id: "mobile",
    label: "Mobile Money",
    short: "Mobile",
    icon: Smartphone,
    description: "EVC Plus, Zaad, or other wallet",
  },
  {
    id: "on_account",
    label: "Pay Later",
    short: "Credit",
    icon: CalendarClock,
    description: "Serve now, collect payment later",
  },
];

function normalizeDefault(method?: PaymentMethod): CheckoutPayment {
  if (method === "mobile" || method === "on_account") return method;
  return "cash";
}

interface PosCheckoutPanelProps {
  open: boolean;
  cart: CartLine[];
  itemCount: number;
  customerId: string;
  customerName: string;
  subtotal: number;
  discount: number;
  discountPct: number;
  tax: number;
  taxRate: number;
  grandTotal: number;
  orderNotes: string;
  branchId?: string;
  branchName?: string;
  branchCode?: string;
  waiterId?: string;
  waiterName?: string;
  waiters?: PosWaiter[];
  onClose: () => void;
  onSaveDraft?: () => void;
  onComplete: (receipt: PosReceipt) => void;
}

export function PosCheckoutPanel({
  open,
  cart,
  itemCount,
  customerId,
  customerName,
  subtotal,
  discount,
  discountPct,
  tax,
  taxRate,
  grandTotal,
  orderNotes,
  branchId,
  branchName = "Main Branch",
  branchCode,
  waiterId,
  waiterName,
  onClose,
  onSaveDraft,
  onComplete,
}: PosCheckoutPanelProps) {
  const [step, setStep] = useState<"payment" | "success">("payment");
  const [profile, setProfile] = useState<PosProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<CheckoutPayment>("cash");
  const [selectedMerchantId, setSelectedMerchantId] = useState("");
  const [amountTendered, setAmountTendered] = useState("");
  const [paymentReference, setPaymentReference] = useState("");
  const [receipt, setReceipt] = useState<PosReceipt | null>(null);

  useEffect(() => {
    if (!open) return;
    setStep("payment");
    setError(null);
    setReceipt(null);
    setAmountTendered(grandTotal.toFixed(2));
    setPaymentReference("");
    setLoadingProfile(true);
    posApi
      .profile()
      .then((res) => {
        setProfile(res.data);
        setPaymentMethod(normalizeDefault(res.data.default_payment_method));
        const mobileMerchants = res.data.merchants.filter((m) => m.provider === "mobile");
        const defaultMerchant =
          mobileMerchants.find((m) => m.is_default) ?? mobileMerchants[0];
        if (defaultMerchant) setSelectedMerchantId(defaultMerchant.id);
      })
      .catch(() =>
        setProfile({ merchants: [], default_payment_method: "cash", receipt_footer: "" })
      )
      .finally(() => setLoadingProfile(false));
  }, [open, grandTotal]);

  const mobileMerchants = useMemo(
    () => profile?.merchants.filter((m) => m.provider === "mobile") ?? [],
    [profile]
  );

  const selectedMerchant =
    profile?.merchants.find((m) => m.id === selectedMerchantId) ?? null;

  const tenderedNum = parseFloat(amountTendered) || 0;
  const change = paymentMethod === "cash" ? Math.max(0, tenderedNum - grandTotal) : 0;
  const isOnAccount = paymentMethod === "on_account";
  const needsCustomer = isOnAccount && customerId === "walkin";
  const canPayCash = paymentMethod !== "cash" || tenderedNum >= grandTotal;
  const needsMerchant = paymentMethod === "mobile";
  const needsWaiter = !waiterId;
  const canSubmit =
    canPayCash &&
    !needsCustomer &&
    !needsWaiter &&
    (!needsMerchant || mobileMerchants.length === 0 || !!selectedMerchantId);

  const activeOption = PAYMENT_OPTIONS.find((o) => o.id === paymentMethod)!;

  const buildNotes = () => {
    const parts = [orderNotes].filter(Boolean);
    if (paymentReference && paymentMethod === "mobile") {
      parts.push(`Ref: ${paymentReference}`);
    }
    return parts.join(" | ");
  };

  const handlePay = async () => {
    if (!waiterId) {
      setError("Select a waiter in the cart before checkout.");
      return;
    }
    setProcessing(true);
    setError(null);
    try {
      const res = await posApi.checkout({
        customer_id: customerId === "walkin" ? undefined : customerId,
        branch_id: branchId,
        items: cart.map((i) => ({
          product_id: i.id,
          quantity: i.qty,
          unit_price: i.price,
        })),
        discount_pct: discountPct,
        discount_amount: discount > 0 ? discount : undefined,
        tax_rate: taxRate,
        payment_method: paymentMethod,
        merchant_id: paymentMethod === "mobile" ? selectedMerchantId || undefined : undefined,
        amount_tendered: paymentMethod === "cash" ? tenderedNum : undefined,
        payment_reference: paymentReference || undefined,
        waiter_id: waiterId,
        waiter_name: waiterName || undefined,
        notes: buildNotes(),
      });
      setReceipt(res.data.receipt);
      setStep("success");
      onComplete(res.data.receipt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment failed");
    } finally {
      setProcessing(false);
    }
  };

  const handlePrintSlip = async () => {
    if (!waiterId) {
      setError("Select a waiter before printing.");
      return;
    }
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

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex bg-[hsl(var(--background)/0.88)] backdrop-blur-md">
      {/* Order summary — desktop */}
      <aside className="relative hidden w-[min(360px,32vw)] flex-col border-r border-border/50 bg-card/80 backdrop-blur-xl lg:flex">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-primary/[0.07] to-transparent" />
        <div className="relative border-b border-border/50 px-6 py-5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary/80">Your order</p>
          <p className="mt-2 text-3xl font-bold tabular-nums tracking-tight text-foreground">
            {formatCurrency(grandTotal)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {itemCount} {itemCount === 1 ? "item" : "items"}
            {discount > 0 && ` · ${formatCurrency(discount)} off`}
          </p>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 scrollbar-thin">
          {cart.map((item) => (
            <div
              key={item.id}
              className="mb-2 flex gap-3 rounded-2xl border border-border/40 bg-background/60 p-3"
            >
              <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-muted ring-1 ring-border/40">
                {item.image ? (
                  <img src={resolveMediaUrl(item.image)} alt="" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-[10px] text-muted-foreground">
                    —
                  </div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{item.name}</p>
                <p className="text-xs text-muted-foreground">
                  {item.qty} × {formatCurrency(item.price)}
                </p>
              </div>
              <span className="shrink-0 text-sm font-bold tabular-nums">
                {formatCurrency(item.price * item.qty)}
              </span>
            </div>
          ))}
        </div>

        <div className="space-y-2 border-t border-border/50 px-6 py-4 text-sm">
          <Row label="Subtotal" value={formatCurrency(subtotal)} />
          {discount > 0 && <Row label="Discount" value={`−${formatCurrency(discount)}`} accent />}
          <Row label={`VAT (${Math.round(taxRate * 100)}%)`} value={formatCurrency(tax)} />
        </div>
      </aside>

      {/* Main checkout */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-border/50 bg-card/70 px-5 py-4 backdrop-blur-xl sm:px-8">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {step === "success" ? "Complete" : "Secure checkout"}
            </p>
            <h1 className="truncate text-lg font-bold tracking-tight sm:text-xl">
              {step === "success" ? "Thank you" : "Complete payment"}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {step === "payment" && (
              <Button
                variant="secondary"
                size="sm"
                className="hidden gap-1.5 rounded-xl sm:inline-flex"
                onClick={handlePrintSlip}
                disabled={printing || needsWaiter}
              >
                <Printer className="h-4 w-4" />
                Print
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-10 w-10 rounded-xl p-0"
              onClick={onClose}
              aria-label="Close checkout"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8 scrollbar-thin">
          {step === "payment" ? (
            <div className="mx-auto flex max-w-lg flex-col gap-5">
              {/* Mobile total */}
              <div className="rounded-2xl border border-primary/15 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-5 lg:hidden">
                <p className="text-xs font-medium text-muted-foreground">{itemCount} items · {customerName}</p>
                <p className="mt-1 text-3xl font-bold tabular-nums text-primary">{formatCurrency(grandTotal)}</p>
              </div>

              {/* Context chips */}
              <div className="flex flex-wrap gap-2">
                <Chip label={customerName} />
                {waiterName ? (
                  <Chip label={`Waiter · ${waiterName}`} />
                ) : (
                  <Chip label="Waiter required" muted />
                )}
                <Chip label={branchName} muted />
              </div>

              {needsWaiter && (
                <p className="rounded-xl bg-amber-500/10 px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300 ring-1 ring-amber-500/20">
                  Close checkout and select a waiter on the cart before you can print or pay.
                </p>
              )}

              {/* Payment picker */}
              <div className="rounded-[1.25rem] border border-border/60 bg-card p-1.5 shadow-[0_8px_30px_hsl(var(--foreground)/0.04)]">
                <div className="grid grid-cols-3 gap-1">
                  {PAYMENT_OPTIONS.map(({ id, short, icon: Icon }) => {
                    const active = paymentMethod === id;
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setPaymentMethod(id)}
                        className={cn(
                          "flex flex-col items-center gap-1.5 rounded-xl px-2 py-3.5 transition-all duration-200",
                          active
                            ? "bg-primary text-primary-foreground shadow-md shadow-primary/25"
                            : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                        )}
                      >
                        <Icon className="h-5 w-5" strokeWidth={active ? 2.25 : 2} />
                        <span className="text-[11px] font-semibold sm:text-xs">{short}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Payment details */}
              <div className="rounded-[1.25rem] border border-border/60 bg-card p-5 shadow-[0_8px_30px_hsl(var(--foreground)/0.04)]">
                <div className="mb-4 flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <activeOption.icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-semibold">{activeOption.label}</p>
                    <p className="text-xs text-muted-foreground">{activeOption.description}</p>
                  </div>
                </div>

                {loadingProfile ? (
                  <div className="h-20 animate-pulse rounded-xl bg-muted/60" />
                ) : (
                  <>
                    {paymentMethod === "cash" && (
                      <div className="space-y-4">
                        <div>
                          <label className="mb-2 block text-xs font-medium text-muted-foreground">
                            Amount received
                          </label>
                          <Input
                            type="number"
                            min={0}
                            step="0.01"
                            value={amountTendered}
                            onChange={(e) => setAmountTendered(e.target.value)}
                            className="h-14 rounded-xl border-border/60 bg-muted/20 text-center text-2xl font-bold tabular-nums"
                            autoFocus
                          />
                        </div>
                        {tenderedNum >= grandTotal && tenderedNum > 0 && (
                          <div className="flex items-center justify-between rounded-xl bg-primary/5 px-4 py-3 ring-1 ring-primary/10">
                            <span className="text-sm text-muted-foreground">Change</span>
                            <span className="text-lg font-bold tabular-nums text-primary">
                              {formatCurrency(change)}
                            </span>
                          </div>
                        )}
                        <div className="flex flex-wrap gap-2">
                          {[grandTotal, Math.ceil(grandTotal / 5) * 5, Math.ceil(grandTotal / 10) * 10].map(
                            (amt, i) => (
                              <button
                                key={i}
                                type="button"
                                onClick={() => setAmountTendered(String(amt))}
                                className="rounded-full border border-border/60 bg-background px-4 py-1.5 text-sm font-medium tabular-nums transition-colors hover:border-primary/40 hover:bg-primary/5"
                              >
                                {formatCurrency(amt)}
                              </button>
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {paymentMethod === "mobile" && (
                      <div className="space-y-4">
                        {mobileMerchants.length > 0 ? (
                          <>
                            <div>
                              <label className="mb-2 block text-xs font-medium text-muted-foreground">
                                Provider
                              </label>
                              <Select value={selectedMerchantId} onValueChange={setSelectedMerchantId}>
                                <SelectTrigger className="h-12 rounded-xl">
                                  <SelectValue placeholder="Select wallet" />
                                </SelectTrigger>
                                <SelectContent>
                                  {mobileMerchants.map((m) => (
                                    <SelectItem key={m.id} value={m.id}>
                                      {m.label || m.company_name}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            {selectedMerchant && (
                              <div className="rounded-xl bg-muted/40 px-4 py-3 ring-1 ring-border/50">
                                <p className="text-xs text-muted-foreground">Send payment to</p>
                                <p className="font-mono text-sm font-semibold text-primary">
                                  {selectedMerchant.merchant_number}
                                </p>
                              </div>
                            )}
                          </>
                        ) : (
                          <p className="rounded-xl border border-dashed border-border px-4 py-3 text-sm text-muted-foreground">
                            Add mobile wallet numbers in Settings → POS Profile.
                          </p>
                        )}
                        <div>
                          <label className="mb-2 block text-xs font-medium text-muted-foreground">
                            Reference (optional)
                          </label>
                          <Input
                            value={paymentReference}
                            onChange={(e) => setPaymentReference(e.target.value)}
                            placeholder="Transaction ID"
                            className="h-11 rounded-xl"
                          />
                        </div>
                      </div>
                    )}

                    {isOnAccount && (
                      <div className="space-y-3 rounded-xl bg-amber-500/[0.07] px-4 py-4 ring-1 ring-amber-500/20">
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                          Customer receives products now. Payment is collected later.
                        </p>
                        {needsCustomer ? (
                          <p className="text-sm font-medium text-destructive">
                            Choose a registered customer in the cart before continuing.
                          </p>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Invoice stays open for 30 days · {customerName}
                          </p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Desktop total reminder */}
              <div className="hidden items-center justify-between rounded-2xl border border-border/50 bg-muted/30 px-5 py-4 lg:flex">
                <span className="text-sm text-muted-foreground">Amount due</span>
                <span className="text-2xl font-bold tabular-nums">{formatCurrency(grandTotal)}</span>
              </div>

              {error && (
                <p className="rounded-xl bg-destructive/10 px-4 py-3 text-center text-sm text-destructive">
                  {error}
                </p>
              )}
            </div>
          ) : receipt ? (
            <div className="mx-auto max-w-md space-y-6 py-4">
              <div className="flex flex-col items-center text-center">
                <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 ring-8 ring-emerald-500/5">
                  <CheckCircle2 className="h-10 w-10" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">
                  {receipt.payment_method === "on_account" ? "Sale recorded" : "Payment complete"}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">{receipt.invoice_number}</p>
                <p className="mt-3 text-3xl font-bold tabular-nums text-primary">
                  {formatCurrency(receipt.total_amount)}
                </p>
              </div>
              <PosReceiptView receipt={receipt} compact onNewSale={onClose} />
            </div>
          ) : null}
        </div>

        {step === "payment" && (
          <footer className="shrink-0 border-t border-border/50 bg-card/80 px-4 py-4 backdrop-blur-xl sm:px-8">
            <div className="mx-auto flex max-w-lg flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex gap-2 sm:mr-auto">
                <Button
                  variant="secondary"
                  className="h-12 flex-1 rounded-xl sm:flex-none sm:px-6"
                  onClick={onClose}
                  disabled={processing}
                >
                  Cancel
                </Button>
                {onSaveDraft && (
                  <Button
                    variant="secondary"
                    className="h-12 gap-2 rounded-xl"
                    onClick={() => {
                      onSaveDraft();
                      onClose();
                    }}
                    disabled={processing}
                  >
                    <FileText className="h-4 w-4" />
                    <span className="hidden sm:inline">Hold</span>
                  </Button>
                )}
              </div>
              <Button
                size="lg"
                className={cn(
                  "h-14 w-full gap-2 rounded-2xl text-base font-semibold sm:w-auto sm:min-w-[240px]",
                  "bg-gradient-to-r from-primary to-emerald-600 shadow-lg shadow-primary/25",
                  "hover:brightness-[1.03] disabled:shadow-none"
                )}
                disabled={!canSubmit || processing}
                onClick={handlePay}
              >
                {processing ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Processing…
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4" />
                    {isOnAccount ? "Record sale" : "Pay"}
                    <span className="tabular-nums">{formatCurrency(grandTotal)}</span>
                  </>
                )}
              </Button>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={cn("flex justify-between", accent ? "text-emerald-600" : "text-muted-foreground")}>
      <span>{label}</span>
      <span className="font-medium tabular-nums text-foreground">{value}</span>
    </div>
  );
}

function Chip({ label, muted }: { label: string; muted?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium ring-1",
        muted
          ? "bg-muted/40 text-muted-foreground ring-border/50"
          : "bg-primary/5 text-foreground ring-primary/15"
      )}
    >
      {!muted && <Sparkles className="h-3 w-3 text-primary/70" />}
      {label}
    </span>
  );
}

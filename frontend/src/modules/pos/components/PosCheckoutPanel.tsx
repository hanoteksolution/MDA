import { useEffect, useMemo, useState } from "react";
import {
  X,
  Banknote,
  CreditCard,
  Smartphone,
  Split,
  Landmark,
  Loader2,
  CheckCircle2,
  Check,
  User,
  UserCircle,
  MapPin,
  Wallet,
  Lock,
  ArrowRight,
  FileText,
  ShieldCheck,
  Plus,
  Gift,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn, formatCurrency } from "@/utils/cn";
import {
  posApi,
  type PaymentMethod,
  type PosProfile,
  type PosReceipt,
} from "@/services/api/pos";
import { PosReceiptView } from "./PosReceiptView";
import type { CartLine } from "../hooks/usePosCart";

const PAYMENT_METHODS: {
  id: PaymentMethod;
  label: string;
  icon: typeof Banknote;
}[] = [
  { id: "cash", label: "Cash", icon: Banknote },
  { id: "card", label: "Card", icon: CreditCard },
  { id: "mobile", label: "Mobile Money", icon: Smartphone },
  { id: "bank", label: "Bank Transfer", icon: Landmark },
  { id: "split", label: "Split Payment", icon: Split },
];

const STEPS = [
  { id: 1, label: "Order Review" },
  { id: 2, label: "Payment Method" },
  { id: 3, label: "Confirmation" },
];

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
  cashierName?: string;
  cashierRole?: string;
  onClose: () => void;
  onSaveDraft?: () => void;
  onComplete: (receipt: PosReceipt) => void;
}

function Stepper({ activeStep }: { activeStep: number }) {
  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, idx) => {
        const done = activeStep > step.id;
        const active = activeStep === step.id;
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors",
                  done && "bg-primary text-primary-foreground",
                  active && "bg-primary text-primary-foreground ring-4 ring-primary/20",
                  !done && !active && "bg-muted text-muted-foreground"
                )}
              >
                {done ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : step.id}
              </div>
              <span
                className={cn(
                  "hidden sm:inline text-sm font-medium",
                  active || done ? "text-foreground" : "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div
                className={cn(
                  "mx-3 h-px w-8 sm:w-16",
                  done ? "bg-primary" : "bg-border"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
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
  branchCode = "BR01",
  cashierName = "Cashier",
  cashierRole = "Staff",
  onClose,
  onSaveDraft,
  onComplete,
}: PosCheckoutPanelProps) {
  const [step, setStep] = useState<"payment" | "success">("payment");
  const [profile, setProfile] = useState<PosProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("mobile");
  const [selectedMerchantId, setSelectedMerchantId] = useState("");
  const [amountTendered, setAmountTendered] = useState("");
  const [mobilePhone, setMobilePhone] = useState("");
  const [accountName, setAccountName] = useState("");
  const [paymentReference, setPaymentReference] = useState("");
  const [receipt, setReceipt] = useState<PosReceipt | null>(null);

  const draftInvoiceRef = useMemo(
    () => `#INV-${new Date().getFullYear()}-${String(Date.now()).slice(-6)}`,
    [open]
  );

  const loyaltyPoints = Math.floor(grandTotal / 10);

  useEffect(() => {
    if (!open) return;
    setStep("payment");
    setError(null);
    setReceipt(null);
    setAmountTendered("");
    setMobilePhone("");
    setAccountName("");
    setPaymentReference("");
    setLoadingProfile(true);
    posApi
      .profile()
      .then((res) => {
        setProfile(res.data);
        setPaymentMethod(res.data.default_payment_method || "mobile");
        const defaultMerchant =
          res.data.merchants.find((m) => m.is_default) ?? res.data.merchants[0];
        if (defaultMerchant) setSelectedMerchantId(defaultMerchant.id);
      })
      .catch(() =>
        setProfile({ merchants: [], default_payment_method: "mobile", receipt_footer: "" })
      )
      .finally(() => setLoadingProfile(false));
  }, [open]);

  const filteredMerchants = useMemo(() => {
    if (!profile) return [];
    if (paymentMethod === "card") {
      return profile.merchants.filter((m) => m.provider === "card");
    }
    if (paymentMethod === "mobile") {
      return profile.merchants.filter((m) => m.provider === "mobile");
    }
    if (paymentMethod === "bank") {
      return profile.merchants.filter((m) => m.provider === "bank");
    }
    return profile.merchants;
  }, [profile, paymentMethod]);

  const selectedMerchant =
    profile?.merchants.find((m) => m.id === selectedMerchantId) ?? null;

  const tenderedNum = parseFloat(amountTendered) || 0;
  const change = paymentMethod === "cash" ? Math.max(0, tenderedNum - grandTotal) : 0;
  const canPayCash = paymentMethod !== "cash" || tenderedNum >= grandTotal;
  const needsMerchant =
    paymentMethod === "card" || paymentMethod === "mobile" || paymentMethod === "bank";
  const canSubmit =
    canPayCash &&
    (!needsMerchant || filteredMerchants.length === 0 || !!selectedMerchantId);

  const buildNotes = () => {
    const parts = [orderNotes].filter(Boolean);
    if (paymentMethod === "mobile" || paymentMethod === "bank") {
      if (mobilePhone) parts.push(`Phone: +254${mobilePhone.replace(/^\+254/, "")}`);
      if (accountName) parts.push(`Account: ${accountName}`);
      if (paymentReference) parts.push(`Ref: ${paymentReference}`);
    }
    return parts.join(" | ");
  };

  const handlePay = async () => {
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
        merchant_id: selectedMerchantId || undefined,
        amount_tendered: paymentMethod === "cash" ? tenderedNum : undefined,
        payment_reference: paymentReference || undefined,
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

  if (!open) return null;

  const activeStep = step === "success" ? 3 : 2;

  return (
    <div className="fixed inset-0 z-50 flex bg-background">
      {/* ── Left: Order Summary ── */}
      <aside className="hidden lg:flex w-[360px] xl:w-[400px] flex-col border-r border-border bg-card shrink-0">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-base font-bold text-foreground">Order Summary</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {itemCount} {itemCount === 1 ? "Item" : "Items"}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin">
          {cart.map((item) => (
            <div key={item.id} className="flex gap-3 rounded-xl p-2 hover:bg-muted/40 transition-colors">
              <div className="h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-muted border border-border">
                {item.image ? (
                  <img src={item.image} alt="" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-muted-foreground text-xs">
                    N/A
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-snug line-clamp-2">{item.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {item.qty} × {formatCurrency(item.price)}
                </p>
              </div>
              <span className="text-sm font-semibold tabular-nums shrink-0 self-start">
                {formatCurrency(item.price * item.qty)}
              </span>
            </div>
          ))}
        </div>

        <div className="border-t border-border px-5 py-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Subtotal</span>
            <span className="tabular-nums">{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Discount</span>
            <span className="tabular-nums">{formatCurrency(discount)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">VAT ({Math.round(taxRate * 100)}%)</span>
            <span className="tabular-nums">{formatCurrency(tax)}</span>
          </div>
          <div className="flex justify-between items-baseline pt-2 border-t border-border">
            <span className="text-sm font-semibold">Total</span>
            <span className="text-2xl font-bold text-primary tabular-nums">
              {formatCurrency(grandTotal)}
            </span>
          </div>
        </div>

        <div className="mx-4 mb-4 rounded-xl bg-primary/10 border border-primary/20 px-4 py-3 text-center">
          <p className="text-sm font-medium text-primary">
            You will earn {loyaltyPoints} Points
          </p>
        </div>
      </aside>

      {/* ── Main checkout ── */}
      <div className="flex flex-1 flex-col min-w-0 bg-muted/20">
        {/* Header */}
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-4 sm:px-6 py-4 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-xl font-bold truncate">
              {step === "success" ? "Confirmation" : "Checkout"}
            </h1>
            {step === "payment" && (
              <Badge variant="default" className="font-mono text-[11px] shrink-0">
                {draftInvoiceRef}
              </Badge>
            )}
            {receipt && (
              <Badge variant="success" className="font-mono text-[11px] shrink-0">
                {receipt.invoice_number}
              </Badge>
            )}
          </div>
          <Stepper activeStep={activeStep} />
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0 shrink-0" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </header>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 scrollbar-thin">
          {step === "payment" ? (
            <div className="mx-auto max-w-6xl">
              {/* Mobile summary strip */}
              <div className="lg:hidden rounded-xl border border-border bg-card p-4 mb-6 flex justify-between items-center">
                <div>
                  <p className="text-xs text-muted-foreground">{itemCount} items</p>
                  <p className="text-xl font-bold text-primary">{formatCurrency(grandTotal)}</p>
                </div>
                <Badge variant="default" className="font-mono text-[10px]">{draftInvoiceRef}</Badge>
              </div>

              <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_1fr]">
                {/* Left info cards */}
                <div className="space-y-4">
                  {/* Customer */}
                  <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <User className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            Customer
                          </p>
                          <p className="font-semibold truncate">{customerName}</p>
                          <Badge variant="secondary" className="mt-1 text-[10px]">
                            {customerId === "walkin" ? "Regular" : "Registered"}
                          </Badge>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" className="text-xs text-primary shrink-0 h-8">
                        Change
                      </Button>
                    </div>
                  </div>

                  {/* Cashier */}
                  <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                        <UserCircle className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Cashier
                        </p>
                        <p className="font-semibold">{cashierName}</p>
                        <p className="text-xs text-muted-foreground">{cashierRole}</p>
                      </div>
                    </div>
                  </div>

                  {/* Branch */}
                  <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                        <MapPin className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Branch
                        </p>
                        <p className="font-semibold">{branchName}</p>
                        <p className="text-xs text-muted-foreground font-mono">{branchCode}</p>
                      </div>
                    </div>
                  </div>

                  {/* Grand Total card */}
                  <div className="rounded-xl bg-primary p-5 text-primary-foreground shadow-lg shadow-primary/25 relative overflow-hidden">
                    <div className="absolute right-4 top-4 opacity-20">
                      <Wallet className="h-16 w-16" />
                    </div>
                    <p className="text-xs font-medium uppercase tracking-widest opacity-90">
                      Grand Total
                    </p>
                    <p className="text-3xl font-bold mt-1 tabular-nums">
                      {formatCurrency(grandTotal)}
                    </p>
                    <p className="text-xs mt-2 opacity-90">
                      Includes VAT of {formatCurrency(tax)} ({Math.round(taxRate * 100)}%)
                    </p>
                  </div>
                </div>

                {/* Right: payment */}
                <div className="rounded-xl border border-border bg-card p-5 sm:p-6 shadow-sm space-y-6">
                  <div>
                    <h3 className="text-base font-bold mb-4">Select Payment Method</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3">
                      {PAYMENT_METHODS.map(({ id, label, icon: Icon }) => {
                        const selected = paymentMethod === id;
                        return (
                          <button
                            key={id}
                            type="button"
                            onClick={() => setPaymentMethod(id)}
                            className={cn(
                              "relative flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all",
                              selected
                                ? "border-primary bg-primary/5 shadow-sm"
                                : "border-border bg-background hover:border-primary/30 hover:bg-muted/30"
                            )}
                          >
                            {selected && (
                              <span className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                <Check className="h-3 w-3" strokeWidth={3} />
                              </span>
                            )}
                            <Icon className={cn("h-6 w-6", selected ? "text-primary" : "text-muted-foreground")} />
                            <span className={cn("text-xs sm:text-sm font-medium text-center leading-tight", selected && "text-primary")}>
                              {label}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Dynamic payment details */}
                  {loadingProfile ? (
                    <div className="h-32 animate-pulse rounded-xl bg-muted" />
                  ) : (
                    <>
                      {paymentMethod === "cash" && (
                        <div className="space-y-3 rounded-xl bg-muted/30 border border-border p-4">
                          <p className="text-sm font-semibold">Cash Payment</p>
                          <FormRow label="Amount Tendered">
                            <Input
                              type="number"
                              min={0}
                              step="0.01"
                              value={amountTendered}
                              onChange={(e) => setAmountTendered(e.target.value)}
                              placeholder={grandTotal.toFixed(2)}
                              className="h-11 text-lg font-semibold"
                              autoFocus
                            />
                          </FormRow>
                          {tenderedNum > 0 && (
                            <p className="text-sm">
                              Change:{" "}
                              <span className="font-bold text-primary">{formatCurrency(change)}</span>
                            </p>
                          )}
                          <div className="flex flex-wrap gap-2">
                            {[grandTotal, Math.ceil(grandTotal / 5) * 5, Math.ceil(grandTotal / 10) * 10].map(
                              (amt, i) => (
                                <Button
                                  key={i}
                                  type="button"
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => setAmountTendered(String(amt))}
                                >
                                  {formatCurrency(amt)}
                                </Button>
                              )
                            )}
                          </div>
                        </div>
                      )}

                      {(paymentMethod === "mobile" || paymentMethod === "bank") && (
                        <div className="space-y-4 rounded-xl bg-muted/30 border border-border p-4">
                          <p className="text-sm font-semibold">
                            {paymentMethod === "mobile" ? "Mobile Money Details" : "Bank Transfer Details"}
                          </p>

                          <FormRow label="Provider">
                            {filteredMerchants.length > 0 ? (
                              <Select
                                value={selectedMerchantId}
                                onValueChange={setSelectedMerchantId}
                              >
                                <SelectTrigger className="h-11 bg-background">
                                  <SelectValue placeholder="Select provider" />
                                </SelectTrigger>
                                <SelectContent>
                                  {filteredMerchants.map((m) => (
                                    <SelectItem key={m.id} value={m.id}>
                                      {m.label || m.company_name} — {m.merchant_number}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            ) : (
                              <div className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-background px-3 py-2.5 text-sm text-muted-foreground">
                                <Plus className="h-4 w-4 shrink-0" />
                                Add merchants in Settings → POS Profile
                              </div>
                            )}
                          </FormRow>

                          {selectedMerchant && (
                            <div className="rounded-lg bg-primary/5 border border-primary/20 px-3 py-2 text-sm">
                              <p className="font-medium">{selectedMerchant.company_name}</p>
                              <p className="font-mono text-primary text-xs mt-0.5">
                                {selectedMerchant.merchant_number}
                              </p>
                            </div>
                          )}

                          <FormRow label="Phone Number">
                            <div className="flex gap-2">
                              <span className="flex h-11 items-center rounded-lg border border-border bg-muted px-3 text-sm text-muted-foreground shrink-0">
                                +254
                              </span>
                              <Input
                                value={mobilePhone}
                                onChange={(e) => setMobilePhone(e.target.value.replace(/\D/g, ""))}
                                placeholder="712 345 678"
                                className="h-11 bg-background"
                              />
                            </div>
                          </FormRow>

                          <FormRow label="Account Name (Optional)">
                            <Input
                              value={accountName}
                              onChange={(e) => setAccountName(e.target.value)}
                              placeholder="Customer name"
                              className="h-11 bg-background"
                            />
                          </FormRow>

                          <FormRow label="Reference / Notes (Optional)">
                            <Input
                              value={paymentReference}
                              onChange={(e) => setPaymentReference(e.target.value)}
                              placeholder="Transaction reference"
                              className="h-11 bg-background"
                            />
                          </FormRow>

                          <div className="flex items-start gap-2 rounded-lg bg-success/10 border border-success/20 px-3 py-2.5">
                            <ShieldCheck className="h-4 w-4 text-success shrink-0 mt-0.5" />
                            <p className="text-xs text-success">
                              Secure payment powered by your selected{" "}
                              {paymentMethod === "mobile" ? "mobile money" : "bank"} provider.
                            </p>
                          </div>
                        </div>
                      )}

                      {paymentMethod === "card" && (
                        <div className="space-y-3 rounded-xl bg-muted/30 border border-border p-4">
                          <p className="text-sm font-semibold">Card Payment</p>
                          {filteredMerchants.length > 0 ? (
                            <div className="grid gap-2 sm:grid-cols-2">
                              {filteredMerchants.map((m) => (
                                <button
                                  key={m.id}
                                  type="button"
                                  onClick={() => setSelectedMerchantId(m.id)}
                                  className={cn(
                                    "rounded-xl border-2 p-3 text-left transition-all",
                                    selectedMerchantId === m.id
                                      ? "border-primary bg-primary/5"
                                      : "border-border bg-background hover:border-primary/30"
                                  )}
                                >
                                  <p className="font-medium text-sm">{m.company_name}</p>
                                  <p className="font-mono text-xs text-primary mt-0.5">
                                    {m.merchant_number}
                                  </p>
                                </button>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              Configure card merchant numbers in Settings → POS Profile.
                            </p>
                          )}
                        </div>
                      )}

                      {paymentMethod === "split" && (
                        <div className="rounded-xl bg-muted/30 border border-border p-4 text-sm text-muted-foreground">
                          Split payment: complete the primary portion now. Remaining balance can be
                          collected separately.
                        </div>
                      )}
                    </>
                  )}

                  {error && (
                    <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                      {error}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ) : receipt ? (
            <div className="mx-auto w-full max-w-2xl space-y-6 px-2">
              <div className="flex flex-col items-center text-center">
                <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 ring-8 ring-emerald-500/10">
                  <CheckCircle2 className="h-10 w-10" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">Payment Successful!</h2>
                <p className="mt-1 text-muted-foreground">Thank you for your purchase.</p>
              </div>

              <div className="rounded-2xl border border-border/70 bg-card p-6 shadow-lg">
                <p className="text-center text-sm font-medium text-muted-foreground">Amount Received</p>
                <p className="text-center text-4xl font-extrabold tabular-nums text-primary">
                  {formatCurrency(receipt.total_amount)}
                </p>
                <p className="mt-1 text-center text-sm text-emerald-600">
                  Paid via {receipt.payment_method_label ?? receipt.payment_method}
                </p>
                <div className="mt-4 grid gap-2 rounded-xl bg-muted/40 p-4 text-sm sm:grid-cols-2">
                  <div>
                    <span className="text-muted-foreground">Receipt #</span>
                    <p className="font-mono font-semibold">{receipt.invoice_number}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Customer</span>
                    <p className="font-medium">{receipt.customer_name}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Cashier</span>
                    <p className="font-medium">{receipt.cashier}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Terminal</span>
                    <p className="font-medium">{receipt.terminal}</p>
                  </div>
                </div>
                {(receipt.loyalty_points_earned ?? loyaltyPoints) > 0 && (
                  <div className="mt-4 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3">
                    <Gift className="h-5 w-5 text-primary" />
                    <div className="text-sm">
                      <p className="font-semibold text-primary">
                        You earned {receipt.loyalty_points_earned ?? loyaltyPoints} points
                      </p>
                      <p className="text-muted-foreground">
                        Total points: {(receipt.loyalty_points_total ?? loyaltyPoints + 1160).toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <PosReceiptView receipt={receipt} compact onNewSale={onClose} />
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <footer className="border-t border-border bg-card px-4 sm:px-6 py-4 shrink-0">
          {step === "payment" ? (
            <div className="mx-auto max-w-6xl flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                className="h-11 gap-2"
                onClick={onClose}
                disabled={processing}
              >
                <X className="h-4 w-4" />
                Cancel
              </Button>
              {onSaveDraft && (
                <Button
                  variant="secondary"
                  className="h-11 gap-2"
                  onClick={() => {
                    onSaveDraft();
                    onClose();
                  }}
                  disabled={processing}
                >
                  <FileText className="h-4 w-4" />
                  Save Draft
                </Button>
              )}
              <Button
                className="h-11 gap-2 ml-auto min-w-[220px] text-base font-semibold shadow-lg shadow-primary/20"
                disabled={!canSubmit || processing}
                onClick={handlePay}
              >
                {processing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4" />
                    Complete Payment
                    <span className="tabular-nums">{formatCurrency(grandTotal)}</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          ) : null}
        </footer>
      </div>
    </div>
  );
}

function FormRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

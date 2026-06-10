import { useEffect, useState } from "react";
import {
  Gift,
  Package,
  RotateCcw,
  ShieldCheck,
  Store,
  User,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { resolveMediaUrl } from "@/config/api";
import { cn, formatCurrency } from "@/utils/cn";
import type { PosReceipt } from "@/services/api/pos";
import { generateBarcodeDataUrl, generateQrDataUrl } from "./receiptAssets";
import {
  formatReceiptDate,
  getCompanyLogoUrl,
  getMerchantRef,
  getPaymentLabel,
  getTaxRateLabel,
  getVerificationUrl,
} from "./receiptFormat";

interface DigitalReceiptProps {
  receipt: PosReceipt;
  className?: string;
  showCodes?: boolean;
}

export function DigitalReceipt({ receipt, className, showCodes = true }: DigitalReceiptProps) {
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [barcodeUrl, setBarcodeUrl] = useState<string | null>(null);

  const logoUrl = getCompanyLogoUrl(receipt);
  const paymentLabel = getPaymentLabel(receipt);
  const taxLabel = getTaxRateLabel(receipt);
  const merchantRef = getMerchantRef(receipt);
  const loyaltyEarned = receipt.loyalty_points_earned ?? Math.floor(receipt.total_amount / 10);
  const loyaltyTotal = receipt.loyalty_points_total ?? loyaltyEarned + 1160;
  const verificationUrl = getVerificationUrl(receipt);

  useEffect(() => {
    if (!showCodes) return;
    let active = true;
    generateQrDataUrl(verificationUrl, 120).then((url) => {
      if (active) setQrUrl(url);
    });
    setBarcodeUrl(generateBarcodeDataUrl(receipt.invoice_number, 1.6, 44));
    return () => {
      active = false;
    };
  }, [receipt.invoice_number, showCodes, verificationUrl]);

  return (
    <article
      className={cn(
        "overflow-hidden rounded-2xl border border-border/70 bg-card shadow-xl shadow-black/5",
        className
      )}
    >
      {/* Header */}
      <header className="border-b border-border/60 bg-gradient-to-br from-card via-card to-muted/30 px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-4">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt=""
                className="h-12 w-12 shrink-0 rounded-xl border border-border/60 bg-white object-contain p-1"
              />
            ) : (
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Store className="h-6 w-6" />
              </div>
            )}
            <div className="min-w-0">
              <h2 className="text-lg font-bold tracking-tight text-foreground">
                {receipt.company.name}
              </h2>
              {receipt.company.legal_name && (
                <p className="text-xs text-muted-foreground">{receipt.company.legal_name}</p>
              )}
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {receipt.company.address}
              </p>
              <p className="text-xs text-muted-foreground">
                {receipt.company.phone}
                {receipt.company.email ? ` · ${receipt.company.email}` : ""}
              </p>
              {receipt.company.tax_id && (
                <p className="text-xs text-muted-foreground">Tax ID: {receipt.company.tax_id}</p>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
              Invoice / Receipt
            </p>
            <Badge className="mt-1 font-mono text-sm font-bold">{receipt.invoice_number}</Badge>
            {barcodeUrl && showCodes && (
              <img src={barcodeUrl} alt="" className="ml-auto mt-2 h-10 max-w-[140px]" />
            )}
          </div>
        </div>
      </header>

      {/* Meta grid */}
      <div className="grid grid-cols-2 gap-px border-b border-border/60 bg-border/40 sm:grid-cols-4">
        {[
          { label: "Date & Time", value: formatReceiptDate(receipt) },
          { label: "Cashier", value: receipt.cashier },
          { label: "Payment", value: paymentLabel },
          { label: "Reference", value: merchantRef },
        ].map((cell) => (
          <div key={cell.label} className="bg-card px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {cell.label}
            </p>
            <p className="mt-0.5 text-sm font-medium text-foreground">{cell.value}</p>
          </div>
        ))}
      </div>

      {/* Branch + customer */}
      <div className="space-y-3 border-b border-border/60 px-6 py-4">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Store className="h-4 w-4 text-primary" />
          <span className="font-semibold">{receipt.branch.name}</span>
          <span className="text-muted-foreground">({receipt.branch.code})</span>
          {receipt.branch.address && (
            <span className="text-xs text-muted-foreground">· {receipt.branch.address}</span>
          )}
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
            <User className="h-4 w-4" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Customer
            </p>
            <p className="text-sm font-semibold">{receipt.customer_name}</p>
          </div>
          <span className="ml-auto text-xs text-muted-foreground">{receipt.terminal}</span>
        </div>
      </div>

      {/* Line items */}
      <div className="px-6 py-4">
        <p className="mb-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Order Items
        </p>
        <div className="space-y-3">
          {receipt.items.map((item, idx) => {
            const imageUrl = resolveMediaUrl(item.image);
            return (
              <div
                key={`${item.sku}-${idx}`}
                className="flex items-center gap-3 rounded-xl border border-border/50 bg-muted/20 px-3 py-2.5"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border/60 bg-card">
                  {imageUrl ? (
                    <img src={imageUrl} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <Package className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{item.name}</p>
                  <p className="text-[11px] text-muted-foreground">SKU: {item.sku}</p>
                </div>
                <div className="shrink-0 text-right text-xs">
                  <p className="text-muted-foreground">
                    {item.quantity} × {formatCurrency(item.unit_price)}
                  </p>
                  <p className="font-bold tabular-nums">{formatCurrency(item.line_total)}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Totals */}
      <div className="border-t border-border/60 bg-muted/20 px-6 py-4">
        <div className="ml-auto max-w-xs space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Subtotal</span>
            <span className="tabular-nums">{formatCurrency(receipt.subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Discount</span>
            <span className="tabular-nums text-emerald-600">
              {receipt.discount_amount > 0
                ? `−${formatCurrency(receipt.discount_amount)}`
                : formatCurrency(0)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">{taxLabel}</span>
            <span className="tabular-nums">{formatCurrency(receipt.tax_amount)}</span>
          </div>
          <div className="flex items-baseline justify-between border-t border-border/60 pt-3">
            <span className="text-base font-bold">Grand Total</span>
            <span className="text-2xl font-extrabold tabular-nums text-primary">
              {formatCurrency(receipt.total_amount)}
            </span>
          </div>
          {receipt.payment_method === "cash" && receipt.amount_tendered != null && (
            <>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Tendered</span>
                <span className="tabular-nums">{formatCurrency(receipt.amount_tendered)}</span>
              </div>
              <div className="flex justify-between text-xs font-medium">
                <span>Change</span>
                <span className="tabular-nums">{formatCurrency(receipt.change ?? 0)}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Payment verification */}
      <div className="mx-6 mb-4 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
        <div>
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
            Paid via {paymentLabel}
          </p>
          <p className="text-xs text-muted-foreground">Ref: {merchantRef}</p>
        </div>
        <Badge variant="success" className="font-bold uppercase tracking-wider">
          Paid
        </Badge>
        {qrUrl && showCodes && (
          <div className="flex items-center gap-3">
            <img src={qrUrl} alt="Verify receipt" className="h-16 w-16 rounded-lg border border-border/60 bg-white p-1" />
            <div className="max-w-[140px]">
              <p className="text-[10px] font-semibold text-muted-foreground">Verify receipt</p>
              <p className="break-all text-[9px] text-muted-foreground">{verificationUrl}</p>
            </div>
          </div>
        )}
      </div>

      {/* Footer info cards */}
      <div className="grid gap-px border-t border-border/60 bg-border/40 sm:grid-cols-3">
        <div className="flex gap-3 bg-card px-4 py-4">
          <ShieldCheck className="h-5 w-5 shrink-0 text-primary" />
          <div>
            <p className="text-xs font-bold">Secure Payment</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
              Your payment is 100% secure. Thank you!
            </p>
          </div>
        </div>
        <div className="flex gap-3 bg-card px-4 py-4">
          <Gift className="h-5 w-5 shrink-0 text-primary" />
          <div>
            <p className="text-xs font-bold">Loyalty Points</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
              You earned <strong className="text-foreground">{loyaltyEarned}</strong> points.
              Total: <strong className="text-foreground">{loyaltyTotal.toLocaleString()}</strong>
            </p>
          </div>
        </div>
        <div className="flex gap-3 bg-card px-4 py-4">
          <RotateCcw className="h-5 w-5 shrink-0 text-primary" />
          <div>
            <p className="text-xs font-bold">Return Policy</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
              {receipt.return_policy ??
                "Items can be returned within 7 days with original receipt."}
            </p>
          </div>
        </div>
      </div>

      {/* Thank you band */}
      <footer className="bg-gradient-to-r from-slate-900 to-slate-800 px-6 py-4 text-center text-sm font-medium text-white">
        {receipt.footer}
      </footer>
    </article>
  );
}

import { resolveMediaUrl } from "@/config/api";
import type { PosReceipt } from "@/services/api/pos";

export type ThermalWidth = "58mm" | "80mm";

export function getPaymentLabel(receipt: PosReceipt): string {
  return receipt.payment_method_label ?? receipt.payment_method.replace(/_/g, " ");
}

/** Thermal receipt date: 11/06/2026 09:15 AM */
export function formatThermalReceiptDate(receipt: PosReceipt): string {
  try {
    let d: Date;
    if (receipt.datetime_display) {
      d = new Date(`${receipt.date}T${receipt.time || "00:00"}`);
      if (Number.isNaN(d.getTime())) d = new Date(receipt.datetime_display);
    } else {
      d = new Date(`${receipt.date}T${receipt.time || "00:00"}`);
    }
    if (Number.isNaN(d.getTime())) return `${receipt.date} ${receipt.time}`;
    const date = d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
    const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
    return `${date} ${time}`;
  } catch {
    return `${receipt.date} ${receipt.time}`;
  }
}

export function formatReceiptDate(receipt: PosReceipt): string {
  if (receipt.datetime_display) return receipt.datetime_display;
  try {
    const d = new Date(`${receipt.date}T${receipt.time}`);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return `${receipt.date} ${receipt.time}`;
  }
}

export function getTaxRateLabel(receipt: PosReceipt): string {
  const rate = receipt.tax_rate ?? 0;
  if (rate <= 0) return "Tax";
  return `Tax (${Math.round(rate * 100)}%)`;
}

export function getVerificationUrl(receipt: PosReceipt): string {
  const path = receipt.verification_path ?? `/receipt/verify/${receipt.invoice_id}`;
  if (path.startsWith("http")) return path;
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://mda-retail.app";
  return `${origin}${path.startsWith("/") ? path : `/${path}`}`;
}

export function getCompanyLogoUrl(receipt: PosReceipt): string | undefined {
  return resolveMediaUrl(receipt.company.logo);
}

export function getMerchantRef(receipt: PosReceipt): string {
  return receipt.payment_reference || receipt.merchant_reference || receipt.merchant?.merchant_number || "—";
}

export function escHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

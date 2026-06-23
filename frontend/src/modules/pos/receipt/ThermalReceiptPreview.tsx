import { useEffect, useState } from "react";
import type { PosReceipt } from "@/services/api/pos";
import { renderPremiumThermalReceipt } from "@/documents/renderers/thermal";
import { THERMAL_RECEIPT_CSS } from "@/documents/styles/thermalReceipt";
import { generateBarcodeDataUrl } from "./receiptAssets";
import { cn } from "@/utils/cn";

interface ThermalReceiptPreviewProps {
  receipt: PosReceipt;
  width?: "58mm" | "80mm";
  className?: string;
}

export function ThermalReceiptPreview({ receipt, width = "80mm", className }: ThermalReceiptPreviewProps) {
  const [html, setHtml] = useState("");

  useEffect(() => {
    const barcode = generateBarcodeDataUrl(receipt.invoice_number, 1.8, 44);
    const body = renderPremiumThermalReceipt(receipt, { qrDataUrl: "", barcodeDataUrl: barcode }, width);
    setHtml(`<style>${THERMAL_RECEIPT_CSS}</style>${body}`);
  }, [receipt, width]);

  if (!html) return null;

  return (
    <div
      className={cn("mx-auto overflow-hidden rounded-lg border border-border bg-white shadow-sm", className)}
      style={{ width, maxWidth: "100%" }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

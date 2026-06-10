import type { PosReceipt } from "@/services/api/pos";
import { generateBarcodeDataUrl, generateQrDataUrl } from "./receiptAssets";
import { buildThermalReceiptHtml, getThermalPrintStyles } from "./thermalReceiptHtml";
import { getVerificationUrl, type ThermalWidth } from "./receiptFormat";

const RECEIPT_PRINT_ID = "pos-receipt-print-root";
const RECEIPT_PRINT_STYLE_ID = "pos-receipt-print-style";

export interface PrintReceiptOptions {
  width?: ThermalWidth;
}

export async function printPosReceipt(
  receipt: PosReceipt,
  options: PrintReceiptOptions = {}
): Promise<void> {
  const width = options.width ?? "80mm";
  const verificationUrl = getVerificationUrl(receipt);

  const [qrDataUrl] = await Promise.all([
    generateQrDataUrl(verificationUrl, width === "58mm" ? 120 : 160),
  ]);
  const barcodeDataUrl = generateBarcodeDataUrl(receipt.invoice_number, width === "58mm" ? 1 : 1.4);

  const existing = document.getElementById(RECEIPT_PRINT_ID);
  if (existing) existing.remove();
  const existingStyle = document.getElementById(RECEIPT_PRINT_STYLE_ID);
  if (existingStyle) existingStyle.remove();

  const container = document.createElement("div");
  container.id = RECEIPT_PRINT_ID;
  container.innerHTML = buildThermalReceiptHtml(
    receipt,
    { qrDataUrl, barcodeDataUrl },
    width
  );
  document.body.appendChild(container);

  const style = document.createElement("style");
  style.id = RECEIPT_PRINT_STYLE_ID;
  style.textContent = getThermalPrintStyles(width);
  document.head.appendChild(style);

  window.print();

  setTimeout(() => {
    container.remove();
    style.remove();
  }, 600);
}

export function printThermalReceipt58(receipt: PosReceipt) {
  return printPosReceipt(receipt, { width: "58mm" });
}

export function printThermalReceipt80(receipt: PosReceipt) {
  return printPosReceipt(receipt, { width: "80mm" });
}

import type { PosReceipt } from "@/services/api/pos";
import { THERMAL_RECEIPT_PRINT_CSS } from "@/documents/styles/thermalReceipt";
import { printThermalDocument } from "@/utils/printThermal";
import { generateBarcodeDataUrl, generateQrDataUrl } from "./receiptAssets";
import { buildThermalReceiptHtml } from "./thermalReceiptHtml";
import { getVerificationUrl, type ThermalWidth } from "./receiptFormat";

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

  const body = buildThermalReceiptHtml(
    receipt,
    { qrDataUrl, barcodeDataUrl },
    width
  );

  await printThermalDocument(body, {
    width,
    css: THERMAL_RECEIPT_PRINT_CSS,
  });
}

export function printThermalReceipt58(receipt: PosReceipt) {
  return printPosReceipt(receipt, { width: "58mm" });
}

export function printThermalReceipt80(receipt: PosReceipt) {
  return printPosReceipt(receipt, { width: "80mm" });
}

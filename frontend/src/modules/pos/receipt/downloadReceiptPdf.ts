import type { PosReceipt } from "@/services/api/pos";
import { downloadReceiptDocumentPdf } from "@/documents/engine";
import { generateBarcodeDataUrl, generateQrDataUrl } from "./receiptAssets";
import { getVerificationUrl } from "./receiptFormat";

export async function downloadReceiptPdf(receipt: PosReceipt): Promise<void> {
  const verificationUrl = getVerificationUrl(receipt);
  const [qrDataUrl, barcodeDataUrl] = await Promise.all([
    generateQrDataUrl(verificationUrl, 200),
    Promise.resolve(generateBarcodeDataUrl(receipt.invoice_number, 1.2, 36)),
  ]);
  await downloadReceiptDocumentPdf(receipt, { qr: qrDataUrl, barcode: barcodeDataUrl }, "tax_invoice");
}

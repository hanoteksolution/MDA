import { jsPDF } from "jspdf";
import type { PosReceipt } from "@/services/api/pos";
import { formatCurrency } from "@/utils/cn";
import { generateBarcodeDataUrl, generateQrDataUrl } from "./receiptAssets";
import {
  formatReceiptDate,
  getMerchantRef,
  getPaymentLabel,
  getTaxRateLabel,
  getVerificationUrl,
} from "./receiptFormat";

export async function downloadReceiptPdf(receipt: PosReceipt): Promise<void> {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const margin = 16;
  let y = margin;

  const verificationUrl = getVerificationUrl(receipt);
  const [qrDataUrl, barcodeDataUrl] = await Promise.all([
    generateQrDataUrl(verificationUrl, 200),
    Promise.resolve(generateBarcodeDataUrl(receipt.invoice_number, 1.2, 36)),
  ]);

  const paymentLabel = getPaymentLabel(receipt);
  const taxLabel = getTaxRateLabel(receipt);
  const merchantRef = getMerchantRef(receipt);
  const loyaltyEarned = receipt.loyalty_points_earned ?? Math.floor(receipt.total_amount / 10);
  const loyaltyTotal = receipt.loyalty_points_total ?? loyaltyEarned + 1160;

  const addText = (
    text: string,
    x: number,
    size = 10,
    style: "normal" | "bold" = "normal",
    color: [number, number, number] = [30, 30, 30]
  ) => {
    doc.setFont("helvetica", style);
    doc.setFontSize(size);
    doc.setTextColor(...color);
    doc.text(text, x, y);
    y += size * 0.45 + 2;
  };

  // Header band
  doc.setFillColor(16, 185, 129);
  doc.rect(0, 0, pageW, 28, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(receipt.company.name, margin, 14);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text("INVOICE / RECEIPT", pageW - margin, 14, { align: "right" });
  doc.text(receipt.invoice_number, pageW - margin, 20, { align: "right" });

  y = 36;
  doc.setTextColor(30, 30, 30);
  addText(receipt.company.address, margin, 9);
  addText(`Tel: ${receipt.company.phone}`, margin, 9);
  if (receipt.company.tax_id) addText(`Tax ID: ${receipt.company.tax_id}`, margin, 9);

  y += 2;
  doc.setDrawColor(220, 220, 220);
  doc.line(margin, y, pageW - margin, y);
  y += 6;

  const colW = (pageW - margin * 2) / 4;
  const meta = [
    ["Date & Time", formatReceiptDate(receipt)],
    ["Cashier", receipt.cashier],
    ["Payment", paymentLabel],
    ["Reference", merchantRef],
  ];
  meta.forEach(([label, value], i) => {
    const x = margin + i * colW;
    doc.setFontSize(8);
    doc.setTextColor(120, 120, 120);
    doc.text(label, x, y);
    doc.setFontSize(10);
    doc.setTextColor(30, 30, 30);
    doc.setFont("helvetica", "bold");
    doc.text(String(value).slice(0, 28), x, y + 5);
    doc.setFont("helvetica", "normal");
  });
  y += 14;

  addText(`${receipt.branch.name} (${receipt.branch.code})`, margin, 10, "bold");
  addText(`Customer: ${receipt.customer_name}`, margin, 10);

  y += 2;
  doc.line(margin, y, pageW - margin, y);
  y += 6;

  // Items header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  doc.text("ITEM", margin, y);
  doc.text("QTY", pageW - margin - 55, y);
  doc.text("PRICE", pageW - margin - 38, y);
  doc.text("TOTAL", pageW - margin - 18, y, { align: "right" });
  y += 4;
  doc.line(margin, y, pageW - margin, y);
  y += 5;

  doc.setTextColor(30, 30, 30);
  receipt.items.forEach((item) => {
    if (y > 250) {
      doc.addPage();
      y = margin;
    }
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text(item.name.slice(0, 42), margin, y);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(120, 120, 120);
    doc.text(`SKU: ${item.sku}`, margin, y + 4);
    doc.setTextColor(30, 30, 30);
    doc.setFontSize(10);
    doc.text(String(item.quantity), pageW - margin - 55, y);
    doc.text(formatCurrency(item.unit_price), pageW - margin - 38, y);
    doc.setFont("helvetica", "bold");
    doc.text(formatCurrency(item.line_total), pageW - margin, y, { align: "right" });
    doc.setFont("helvetica", "normal");
    y += 10;
  });

  y += 4;
  const totalsX = pageW - margin - 55;
  const rows: [string, string][] = [
    ["Subtotal", formatCurrency(receipt.subtotal)],
    ["Discount", receipt.discount_amount > 0 ? `−${formatCurrency(receipt.discount_amount)}` : formatCurrency(0)],
    [taxLabel, formatCurrency(receipt.tax_amount)],
  ];
  rows.forEach(([label, value]) => {
    doc.setFontSize(10);
    doc.text(label, totalsX, y);
    doc.text(value, pageW - margin, y, { align: "right" });
    y += 6;
  });
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(16, 185, 129);
  doc.text("Grand Total", totalsX, y);
  doc.text(formatCurrency(receipt.total_amount), pageW - margin, y, { align: "right" });
  y += 10;

  doc.setTextColor(30, 30, 30);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(`Paid via ${paymentLabel} · Ref: ${merchantRef}`, margin, y);
  y += 8;

  doc.addImage(barcodeDataUrl, "PNG", margin, y, 50, 12);
  doc.addImage(qrDataUrl, "PNG", pageW - margin - 28, y - 2, 28, 28);
  doc.setFontSize(7);
  doc.setTextColor(120, 120, 120);
  doc.text("Scan to verify", pageW - margin - 28, y + 32);
  y += 38;

  doc.setTextColor(30, 30, 30);
  doc.setFontSize(9);
  doc.text(
    `Loyalty: +${loyaltyEarned} points (Total: ${loyaltyTotal.toLocaleString()})`,
    margin,
    y
  );
  y += 6;
  const policy = receipt.return_policy ?? "Items can be returned within 7 days.";
  doc.text(doc.splitTextToSize(policy, pageW - margin * 2) as string[], margin, y);
  y += 12;

  doc.setFillColor(30, 41, 59);
  doc.rect(0, doc.internal.pageSize.getHeight() - 18, pageW, 18, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(10);
  doc.text(receipt.footer, pageW / 2, doc.internal.pageSize.getHeight() - 8, { align: "center" });

  doc.save(`${receipt.invoice_number}.pdf`);
}

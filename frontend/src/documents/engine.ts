import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { printHtmlDocument } from "@/utils/printDocument";
import { savePdfDocument } from "@/utils/savePdf";
import {
  isCustomerReportDocument,
  isDeliveryNoteDocument,
  isProductListDocument,
  isPurchaseOrderDocument,
  isSalesDocument,
  isSalesReportDocument,
  renderEnterpriseDocument,
  renderTableReportDocument,
  wrapA4Html,
} from "./layout";
import { renderCustomerReportDocument } from "./templates/customerReportDocument";
import { renderDeliveryNoteDocument } from "./templates/deliveryNoteDocument";
import { renderProductListDocument } from "./templates/productListDocument";
import { renderPurchaseOrderDocument } from "./templates/purchaseOrderDocument";
import { renderSalesReportDocument } from "./templates/salesReportDocument";
import { documentFromQuotation, documentFromReceipt, enterpriseToSalesPayload } from "./presets";
import { renderSalesDocument } from "./templates/salesDocument";
import type { EnterpriseDocument, PageSize, TableReportDocument } from "./types";
import { slugFilename } from "./utils";
import { A4_PRINT_CSS, CUSTOMER_REPORT_CSS, DELIVERY_NOTE_CSS, PRODUCT_LIST_CSS, PURCHASE_ORDER_CSS, SALES_DOCUMENT_CSS, SALES_REPORT_CSS, TABLE_REPORT_CSS } from "./styles";

const PDF_ROOT_ID = "mda-pdf-render-root";

function pageDimensions(size: PageSize): { width: number; height: number; orientation: "p" | "l"; format: string } {
  switch (size) {
    case "a4-landscape":
      return { width: 297, height: 210, orientation: "l", format: "a4" };
    case "letter":
      return { width: 216, height: 279, orientation: "p", format: "letter" };
    default:
      return { width: 210, height: 297, orientation: "p", format: "a4" };
  }
}

function resolveSalesPayload(doc: EnterpriseDocument) {
  return doc.salesPayload ?? enterpriseToSalesPayload(doc);
}

/** Print customers report using the premium analytics layout. */
export async function printCustomerReportDocument(doc: EnterpriseDocument): Promise<void> {
  const payload = doc.customerReportPayload;
  if (!payload) {
    await printEnterpriseDocument(doc);
    return;
  }
  const html = wrapA4Html(renderCustomerReportDocument(payload), "customer-report");
  printHtmlDocument(html, { width: "210mm" });
}

export async function downloadCustomerReportPdf(
  doc: EnterpriseDocument,
  filename?: string
): Promise<boolean> {
  const payload = doc.customerReportPayload;
  const name = filename ?? `${slugFilename(doc.meta.documentNumber)}.pdf`;
  if (!payload) {
    return downloadEnterprisePdf(doc, name);
  }
  return saveHtmlAsPdf(renderCustomerReportDocument(payload), name, "a4-portrait", "customer-report");
}

/** Print delivery note using the premium DN layout. */
export async function printDeliveryNoteDocument(doc: EnterpriseDocument): Promise<void> {
  const payload = doc.deliveryNotePayload;
  if (!payload) {
    await printEnterpriseDocument(doc);
    return;
  }
  const html = wrapA4Html(renderDeliveryNoteDocument(payload), "delivery-note");
  printHtmlDocument(html, { width: "210mm" });
}

export async function downloadDeliveryNotePdf(
  doc: EnterpriseDocument,
  filename?: string
): Promise<boolean> {
  const payload = doc.deliveryNotePayload;
  const name = filename ?? `${slugFilename(doc.meta.documentNumber)}.pdf`;
  if (!payload) {
    return downloadEnterprisePdf(doc, name);
  }
  return saveHtmlAsPdf(renderDeliveryNoteDocument(payload), name, "a4-portrait", "delivery-note");
}

/** Print purchase order using the premium PO layout. */
export async function printPurchaseOrderDocument(doc: EnterpriseDocument): Promise<void> {
  const payload = doc.purchaseOrderPayload;
  if (!payload) {
    await printEnterpriseDocument(doc);
    return;
  }
  const html = wrapA4Html(renderPurchaseOrderDocument(payload), "purchase-order");
  printHtmlDocument(html, { width: "210mm" });
}

export async function downloadPurchaseOrderPdf(
  doc: EnterpriseDocument,
  filename?: string
): Promise<boolean> {
  const payload = doc.purchaseOrderPayload;
  const name = filename ?? `${slugFilename(doc.meta.documentNumber)}.pdf`;
  if (!payload) {
    return downloadEnterprisePdf(doc, name);
  }
  return saveHtmlAsPdf(renderPurchaseOrderDocument(payload), name, "a4-portrait", "purchase-order");
}

/** Print sales report using the premium analytics layout. */
export async function printSalesReportDocument(doc: EnterpriseDocument): Promise<void> {
  const payload = doc.salesReportPayload;
  if (!payload) {
    await printEnterpriseDocument(doc);
    return;
  }
  const html = wrapA4Html(renderSalesReportDocument(payload), "sales-report");
  printHtmlDocument(html, { width: "210mm" });
}

export async function downloadSalesReportPdf(
  doc: EnterpriseDocument,
  filename?: string
): Promise<boolean> {
  const payload = doc.salesReportPayload;
  const name = filename ?? "sales-report.pdf";
  if (!payload) {
    return downloadEnterprisePdf(doc, name);
  }
  return saveHtmlAsPdf(renderSalesReportDocument(payload), name, "a4-portrait", "sales-report");
}

/** Print product list using the premium catalog report layout. */
export async function printProductListDocument(doc: EnterpriseDocument): Promise<void> {
  const payload = doc.productListPayload;
  if (!payload) {
    await printEnterpriseDocument(doc);
    return;
  }
  const html = wrapA4Html(renderProductListDocument(payload), "product-list");
  printHtmlDocument(html, { width: "210mm" });
}

export async function downloadProductListPdf(
  doc: EnterpriseDocument,
  filename?: string
): Promise<boolean> {
  const payload = doc.productListPayload;
  const name = filename ?? "product-list.pdf";
  if (!payload) {
    return downloadEnterprisePdf(doc, name);
  }
  return saveHtmlAsPdf(renderProductListDocument(payload), name, "a4-portrait", "product-list");
}

export async function printSalesDocument(doc: EnterpriseDocument): Promise<void> {
  const payload = resolveSalesPayload(doc);
  if (!payload) {
    const html = wrapA4Html(renderEnterpriseDocument(doc), "enterprise");
    printHtmlDocument(html, { width: "210mm" });
    return;
  }
  const html = wrapA4Html(renderSalesDocument(payload), "sales");
  printHtmlDocument(html, { width: "210mm" });
}

export async function downloadSalesDocumentPdf(
  doc: EnterpriseDocument,
  filename?: string
): Promise<boolean> {
  const payload = resolveSalesPayload(doc);
  const name = filename ?? `${slugFilename(doc.meta.documentNumber)}.pdf`;
  if (!payload) {
    return downloadEnterprisePdf(doc, name);
  }
  return saveHtmlAsPdf(renderSalesDocument(payload), name, "a4-portrait", true);
}

export async function printEnterpriseDocument(
  doc: EnterpriseDocument,
  pageSize: PageSize = "a4-portrait"
): Promise<void> {
  if (isCustomerReportDocument(doc)) {
    await printCustomerReportDocument(doc);
    return;
  }
  if (isDeliveryNoteDocument(doc)) {
    await printDeliveryNoteDocument(doc);
    return;
  }
  if (isPurchaseOrderDocument(doc)) {
    await printPurchaseOrderDocument(doc);
    return;
  }
  if (isSalesReportDocument(doc)) {
    await printSalesReportDocument(doc);
    return;
  }
  if (isProductListDocument(doc)) {
    await printProductListDocument(doc);
    return;
  }
  if (isSalesDocument(doc)) {
    await printSalesDocument(doc);
    return;
  }
  const html = wrapA4Html(renderEnterpriseDocument(doc), "enterprise");
  const width = pageSize === "a4-landscape" ? "297mm" : "210mm";
  printHtmlDocument(html, { width });
}

export async function printTableReport(doc: TableReportDocument, pageSize: PageSize = "a4-portrait"): Promise<void> {
  const html = wrapA4Html(renderTableReportDocument(doc), "table-report");
  const width = pageSize === "a4-portrait" ? "210mm" : "297mm";
  printHtmlDocument(html, { width });
}

export async function downloadEnterprisePdf(
  doc: EnterpriseDocument,
  filename?: string,
  pageSize: PageSize = "a4-portrait"
): Promise<boolean> {
  const name = filename ?? `${slugFilename(doc.meta.documentNumber)}.pdf`;
  if (isCustomerReportDocument(doc)) {
    return downloadCustomerReportPdf(doc, name);
  }
  if (isDeliveryNoteDocument(doc)) {
    return downloadDeliveryNotePdf(doc, name);
  }
  if (isPurchaseOrderDocument(doc)) {
    return downloadPurchaseOrderPdf(doc, name);
  }
  if (isSalesReportDocument(doc)) {
    return downloadSalesReportPdf(doc, name);
  }
  if (isProductListDocument(doc)) {
    return downloadProductListPdf(doc, name);
  }
  if (isSalesDocument(doc)) {
    return downloadSalesDocumentPdf(doc, name);
  }
  return saveHtmlAsPdf(renderEnterpriseDocument(doc), name, pageSize, false);
}

export async function downloadTableReportPdf(
  doc: TableReportDocument,
  filename?: string,
  pageSize: PageSize = "a4-portrait"
): Promise<boolean> {
  const name = filename ?? `${slugFilename(doc.title)}.pdf`;
  return saveHtmlAsPdf(renderTableReportDocument(doc), name, pageSize, "table-report");
}

export async function saveHtmlAsPdf(
  bodyHtml: string,
  filename: string,
  pageSize: PageSize = "a4-portrait",
  salesLayout: boolean | "product-list" | "sales-report" | "purchase-order" | "delivery-note" | "table-report" | "customer-report" = false
): Promise<boolean> {
  const existing = document.getElementById(PDF_ROOT_ID);
  if (existing) existing.remove();

  const host = document.createElement("div");
  host.id = PDF_ROOT_ID;
  host.style.cssText =
    `position:fixed;left:-10000px;top:0;width:794px;background:#fff;z-index:-1;`;
  const css =
    salesLayout === "sales-report"
      ? SALES_REPORT_CSS
      : salesLayout === "customer-report"
        ? CUSTOMER_REPORT_CSS
        : salesLayout === "table-report"
          ? TABLE_REPORT_CSS
          : salesLayout === "delivery-note"
          ? DELIVERY_NOTE_CSS
          : salesLayout === "purchase-order"
            ? PURCHASE_ORDER_CSS
            : salesLayout === "product-list"
              ? PRODUCT_LIST_CSS
              : salesLayout
                ? SALES_DOCUMENT_CSS
                : A4_PRINT_CSS;
  host.innerHTML = `<style>${css}</style>${bodyHtml}`;
  document.body.appendChild(host);

  try {
    await new Promise((r) => setTimeout(r, 120));
    const canvas = await html2canvas(host, {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff",
      logging: false,
    });

    const { orientation, format } = pageDimensions(pageSize);
    const pdf = new jsPDF({ orientation, unit: "mm", format });
    const imgData = canvas.toDataURL("image/png");
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const imgHeight = (canvas.height * pdfWidth) / canvas.width;

    let position = 0;
    let remaining = imgHeight;

    pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
    remaining -= pdfHeight;

    while (remaining > 0) {
      position -= pdfHeight;
      pdf.addPage(format, orientation);
      pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
      remaining -= pdfHeight;
    }

    return savePdfDocument(pdf, filename);
  } finally {
    host.remove();
  }
}

export async function printReceiptDocument(
  receipt: Parameters<typeof documentFromReceipt>[0],
  assets?: Parameters<typeof documentFromReceipt>[2],
  type: Parameters<typeof documentFromReceipt>[1] = "tax_invoice"
): Promise<void> {
  const doc = documentFromReceipt(receipt, type, assets);
  await printSalesDocument(doc);
}

export async function downloadReceiptDocumentPdf(
  receipt: Parameters<typeof documentFromReceipt>[0],
  assets?: Parameters<typeof documentFromReceipt>[2],
  type: Parameters<typeof documentFromReceipt>[1] = "tax_invoice"
): Promise<boolean> {
  const doc = documentFromReceipt(receipt, type, assets);
  return downloadSalesDocumentPdf(doc, `${receipt.invoice_number}.pdf`);
}

export async function printQuotationDocument(
  quotation: Parameters<typeof documentFromQuotation>[0],
  branding: Parameters<typeof documentFromQuotation>[1],
  assets?: Parameters<typeof documentFromQuotation>[2]
): Promise<void> {
  const doc = documentFromQuotation(quotation, branding, assets);
  await printSalesDocument(doc);
}

export async function downloadQuotationDocumentPdf(
  quotation: Parameters<typeof documentFromQuotation>[0],
  branding: Parameters<typeof documentFromQuotation>[1],
  assets?: Parameters<typeof documentFromQuotation>[2]
): Promise<boolean> {
  const doc = documentFromQuotation(quotation, branding, assets);
  return downloadSalesDocumentPdf(doc, `${quotation.number}.pdf`);
}

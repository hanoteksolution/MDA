import {
  renderBottomSection,
  renderDataGrid,
  renderFooter,
  renderHeader,
  renderKpiGrid,
  renderNotes,
  renderParties,
  renderSignatures,
} from "./components";
import { enterpriseToSalesPayload } from "./presets";
import { renderProductListDocument } from "./templates/productListDocument";
import { renderSalesDocument } from "./templates/salesDocument";
import { renderCustomerReportDocument } from "./templates/customerReportDocument";
import { renderDeliveryNoteDocument } from "./templates/deliveryNoteDocument";
import { renderPurchaseOrderDocument } from "./templates/purchaseOrderDocument";
import { renderSalesReportDocument } from "./templates/salesReportDocument";
import { renderTableReportDocumentPremium } from "./templates/tableReportDocument";
import { A4_PRINT_CSS, CUSTOMER_REPORT_CSS, DELIVERY_NOTE_CSS, PRODUCT_LIST_CSS, PURCHASE_ORDER_CSS, SALES_DOCUMENT_CSS, SALES_REPORT_CSS, TABLE_REPORT_CSS } from "./styles";
import type { EnterpriseDocument, TableReportDocument } from "./types";
import { esc } from "./utils";

export function renderEnterpriseDocument(doc: EnterpriseDocument): string {
  if (doc.customerReportPayload) {
    return renderCustomerReportDocument(doc.customerReportPayload);
  }
  if (doc.deliveryNotePayload) {
    return renderDeliveryNoteDocument(doc.deliveryNotePayload);
  }
  if (doc.purchaseOrderPayload) {
    return renderPurchaseOrderDocument(doc.purchaseOrderPayload);
  }
  if (doc.salesReportPayload) {
    return renderSalesReportDocument(doc.salesReportPayload);
  }
  if (doc.productListPayload) {
    return renderProductListDocument(doc.productListPayload);
  }
  const salesPayload = doc.salesPayload ?? enterpriseToSalesPayload(doc);
  if (salesPayload) {
    return renderSalesDocument(salesPayload);
  }
  return `
    <div class="mda-doc">
      ${doc.watermark ? `<div class="mda-watermark">${esc(doc.watermark)}</div>` : ""}
      ${renderHeader(doc.branding, doc.meta, { qr: doc.qrDataUrl, barcode: doc.barcodeDataUrl })}
      <div class="mda-doc-body">
        ${renderParties(doc.billTo, doc.shipTo)}
        ${renderKpiGrid(doc.kpis)}
        ${renderDataGrid(doc.columns, doc.rows)}
        ${renderBottomSection(doc.analytics, doc.financials)}
        ${renderNotes(doc.notes, doc.terms)}
        ${renderSignatures(doc.signatures)}
      </div>
      ${renderFooter(doc.branding, doc.footerMessage, doc.confidential)}
    </div>`;
}

export function renderTableReportDocument(doc: TableReportDocument): string {
  return renderTableReportDocumentPremium(doc);
}

/** Printable fragment: inline styles + body (not a full HTML document). */
export function wrapA4Html(
  body: string,
  variant: "enterprise" | "sales" | "product-list" | "sales-report" | "purchase-order" | "delivery-note" | "table-report" | "customer-report" = "enterprise"
): string {
  const css =
    variant === "sales"
      ? SALES_DOCUMENT_CSS
      : variant === "product-list"
        ? PRODUCT_LIST_CSS
        : variant === "sales-report"
          ? SALES_REPORT_CSS
          : variant === "customer-report"
            ? CUSTOMER_REPORT_CSS
            : variant === "purchase-order"
              ? PURCHASE_ORDER_CSS
              : variant === "delivery-note"
                ? DELIVERY_NOTE_CSS
                : variant === "table-report"
                  ? TABLE_REPORT_CSS
                  : A4_PRINT_CSS;
  return `<style>${css}</style>${body}`;
}

export function isSalesDocument(doc: EnterpriseDocument): boolean {
  return Boolean(doc.salesPayload ?? enterpriseToSalesPayload(doc));
}

export function isProductListDocument(doc: EnterpriseDocument): boolean {
  return Boolean(doc.productListPayload) || doc.type === "product_list";
}

export function isSalesReportDocument(doc: EnterpriseDocument): boolean {
  return Boolean(doc.salesReportPayload) || doc.type === "sales_report";
}

export function isPurchaseOrderDocument(doc: EnterpriseDocument): boolean {
  return Boolean(doc.purchaseOrderPayload) || doc.type === "purchase_order";
}

export function isDeliveryNoteDocument(doc: EnterpriseDocument): boolean {
  return Boolean(doc.deliveryNotePayload) || doc.type === "delivery_note";
}

export function isCustomerReportDocument(doc: EnterpriseDocument): boolean {
  return Boolean(doc.customerReportPayload) || doc.type === "customer_statement";
}

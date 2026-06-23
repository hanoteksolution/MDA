import { formatCurrency } from "@/utils/cn";
import type { PosReceipt } from "@/services/api/pos";
import {
  formatThermalReceiptDate,
  getPaymentLabel,
  getTaxRateLabel,
  type ThermalWidth,
} from "@/modules/pos/receipt/receiptFormat";
import { esc } from "../utils";
import { THERMAL_RECEIPT_CSS } from "../styles/thermalReceipt";

export interface ThermalAssets {
  qrDataUrl: string;
  barcodeDataUrl: string;
}

const LOGO_HEX = `
<svg class="th-logo" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M18 2L31 10V26L18 34L5 26V10L18 2Z" fill="#001B3D"/>
  <path d="M18 6L27 12V24L18 30L9 24V12L18 6Z" fill="#2563EB"/>
  <text x="18" y="23" text-anchor="middle" fill="#fff" font-family="Inter,sans-serif" font-size="12" font-weight="800">M</text>
</svg>`;

function metaRow(label: string, value: string): string {
  return `<div class="row"><span class="label">${esc(label)}:</span><span class="value">${esc(value)}</span></div>`;
}

function totalRow(label: string, value: string, grand = false): string {
  const cls = grand ? "row grand" : "row";
  return `<div class="${cls}"><span>${esc(label)}</span><span>${esc(value)}</span></div>`;
}

export function renderPremiumThermalReceipt(
  receipt: PosReceipt,
  assets: ThermalAssets,
  width: ThermalWidth = "80mm"
): string {
  const isNarrow = width === "58mm";
  const company = receipt.company.name.toUpperCase();
  const tagline = "ERP & POS SYSTEM";
  const taxLabel = getTaxRateLabel(receipt);
  const paymentLabel = getPaymentLabel(receipt);
  const isCash = receipt.payment_method === "cash";

  const items = receipt.items
    .map(
      (item) => `
      <tr>
        <td class="item-name">${esc(item.name)}</td>
        <td class="qty">${item.quantity % 1 === 0 ? item.quantity : item.quantity.toFixed(1)}</td>
        <td class="num">${formatCurrency(item.unit_price)}</td>
        <td class="num">${formatCurrency(item.line_total)}</td>
      </tr>`
    )
    .join("");

  const paymentSection =
    isCash && receipt.amount_tendered != null
      ? `
      <hr class="th-dash" />
      <div class="th-totals">
        ${totalRow("Cash", formatCurrency(receipt.amount_tendered))}
        ${receipt.change != null ? totalRow("Change", formatCurrency(receipt.change)) : ""}
      </div>`
      : !isCash
        ? `
      <hr class="th-dash" />
      <div class="th-totals">
        ${totalRow(paymentLabel, formatCurrency(receipt.total_amount))}
      </div>`
        : "";

  const addressLines = (receipt.company.address || receipt.branch?.address || "")
    .split(/[,\n]/)
    .map((l) => l.trim())
    .filter(Boolean);

  const storeLines = addressLines.length
    ? addressLines.map((l) => `<p>${esc(l)}</p>`).join("")
    : `<p>${esc(receipt.company.address || "—")}</p>`;

  return `
    <div class="mda-thermal${isNarrow ? " narrow" : ""}">
      <div class="th-brand">
        ${LOGO_HEX}
        <div>
          <h1 class="th-company">${esc(company)}</h1>
          <p class="th-tag">${esc(tagline)}</p>
        </div>
      </div>

      <div class="th-store">
        ${storeLines}
        <p>Tel: ${esc(receipt.company.phone || receipt.branch?.phone || "—")}</p>
      </div>

      <h2 class="th-title">Receipt</h2>

      <hr class="th-dash" />

      <div class="th-meta">
        ${metaRow("Receipt No", receipt.invoice_number)}
        ${metaRow("Date", formatThermalReceiptDate(receipt))}
        ${metaRow("Cashier", receipt.cashier)}
      </div>

      <hr class="th-dash" />

      <table class="th-table">
        <thead>
          <tr>
            <th class="left">Item</th>
            <th class="center" style="width:28px">Qty</th>
            <th class="right" style="width:44px">Price</th>
            <th class="right" style="width:48px">Total</th>
          </tr>
        </thead>
        <tbody>${items}</tbody>
      </table>

      <hr class="th-dash" />

      <div class="th-totals">
        ${totalRow("Subtotal", formatCurrency(receipt.subtotal))}
        ${totalRow("Discount", receipt.discount_amount > 0 ? formatCurrency(receipt.discount_amount) : formatCurrency(0))}
        ${totalRow(taxLabel, formatCurrency(receipt.tax_amount))}
      </div>

      <hr class="th-dash" />

      <div class="th-totals">
        ${totalRow("Total", formatCurrency(receipt.total_amount), true)}
      </div>

      ${paymentSection}

      <hr class="th-dash" />

      <p class="th-thanks">${esc(receipt.footer || "Thank you for shopping with us!")}</p>

      <div class="th-barcode">
        <img src="${assets.barcodeDataUrl}" alt="" />
      </div>
    </div>`;
}

export function getThermalPageCss(width: ThermalWidth): string {
  const pad = width === "58mm" ? "3mm 4mm" : "4mm 5mm";
  return `
    ${THERMAL_RECEIPT_CSS}
    @page { size: ${width} auto; margin: 0; }
    body { margin: 0; background: #fff; }
    #pos-receipt-print-root { width: ${width}; padding: ${pad}; background: #fff; }
  `;
}

/** @deprecated use THERMAL_RECEIPT_CSS */
export const THERMAL_PRINT_CSS = THERMAL_RECEIPT_CSS;

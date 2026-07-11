import { formatCurrency } from "@/utils/cn";
import type { PosReceipt } from "@/services/api/pos";
import type { DocumentBranding } from "../types";
import {
  formatThermalReceiptDate,
  getCompanyLogoUrl,
  getPaymentLabel,
  type ThermalWidth,
} from "@/modules/pos/receipt/receiptFormat";
import { esc } from "../utils";
import { THERMAL_RECEIPT_CSS } from "../styles/thermalReceipt";

export interface ThermalAssets {
  qrDataUrl: string;
  barcodeDataUrl: string;
}

function metaRow(label: string, value: string): string {
  return `<div class="row"><span class="label">${esc(label)}</span><span class="value">${esc(value)}</span></div>`;
}

function totalRow(label: string, value: string, grand = false): string {
  const cls = grand ? "row grand" : "row";
  return `<div class="${cls}"><span>${esc(label)}</span><span>${esc(value)}</span></div>`;
}

function fmtQty(n: number): string {
  return n % 1 === 0 ? String(n) : n.toFixed(2);
}

function fmtMoney(n: number): string {
  return n.toFixed(2);
}

function brandHeader(company: string, phone: string, logoUrl?: string): string {
  const brand = logoUrl
    ? `<img class="th-brand-logo" src="${esc(logoUrl)}" alt="${esc(company)}" />`
    : `<h1 class="th-company">${esc(company)}</h1>`;
  return `
    <div class="th-kisima-head">
      ${brand}
      ${phone ? `<p class="th-tel">Tel: ${esc(phone)}</p>` : ""}
    </div>`;
}

/**
 * Short Kisima-style thermal receipt:
 * logo or company name + tel → payment guide → receipt no → items → totals → paid/unpaid
 */
export function renderPremiumThermalReceipt(
  receipt: PosReceipt,
  _assets: ThermalAssets,
  width: ThermalWidth = "80mm"
): string {
  const isNarrow = width === "58mm";
  const company = (receipt.company.name || "Store").toUpperCase();
  const phone = receipt.company.phone || receipt.branch?.phone || "";
  const logoUrl = getCompanyLogoUrl(receipt);
  const paymentLabel = getPaymentLabel(receipt);
  const paid =
    receipt.is_paid === true ||
    receipt.status === "paid" ||
    (receipt.is_paid == null &&
      receipt.status == null &&
      receipt.payment_method !== "on_account" &&
      receipt.payment_method !== "invoice");

  const guide = (receipt.payment_guide || []).slice(0, 4);
  const guideBlock =
    guide.length > 0
      ? `<div class="th-guide">
          ${guide
            .map(
              (g) =>
                `<div class="th-guide-row"><span>${esc(g.label.toUpperCase())}</span><span>${esc(g.number)}</span></div>`
            )
            .join("")}
        </div>`
      : "";

  const items = receipt.items
    .map((item, idx) => {
      const qty = fmtQty(item.quantity);
      return `<tr>
        <td class="idx">${idx + 1}</td>
        <td class="item-name">${esc(item.name)}</td>
        <td class="qty">${qty}</td>
        <td class="num">${fmtMoney(item.unit_price)}</td>
        <td class="num">${fmtMoney(item.line_total)}</td>
      </tr>`;
    })
    .join("");

  const merchantLine =
    receipt.merchant?.merchant_number || receipt.merchant_reference
      ? metaRow(
          "Received via",
          `${receipt.merchant?.label || receipt.merchant?.company_name || paymentLabel} — ${
            receipt.merchant?.merchant_number || receipt.merchant_reference
          }`
        )
      : "";

  const cashLines =
    receipt.payment_method === "cash" && receipt.amount_tendered != null
      ? `${metaRow("Tendered", formatCurrency(receipt.amount_tendered))}${
          receipt.change != null && receipt.change > 0
            ? metaRow("Change", formatCurrency(receipt.change))
            : ""
        }`
      : "";

  const waiterRow = receipt.waiter ? metaRow("Waiter", receipt.waiter) : "";

  return `
    <div class="mda-thermal kisima${isNarrow ? " narrow" : ""}">
      ${brandHeader(company, phone, logoUrl)}

      ${guideBlock}

      <div class="th-sep th-sep-dbl"></div>

      <div class="th-meta">
        ${metaRow("Receipt No", receipt.invoice_number)}
        ${metaRow("Date", formatThermalReceiptDate(receipt))}
        ${metaRow("Cashier", receipt.cashier || "—")}
        ${metaRow("Customer", receipt.customer_name || "Guest")}
        ${waiterRow}
      </div>

      <div class="th-sep"></div>

      <table class="th-table th-table-kisima">
        <thead>
          <tr>
            <th class="left" style="width:12px">#</th>
            <th class="left">Item</th>
            <th class="center" style="width:26px">Qty</th>
            <th class="right" style="width:38px">Price</th>
            <th class="right" style="width:42px">Total</th>
          </tr>
        </thead>
        <tbody>${items}</tbody>
      </table>

      <div class="th-sep"></div>

      <div class="th-totals">
        ${totalRow("Subtotal", fmtMoney(receipt.subtotal))}
        ${receipt.discount_amount > 0 ? totalRow("Discount", `-${fmtMoney(receipt.discount_amount)}`) : ""}
        ${receipt.tax_amount > 0 ? totalRow("Tax", fmtMoney(receipt.tax_amount)) : ""}
        ${totalRow("TOTAL", `$${fmtMoney(receipt.total_amount)}`, true)}
      </div>

      <div class="th-sep th-sep-dbl"></div>

      <div class="th-meta">
        ${metaRow("Method", paymentLabel)}
        ${merchantLine}
        ${cashLines}
        ${metaRow(paid ? "Paid" : "Due", `$${fmtMoney(receipt.total_amount)}`)}
      </div>

      <div class="th-paid-banner ${paid ? "paid" : "unpaid"}">
        ${paid ? "★ PAID IN FULL ★" : "○ UNPAID — PAY LATER ○"}
      </div>

      <div class="th-sep"></div>

      <p class="th-thanks">${esc(receipt.footer || "Thank you for your purchase!")}</p>
      <p class="th-credit">Please come again</p>
      <p class="th-receipt-ref">${esc(receipt.invoice_number)}</p>
    </div>`;
}

export interface ThermalSlipItem {
  name: string;
  sku?: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface ThermalSlipInput {
  title: string;
  subtitle?: string;
  slipNumber: string;
  customerName: string;
  waiterName?: string;
  branchName?: string;
  cashierName?: string;
  heldAt?: string;
  notes?: string;
  items: ThermalSlipItem[];
  subtotal: number;
  discount: number;
  tax: number;
  taxRate: number;
  grandTotal: number;
  footer?: string;
  branding: DocumentBranding;
  isHold?: boolean;
}

function formatSlipDateTime(): string {
  const d = new Date();
  const date = d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
  const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
  return `${date} ${time}`;
}

/** Compact order / hold slip — same visual language, no payment guide. */
export function renderPremiumThermalSlip(
  slip: ThermalSlipInput,
  _assets: ThermalAssets,
  width: ThermalWidth = "80mm"
): string {
  const isNarrow = width === "58mm";
  const b = slip.branding;
  const company = (b.companyName || "Your Company").toUpperCase();
  const phone = b.phone || "";
  const logoUrl = b.logoUrl || undefined;
  const when = slip.heldAt || formatSlipDateTime();
  const title = slip.isHold ? "ON HOLD" : (slip.title || "ORDER").toUpperCase();

  const items = slip.items
    .map((item, idx) => {
      const qty = fmtQty(item.quantity);
      return `<tr>
        <td class="idx">${idx + 1}</td>
        <td class="item-name">${esc(item.name)}</td>
        <td class="qty">${qty}</td>
        <td class="num">${fmtMoney(item.unit_price)}</td>
        <td class="num">${fmtMoney(item.line_total)}</td>
      </tr>`;
    })
    .join("");

  return `
    <div class="mda-thermal kisima${isNarrow ? " narrow" : ""}">
      ${brandHeader(company, phone, logoUrl)}

      <div class="th-sep th-sep-dbl"></div>

      <div class="th-meta">
        ${metaRow("Receipt No", slip.slipNumber)}
        ${metaRow("Date", when)}
        ${metaRow("Customer", slip.customerName || "Guest")}
        ${slip.waiterName ? metaRow("Waiter", slip.waiterName) : ""}
      </div>

      <div class="th-paid-banner unpaid" style="margin-top:6px">${esc(title)}</div>

      <div class="th-sep"></div>

      <table class="th-table th-table-kisima">
        <thead>
          <tr>
            <th class="left" style="width:12px">#</th>
            <th class="left">Item</th>
            <th class="center" style="width:26px">Qty</th>
            <th class="right" style="width:38px">Price</th>
            <th class="right" style="width:42px">Total</th>
          </tr>
        </thead>
        <tbody>${items}</tbody>
      </table>

      <div class="th-sep"></div>

      <div class="th-totals">
        ${totalRow("Subtotal", fmtMoney(slip.subtotal))}
        ${slip.discount > 0 ? totalRow("Discount", `-${fmtMoney(slip.discount)}`) : ""}
        ${slip.tax > 0 ? totalRow("Tax", fmtMoney(slip.tax)) : ""}
        ${totalRow("TOTAL", `$${fmtMoney(slip.grandTotal)}`, true)}
      </div>

      ${slip.notes?.trim() ? `<p class="th-notes-inline">${esc(slip.notes.trim())}</p>` : ""}

      <div class="th-sep"></div>
      <p class="th-thanks">${slip.isHold ? "Present this slip when paying." : "Thank you!"}</p>
      <p class="th-receipt-ref">${esc(slip.slipNumber)}</p>
    </div>`;
}

export function getThermalPageCss(width: ThermalWidth): string {
  const pad = width === "58mm" ? "3mm 5mm" : "4mm 6mm";
  return `
    ${THERMAL_RECEIPT_CSS}
    @page { size: ${width} auto; margin: 0; }
    body { margin: 0; background: #fff; padding: ${pad}; }
    #pos-receipt-print-root { width: 100%; max-width: ${width}; padding: 0 2mm; background: #fff; }
  `;
}

/** @deprecated use THERMAL_RECEIPT_CSS */
export const THERMAL_PRINT_CSS = THERMAL_RECEIPT_CSS;

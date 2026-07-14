import { formatCurrency } from "@/utils/cn";
import type { PosReceipt } from "@/services/api/pos";
import type { DocumentBranding } from "../types";
import {
  getCompanyLogoUrl,
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

/** Inject receipt total into Waafi/EVC-style USSD merchant codes. */
export function formatMerchantCode(raw: string, amount: number): string {
  const amountStr = fmtMoney(amount);
  let n = (raw || "").trim();
  if (!n) return "";
  if (n.includes("{amount}")) return n.replaceAll("{amount}", amountStr);
  // *789*607822*12.00# → replace amount segment
  if (/^\*\d+\*\d+\*[\d.]+#$/.test(n)) {
    return n.replace(/\*[\d.]+#$/, `*${amountStr}#`);
  }
  // *789*607822# or *789*607822*# → insert amount before #
  if (n.startsWith("*") && n.endsWith("#")) {
    const core = n.slice(0, -1);
    return core.endsWith("*") ? `${core}${amountStr}#` : `${core}*${amountStr}#`;
  }
  // *789*607822 or *789*607822*
  if (n.startsWith("*") && !n.includes("#")) {
    return n.endsWith("*") ? `${n}${amountStr}#` : `${n}*${amountStr}#`;
  }
  return n;
}

function splitDateTime(receipt: PosReceipt): { date: string; time: string } {
  try {
    const d = new Date(`${receipt.date}T${receipt.time || "00:00"}`);
    if (!Number.isNaN(d.getTime())) {
      return {
        date: d.toLocaleDateString("en-US"),
        time: d.toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        }),
      };
    }
  } catch {
    /* fall through */
  }
  return { date: receipt.date, time: receipt.time || "" };
}

/**
 * Compact thermal receipt matching shop roll layout:
 * company + address + merchants → meta → borderless items → totals → contact
 */
export function renderPremiumThermalReceipt(
  receipt: PosReceipt,
  _assets: ThermalAssets,
  width: ThermalWidth = "80mm"
): string {
  const isNarrow = width === "58mm";
  const company = receipt.company.name || "Store";
  const address =
    (receipt.company.address || "").trim() ||
    (receipt.branch?.address || "").trim();
  const phone = (receipt.company.phone || receipt.branch?.phone || "").trim();
  const logoUrl = getCompanyLogoUrl(receipt);
  const paymentLabel = getPaymentLabel(receipt);
  const { date, time } = splitDateTime(receipt);
  const taxLabel = getTaxRateLabel(receipt).replace("Tax", "VAT");

  const guide = (receipt.payment_guide || []).slice(0, 4);
  const merchantsBlock =
    guide.length > 0
      ? `<div class="th-merchants">
          ${guide
            .map((g) => {
              const code = formatMerchantCode(g.number, receipt.total_amount);
              return `<div class="th-merchant-row"><span class="m-label">${esc(g.label)}:</span> <span class="m-code">${esc(code)}</span></div>`;
            })
            .join("")}
        </div>`
      : "";

  const items = receipt.items
    .map((item) => {
      const qty = fmtQty(item.quantity);
      return `<tr>
        <td class="item-name">${esc(item.name)}</td>
        <td class="qty">${qty}</td>
        <td class="num">${fmtMoney(item.unit_price)}</td>
        <td class="num">${fmtMoney(item.line_total)}</td>
      </tr>`;
    })
    .join("");

  const cashLines =
    receipt.payment_method === "cash" && receipt.amount_tendered != null
      ? `${totalRow("Tendered", `$${fmtMoney(receipt.amount_tendered)}`)}${
          receipt.change != null && receipt.change > 0
            ? totalRow("Change", `$${fmtMoney(receipt.change)}`)
            : ""
        }`
      : "";

  const servedBy = receipt.waiter || receipt.cashier || "—";

  return `
    <div class="mda-thermal kisima compact${isNarrow ? " narrow" : ""}">
      <div class="th-kisima-head">
        ${logoUrl ? `<img class="th-brand-logo" src="${esc(logoUrl)}" alt="" />` : ""}
        <h1 class="th-company">${esc(company)}</h1>
        ${address ? `<p class="th-address">${esc(address)}</p>` : ""}
        ${!address && phone ? `<p class="th-address">Tel: ${esc(phone)}</p>` : ""}
      </div>

      ${merchantsBlock}

      <div class="th-meta">
        ${metaRow("Date", date)}
        ${metaRow("Time", time)}
        ${metaRow("Ref No", receipt.invoice_number)}
        ${metaRow("Served By", servedBy)}
      </div>

      <div class="th-sep"></div>

      <table class="th-table th-table-kisima">
        <thead>
          <tr>
            <th class="left">ItemName</th>
            <th class="center">QTY</th>
            <th class="right">Price</th>
            <th class="right">Amount</th>
          </tr>
        </thead>
        <tbody>${items}</tbody>
      </table>

      <div class="th-sep"></div>

      <div class="th-totals">
        ${totalRow("Discount", `$${fmtMoney(receipt.discount_amount)}`)}
        ${receipt.tax_amount > 0 || (receipt.tax_rate ?? 0) > 0 ? totalRow(taxLabel, `$${fmtMoney(receipt.tax_amount)}`) : ""}
        ${totalRow("Total", `$${fmtMoney(receipt.total_amount)}`, true)}
        ${cashLines}
        ${
          receipt.payment_method && receipt.payment_method !== "cash"
            ? totalRow("Method", paymentLabel)
            : ""
        }
      </div>

      <div class="th-sep"></div>

      <div class="th-footer-block">
        ${phone ? `<p class="th-contact">Contact Us Here:${esc(phone)}</p>` : ""}
        <p class="th-thanks">${esc(receipt.footer || "Take care & see you later,")}</p>
      </div>
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

function formatSlipDateTime(): { date: string; time: string } {
  const d = new Date();
  return {
    date: d.toLocaleDateString("en-US"),
    time: d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }),
  };
}

/** Compact order / hold slip — same tight layout, no merchant block. */
export function renderPremiumThermalSlip(
  slip: ThermalSlipInput,
  _assets: ThermalAssets,
  width: ThermalWidth = "80mm"
): string {
  const isNarrow = width === "58mm";
  const b = slip.branding;
  const company = b.companyName || "Your Company";
  const address = (b.address || "").trim();
  const phone = b.phone || "";
  const logoUrl = b.logoUrl || undefined;
  const when = slip.heldAt
    ? { date: slip.heldAt, time: "" }
    : formatSlipDateTime();
  const title = slip.isHold ? "ON HOLD" : (slip.title || "ORDER").toUpperCase();
  const vatPct = Math.round((slip.taxRate || 0) * 100);

  const items = slip.items
    .map((item) => {
      const qty = fmtQty(item.quantity);
      return `<tr>
        <td class="item-name">${esc(item.name)}</td>
        <td class="qty">${qty}</td>
        <td class="num">${fmtMoney(item.unit_price)}</td>
        <td class="num">${fmtMoney(item.line_total)}</td>
      </tr>`;
    })
    .join("");

  return `
    <div class="mda-thermal kisima compact${isNarrow ? " narrow" : ""}">
      <div class="th-kisima-head">
        ${logoUrl ? `<img class="th-brand-logo" src="${esc(logoUrl)}" alt="" />` : ""}
        <h1 class="th-company">${esc(company)}</h1>
        ${address ? `<p class="th-address">${esc(address)}</p>` : ""}
      </div>

      <div class="th-meta">
        ${metaRow("Date", when.date)}
        ${when.time ? metaRow("Time", when.time) : ""}
        ${metaRow("Ref No", slip.slipNumber)}
        ${metaRow("Served By", slip.waiterName || slip.cashierName || "—")}
        ${metaRow("Customer", slip.customerName || "Guest")}
        ${metaRow("Status", title)}
      </div>

      <div class="th-sep"></div>

      <table class="th-table th-table-kisima">
        <thead>
          <tr>
            <th class="left">ItemName</th>
            <th class="center">QTY</th>
            <th class="right">Price</th>
            <th class="right">Amount</th>
          </tr>
        </thead>
        <tbody>${items}</tbody>
      </table>

      <div class="th-sep"></div>

      <div class="th-totals">
        ${totalRow("Discount", `$${fmtMoney(slip.discount)}`)}
        ${slip.tax > 0 ? totalRow(vatPct ? `VAT ${vatPct}%` : "VAT", `$${fmtMoney(slip.tax)}`) : ""}
        ${totalRow("Total", `$${fmtMoney(slip.grandTotal)}`, true)}
      </div>

      ${slip.notes?.trim() ? `<p class="th-notes-inline">${esc(slip.notes.trim())}</p>` : ""}

      <div class="th-sep"></div>
      <div class="th-footer-block">
        ${phone ? `<p class="th-contact">Contact Us Here:${esc(phone)}</p>` : ""}
        <p class="th-thanks">${slip.isHold ? "Present this slip when paying." : "Thank you!"}</p>
      </div>
    </div>`;
}

export function getThermalPageCss(width: ThermalWidth): string {
  return `
    ${THERMAL_RECEIPT_CSS}
    @page { size: ${width} auto; margin: 0; }
    body { margin: 0; background: #fff; padding: 0; }
    #pos-receipt-print-root { width: 100%; max-width: ${width}; padding: 0; background: #fff; }
  `;
}

/** @deprecated use THERMAL_RECEIPT_CSS */
export const THERMAL_PRINT_CSS = THERMAL_RECEIPT_CSS;

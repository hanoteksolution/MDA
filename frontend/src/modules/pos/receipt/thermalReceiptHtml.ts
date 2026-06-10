import { formatCurrency } from "@/utils/cn";
import type { PosReceipt } from "@/services/api/pos";
import {
  escHtml,
  formatReceiptDate,
  getCompanyLogoUrl,
  getMerchantRef,
  getPaymentLabel,
  getTaxRateLabel,
  getVerificationUrl,
  type ThermalWidth,
} from "./receiptFormat";

export interface ThermalReceiptAssets {
  qrDataUrl: string;
  barcodeDataUrl: string;
}

export function buildThermalReceiptHtml(
  receipt: PosReceipt,
  assets: ThermalReceiptAssets,
  width: ThermalWidth = "80mm"
): string {
  const isNarrow = width === "58mm";
  const baseFont = isNarrow ? "10px" : "11px";
  const titleFont = isNarrow ? "14px" : "16px";
  const logoUrl = getCompanyLogoUrl(receipt);
  const verificationUrl = getVerificationUrl(receipt);
  const paymentLabel = getPaymentLabel(receipt);
  const taxLabel = getTaxRateLabel(receipt);
  const merchantRef = getMerchantRef(receipt);
  const loyaltyEarned = receipt.loyalty_points_earned ?? Math.floor(receipt.total_amount / 10);
  const loyaltyTotal = receipt.loyalty_points_total ?? loyaltyEarned + 1160;

  const logoBlock = logoUrl
    ? `<img src="${escHtml(logoUrl)}" alt="" style="max-height:42px;max-width:120px;margin:0 auto 8px;display:block" />`
    : `<div style="font-size:${titleFont};font-weight:800;letter-spacing:0.04em;margin-bottom:4px">${escHtml(receipt.company.name)}</div>`;

  const items = receipt.items
    .map(
      (item) => `
      <tr>
        <td style="padding:6px 0;vertical-align:top;border-bottom:1px dotted #ccc">
          <div style="font-weight:600;font-size:${baseFont}">${escHtml(item.name)}</div>
          <div style="font-size:9px;color:#555;margin-top:2px">SKU: ${escHtml(item.sku)}</div>
        </td>
        <td style="padding:6px 4px;text-align:center;vertical-align:top;border-bottom:1px dotted #ccc;font-size:${baseFont}">${item.quantity}</td>
        <td style="padding:6px 4px;text-align:right;vertical-align:top;border-bottom:1px dotted #ccc;font-size:${baseFont};white-space:nowrap">${formatCurrency(item.unit_price)}</td>
        <td style="padding:6px 0;text-align:right;vertical-align:top;border-bottom:1px dotted #ccc;font-size:${baseFont};font-weight:700;white-space:nowrap">${formatCurrency(item.line_total)}</td>
      </tr>`
    )
    .join("");

  const tenderBlock =
    receipt.payment_method === "cash" && receipt.amount_tendered != null
      ? `
        <div class="row"><span>Tendered</span><span>${formatCurrency(receipt.amount_tendered)}</span></div>
        <div class="row"><span>Change</span><span>${formatCurrency(receipt.change ?? 0)}</span></div>`
      : "";

  const discountRow =
    receipt.discount_amount > 0
      ? `<div class="row"><span>Discount</span><span>−${formatCurrency(receipt.discount_amount)}</span></div>`
      : "";

  return `
    <div class="thermal-receipt">
      <div class="center section">
        ${logoBlock}
        ${logoUrl ? `<div style="font-size:${titleFont};font-weight:800;margin-bottom:2px">${escHtml(receipt.company.name)}</div>` : ""}
        ${receipt.company.legal_name ? `<div style="font-size:9px;color:#444">${escHtml(receipt.company.legal_name)}</div>` : ""}
        <div style="font-size:9px;color:#444;margin-top:4px;line-height:1.4">${escHtml(receipt.company.address)}</div>
        <div style="font-size:9px;color:#444">Tel: ${escHtml(receipt.company.phone)}</div>
        ${receipt.company.email ? `<div style="font-size:9px;color:#444">${escHtml(receipt.company.email)}</div>` : ""}
        ${receipt.company.tax_id ? `<div style="font-size:9px;color:#444">Tax ID: ${escHtml(receipt.company.tax_id)}</div>` : ""}
      </div>

      <div class="divider"></div>

      <div class="section" style="font-size:${baseFont}">
        <div style="font-weight:700;margin-bottom:2px">${escHtml(receipt.branch.name)} <span style="font-weight:500;color:#555">(${escHtml(receipt.branch.code)})</span></div>
        ${receipt.branch.address ? `<div style="font-size:9px;color:#555">${escHtml(receipt.branch.address)}</div>` : ""}
        ${receipt.branch.phone ? `<div style="font-size:9px;color:#555">Tel: ${escHtml(receipt.branch.phone)}</div>` : ""}
      </div>

      <div class="divider"></div>

      <div class="section meta">
        <div class="meta-row">
          <div>
            <div><strong>Receipt #</strong> ${escHtml(receipt.invoice_number)}</div>
            <div>${escHtml(formatReceiptDate(receipt))}</div>
            <div>Cashier: ${escHtml(receipt.cashier)}</div>
            <div>Terminal: ${escHtml(receipt.terminal)}</div>
            <div>Customer: ${escHtml(receipt.customer_name)}</div>
            <div>Payment: ${escHtml(paymentLabel)}</div>
            <div>Ref: ${escHtml(merchantRef)}</div>
          </div>
          <div style="text-align:right">
            <img src="${assets.barcodeDataUrl}" alt="" style="height:36px;max-width:100px" />
          </div>
        </div>
      </div>

      <div class="divider"></div>

      <table class="items">
        <thead>
          <tr>
            <th style="text-align:left">Item</th>
            <th style="text-align:center;width:28px">Qty</th>
            <th style="text-align:right;width:52px">Price</th>
            <th style="text-align:right;width:52px">Total</th>
          </tr>
        </thead>
        <tbody>${items}</tbody>
      </table>

      <div class="divider"></div>

      <div class="totals section">
        <div class="row"><span>Subtotal</span><span>${formatCurrency(receipt.subtotal)}</span></div>
        ${discountRow}
        <div class="row"><span>${escHtml(taxLabel)}</span><span>${formatCurrency(receipt.tax_amount)}</span></div>
        <div class="row total"><span>TOTAL</span><span>${formatCurrency(receipt.total_amount)}</span></div>
        ${tenderBlock}
      </div>

      <div class="divider"></div>

      <div class="section verify">
        <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">Payment Verification</div>
        <div style="font-size:${baseFont}">Paid via ${escHtml(paymentLabel)}</div>
        <div style="font-size:9px;color:#555">Ref: ${escHtml(merchantRef)}</div>
        <div class="paid-badge">PAID</div>
        <div class="center" style="margin-top:10px">
          <img src="${assets.qrDataUrl}" alt="QR" style="width:88px;height:88px" />
          <div style="font-size:8px;color:#555;margin-top:4px;line-height:1.3">Scan to verify this receipt</div>
          <div style="font-size:7px;color:#888;word-break:break-all;margin-top:2px">${escHtml(verificationUrl)}</div>
        </div>
      </div>

      <div class="divider"></div>

      <div class="section loyalty">
        <div style="font-size:9px;font-weight:700">Loyalty Points</div>
        <div style="font-size:${baseFont}">Earned: <strong>${loyaltyEarned}</strong> · Total: <strong>${loyaltyTotal.toLocaleString()}</strong></div>
      </div>

      <div class="divider"></div>

      <div class="section policy" style="font-size:8px;color:#555;line-height:1.4">
        ${escHtml(receipt.return_policy ?? "Items can be returned within 7 days with original receipt.")}
      </div>

      <div class="footer center">
        ${escHtml(receipt.footer)}
      </div>
    </div>
  `;
}

export function getThermalPrintStyles(width: ThermalWidth): string {
  const isNarrow = width === "58mm";
  const pad = isNarrow ? "4mm" : "5mm";
  const fontSize = isNarrow ? "10px" : "11px";

  return `
    @page { size: ${width} auto; margin: 0; }
    @media print {
      body * { visibility: hidden !important; }
      #pos-receipt-print-root, #pos-receipt-print-root * { visibility: visible !important; }
      #pos-receipt-print-root {
        position: absolute; left: 0; top: 0;
        width: ${width};
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        font-size: ${fontSize};
        color: #111; background: #fff;
        padding: ${pad};
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
    }
    @media screen {
      #pos-receipt-print-root { display: none; }
    }
    #pos-receipt-print-root .thermal-receipt { width: 100%; }
    #pos-receipt-print-root .center { text-align: center; }
    #pos-receipt-print-root .section { margin-bottom: 8px; }
    #pos-receipt-print-root .divider {
      border-top: 1px dashed #999;
      margin: 8px 0;
    }
    #pos-receipt-print-root .meta-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }
    #pos-receipt-print-root table.items {
      width: 100%;
      border-collapse: collapse;
      font-size: inherit;
    }
    #pos-receipt-print-root table.items th {
      font-size: 8px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #555;
      border-bottom: 1px solid #111;
      padding-bottom: 4px;
    }
    #pos-receipt-print-root .totals .row {
      display: flex;
      justify-content: space-between;
      margin: 3px 0;
    }
    #pos-receipt-print-root .totals .total {
      font-size: ${isNarrow ? "15px" : "17px"};
      font-weight: 800;
      margin-top: 6px;
      padding-top: 6px;
      border-top: 2px solid #111;
    }
    #pos-receipt-print-root .paid-badge {
      display: inline-block;
      margin-top: 6px;
      padding: 2px 10px;
      border: 2px solid #111;
      font-weight: 800;
      font-size: 10px;
      letter-spacing: 0.1em;
    }
    #pos-receipt-print-root .verify {
      border: 1px solid #ddd;
      padding: 8px;
      border-radius: 4px;
    }
    #pos-receipt-print-root .footer {
      margin-top: 12px;
      font-size: 10px;
      font-weight: 600;
      line-height: 1.4;
    }
  `;
}

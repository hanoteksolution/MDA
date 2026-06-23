import type { SalesDocumentPayload } from "../types";
import { esc } from "../utils";

const LOGO_HEX = `
<svg class="sd-logo-hex" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M26 3L45 14.5V37.5L26 49L7 37.5V14.5L26 3Z" fill="#001B3D"/>
  <path d="M26 9L39 17V35L26 43L13 35V17L26 9Z" fill="#2563EB"/>
  <text x="26" y="32" text-anchor="middle" fill="#fff" font-family="Inter,sans-serif" font-size="17" font-weight="800">M</text>
</svg>`;

function contactIcon(type: "phone" | "email" | "web"): string {
  const paths = {
    phone: '<path d="M6.6 10.8c1.4 2.8 3.8 5.2 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C9.6 21 3 14.4 3 6c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1L6.6 10.8z"/>',
    email: '<path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4-8 5L4 8V6l8 5 8-5v2z"/>',
    web: '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm7.9 6H15.9c-.3-1.5-.8-2.9-1.4-4 2 .6 3.7 2 5.4 4zM12 4c.8 1.2 1.5 2.6 1.9 4h-3.8c.4-1.4 1.1-2.8 1.9-4zM4.5 8h4.6c-.2.6-.3 1.3-.4 2H4.1c.1-1 .3-1.9.4-2zm-.4 6h4.6c.1.7.2 1.4.4 2H4.5c-.1-.6-.3-1.3-.4-2zm1 4h4c.1.7.3 1.4.5 2.1-1.8 1.4-3.5 2.8-5.5 4 1.4-1.7 2.5-3.7 3-6.1zM12 20c-.8-1.2-1.5-2.6-1.9-4h3.8c-.4 1.4-1.1 2.8-1.9 4zm4.1 0c-.5 2.4-1.6 4.4-3 6.1 2-.6 3.7-2 5.1-3.9-.2-.7-.4-1.4-.5-2.2h-1.6z"/>',
  };
  return `<svg width="11" height="11" viewBox="0 0 24 24" fill="#94A3B8">${paths[type]}</svg>`;
}

function renderTable(payload: SalesDocumentPayload): string {
  const isQuote = payload.variant === "quotation";
  const head = isQuote
    ? `<tr>
        <th class="center" style="width:34px">#</th>
        <th class="left">Item Description</th>
        <th class="center" style="width:44px">Qty</th>
        <th class="right" style="width:76px">Unit Price</th>
        <th class="right" style="width:68px">Discount</th>
        <th class="right" style="width:76px">Total</th>
      </tr>`
    : `<tr>
        <th class="center" style="width:34px">#</th>
        <th class="left">Item Description</th>
        <th class="center" style="width:44px">Qty</th>
        <th class="right" style="width:68px">Unit Price</th>
        <th class="right" style="width:60px">Discount</th>
        <th class="right" style="width:52px">Tax</th>
        <th class="right" style="width:76px">Amount</th>
      </tr>`;

  const body = payload.rows
    .map((row, i) => {
      const idx = String(i + 1).padStart(2, "0");
      const discount = row.discount && row.discount !== "—" ? row.discount : "$0.00";
      const desc = `<div class="item-name">${esc(row.name)}</div>${row.sku ? `<div class="item-sku">${esc(row.sku)}</div>` : ""}`;
      if (isQuote) {
        return `<tr>
          <td class="idx">${idx}</td>
          <td>${desc}</td>
          <td class="qty">${esc(String(row.quantity ?? ""))}</td>
          <td class="num">${esc(row.unitPrice ?? "")}</td>
          <td class="num">${esc(discount)}</td>
          <td class="num" style="font-weight:700">${esc(row.total)}</td>
        </tr>`;
      }
      return `<tr>
        <td class="idx">${idx}</td>
        <td>${desc}</td>
        <td class="qty">${esc(String(row.quantity ?? ""))}</td>
        <td class="num">${esc(row.unitPrice ?? "")}</td>
        <td class="num">${esc(discount)}</td>
        <td class="num">${esc(row.tax ?? "—")}</td>
        <td class="num" style="font-weight:700">${esc(row.total)}</td>
      </tr>`;
    })
    .join("");

  return `<div class="sd-table-wrap"><table class="sd-table"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
}

function renderTotals(payload: SalesDocumentPayload): string {
  const lines = payload.financials.filter((f) => !f.highlight);
  const grand = payload.financials.find((f) => f.highlight);
  const grandClass = payload.variant === "quotation" ? "quotation" : "invoice";

  return `
    <div class="sd-totals">
      ${lines.map((l) => `<div class="row"><span>${esc(l.label)}</span><span>${esc(l.value)}</span></div>`).join("")}
      ${payload.shipping ? `<div class="row"><span>Shipping</span><span>${esc(payload.shipping)}</span></div>` : ""}
      <div class="sd-grand ${grandClass}">
        <span class="label">Grand Total</span>
        <span class="value">${esc(grand?.value ?? "")}</span>
      </div>
    </div>`;
}

function renderLeftColumn(payload: SalesDocumentPayload): string {
  if (payload.variant === "quotation") {
    const terms = payload.terms?.length
      ? payload.terms
      : [
          "This quotation is valid for 14 days from the date of issue.",
          "Prices are subject to change without prior notice.",
          "Payment terms: 50% advance, balance on delivery.",
          "Goods remain property of seller until fully paid.",
        ];
    return `
      <div class="sd-side-box">
        <h4>Terms &amp; Conditions</h4>
        <ul>${terms.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
      </div>`;
  }

  const methods = payload.paymentMethods?.length
    ? payload.paymentMethods
    : [{ title: "Cash / Card", lines: ["Pay at point of sale."] }];

  return `
    <div class="sd-side-box">
      <h4>Payment Method</h4>
      ${methods
        .map(
          (m) => `
        <div class="sd-pay-block">
          <p><strong>${esc(m.title)}</strong></p>
          ${m.lines.map((l) => `<p>${esc(l)}</p>`).join("")}
        </div>`
        )
        .join("")}
    </div>
    ${
      payload.amountInWords
        ? `<div class="sd-amount-words">
        <div class="label">Amount in Words</div>
        <div class="value">${esc(payload.amountInWords)}</div>
      </div>`
        : ""
    }`;
}

function renderContactRow(branding: SalesDocumentPayload["branding"]): string {
  const phone = branding.phone || "";
  const email = branding.email || "";
  const web = branding.website || "";
  return `
    ${phone ? `<span>${contactIcon("phone")} ${esc(phone)}</span>` : ""}
    ${email ? `<span>${contactIcon("email")} ${esc(email)}</span>` : ""}
    ${web ? `<span>${contactIcon("web")} ${esc(web)}</span>` : ""}`;
}

function renderFooter(payload: SalesDocumentPayload): string {
  if (payload.variant === "quotation") {
    return `
      <div class="sd-signatures-row">
        <div class="sd-signature"><div class="line">Customer Signature</div></div>
        <div class="sd-signature"><div class="line">Authorized Signature</div></div>
      </div>
      <div class="sd-quote-footer">
        <div class="sd-contact-row">${renderContactRow(payload.branding)}</div>
        <div class="sd-qr">${payload.qrDataUrl ? `<img src="${payload.qrDataUrl}" alt="QR"/>` : ""}</div>
      </div>`;
  }

  return `
    <div class="sd-footer">
      <div class="sd-signature">
        <div class="sign-img">Authorized</div>
        <div class="line">Authorized Signature</div>
      </div>
      <div class="sd-footer-center">
        <div class="thanks">Thank you for your business!</div>
        <div class="sd-contact-row">${renderContactRow(payload.branding)}</div>
      </div>
      <div class="sd-qr">${payload.qrDataUrl ? `<img src="${payload.qrDataUrl}" alt="QR"/>` : ""}</div>
    </div>`;
}

function renderDocBadge(payload: SalesDocumentPayload, title: string): string {
  const isQuote = payload.variant === "quotation";
  if (isQuote) {
    return `
      <div class="sd-doc-badge quote">
        <p class="title">${title}</p>
        <div class="number-wrap"><p class="number">${esc(payload.meta.documentNumber)}</p></div>
      </div>`;
  }
  return `
    <div class="sd-doc-badge">
      <p class="title">${title}</p>
      <p class="number">${esc(payload.meta.documentNumber)}</p>
    </div>`;
}

export function renderSalesDocument(payload: SalesDocumentPayload): string {
  const docTitle = payload.variant === "quotation" ? "QUOTATION" : "TAX INVOICE";
  const company = payload.branding.companyName.toUpperCase();
  const tagline = (payload.branding.tagline ?? "ERP & POS SYSTEM").toUpperCase();
  const partyLines = payload.party.lines?.filter(Boolean) ?? [];

  return `
    <div class="sales-doc">
      <div class="sd-top">
        <div class="sd-brand">
          ${LOGO_HEX}
          <div>
            <h1 class="sd-company-name">${esc(company)}</h1>
            <p class="sd-company-tag">${esc(tagline)}</p>
          </div>
        </div>
        ${renderDocBadge(payload, docTitle)}
      </div>

      <div class="sd-info-row">
        <div>
          <div class="sd-party-label">${esc(payload.party.title)}:</div>
          <div class="sd-party-name">${esc(payload.party.name)}</div>
          ${partyLines.map((l) => `<div class="sd-party-line">${esc(l)}</div>`).join("")}
        </div>
        <table class="sd-meta-table">
          <tbody>
            ${payload.metaRows
              .map((r) => `<tr><td>${esc(r.label)}:</td><td>${esc(r.value)}</td></tr>`)
              .join("")}
          </tbody>
        </table>
      </div>

      ${renderTable(payload)}

      <div class="sd-bottom">
        <div>${renderLeftColumn(payload)}</div>
        <div>${renderTotals(payload)}</div>
      </div>

      ${renderFooter(payload)}
    </div>`;
}

export const SALES_DOCUMENT_TYPES = new Set(["tax_invoice", "sales_invoice", "proforma_invoice", "quotation"]);

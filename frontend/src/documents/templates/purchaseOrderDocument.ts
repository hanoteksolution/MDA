import type { PurchaseOrderPayload } from "../types";
import { renderMdaFooterBar, renderMdaHeader } from "../shared/documentShell";
import { esc } from "../utils";

export function renderPurchaseOrderDocument(payload: PurchaseOrderPayload): string {
  const partyLines = payload.supplier.lines?.filter(Boolean) ?? [];

  const tableRows = payload.rows
    .map(
      (row) => `
    <tr>
      <td class="idx">${String(row.index).padStart(2, "0")}</td>
      <td class="item-name">${esc(row.name)}</td>
      <td class="qty">${row.quantity % 1 === 0 ? row.quantity : row.quantity.toFixed(1)}</td>
      <td class="num">${esc(row.unitCost)}</td>
      <td class="num">${esc(row.tax)}</td>
      <td class="num" style="font-weight:700">${esc(row.total)}</td>
    </tr>`
    )
    .join("");

  const terms = payload.terms?.length
    ? payload.terms
    : [
        "Please send the invoice with the goods.",
        "Payment will be made within agreed terms.",
      ];

  const b = payload.branding;

  return `
    <div class="mda-doc po-doc">
      ${renderMdaHeader(b, "PURCHASE ORDER", esc(payload.orderNumber))}

      <div class="po-info-row">
        <div>
          <div class="po-party-label">Supplier:</div>
          <div class="po-party-name">${esc(payload.supplier.name)}</div>
          ${partyLines.map((l) => `<div class="po-party-line">${esc(l)}</div>`).join("")}
        </div>
        <table class="po-meta-table">
          <tbody>
            ${payload.metaRows.map((r) => `<tr><td>${esc(r.label)} :</td><td>${esc(r.value)}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>

      <div class="po-table-wrap">
        <table class="po-table">
          <thead>
            <tr>
              <th class="center" style="width:34px">#</th>
              <th class="left">Item Description</th>
              <th class="center" style="width:44px">Qty</th>
              <th class="right" style="width:72px">Unit Cost</th>
              <th class="right" style="width:64px">Tax</th>
              <th class="right" style="width:76px">Total</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>

      <div class="po-mid">
        <div class="po-side-box">
          <h4>Shipping Address</h4>
          ${payload.shippingAddress.map((l) => `<p>${esc(l)}</p>`).join("")}
        </div>
        <div class="po-totals-box">
          <div class="po-totals-body">
            ${payload.totals
              .filter((t) => !t.highlight)
              .map((t) => `<div class="row"><span>${esc(t.label)}</span><span>${esc(t.value)}</span></div>`)
              .join("")}
          </div>
          <div class="po-grand">
            <span class="label">Grand Total</span>
            <span class="value">${esc(payload.grandTotal)}</span>
          </div>
        </div>
      </div>

      <div class="po-bottom">
        <div class="po-side-box">
          <h4>Terms &amp; Conditions</h4>
          <ul>${terms.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
        </div>
        <div class="po-signature">
          <p class="sig-label">Authorized Signature</p>
          <div class="sig-line"></div>
        </div>
      </div>

      ${renderMdaFooterBar(b, "Purchase Order")}
    </div>`;
}

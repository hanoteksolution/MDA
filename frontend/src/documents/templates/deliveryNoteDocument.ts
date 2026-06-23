import type { DeliveryNotePayload } from "../types";
import { renderMdaFooterBar, renderMdaHeader } from "../shared/documentShell";
import { esc } from "../utils";

const TRUCK_ICON = `
<svg class="truck" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 40h36V22H18L12 28H4v12z" fill="#2563EB" opacity="0.15"/>
  <path d="M2 42h40V20H17.5L10 28H2v14zm38-2h8l6-8v-6h-6l-8 8v6z" stroke="#2563EB" stroke-width="2.2" stroke-linejoin="round"/>
  <circle cx="14" cy="44" r="4" fill="#2563EB"/>
  <circle cx="46" cy="44" r="4" fill="#2563EB"/>
  <path d="M18 20h10l6 8" stroke="#2563EB" stroke-width="2.2" stroke-linecap="round"/>
</svg>`;

function formatQty(n: number): string {
  return n % 1 === 0 ? String(n) : n.toFixed(1);
}

export function renderDeliveryNoteDocument(payload: DeliveryNotePayload): string {
  const deliverLines = payload.deliverTo.lines?.filter(Boolean) ?? [];

  const tableRows = payload.rows
    .map(
      (row) => `
    <tr>
      <td class="idx">${String(row.index).padStart(2, "0")}</td>
      <td class="item-name">${esc(row.name)}</td>
      <td class="qty">${formatQty(row.quantityOrdered)}</td>
      <td class="qty">${formatQty(row.quantityDelivered)}</td>
      <td class="unit">${esc(row.unit)}</td>
    </tr>`
    )
    .join("");

  const b = payload.branding;

  return `
    <div class="mda-doc dn-doc">
      ${renderMdaHeader(b, "DELIVERY NOTE", esc(payload.deliveryNumber))}

      <div class="dn-info-row">
        <div>
          <div class="dn-party-label">Deliver To:</div>
          <div class="dn-party-name">${esc(payload.deliverTo.name)}</div>
          ${deliverLines.map((l) => `<div class="dn-party-line">${esc(l)}</div>`).join("")}
        </div>
        <table class="dn-meta-table">
          <tbody>
            ${payload.metaRows.map((r) => `<tr><td>${esc(r.label)} :</td><td>${esc(r.value)}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>

      <div class="dn-table-wrap">
        <table class="dn-table">
          <thead>
            <tr>
              <th class="center" style="width:34px">#</th>
              <th class="left">Item Description</th>
              <th class="center" style="width:72px">Qty Ordered</th>
              <th class="center" style="width:80px">Qty Delivered</th>
              <th class="right" style="width:52px">Unit</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>

      <div class="dn-received-box">
        <div>
          <h4>Received By</h4>
          <div class="dn-field"><span class="label">Name:</span><span class="dots"></span></div>
          <div class="dn-field"><span class="label">Signature:</span><span class="dots"></span></div>
          <div class="dn-field"><span class="label">Date:</span><span class="dots"></span></div>
        </div>
        <div class="dn-thanks">
          ${TRUCK_ICON}
          <p>Thank you for your business!</p>
        </div>
      </div>

      ${renderMdaFooterBar(b, "Delivery Note")}
    </div>`;
}

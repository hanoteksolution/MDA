import type { ProductListPayload } from "../types";
import {
  renderMdaFooterBar,
  renderMdaHeader,
  renderMdaKpiGrid,
} from "../shared/documentShell";
import { esc } from "../utils";

const KPI_ICONS: Record<string, string> = {
  products: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z"/></svg>`,
  categories: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>`,
  stock: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14l-5-5 1.41-1.41L12 14.17l7.59-7.59L21 8l-9 9z"/></svg>`,
  value: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/></svg>`,
};

function statusLabel(status: string): string {
  switch (status) {
    case "out_of_stock": return "Out of Stock";
    case "low_stock": return "Low Stock";
    case "inactive": return "Inactive";
    default: return "Active";
  }
}

function renderDonut(slices: ProductListPayload["categoryChart"]): string {
  if (!slices.length) {
    return `<div class="pl-chart-wrap"><div class="pl-donut" style="background:#E2E8F0"><div class="pl-donut-hole"></div></div><p style="color:#94A3B8;font-size:9px">No category data</p></div>`;
  }

  let cumulative = 0;
  const stops: string[] = [];
  for (const slice of slices) {
    const start = cumulative;
    cumulative += slice.pct;
    stops.push(`${slice.color} ${start}% ${cumulative}%`);
  }

  const legend = slices
    .map(
      (s) => `
    <div class="item">
      <span class="dot" style="background:${s.color}"></span>
      <span class="lbl">${esc(s.label)}</span>
      <span class="pct">${s.pct}%</span>
    </div>`
    )
    .join("");

  return `
    <div class="pl-chart-wrap">
      <div class="pl-donut" style="background:conic-gradient(${stops.join(", ")})">
        <div class="pl-donut-hole"></div>
      </div>
      <div class="pl-legend">${legend}</div>
    </div>`;
}

function productImageCell(imageUrl: string | undefined, name: string): string {
  if (imageUrl) {
    return `<img class="product-img" src="${esc(imageUrl)}" alt="" />`;
  }
  return `<div class="product-img-ph">${esc(name.charAt(0).toUpperCase())}</div>`;
}

export function renderProductListDocument(payload: ProductListPayload): string {
  const kpiAccents: Record<string, string> = {
    products: "#2563EB",
    categories: "#2563EB",
    stock: "#16A34A",
    value: "#16A34A",
  };

  const kpis = payload.kpis.map((k) => ({
    label: k.label,
    value: k.value,
    accent: kpiAccents[k.icon] ?? "#2563EB",
    icon: KPI_ICONS[k.icon] ?? KPI_ICONS.products,
  }));

  const tableRows = payload.rows
    .map(
      (row) => `
    <tr>
      <td class="idx">${String(row.index).padStart(2, "0")}</td>
      <td class="sku">${esc(row.sku)}</td>
      <td>
        <div class="product-cell">
          ${productImageCell(row.imageUrl, row.name)}
          <span class="product-name">${esc(row.name)}</span>
        </div>
      </td>
      <td>${esc(row.category)}</td>
      <td class="num">${esc(row.cost)}</td>
      <td class="num">${esc(row.price)}</td>
      <td class="qty">${row.stock}</td>
      <td><span class="pl-badge ${esc(row.status)}">${esc(statusLabel(row.status))}</span></td>
    </tr>`
    )
    .join("");

  const catRows = payload.categorySummary
    .map(
      (c) => `
    <tr>
      <td>${esc(c.category)}</td>
      <td class="right">${c.items}</td>
      <td class="right">${c.stock.toLocaleString()}</td>
      <td class="right">${esc(c.stockValue)}</td>
    </tr>`
    )
    .join("");

  const page = payload.pageNumber ?? 1;
  const pageCount = payload.pageCount ?? 1;

  const ref = `REF: PL-${Date.now().toString().slice(-6)}`;

  return `
    <div class="mda-doc product-list-doc">
      ${renderMdaHeader(payload.branding, "PRODUCT LIST", ref, [
        { label: "Generated", value: payload.generatedAt },
        { label: "By", value: "MDA ERP" },
      ])}

      ${renderMdaKpiGrid(kpis)}

      <div class="pl-table-wrap">
        <table class="pl-table">
          <thead>
            <tr>
              <th class="center" style="width:32px">#</th>
              <th style="width:72px">SKU</th>
              <th>Product</th>
              <th style="width:100px">Category</th>
              <th class="right" style="width:56px">Cost</th>
              <th class="right" style="width:56px">Price</th>
              <th class="center" style="width:48px">Stock</th>
              <th style="width:80px">Status</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>

      <div class="pl-analytics">
        <div class="pl-panel">
          <h3>Category Summary</h3>
          <table class="pl-cat-table">
            <thead>
              <tr>
                <th>Category</th>
                <th class="right">Items</th>
                <th class="right">Stock</th>
                <th class="right">Stock Value</th>
              </tr>
            </thead>
            <tbody>
              ${catRows}
              <tr class="total">
                <td>Total</td>
                <td class="right">${payload.totals.items}</td>
                <td class="right">${payload.totals.stock.toLocaleString()}</td>
                <td class="right">${esc(payload.totals.stockValue)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pl-panel">
          <h3>Stock by Category</h3>
          ${renderDonut(payload.categoryChart)}
        </div>
      </div>

      ${renderMdaFooterBar(payload.branding, "Product List", {
        thanks: "Thank you for using MDA Retail ERP & POS",
        page: `Page ${page} of ${pageCount}`,
        center: true,
      })}
    </div>`;
}

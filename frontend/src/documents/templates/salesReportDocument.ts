import type { SalesReportPayload } from "../types";
import {
  renderMdaFooterBar,
  renderMdaHeader,
  renderMdaKpiGrid,
} from "../shared/documentShell";
import { esc } from "../utils";

const KPI_ICONS: Record<string, string> = {
  sales: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3.5 18.5 9 13l4 4 7.5-7.5L22 12V4h-8l2.5 2.5L9 14l-4.5-4.5L2 12.5z"/></svg>`,
  orders: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1 1 0 0 0 20 5H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/></svg>`,
  customers: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`,
  profit: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z"/></svg>`,
};

const CHART_COLORS = ["#2563EB", "#60A5FA", "#10B981", "#F59E0B", "#001B3D", "#8B5CF6"];

function renderLineChart(points: { hour: string; value: number }[]): string {
  const w = 340;
  const h = 110;
  const padL = 36;
  const padR = 8;
  const padT = 8;
  const padB = 22;
  const maxVal = Math.max(...points.map((p) => p.value), 1);
  const chartW = w - padL - padR;
  const chartH = h - padT - padB;

  const coords = points.map((p, i) => {
    const x = padL + (i / Math.max(points.length - 1, 1)) * chartW;
    const y = padT + chartH - (p.value / maxVal) * chartH;
    return { x, y, ...p };
  });

  const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${coords[coords.length - 1].x.toFixed(1)},${(padT + chartH).toFixed(1)} L${coords[0].x.toFixed(1)},${(padT + chartH).toFixed(1)} Z`;

  const yLabels = [0, 0.25, 0.5, 0.75, 1].map((pct) => {
    const val = maxVal * pct;
    const y = padT + chartH - pct * chartH;
    const label = val >= 1000 ? `$${(val / 1000).toFixed(val >= 1000 && val < 2000 ? 1 : 0)}K` : `$${Math.round(val)}`;
    return `<text x="${padL - 4}" y="${y + 3}" text-anchor="end" fill="#94A3B8" font-size="7">${label}</text>`;
  });

  const xLabels = coords
    .filter((_, i) => i % 4 === 0)
    .map((c) => `<text x="${c.x}" y="${h - 4}" text-anchor="middle" fill="#94A3B8" font-size="7">${esc(c.hour)}</text>`)
    .join("");

  const dots = coords
    .map((c) => `<circle cx="${c.x.toFixed(1)}" cy="${c.y.toFixed(1)}" r="3" fill="#2563EB" stroke="#fff" stroke-width="1.5"/>`)
    .join("");

  return `
    <div class="sr-line-chart">
      <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="srAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#2563EB" stop-opacity="0.25"/>
            <stop offset="100%" stop-color="#2563EB" stop-opacity="0.02"/>
          </linearGradient>
        </defs>
        ${yLabels.join("")}
        <path d="${areaPath}" fill="url(#srAreaGrad)"/>
        <path d="${linePath}" fill="none" stroke="#2563EB" stroke-width="2" stroke-linejoin="round"/>
        ${dots}
        ${xLabels}
      </svg>
    </div>`;
}

function renderDonut(slices: SalesReportPayload["salesByCategory"]): string {
  if (!slices.length) {
    return `<div class="sr-donut-wrap"><div class="sr-donut" style="background:#E2E8F0"><div class="sr-donut-hole"></div></div><p style="color:#94A3B8;font-size:9px">No data</p></div>`;
  }

  let cumulative = 0;
  const stops: string[] = [];
  slices.forEach((s, i) => {
    const start = cumulative;
    cumulative += s.pct;
    stops.push(`${s.color ?? CHART_COLORS[i % CHART_COLORS.length]} ${start}% ${cumulative}%`);
  });

  const legend = slices
    .map(
      (s, i) => `
    <div class="item">
      <span class="dot" style="background:${s.color ?? CHART_COLORS[i % CHART_COLORS.length]}"></span>
      <span class="lbl">${esc(s.label)}: <strong>${s.pct}%</strong></span>
      <span class="amt">${esc(s.revenueFormatted)}</span>
    </div>`
    )
    .join("");

  return `
    <div class="sr-donut-wrap">
      <div class="sr-donut" style="background:conic-gradient(${stops.join(", ")})">
        <div class="sr-donut-hole"></div>
      </div>
      <div class="sr-legend">${legend}</div>
    </div>`;
}

export function renderSalesReportDocument(payload: SalesReportPayload): string {
  const kpiAccents: Record<string, string> = {
    sales: "#2563EB",
    orders: "#2563EB",
    customers: "#2563EB",
    profit: "#B45309",
  };

  const kpis = payload.kpis.map((k) => ({
    label: k.label,
    value: k.value,
    accent: kpiAccents[k.icon] ?? "#2563EB",
    icon: `<div class="icon-wrap">${KPI_ICONS[k.icon] ?? KPI_ICONS.sales}</div>`,
  }));

  const productRows = payload.topProducts
    .map(
      (p) => `
    <tr>
      <td class="idx">${String(p.index).padStart(2, "0")}</td>
      <td class="name">${esc(p.name)}</td>
      <td class="qty">${p.sold % 1 === 0 ? p.sold : p.sold.toFixed(1)}</td>
      <td class="num">${esc(p.revenueFormatted)}</td>
      <td class="num">${esc(p.profitFormatted)}</td>
    </tr>`
    )
    .join("");

  const summaryRows = payload.summary
    .map((s) => {
      const cls = s.highlight ? "row green" : "row";
      return `<div class="${cls}"><span>${esc(s.label)}</span><span>${esc(s.value)}</span></div>`;
    })
    .join("");

  const ref = `REF: SR-${Date.now().toString().slice(-6)}`;

  return `
    <div class="mda-doc sales-report-doc">
      ${renderMdaHeader(payload.branding, "SALES REPORT", ref, [
        { label: "Period", value: payload.dateRange },
        { label: "By", value: "MDA ERP" },
      ])}

      ${renderMdaKpiGrid(kpis)}

      <div class="mda-charts sr-charts">
        <div class="sr-panel">
          <h3>Sales Overview</h3>
          ${renderLineChart(payload.hourlySales)}
        </div>
        <div class="sr-panel">
          <h3>Sales by Category</h3>
          ${renderDonut(payload.salesByCategory)}
        </div>
      </div>

      <div class="sr-bottom">
        <div class="sr-table-wrap">
          <table class="sr-table">
            <thead>
              <tr>
                <th class="center" style="width:28px">#</th>
                <th>Product</th>
                <th class="center" style="width:56px">Qty Sold</th>
                <th class="right" style="width:72px">Total Sales</th>
                <th class="right" style="width:72px">Profit</th>
              </tr>
            </thead>
            <tbody>${productRows}</tbody>
          </table>
        </div>
        <div class="sr-summary">
          <div class="sr-summary-head">Summary</div>
          <div class="sr-summary-body">${summaryRows}</div>
        </div>
      </div>

      ${renderMdaFooterBar(payload.branding, "Sales Report", {
        thanks: "Thank you for your business!",
        page: `Page ${payload.pageNumber ?? 1} of ${payload.pageCount ?? 1}`,
        center: true,
      })}
    </div>`;
}

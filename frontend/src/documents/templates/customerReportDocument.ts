import type { CustomerReportPayload } from "../types";
import {
  renderMdaHeader,
  renderMdaKpiGrid,
  renderMdaSectionLabel,
} from "../shared/documentShell";
import { esc } from "../utils";

const DIST_COLORS: Record<string, string> = {
  Retail: "#10B981",
  Corporate: "#2563EB",
  Wholesale: "#8B5CF6",
};

const AVATAR_COLORS = ["#2563EB", "#10B981", "#8B5CF6", "#F59E0B", "#DC2626", "#001B3D"];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function avatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function formatDocDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function renderGrowthChart(points: { month: string; value: number }[]): string {
  const w = 320;
  const h = 100;
  const padL = 28;
  const padR = 8;
  const padT = 8;
  const padB = 20;
  const maxVal = Math.max(...points.map((p) => p.value), 1);
  const chartW = w - padL - padR;
  const chartH = h - padT - padB;
  const coords = points.map((p, i) => ({
    x: padL + (i / Math.max(points.length - 1, 1)) * chartW,
    y: padT + chartH - (p.value / maxVal) * chartH,
    ...p,
  }));
  const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${coords[coords.length - 1].x.toFixed(1)},${(padT + chartH).toFixed(1)} L${coords[0].x.toFixed(1)},${(padT + chartH).toFixed(1)} Z`;
  const xLabels = coords
    .filter((_, i) => i % 2 === 0)
    .map((c) => `<text x="${c.x}" y="${h - 3}" text-anchor="middle" fill="#94A3B8" font-size="6.5">${esc(c.month)}</text>`)
    .join("");
  return `
    <div class="cr-line-chart">
      <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="crGrowthGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#2563EB" stop-opacity="0.22"/>
            <stop offset="100%" stop-color="#2563EB" stop-opacity="0.02"/>
          </linearGradient>
        </defs>
        <path d="${areaPath}" fill="url(#crGrowthGrad)"/>
        <path d="${linePath}" fill="none" stroke="#2563EB" stroke-width="2"/>
        ${coords.map((c) => `<circle cx="${c.x.toFixed(1)}" cy="${c.y.toFixed(1)}" r="2.5" fill="#2563EB"/>`).join("")}
        ${xLabels}
      </svg>
    </div>`;
}

function renderDonut(slices: CustomerReportPayload["distribution"], total: number): string {
  if (!slices.length) {
    return `<div class="cr-donut-wrap"><div class="cr-donut" style="background:#E2E8F0"><div class="cr-donut-hole"></div></div></div>`;
  }
  let cumulative = 0;
  const stops: string[] = [];
  slices.forEach((s) => {
    const start = cumulative;
    cumulative += s.pct;
    stops.push(`${DIST_COLORS[s.label] ?? "#2563EB"} ${start}% ${cumulative}%`);
  });
  const legend = slices
    .map(
      (s) => `
    <div class="item">
      <span class="dot" style="background:${DIST_COLORS[s.label] ?? "#2563EB"}"></span>
      <span class="lbl">${esc(s.label)}</span>
      <span class="pct">${s.count} · ${s.pct}%</span>
    </div>`
    )
    .join("");
  return `
    <div class="cr-donut-wrap">
      <div class="cr-donut" style="background:conic-gradient(${stops.join(", ")})">
        <div class="cr-donut-hole"></div>
      </div>
      <div class="cr-legend">
        ${legend}
        <div class="cr-total-box">Total Customers: ${total}</div>
      </div>
    </div>`;
}

function renderTopList(rows: CustomerReportPayload["topBySales"]): string {
  if (!rows.length) {
    return `<div class="cr-top-list"><p style="color:#94A3B8;font-size:8px">No data</p></div>`;
  }
  return `
    <div class="cr-top-list">
      ${rows
        .map(
          (r) => `
        <div class="row">
          <span class="rank">${r.rank}</span>
          <span class="name">${esc(r.name)}</span>
          <span class="amt">${esc(r.amount)}</span>
          <span class="pct">${esc(r.pct)}</span>
        </div>`
        )
        .join("")}
    </div>`;
}

export function renderCustomerReportDocument(payload: CustomerReportPayload): string {
  const b = payload.branding;

  const kpis = payload.kpis.map((k) => ({
    label: k.label,
    value: k.value,
    accent: k.color,
    sub: k.sub,
    icon: k.icon,
  }));

  const tableRows = payload.directory
    .map((row) => {
      const typeCls = row.type.toLowerCase();
      const statusCls = row.isActive ? "active" : "inactive";
      const lastTx = row.lastTransaction === "—" ? "—" : formatDocDate(row.lastTransaction);
      return `
    <tr>
      <td class="idx">${String(row.index).padStart(2, "0")}</td>
      <td>
        <div class="cr-customer-cell">
          <div class="cr-avatar" style="background:${avatarColor(row.name)}">${esc(initials(row.name))}</div>
          <span style="font-weight:600">${esc(row.name)}</span>
        </div>
      </td>
      <td>${esc(row.code)}</td>
      <td>${esc(row.phone)}</td>
      <td>${esc(row.email)}</td>
      <td><span class="cr-badge ${typeCls}">${esc(row.type)}</span></td>
      <td class="num">${esc(row.creditLimit)}</td>
      <td class="num">${esc(row.balance)}</td>
      <td>${esc(lastTx)}</td>
      <td class="cr-status ${statusCls}">${esc(row.status)}</td>
    </tr>`;
    })
    .join("");

  const finCards = payload.financialSummary
    .map((f) => `<div class="cr-mini-card"><div class="label">${esc(f.label)}</div><div class="value">${esc(f.value)}</div></div>`)
    .join("");

  const contactCards = payload.contactSummary
    .map(
      (c) =>
        `<div class="cr-mini-card${c.warning ? " warn" : ""}"><div class="label">${esc(c.label)}</div><div class="value">${esc(c.value)}</div></div>`
    )
    .join("");

  const qr = payload.qrDataUrl
    ? `<img class="cr-qr" src="${payload.qrDataUrl}" alt="QR" />`
    : "";

  const contactLines = [
    b.address ? `<div>📍 ${esc(b.address)}</div>` : "",
    b.phone ? `<div>📞 ${esc(b.phone)}</div>` : "",
    b.email ? `<div>✉ ${esc(b.email)}</div>` : "",
    b.website ? `<div>🌐 ${esc(b.website)}</div>` : "",
    b.taxId ? `<div>Tax/VAT: ${esc(b.taxId)}</div>` : "",
  ].join("");

  const totalCustomers = payload.kpis.find((k) => k.key === "total")?.value ?? String(payload.directory.length);

  return `
    <div class="mda-doc customer-report-doc">
      ${renderMdaHeader(b, "CUSTOMERS REPORT", `REF: ${payload.reportId}`, [
        { label: "Report Date", value: formatDocDate(payload.reportDate) },
        { label: "Generated By", value: payload.generatedBy },
        { label: "Branch", value: payload.branch ?? "All Branches" },
        { label: "Print Date", value: formatDocDate(payload.printDate) },
      ])}

      <div class="cr-header-extra">
        <div class="cr-contact">${contactLines}</div>
        ${qr}
      </div>

      ${renderMdaSectionLabel("Customer Summary")}
      ${renderMdaKpiGrid(kpis, "eight cr-kpi-grid")}

      <div class="mda-charts cr-charts">
        <div class="cr-panel">
          <h3>Customer Distribution</h3>
          ${renderDonut(payload.distribution, Number(totalCustomers) || payload.directory.length)}
        </div>
        <div class="cr-panel">
          <div class="cr-panel-head">
            <h3 style="margin:0">Customer Growth (Monthly Registration)</h3>
            <span class="cr-year-badge">${payload.growthYear}</span>
          </div>
          ${renderGrowthChart(payload.monthlyGrowth)}
        </div>
      </div>

      ${renderMdaSectionLabel("Customer Directory")}
      <div class="cr-table-wrap">
        <table class="cr-table">
          <thead>
            <tr>
              <th class="center" style="width:24px">#</th>
              <th>Customer</th>
              <th style="width:52px">Code</th>
              <th style="width:72px">Phone</th>
              <th style="width:88px">Email</th>
              <th style="width:56px">Type</th>
              <th class="right" style="width:56px">Credit Limit</th>
              <th class="right" style="width:52px">Balance</th>
              <th style="width:58px">Last Transaction</th>
              <th style="width:44px">Status</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
        <div class="cr-table-foot">Showing 1 to ${payload.directory.length} of ${payload.directory.length} customers</div>
      </div>

      <div class="cr-mid-grid">
        <div>
          ${renderMdaSectionLabel("Financial Summary")}
          <div class="cr-mini-grid">${finCards}</div>
        </div>
        <div>
          ${renderMdaSectionLabel("Contact Information Summary")}
          <div class="cr-mini-grid">${contactCards}</div>
        </div>
      </div>

      ${renderMdaSectionLabel("Top Customers")}
      <div class="cr-top-grid">
        <div class="cr-panel">
          <h3>Top 5 by Total Sales</h3>
          ${renderTopList(payload.topBySales)}
        </div>
        <div class="cr-panel">
          <h3>Top 5 by Profit</h3>
          ${renderTopList(payload.topByProfit)}
        </div>
        <div class="cr-panel">
          <h3>Top 5 by Outstanding Balance</h3>
          ${renderTopList(payload.topByOutstanding)}
        </div>
      </div>

      <div class="cr-signoff">
        <div class="cr-thanks">
          <p class="script">Thank You!</p>
          <p>We appreciate your business and continued partnership with MDA Retail.</p>
          <p style="margin-top:6px">${b.phone ? `📞 ${esc(b.phone)}` : ""} ${b.email ? `· ✉ ${esc(b.email)}` : ""}</p>
        </div>
        <div class="cr-sign-box">
          <div class="label">Authorized Signature</div>
          <div class="line"></div>
        </div>
        <div class="cr-page-meta">
          <div>Page ${payload.pageNumber ?? 1} of ${payload.pageCount ?? 1}</div>
          <div>Generated ${esc(payload.generatedAt)}</div>
        </div>
      </div>

      <footer class="mda-footer-bar cr-footer">
        Confidential ERP Report | MDA Retail ERP &amp; POS System | Enterprise Edition
      </footer>
    </div>`;
}

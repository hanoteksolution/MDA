import { KPI_ACCENTS, STATUS_STYLES } from "./tokens";
import type {
  AnalyticsBlock,
  DocumentBranding,
  DocumentMeta,
  DocumentStatus,
  FinancialLine,
  KpiCardData,
  LineItemRow,
  PartyInfo,
  SignatureBlock,
  TableColumn,
} from "./types";
import { esc, nowStamp } from "./utils";

export function statusBadge(status?: DocumentStatus): string {
  if (!status) return "";
  const s = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return `<span class="mda-status-badge" style="background:${s.bg};color:${s.color}">${s.label}</span>`;
}

export function renderHeader(
  branding: DocumentBranding,
  meta: DocumentMeta,
  codes?: { qr?: string; barcode?: string }
): string {
  const logo = branding.logoUrl
    ? `<img src="${esc(branding.logoUrl)}" alt="" />`
    : esc(branding.companyName.charAt(0));

  return `
    <header class="mda-doc-header">
      <div class="mda-brand">
        <div class="mda-logo">${logo}</div>
        <div>
          <h1>${esc(branding.companyName)}</h1>
          <p class="tagline">${esc(branding.tagline ?? "ERP & POS System")}</p>
          ${branding.branchName ? `<p class="meta-line">${esc(branding.branchName)}${branding.branchCode ? ` · ${esc(branding.branchCode)}` : ""}</p>` : ""}
          <p class="meta-line">${esc(branding.address)}</p>
          <p class="meta-line">${esc(branding.phone)}${branding.email ? ` · ${esc(branding.email)}` : ""}</p>
          ${branding.taxId ? `<p class="meta-line">Tax ID: ${esc(branding.taxId)}</p>` : ""}
        </div>
      </div>
      <div class="mda-doc-meta">
        <p class="mda-doc-title">${esc(meta.documentTitle)}</p>
        <div class="mda-doc-number">${esc(meta.documentNumber)}</div>
        <div class="mda-meta-grid">
          <div><strong>Issue:</strong> ${esc(meta.issueDate)}</div>
          ${meta.dueDate ? `<div><strong>Due:</strong> ${esc(meta.dueDate)}</div>` : ""}
          ${meta.generatedBy ? `<div><strong>By:</strong> ${esc(meta.generatedBy)}</div>` : ""}
          ${meta.reference ? `<div><strong>Ref:</strong> ${esc(meta.reference)}</div>` : ""}
        </div>
        ${statusBadge(meta.status)}
        ${codes?.qr || codes?.barcode ? `
          <div class="mda-header-codes">
            ${codes.barcode ? `<img src="${codes.barcode}" alt="" height="32" />` : ""}
            ${codes.qr ? `<img src="${codes.qr}" alt="" width="48" height="48" />` : ""}
          </div>` : ""}
      </div>
    </header>`;
}

export function renderParties(billTo?: PartyInfo, shipTo?: PartyInfo): string {
  if (!billTo && !shipTo) return "";
  const party = (p: PartyInfo) => `
    <div class="mda-party">
      <h3>${esc(p.title)}</h3>
      <div class="name">${esc(p.name)}</div>
      ${(p.lines ?? []).map((l) => `<div class="line">${esc(l)}</div>`).join("")}
    </div>`;
  return `<div class="mda-parties">${billTo ? party(billTo) : ""}${shipTo ? party(shipTo) : ""}</div>`;
}

export function renderKpiGrid(kpis?: KpiCardData[]): string {
  if (!kpis?.length) return "";
  return `<div class="mda-kpi-grid">${kpis
    .map(
      (k) => `
    <div class="mda-kpi" style="--kpi-accent:${KPI_ACCENTS[k.accent ?? "primary"]}">
      <div class="label">${esc(k.label)}</div>
      <div class="value">${esc(k.value)}</div>
    </div>`
    )
    .join("")}</div>`;
}

export function renderDataGrid(columns: TableColumn[], rows: LineItemRow[]): string {
  const head = columns
    .map(
      (c) =>
        `<th class="${c.align === "center" ? "center" : c.align === "right" ? "right" : ""}">${esc(c.label)}</th>`
    )
    .join("");

  const body = rows
    .map((row) => {
      const cells = columns
        .map((col) => {
          const align = col.align === "center" ? "center" : col.align === "right" ? "right" : "left";
          let content = "";
          switch (col.key) {
            case "item":
              content = `
                <div style="display:flex;gap:10px;align-items:flex-start">
                  ${row.imageUrl ? `<img class="item-img" src="${esc(row.imageUrl)}" alt="" />` : ""}
                  <div>
                    <div class="item-name">${esc(row.name)}</div>
                    ${row.sku ? `<div class="item-sub">SKU: ${esc(row.sku)}</div>` : ""}
                    ${row.description ? `<div class="item-sub">${esc(row.description)}</div>` : ""}
                    ${row.category ? `<div class="item-sub">${esc(row.category)}</div>` : ""}
                  </div>
                </div>`;
              break;
            case "qty":
              content = esc(String(row.quantity ?? ""));
              break;
            case "unit_price":
              content = esc(row.unitPrice ?? "");
              break;
            case "discount":
              content = esc(row.discount ?? "—");
              break;
            case "tax":
              content = esc(row.tax ?? "—");
              break;
            case "total":
              content = `<strong>${esc(row.total)}</strong>`;
              break;
            case "status":
              content = row.status ? statusBadge(row.status) : "";
              break;
            default:
              content = esc(row.extra?.[col.key] ?? "");
          }
          return `<td style="text-align:${align}">${content}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  return `
    <div class="mda-table-wrap">
      <table class="mda-table">
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

export function renderSimpleTable(
  columns: { header: string; align?: "left" | "center" | "right" }[],
  rows: string[][]
): string {
  const head = columns
    .map(
      (c) =>
        `<th class="${c.align === "center" ? "center" : c.align === "right" ? "right" : ""}">${esc(c.header)}</th>`
    )
    .join("");
  const body = rows
    .map((row) => {
      const cells = row
        .map((cell, i) => {
          const align = columns[i]?.align ?? "left";
          return `<td style="text-align:${align}">${esc(cell)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `
    <div class="mda-table-wrap">
      <table class="mda-table">
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

export function renderFinancials(lines?: FinancialLine[]): string {
  if (!lines?.length) return "";
  const rows = lines
    .filter((l) => !l.highlight)
    .map(
      (l) =>
        `<div class="row${l.emphasis ? " highlight" : ""}"><span>${esc(l.label)}</span><strong>${esc(l.value)}</strong></div>`
    )
    .join("");
  const grand = lines.find((l) => l.highlight);
  return `
    <div class="mda-financial">
      ${rows}
      ${
        grand
          ? `<div class="grand"><span>${esc(grand.label)}</span><span>${esc(grand.value)}</span></div>`
          : ""
      }
    </div>`;
}

export function renderAnalytics(blocks?: AnalyticsBlock[]): string {
  if (!blocks?.length) return "";
  return blocks
    .map(
      (b) => `
    <div class="mda-analytics">
      <h4>${esc(b.title)}</h4>
      ${b.items
        .map(
          (i) => `
        <div class="mda-analytics-row">
          <span>${esc(i.label)}</span>
          <span><strong>${esc(i.value)}</strong>${i.pct ? ` <span style="color:#10B981">${esc(i.pct)}</span>` : ""}</span>
        </div>`
        )
        .join("")}
    </div>`
    )
    .join("");
}

export function renderBottomSection(
  analytics?: AnalyticsBlock[],
  financials?: FinancialLine[]
): string {
  if (!analytics?.length && !financials?.length) return "";
  return `
    <div class="mda-bottom">
      <div>${renderAnalytics(analytics)}</div>
      <div>${renderFinancials(financials)}</div>
    </div>`;
}

export function renderNotes(notes?: string, terms?: string): string {
  if (!notes && !terms) return "";
  return `
    ${notes ? `<div class="mda-notes"><strong>Notes</strong>${esc(notes)}</div>` : ""}
    ${terms ? `<div class="mda-notes"><strong>Terms & Conditions</strong>${esc(terms)}</div>` : ""}`;
}

export function renderSignatures(blocks?: SignatureBlock[]): string {
  if (!blocks?.length) return "";
  return `<div class="mda-signatures">${blocks
    .map(
      (s) => `
    <div class="mda-signature">
      <div class="label">${esc(s.label)}</div>
      <div class="line">${esc(s.name ?? "")}${s.title ? ` · ${esc(s.title)}` : ""}</div>
    </div>`
    )
    .join("")}</div>`;
}

export function renderFooter(branding: DocumentBranding, message?: string, confidential?: boolean): string {
  return `
    <footer class="mda-doc-footer">
      <div>
        <div class="thanks">${esc(message ?? "Thank you for your business")}</div>
        ${confidential ? `<div class="confidential">Confidential — For authorized use only</div>` : ""}
      </div>
      <div style="text-align:right">
        <div>${esc(branding.website ?? "")} · ${esc(branding.email ?? "")}</div>
        <div>Generated ${esc(nowStamp())}</div>
      </div>
    </footer>`;
}

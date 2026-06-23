import type { TableReportDocument } from "../types";
import {
  renderMdaFooterBar,
  renderMdaHeader,
  renderMdaKpiGrid,
} from "../shared/documentShell";
import { esc } from "../utils";

function alignClass(align?: string): string {
  if (align === "center") return "center";
  if (align === "right") return "right";
  return "";
}

export function renderTableReportDocumentPremium(doc: TableReportDocument): string {
  const generatedBy = doc.generatedBy ?? "MDA ERP";
  const ref = doc.reference ? `REF: ${doc.reference}` : `REF: RPT-${Date.now().toString().slice(-6)}`;
  const issueDate = new Date().toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  const kpis = (doc.kpis ?? []).map((k) => ({
    label: k.label,
    value: k.value,
    accent: k.accent === "success" ? "#16A34A" : k.accent === "warning" ? "#F59E0B" : "#2563EB",
  }));

  const headerCells = doc.columns
    .map((col) => `<th class="${alignClass(col.align)}">${esc(col.header)}</th>`)
    .join("");

  const bodyRows = doc.rows
    .map(
      (row) => `
    <tr>
      ${row
        .map((cell, i) => {
          const align = alignClass(doc.columns[i]?.align);
          const cls = cell === "Low Stock" ? ' style="color:#B45309;font-weight:600"' :
            cell === "Out of Stock" ? ' style="color:#DC2626;font-weight:600"' :
            cell === "OK" || cell === "Active" ? ' style="color:#16A34A;font-weight:600"' :
            cell === "Inactive" ? ' style="color:#64748B"' : "";
          return `<td${align ? ` class="${align}"` : ""}${cls}>${esc(cell)}</td>`;
        })
        .join("")}
    </tr>`
    )
    .join("");

  return `
    <div class="mda-doc table-report-doc">
      ${renderMdaHeader(doc.branding, doc.title.toUpperCase(), ref, [
        { label: "Date", value: issueDate },
        { label: "By", value: generatedBy },
      ])}

      ${renderMdaKpiGrid(kpis)}

      <div class="mda-table-wrap tr-table-wrap">
        <table class="mda-table tr-table">
          <thead><tr>${headerCells}</tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>

      ${renderMdaFooterBar(doc.branding, doc.title)}
    </div>`;
}

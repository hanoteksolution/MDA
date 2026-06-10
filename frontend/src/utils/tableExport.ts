import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

export interface ExportColumn<T> {
  header: string;
  exportValue: (row: T) => string;
}

export interface TableExportOptions<T> {
  title: string;
  columns: ExportColumn<T>[];
  data: T[];
  subtitle?: string;
}

function buildRows<T>(columns: ExportColumn<T>[], data: T[]): string[][] {
  return data.map((row) => columns.map((col) => col.exportValue(row)));
}

export function printTable<T>({ title, columns, data, subtitle }: TableExportOptions<T>) {
  const headers = columns.map((c) => c.header);
  const rows = buildRows(columns, data);

  const html = `<!DOCTYPE html>
<html><head>
  <title>${title}</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; padding: 32px; color: #111; }
    h1 { font-size: 20px; margin: 0 0 4px; }
    p.meta { color: #666; font-size: 12px; margin: 0 0 20px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { text-align: left; background: #f4f6f8; padding: 10px 12px; border-bottom: 2px solid #e2e8f0; }
    td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
    tr:nth-child(even) td { background: #fafbfc; }
    @media print { body { padding: 16px; } }
  </style>
</head><body>
  <h1>${title}</h1>
  <p class="meta">${subtitle ?? `Generated ${new Date().toLocaleString()}`} · ${data.length} record(s)</p>
  <table>
    <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>
      ${rows.map((row) => `<tr>${row.map((c) => `<td>${c.replace(/</g, "&lt;")}</td>`).join("")}</tr>`).join("")}
    </tbody>
  </table>
</body></html>`;

  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) return;
  win.document.write(html);
  win.document.close();
  win.focus();
  win.print();
}

export function downloadTablePdf<T>({ title, columns, data, subtitle }: TableExportOptions<T>) {
  const doc = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();

  doc.setFontSize(16);
  doc.setTextColor(17, 24, 39);
  doc.text(title, 40, 40);

  doc.setFontSize(10);
  doc.setTextColor(100, 116, 139);
  doc.text(subtitle ?? `Generated ${new Date().toLocaleString()}`, 40, 58);

  autoTable(doc, {
    startY: 72,
    head: [columns.map((c) => c.header)],
    body: buildRows(columns, data),
    styles: {
      fontSize: 9,
      cellPadding: 6,
      lineColor: [226, 232, 240],
      lineWidth: 0.5,
    },
    headStyles: {
      fillColor: [16, 185, 129],
      textColor: 255,
      fontStyle: "bold",
    },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    margin: { left: 40, right: 40 },
    tableWidth: pageWidth - 80,
  });

  const safeName = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  doc.save(`${safeName || "export"}-${new Date().toISOString().slice(0, 10)}.pdf`);
}

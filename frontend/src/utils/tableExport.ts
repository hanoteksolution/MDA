import { getDocumentBranding } from "@/documents/branding";
import { downloadTableReportPdf, printTableReport } from "@/documents/engine";
import type { TableReportDocument } from "@/documents/types";
import { nowStamp } from "@/documents/utils";

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

export async function buildTableReportDocument<T>({
  title,
  columns,
  data,
  subtitle,
}: TableExportOptions<T>): Promise<TableReportDocument> {
  const branding = await getDocumentBranding();
  const stamp = nowStamp();
  return {
    title,
    subtitle: subtitle ?? `Generated ${stamp} · ${data.length} record(s)`,
    branding,
    columns: columns.map((c) => ({ header: c.header })),
    rows: data.map((row) => columns.map((col) => col.exportValue(row))),
    reference: `RPT-${Date.now().toString().slice(-6)}`,
    generatedAt: stamp,
    generatedBy: "MDA ERP",
    kpis: [
      { label: "Records", value: String(data.length), accent: "primary" },
      { label: "Report", value: title, accent: "neutral" },
      { label: "Generated", value: new Date().toLocaleDateString(), accent: "success" },
      { label: "System", value: "MDA ERP", accent: "primary" },
    ],
  };
}

export async function printTable<T>(options: TableExportOptions<T>) {
  const doc = await buildTableReportDocument(options);
  await printTableReport(doc);
}

export async function downloadTablePdf<T>(options: TableExportOptions<T>) {
  const doc = await buildTableReportDocument(options);
  await downloadTableReportPdf(doc);
}

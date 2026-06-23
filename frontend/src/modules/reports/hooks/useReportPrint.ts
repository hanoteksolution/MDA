import { useCallback, useState } from "react";
import { downloadTableReportPdf, printTableReport } from "@/documents/engine";
import type { ReportResult } from "@/services/api/reports";
import { reportsApi } from "@/services/api/reports";
import { buildTableReportDocument } from "@/utils/tableExport";
import { formatCurrency } from "@/utils/cn";
import { slugFilename } from "@/documents/utils";

function formatHeader(col: string): string {
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isCurrencyColumn(col: string): boolean {
  return (
    col.includes("amount") ||
    col.includes("total") ||
    col.includes("revenue") ||
    col.includes("value") ||
    col.includes("cost") ||
    col.includes("balance") ||
    col.includes("profit") ||
    col === "value"
  );
}

function formatCell(col: string, val: string | number | undefined | null): string {
  if (val == null) return "";
  if (typeof val === "number" && isCurrencyColumn(col)) {
    return formatCurrency(val);
  }
  return String(val);
}

function periodSubtitle(dateFrom?: string, dateTo?: string): string | undefined {
  if (!dateFrom && !dateTo) return undefined;
  const from = dateFrom ? new Date(dateFrom).toLocaleDateString() : "…";
  const to = dateTo ? new Date(dateTo).toLocaleDateString() : "…";
  return `Period: ${from} to ${to}`;
}

async function documentFromResult(
  reportData: ReportResult,
  title: string,
  dateFrom?: string,
  dateTo?: string
) {
  const columns = reportData.columns.map((col) => ({
    header: formatHeader(col),
    exportValue: (row: Record<string, string | number>) => formatCell(col, row[col]),
  }));

  return buildTableReportDocument({
    title,
    columns,
    data: reportData.rows,
    subtitle: periodSubtitle(dateFrom, dateTo),
  });
}

export function useReportPrint(dateFrom?: string, dateTo?: string) {
  const [printing, setPrinting] = useState(false);

  const printReportData = useCallback(
    async (reportData: ReportResult, title: string) => {
      setPrinting(true);
      try {
        const doc = await documentFromResult(reportData, title, dateFrom, dateTo);
        await printTableReport(doc);
      } finally {
        setPrinting(false);
      }
    },
    [dateFrom, dateTo]
  );

  const downloadReportData = useCallback(
    async (reportData: ReportResult, title: string) => {
      setPrinting(true);
      try {
        const doc = await documentFromResult(reportData, title, dateFrom, dateTo);
        await downloadTableReportPdf(doc, `${slugFilename(title)}.pdf`);
      } finally {
        setPrinting(false);
      }
    },
    [dateFrom, dateTo]
  );

  const printReport = useCallback(
    async (category: string, reportName: string) => {
      setPrinting(true);
      try {
        const res = await reportsApi.data({
          category,
          report: reportName,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        });
        const doc = await documentFromResult(res.data, reportName, dateFrom, dateTo);
        await printTableReport(doc);
      } finally {
        setPrinting(false);
      }
    },
    [dateFrom, dateTo]
  );

  const downloadReport = useCallback(
    async (category: string, reportName: string) => {
      setPrinting(true);
      try {
        const res = await reportsApi.data({
          category,
          report: reportName,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        });
        const doc = await documentFromResult(res.data, reportName, dateFrom, dateTo);
        await downloadTableReportPdf(doc, `${slugFilename(reportName)}.pdf`);
      } finally {
        setPrinting(false);
      }
    },
    [dateFrom, dateTo]
  );

  return {
    printing,
    printReportData,
    downloadReportData,
    printReport,
    downloadReport,
  };
}

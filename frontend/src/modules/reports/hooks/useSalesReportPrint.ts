import { useCallback, useState } from "react";
import { reportsApi } from "@/services/api/reports";
import { buildSalesReportDocument } from "@/documents/salesReport";
import { downloadSalesReportPdf, printSalesReportDocument } from "@/documents/engine";

export function useSalesReportPrint(dateFrom?: string, dateTo?: string) {
  const [printing, setPrinting] = useState(false);

  const loadDocument = useCallback(async () => {
    const res = await reportsApi.salesPrint({
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    });
    return buildSalesReportDocument(res.data);
  }, [dateFrom, dateTo]);

  const printSalesReport = useCallback(async () => {
    setPrinting(true);
    try {
      const doc = await loadDocument();
      await printSalesReportDocument(doc);
    } finally {
      setPrinting(false);
    }
  }, [loadDocument]);

  const downloadSalesReport = useCallback(async () => {
    setPrinting(true);
    try {
      const doc = await loadDocument();
      await downloadSalesReportPdf(doc, "sales-report.pdf");
    } finally {
      setPrinting(false);
    }
  }, [loadDocument]);

  return { printing, printSalesReport, downloadSalesReport };
}

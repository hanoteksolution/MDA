import { useCallback, useState } from "react";
import { customersApi } from "@/services/api/partners";
import { buildCustomerReportDocument } from "@/documents/customerReport";
import { downloadCustomerReportPdf, printCustomerReportDocument } from "@/documents/engine";
import { generateQrDataUrl } from "@/modules/pos/receipt/receiptAssets";

export function useCustomerListPrint(filters?: { search?: string; customer_type?: string }) {
  const [printing, setPrinting] = useState(false);

  const loadDocument = useCallback(async () => {
    const params: Record<string, string | undefined> = {};
    if (filters?.search) params.search = filters.search;
    if (filters?.customer_type) params.customer_type = filters.customer_type;

    const res = await customersApi.printReport(params);
    const qr = await generateQrDataUrl(
      `${typeof window !== "undefined" ? window.location.origin : ""}/customers`,
      120
    );
    return buildCustomerReportDocument(res.data, qr);
  }, [filters?.search, filters?.customer_type]);

  const printCustomerList = useCallback(async () => {
    setPrinting(true);
    try {
      const doc = await loadDocument();
      await printCustomerReportDocument(doc);
    } finally {
      setPrinting(false);
    }
  }, [loadDocument]);

  const downloadCustomerList = useCallback(async () => {
    setPrinting(true);
    try {
      const doc = await loadDocument();
      const name = doc.meta.documentNumber ? `${doc.meta.documentNumber}.pdf` : "customers-report.pdf";
      await downloadCustomerReportPdf(doc, name);
    } finally {
      setPrinting(false);
    }
  }, [loadDocument]);

  return { printing, printCustomerList, downloadCustomerList };
}

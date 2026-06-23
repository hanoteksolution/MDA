import { useCallback, useState } from "react";
import { purchasesApi } from "@/services/api/partners";
import { buildPurchaseOrderDocument } from "@/documents/purchaseOrder";
import { downloadPurchaseOrderPdf, printPurchaseOrderDocument } from "@/documents/engine";

export function usePurchaseOrderPrint() {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const loadDocument = useCallback(async (orderId: string) => {
    const res = await purchasesApi.get(orderId);
    return buildPurchaseOrderDocument(res.data);
  }, []);

  const printPurchaseOrder = useCallback(
    async (orderId: string) => {
      setLoadingId(orderId);
      try {
        const doc = await loadDocument(orderId);
        await printPurchaseOrderDocument(doc);
      } finally {
        setLoadingId(null);
      }
    },
    [loadDocument]
  );

  const downloadPurchaseOrder = useCallback(
    async (orderId: string, orderNumber?: string) => {
      setLoadingId(orderId);
      try {
        const doc = await loadDocument(orderId);
        const filename = orderNumber ? `${orderNumber}.pdf` : undefined;
        await downloadPurchaseOrderPdf(doc, filename);
      } finally {
        setLoadingId(null);
      }
    },
    [loadDocument]
  );

  return { loadingId, printPurchaseOrder, downloadPurchaseOrder };
}

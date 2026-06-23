import { useCallback, useState } from "react";
import { salesApi } from "@/services/api/sales";
import type { PosReceipt } from "@/services/api/pos";
import type { SalesDocumentPreviewState } from "../components/SalesReceiptDialog";
import {
  printReceiptDocument,
  downloadReceiptDocumentPdf,
  printQuotationDocument,
  downloadQuotationDocumentPdf,
  printDeliveryNoteDocument,
  downloadDeliveryNotePdf,
} from "@/documents/engine";
import { buildDeliveryNoteDocument } from "@/documents/deliveryNote";
import { getDocumentBranding } from "@/documents/branding";
import { generateBarcodeDataUrl, generateQrDataUrl } from "@/modules/pos/receipt/receiptAssets";
import { getVerificationUrl } from "@/modules/pos/receipt/receiptFormat";
import { printThermalReceipt80 } from "@/modules/pos/receipt/printReceipt";

export function useSalesReceipt() {
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [documentPreview, setDocumentPreview] = useState<SalesDocumentPreviewState | null>(null);

  const fetchReceipt = useCallback(async (invoiceId: string) => {
    const res = await salesApi.getInvoiceReceipt(invoiceId);
    return res.data;
  }, []);

  const loadAssets = useCallback(async (receipt: PosReceipt) => {
    const verificationUrl = getVerificationUrl(receipt);
    const [qr, barcode] = await Promise.all([
      generateQrDataUrl(verificationUrl, 160),
      Promise.resolve(generateBarcodeDataUrl(receipt.invoice_number, 1.4, 40)),
    ]);
    return { qr, barcode };
  }, []);

  const printReceipt = useCallback(
    async (invoiceId: string) => {
      setLoadingId(invoiceId);
      try {
        const receipt = await fetchReceipt(invoiceId);
        await printThermalReceipt80(receipt);
      } finally {
        setLoadingId(null);
      }
    },
    [fetchReceipt]
  );

  const downloadReceipt = useCallback(
    async (invoiceId: string) => {
      setLoadingId(invoiceId);
      try {
        const receipt = await fetchReceipt(invoiceId);
        const assets = await loadAssets(receipt);
        await downloadReceiptDocumentPdf(receipt, assets, "tax_invoice");
      } finally {
        setLoadingId(null);
      }
    },
    [fetchReceipt, loadAssets]
  );

  const printInvoice = useCallback(
    async (invoiceId: string) => {
      setLoadingId(invoiceId);
      try {
        const receipt = await fetchReceipt(invoiceId);
        const assets = await loadAssets(receipt);
        await printReceiptDocument(receipt, assets, "tax_invoice");
      } finally {
        setLoadingId(null);
      }
    },
    [fetchReceipt, loadAssets]
  );

  const printDeliveryNote = useCallback(async (invoiceId: string) => {
    setLoadingId(invoiceId);
    try {
      const res = await salesApi.getInvoiceDeliveryNote(invoiceId);
      const doc = await buildDeliveryNoteDocument(res.data);
      await printDeliveryNoteDocument(doc);
    } finally {
      setLoadingId(null);
    }
  }, []);

  const downloadDeliveryNote = useCallback(async (invoiceId: string) => {
    setLoadingId(invoiceId);
    try {
      const res = await salesApi.getInvoiceDeliveryNote(invoiceId);
      const doc = await buildDeliveryNoteDocument(res.data);
      await downloadDeliveryNotePdf(doc, `${res.data.delivery_number}.pdf`);
    } finally {
      setLoadingId(null);
    }
  }, []);

  const printQuotation = useCallback(async (quotationId: string) => {
    setLoadingId(quotationId);
    try {
      const [qRes, branding] = await Promise.all([
        salesApi.getQuotation(quotationId),
        getDocumentBranding(),
      ]);
      const q = qRes.data;
      const qr = await generateQrDataUrl(
        `${typeof window !== "undefined" ? window.location.origin : ""}/sales/quotations/${q.id}`,
        160
      );
      await printQuotationDocument(q, branding, { qr });
    } finally {
      setLoadingId(null);
    }
  }, []);

  const downloadQuotation = useCallback(async (quotationId: string) => {
    setLoadingId(quotationId);
    try {
      const [qRes, branding] = await Promise.all([
        salesApi.getQuotation(quotationId),
        getDocumentBranding(),
      ]);
      const q = qRes.data;
      const qr = await generateQrDataUrl(
        `${typeof window !== "undefined" ? window.location.origin : ""}/sales/quotations/${q.id}`,
        160
      );
      await downloadQuotationDocumentPdf(q, branding, { qr });
    } finally {
      setLoadingId(null);
    }
  }, []);

  const openPreview = useCallback(
    async (invoiceId: string, mode: SalesDocumentPreviewState["mode"]) => {
      setLoadingId(invoiceId);
      try {
        const receipt = await fetchReceipt(invoiceId);
        setDocumentPreview({ receipt, mode });
      } finally {
        setLoadingId(null);
      }
    },
    [fetchReceipt]
  );

  const viewInvoice = useCallback(
    (invoiceId: string) => openPreview(invoiceId, "invoice"),
    [openPreview]
  );

  const viewThermalReceipt = useCallback(
    (invoiceId: string) => openPreview(invoiceId, "receipt"),
    [openPreview]
  );

  const closePreview = useCallback(() => setDocumentPreview(null), []);

  return {
    loadingId,
    documentPreview,
    printReceipt,
    printInvoice,
    printDeliveryNote,
    printQuotation,
    downloadReceipt,
    downloadDeliveryNote,
    downloadQuotation,
    viewInvoice,
    viewThermalReceipt,
    closePreview,
  };
}

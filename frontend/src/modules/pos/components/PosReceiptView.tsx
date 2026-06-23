import { useState } from "react";
import {
  Download,
  Mail,
  Printer,
  Loader2,
  Plus,
  FileText,
  Receipt as ReceiptIcon,
} from "lucide-react";
import type { PosReceipt } from "@/services/api/pos";
import { Button } from "@/components/ui/button";
import { SalesDocumentPreview } from "@/documents/components/SalesDocumentPreview";
import { ThermalReceiptPreview } from "../receipt/ThermalReceiptPreview";
import { printReceiptDocument, downloadReceiptDocumentPdf } from "@/documents/engine";
import { generateBarcodeDataUrl, generateQrDataUrl } from "../receipt/receiptAssets";
import { getVerificationUrl } from "../receipt/receiptFormat";
import { printThermalReceipt58, printThermalReceipt80 } from "../receipt/printReceipt";
import { cn } from "@/utils/cn";

export type ReceiptPreviewTab = "invoice" | "receipt";

/** invoice = A4 tax invoice only; receipt = thermal only; both = tab switcher (POS). */
export type DocumentPreviewMode = "invoice" | "receipt" | "both";

interface PosReceiptViewProps {
  receipt: PosReceipt;
  onPrint?: () => void;
  onNewSale?: () => void;
  compact?: boolean;
  showActions?: boolean;
  /** Lock preview to one document type, or allow switching (POS). */
  mode?: DocumentPreviewMode;
  /** Initial tab when mode is "both". */
  defaultPreview?: ReceiptPreviewTab;
  onPreviewTabChange?: (tab: ReceiptPreviewTab) => void;
}

export function PosReceiptView({
  receipt,
  onPrint,
  onNewSale,
  compact,
  showActions = true,
  mode = "both",
  defaultPreview = "receipt",
  onPreviewTabChange,
}: PosReceiptViewProps) {
  const [previewTab, setPreviewTab] = useState<ReceiptPreviewTab>(
    mode === "both" ? defaultPreview : mode
  );
  const [printing, setPrinting] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const activeTab: ReceiptPreviewTab = mode === "both" ? previewTab : mode;

  const selectTab = (tab: ReceiptPreviewTab) => {
    if (mode !== "both") return;
    setPreviewTab(tab);
    onPreviewTabChange?.(tab);
  };

  const handlePrint = async (fn: (r: PosReceipt) => Promise<void>) => {
    setPrinting(true);
    try {
      await fn(receipt);
      onPrint?.();
    } finally {
      setPrinting(false);
    }
  };

  const loadAssets = async () => {
    const verificationUrl = getVerificationUrl(receipt);
    const [qr, barcode] = await Promise.all([
      generateQrDataUrl(verificationUrl, 160),
      Promise.resolve(generateBarcodeDataUrl(receipt.invoice_number, 1.4, 40)),
    ]);
    return { qr, barcode };
  };

  const handleDownloadInvoicePdf = async () => {
    setDownloading(true);
    try {
      const assets = await loadAssets();
      await downloadReceiptDocumentPdf(receipt, assets, "tax_invoice");
    } finally {
      setDownloading(false);
    }
  };

  const handlePrintInvoice = async () => {
    setPrinting(true);
    try {
      const assets = await loadAssets();
      await printReceiptDocument(receipt, assets, "tax_invoice");
      onPrint?.();
    } finally {
      setPrinting(false);
    }
  };

  const handleEmail = () => {
    const isInvoice = activeTab === "invoice";
    const subject = encodeURIComponent(
      `${isInvoice ? "Tax Invoice" : "Receipt"} ${receipt.invoice_number}`
    );
    const body = encodeURIComponent(
      `Thank you for your purchase.\n\n${isInvoice ? "Invoice" : "Receipt"}: ${receipt.invoice_number}\nTotal: ${receipt.total_amount}\n\n— ${receipt.company.name}`
    );
    window.open(`mailto:?subject=${subject}&body=${body}`, "_blank");
  };

  const showInvoiceActions = mode === "invoice" || activeTab === "invoice";
  const showReceiptActions = mode === "receipt" || activeTab === "receipt";

  return (
    <div className={compact ? "space-y-4" : "space-y-5"}>
      {mode === "both" && (
        <div className="flex rounded-xl border border-border bg-muted/40 p-1">
          <button
            type="button"
            onClick={() => selectTab("invoice")}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors",
              activeTab === "invoice"
                ? "bg-white text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <FileText className="h-4 w-4 shrink-0" />
            Tax Invoice (A4)
          </button>
          <button
            type="button"
            onClick={() => selectTab("receipt")}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors",
              activeTab === "receipt"
                ? "bg-white text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <ReceiptIcon className="h-4 w-4 shrink-0" />
            Receipt (Thermal)
          </button>
        </div>
      )}

      {activeTab === "invoice" ? (
        <SalesDocumentPreview
          receipt={receipt}
          type="tax_invoice"
          className={compact ? "max-h-[58vh]" : "max-h-[62vh]"}
        />
      ) : (
        <div className="flex justify-center rounded-xl border border-dashed border-border bg-muted/20 py-6">
          <ThermalReceiptPreview receipt={receipt} width="80mm" className="p-3 shadow-md" />
        </div>
      )}

      {showActions && (
        <div className="space-y-3">
          {showInvoiceActions && (
            <div className="space-y-2">
              {mode === "both" && (
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  A4 Invoice
                </p>
              )}
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <Button
                  variant="default"
                  className="gap-2"
                  disabled={printing}
                  onClick={handlePrintInvoice}
                >
                  {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Printer className="h-4 w-4" />}
                  Print Invoice (A4)
                </Button>
                <Button
                  variant="secondary"
                  className="gap-2"
                  onClick={handleDownloadInvoicePdf}
                  disabled={downloading}
                >
                  {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  Download PDF
                </Button>
                {mode === "invoice" && (
                  <Button variant="secondary" className="gap-2" onClick={handleEmail}>
                    <Mail className="h-4 w-4" />
                    Email
                  </Button>
                )}
              </div>
            </div>
          )}

          {showReceiptActions && (
            <div className="space-y-2">
              {mode === "both" && (
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Thermal Receipt
                </p>
              )}
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <Button
                  variant="default"
                  className="gap-2"
                  disabled={printing}
                  onClick={() => handlePrint(printThermalReceipt80)}
                >
                  {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Printer className="h-4 w-4" />}
                  Print 80mm
                </Button>
                <Button
                  variant="secondary"
                  className="gap-2"
                  disabled={printing}
                  onClick={() => handlePrint(printThermalReceipt58)}
                >
                  Print 58mm
                </Button>
                {mode === "receipt" && (
                  <Button variant="secondary" className="gap-2" onClick={handleEmail}>
                    <Mail className="h-4 w-4" />
                    Email
                  </Button>
                )}
              </div>
            </div>
          )}

          {mode === "both" && (
            <Button variant="secondary" className="w-full gap-2" onClick={handleEmail}>
              <Mail className="h-4 w-4" />
              Email
            </Button>
          )}

          {onNewSale && (
            <Button className="w-full gap-2" onClick={onNewSale}>
              <Plus className="h-4 w-4" />
              Done · New Sale
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

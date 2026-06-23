import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PosReceipt } from "@/services/api/pos";
import {
  PosReceiptView,
  type DocumentPreviewMode,
} from "@/modules/pos/components/PosReceiptView";
import { cn } from "@/utils/cn";

export interface SalesDocumentPreviewState {
  receipt: PosReceipt;
  mode: DocumentPreviewMode;
}

interface SalesReceiptDialogProps {
  preview: SalesDocumentPreviewState | null;
  onClose: () => void;
}

const TITLES: Record<Exclude<DocumentPreviewMode, "both">, string> = {
  invoice: "Tax Invoice (A4)",
  receipt: "Thermal Receipt",
};

export function SalesReceiptDialog({ preview, onClose }: SalesReceiptDialogProps) {
  if (!preview || preview.mode === "both") return null;

  const { receipt, mode } = preview;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div
        className={cn(
          "flex max-h-[92vh] w-full flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-2xl",
          mode === "invoice" ? "max-w-3xl" : "max-w-md"
        )}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-lg font-bold">{TITLES[mode]}</h2>
            <p className="text-sm text-muted-foreground font-mono">{receipt.invoice_number}</p>
          </div>
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
          <PosReceiptView receipt={receipt} showActions mode={mode} onNewSale={onClose} />
        </div>
      </div>
    </div>
  );
}

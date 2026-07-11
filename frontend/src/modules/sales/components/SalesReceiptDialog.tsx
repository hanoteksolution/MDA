import { X, CircleCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PosReceipt } from "@/services/api/pos";
import type { SaleDocStatus } from "@/services/api/sales";
import {
  PosReceiptView,
  type DocumentPreviewMode,
} from "@/modules/pos/components/PosReceiptView";
import { cn, formatCurrency } from "@/utils/cn";

export interface SalesDocumentPreviewState {
  receipt: PosReceipt;
  mode: DocumentPreviewMode;
  invoiceId: string;
  status: SaleDocStatus;
}

interface SalesReceiptDialogProps {
  preview: SalesDocumentPreviewState | null;
  onClose: () => void;
  onMarkPaid?: (invoiceId: string) => Promise<void>;
  markingPaid?: boolean;
}

const TITLES: Record<Exclude<DocumentPreviewMode, "both">, string> = {
  invoice: "Tax Invoice (A4)",
  receipt: "Thermal Receipt",
};

function canMarkPaid(status: SaleDocStatus) {
  return status !== "paid" && status !== "cancelled";
}

export function SalesReceiptDialog({
  preview,
  onClose,
  onMarkPaid,
  markingPaid,
}: SalesReceiptDialogProps) {
  if (!preview || preview.mode === "both") return null;

  const { receipt, mode, invoiceId, status } = preview;
  const showMarkPaid = onMarkPaid && canMarkPaid(status);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div
        className={cn(
          "flex max-h-[92vh] w-full flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-2xl",
          mode === "invoice" ? "max-w-3xl" : "max-w-md"
        )}
      >
        <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-lg font-bold">{TITLES[mode]}</h2>
            <p className="text-sm text-muted-foreground font-mono">{receipt.invoice_number}</p>
            {status !== "paid" && (
              <p className="mt-0.5 text-xs font-medium text-amber-600 capitalize">
                Unpaid · {formatCurrency(receipt.total_amount)} due
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {showMarkPaid && (
              <Button
                size="sm"
                className="gap-1.5 rounded-xl"
                disabled={markingPaid}
                onClick={() => onMarkPaid(invoiceId)}
              >
                {markingPaid ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CircleCheck className="h-4 w-4" />
                )}
                Mark paid
              </Button>
            )}
            <Button variant="ghost" size="sm" className="h-9 w-9 p-0" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
          <PosReceiptView receipt={receipt} showActions mode={mode} onNewSale={onClose} />
        </div>
      </div>
    </div>
  );
}

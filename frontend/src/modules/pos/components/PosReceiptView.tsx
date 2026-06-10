import { useState } from "react";
import {
  Download,
  Mail,
  Printer,
  Loader2,
  Plus,
} from "lucide-react";
import type { PosReceipt } from "@/services/api/pos";
import { Button } from "@/components/ui/button";
import { DigitalReceipt } from "../receipt/DigitalReceipt";
import { downloadReceiptPdf } from "../receipt/downloadReceiptPdf";
import { printThermalReceipt58, printThermalReceipt80 } from "../receipt/printReceipt";

interface PosReceiptViewProps {
  receipt: PosReceipt;
  onPrint?: () => void;
  onNewSale?: () => void;
  compact?: boolean;
  showActions?: boolean;
}

export function PosReceiptView({
  receipt,
  onPrint,
  onNewSale,
  compact,
  showActions = true,
}: PosReceiptViewProps) {
  const [printing, setPrinting] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handlePrint = async (fn: (r: PosReceipt) => Promise<void>) => {
    setPrinting(true);
    try {
      await fn(receipt);
      onPrint?.();
    } finally {
      setPrinting(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadReceiptPdf(receipt);
    } finally {
      setDownloading(false);
    }
  };

  const handleEmail = () => {
    const subject = encodeURIComponent(`Receipt ${receipt.invoice_number}`);
    const body = encodeURIComponent(
      `Thank you for your purchase.\n\nReceipt: ${receipt.invoice_number}\nTotal: ${receipt.total_amount}\n\n— ${receipt.company.name}`
    );
    window.open(`mailto:?subject=${subject}&body=${body}`, "_blank");
  };

  return (
    <div className={compact ? "space-y-4" : "space-y-6"}>
      <DigitalReceipt receipt={receipt} className={compact ? "shadow-md" : undefined} />

      {showActions && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Button
              variant="secondary"
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
            <Button variant="secondary" className="gap-2" onClick={handleEmail}>
              <Mail className="h-4 w-4" />
              Email
            </Button>
            <Button
              variant="secondary"
              className="gap-2"
              onClick={handleDownload}
              disabled={downloading}
            >
              {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              PDF
            </Button>
          </div>
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

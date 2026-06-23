import { useEffect, useState } from "react";
import type { PosReceipt } from "@/services/api/pos";
import type { DocumentType } from "../types";
import { documentFromReceipt } from "../presets";
import { renderEnterpriseDocument } from "../layout";
import { SALES_DOCUMENT_CSS } from "../styles";
import { generateQrDataUrl } from "@/modules/pos/receipt/receiptAssets";
import { getVerificationUrl } from "@/modules/pos/receipt/receiptFormat";

interface SalesDocumentPreviewProps {
  receipt: PosReceipt;
  type?: DocumentType;
  className?: string;
}

export function SalesDocumentPreview({
  receipt,
  type = "tax_invoice",
  className,
}: SalesDocumentPreviewProps) {
  const [html, setHtml] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const qr = await generateQrDataUrl(getVerificationUrl(receipt), 160);
      if (cancelled) return;
      const doc = documentFromReceipt(receipt, type, { qr });
      const body = renderEnterpriseDocument(doc);
      setHtml(`<style>${SALES_DOCUMENT_CSS}</style>${body}`);
    })();
    return () => {
      cancelled = true;
    };
  }, [receipt, type]);

  if (!html) {
    return (
      <div className={`flex min-h-[480px] items-center justify-center rounded-xl border border-border bg-white ${className ?? ""}`}>
        <p className="text-sm text-muted-foreground">Loading preview…</p>
      </div>
    );
  }

  return (
    <div
      className={`overflow-auto rounded-xl border border-border bg-white shadow-sm ${className ?? ""}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

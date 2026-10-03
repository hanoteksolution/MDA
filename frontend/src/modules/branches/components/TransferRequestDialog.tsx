import { useEffect, useState } from "react";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
import { Input } from "@/components/ui/input";
import { appDialog } from "@/components/feedback/AppDialog";
import { branchOpsApi } from "@/services/api/branchOps";

export interface TransferDraft {
  productId: string;
  productName: string;
  sourceBranchId: string;
  sourceBranchName: string;
  destinationBranchId: string;
  destinationBranchName: string;
  quantity: number;
}

/**
 * Ask another branch for stock through the existing transfer workflow. Nothing moves until the
 * source branch approves, reserves and dispatches; the destination then receives.
 */
export function TransferRequestDialog({ draft, onClose, onCreated }: {
  draft: TransferDraft | null;
  onClose: () => void;
  onCreated?: (requestNumber: string) => void;
}) {
  const [quantity, setQuantity] = useState("1");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setQuantity(String(draft?.quantity || 1));
    setNotes("");
  }, [draft]);
  const qty = Number(quantity);
  const valid = Boolean(draft) && Number.isFinite(qty) && qty > 0;

  const submit = async () => {
    if (!draft || !valid) return;
    setBusy(true);
    try {
      const r = await branchOpsApi.requestTransfer({
        source_branch_id: draft.sourceBranchId,
        destination_branch_id: draft.destinationBranchId,
        lines: [{ product_id: draft.productId, quantity: String(qty) }],
        notes,
      });
      onClose();
      onCreated?.(r.data.request_number);
      await appDialog.alert(`${r.data.request_number} sent to ${draft.sourceBranchName} for approval.`, { title: "Transfer requested", tone: "success" });
    } catch (e) {
      await appDialog.alert(e instanceof Error ? e.message : "Could not request the transfer.", { title: "Request failed", tone: "danger" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <PlatformConfirmDialog
      open={Boolean(draft)}
      tone="default"
      title="Request branch transfer"
      description={draft ? `${draft.productName}: from ${draft.sourceBranchName} to ${draft.destinationBranchName}. ${draft.sourceBranchName} must approve before any stock moves.` : ""}
      confirmLabel="Send request"
      loading={busy}
      confirmDisabled={!valid}
      onConfirm={() => void submit()}
      onCancel={onClose}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="space-y-1 text-sm">
          <span className="font-medium">Quantity</span>
          <Input type="number" min="0" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </label>
        <label className="space-y-1 text-sm sm:col-span-2">
          <span className="font-medium">Note for {draft?.sourceBranchName ?? "the source branch"}</span>
          <Input value={notes} maxLength={250} placeholder="e.g. Customer waiting at the counter" onChange={(e) => setNotes(e.target.value)} />
        </label>
      </div>
    </PlatformConfirmDialog>
  );
}

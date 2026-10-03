import { useState } from "react";
import { Button } from "@/components/ui/button";
import { inventoryApi } from "@/services/api/catalog";
import type { ProductAvailability } from "@/types/models/catalog";
import { CrossBranchPanel } from "@/modules/branches/components/CrossBranchPanel";
import { TransferRequestDialog, type TransferDraft } from "@/modules/branches/components/TransferRequestDialog";

/**
 * Branch Phase 3 cross-branch stock visibility (BRANCH_INVENTORY.md §7), extended with the
 * per-branch breakdown and a "Request transfer" hand-off to the existing transfer workflow.
 * Fetches on demand. Never a mutation of another branch's stock: a request moves nothing until
 * the source branch approves it.
 */
export function CrossBranchAvailability({ productId, requested = 0, compact = false }: {
  productId: string;
  requested?: number;
  compact?: boolean;
}) {
  const [data, setData] = useState<ProductAvailability | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<TransferDraft | null>(null);

  async function load(force = false) {
    if ((data && !force) || loading) {
      setOpen((v) => !v);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await inventoryApi.productAvailability(productId);
      setData(response.data);
      setOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not check other branches.");
      setOpen(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="inline-flex max-w-full flex-col items-start gap-1">
      <Button size="sm" variant="ghost" onClick={() => void load()} disabled={loading}>
        {loading ? "Checking…" : open ? "Hide other branches" : "Check other branches"}
      </Button>
      {open && error && <span className="text-xs text-destructive">{error}</span>}
      {open && data && (
        <div className={compact ? "w-full" : "w-full min-w-[320px] max-w-2xl"}>
          <CrossBranchPanel
            data={data}
            requested={requested}
            onRequestTransfer={(sourceId, sourceName, suggested) =>
              setDraft({
                productId: data.product_id,
                productName: data.product_name,
                sourceBranchId: sourceId,
                sourceBranchName: sourceName,
                destinationBranchId: data.current_branch.branch_id,
                destinationBranchName: data.current_branch.branch_name,
                quantity: suggested,
              })
            }
          />
        </div>
      )}
      <TransferRequestDialog draft={draft} onClose={() => setDraft(null)} onCreated={() => void load(true)} />
    </div>
  );
}

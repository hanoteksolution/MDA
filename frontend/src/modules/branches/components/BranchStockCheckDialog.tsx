import { useEffect, useState } from "react";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
import { inventoryApi } from "@/services/api/catalog";
import type { ProductAvailability } from "@/types/models/catalog";
import { CrossBranchPanel } from "./CrossBranchPanel";
import { TransferRequestDialog, type TransferDraft } from "./TransferRequestDialog";

/** POS / product lookup: where else is this product? Visibility plus a transfer request — never a sale. */
export function BranchStockCheckDialog({ product, requested = 0, onClose }: {
  product: { id: string; name: string } | null;
  requested?: number;
  onClose: () => void;
}) {
  const [data, setData] = useState<ProductAvailability | null>(null);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<TransferDraft | null>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    if (!product) return;
    let active = true;
    setData(null);
    setError("");
    inventoryApi
      .productAvailability(product.id)
      .then((r) => active && setData(r.data))
      .catch((e: unknown) => active && setError(e instanceof Error ? e.message : "Could not check other branches."));
    return () => {
      active = false;
    };
  }, [product, reload]);

  return (
    <>
      <PlatformConfirmDialog
        open={Boolean(product) && !draft}
        wide
        tone="default"
        title={`${product?.name ?? "Product"} — other branches`}
        description="Stock you can see in other branches. You cannot sell it from here; request a transfer and the other branch approves it."
        confirmLabel="Done"
        onConfirm={onClose}
        onCancel={onClose}
      >
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!data && !error && <p className="text-sm text-muted-foreground">Checking branches…</p>}
        {data && (
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
        )}
      </PlatformConfirmDialog>
      <TransferRequestDialog draft={draft} onClose={() => setDraft(null)} onCreated={() => setReload((v) => v + 1)} />
    </>
  );
}

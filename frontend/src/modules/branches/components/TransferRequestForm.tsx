import { useEffect, useState } from "react";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { branchOpsApi, type CrossBranchSearchResult } from "@/services/api/branchOps";
import { ALL_BRANCHES } from "@/services/api/branchContext";
import { useBranchStore } from "@/store/branchStore";
import { activeBranchLabel } from "@/components/branch/BranchSwitcher";
import { TransferRequestDialog, type TransferDraft } from "./TransferRequestDialog";
import { num, qtyText } from "../lib";

/**
 * "Request stock for this branch": search the catalog, see which branches hold it, pick the
 * source. The active branch is the destination, so a single branch must be selected.
 */
export function TransferRequestForm({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated?: () => void }) {
  const { activeBranchId, branches } = useBranchStore();
  const [term, setTerm] = useState("");
  const [result, setResult] = useState<CrossBranchSearchResult | null>(null);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<TransferDraft | null>(null);
  const single = Boolean(activeBranchId && activeBranchId !== ALL_BRANCHES);

  useEffect(() => {
    if (!open) {
      setTerm("");
      setResult(null);
      setError("");
    }
  }, [open]);
  useEffect(() => {
    if (!open || !single || term.trim().length < 2) return;
    const t = setTimeout(() => {
      branchOpsApi.crossBranchSearch(term.trim())
        .then((r) => { setResult(r.data); setError(""); })
        .catch((e: unknown) => setError(e instanceof Error ? e.message : "Search failed."));
    }, 300);
    return () => clearTimeout(t);
  }, [term, open, single]);

  return (
    <>
      <PlatformConfirmDialog
        open={open && !draft} wide tone="default"
        title={`Request stock for ${activeBranchLabel(activeBranchId, branches)}`}
        description="Find the product, then choose the branch to request it from. That branch approves before anything moves."
        confirmLabel="Close" onConfirm={onClose} onCancel={onClose}
      >
        {!single ? (
          <p className="rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-sm">Select a single branch in the header first — it will receive the stock.</p>
        ) : (
          <div className="space-y-3 text-sm">
            <Input autoFocus placeholder="Search product name, SKU or barcode…" value={term} onChange={(e) => setTerm(e.target.value)} aria-label="Search products" />
            {error && <p className="text-destructive">{error}</p>}
            {result && !result.can_view_other_branches && <p className="text-muted-foreground">Your role here cannot see other branches' stock.</p>}
            {result?.results.length === 0 && <p className="text-muted-foreground">No products match.</p>}
            <ul className="space-y-2">
              {result?.results.map((p) => (
                <li key={p.product_id} className="rounded-xl border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{p.product_name} <span className="text-xs text-muted-foreground">{p.product_sku}</span></span>
                    <Badge variant={num(p.current_branch.available) > 0 ? "success" : "destructive"}>Here: {qtyText(p.current_branch.available)}</Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {p.other_branches.filter((b) => num(b.available) > 0).map((b) => (
                      <button key={b.branch_id} type="button" className="rounded-lg border px-2.5 py-1 text-xs hover:bg-muted"
                        onClick={() => setDraft({ productId: p.product_id, productName: p.product_name, sourceBranchId: b.branch_id,
                          sourceBranchName: b.branch_name, destinationBranchId: p.current_branch.branch_id,
                          destinationBranchName: p.current_branch.branch_name, quantity: 1 })}>
                        Request from {b.branch_name} ({qtyText(b.available)} available)
                      </button>
                    ))}
                    {result.can_view_other_branches && !p.other_branches.some((b) => num(b.available) > 0) && (
                      <span className="text-xs text-muted-foreground">No other branch has stock.</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </PlatformConfirmDialog>
      <TransferRequestDialog draft={draft} onClose={() => setDraft(null)} onCreated={() => { onCreated?.(); onClose(); }} />
    </>
  );
}
